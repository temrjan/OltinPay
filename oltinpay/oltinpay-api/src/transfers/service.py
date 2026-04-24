"""Transfer service layer."""

import asyncio
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.balances.db import get_balance
from src.balances.models import AccountType, Currency
from src.common.exceptions import (
    BadRequestException,
    InsufficientBalanceException,
    NotFoundException,
)
from src.notifications import notify_transfer_received
from src.transfers.models import Transfer, TransferStatus
from src.transfers.schemas import TransferListResponse
from src.users import service as user_service
from src.users.models import User

# Fee constants
TRANSFER_FEE_RATE = Decimal("0.01")  # 1%
MIN_FEE_USD = Decimal("0.05")
OLTIN_PRICE_USD = Decimal("100")  # Fixed demo price

# Strong refs to fire-and-forget notification tasks. Without retaining
# references, asyncio may GC the task before it completes, dropping the
# notification silently. See asyncio.create_task in the stdlib docs.
_background_tasks: set[asyncio.Task[object]] = set()


def calculate_fee(amount: Decimal) -> Decimal:
    """Calculate transfer fee.

    Fee: 1% of amount, minimum 0.05 USD equivalent.
    """
    fee = amount * TRANSFER_FEE_RATE
    min_fee_oltin = MIN_FEE_USD / OLTIN_PRICE_USD

    return max(fee, min_fee_oltin)


async def create_transfer(
    db: AsyncSession,
    from_user: User,
    to_oltin_id: str,
    amount: Decimal,
) -> Transfer:
    """Create transfer between users.

    1. Find recipient by oltin_id
    2. Check sender has enough balance
    3. Deduct from sender wallet
    4. Add to recipient wallet (minus fee)
    5. Create transfer record
    6. Send notification to recipient
    """
    # Cannot transfer to self
    to_oltin_id_normalized = to_oltin_id.lower().strip()
    if to_oltin_id_normalized.startswith("@"):
        to_oltin_id_normalized = to_oltin_id_normalized[1:]

    if to_oltin_id_normalized == from_user.oltin_id:
        raise BadRequestException("Cannot transfer to yourself")

    # Find recipient
    to_user = await user_service.get_user_by_oltin_id(db, to_oltin_id)
    if not to_user:
        raise NotFoundException(f"User @{to_oltin_id} not found")

    # Calculate fee
    fee = calculate_fee(amount)
    net_amount = amount - fee

    # Check sender balance
    sender_balance = await get_balance(
        db, from_user.id, AccountType.WALLET, Currency.OLTIN
    )
    if not sender_balance or sender_balance.amount < amount:
        raise InsufficientBalanceException("Insufficient OLTIN in wallet")

    # Get recipient balance
    recipient_balance = await get_balance(
        db, to_user.id, AccountType.WALLET, Currency.OLTIN
    )
    if not recipient_balance:
        raise BadRequestException("Recipient wallet not found")

    # Perform transfer
    sender_balance.amount -= amount
    recipient_balance.amount += net_amount

    # Create transfer record
    transfer = Transfer(
        from_user_id=from_user.id,
        to_user_id=to_user.id,
        amount=amount,
        fee=fee,
        status=TransferStatus.PENDING,
    )
    db.add(transfer)

    await db.flush()
    await db.refresh(transfer)

    # Send notification to recipient (fire and forget)
    task = asyncio.create_task(
        notify_transfer_received(
            recipient_telegram_id=to_user.telegram_id,
            sender_oltin_id=from_user.oltin_id,
            amount=str(net_amount),
            language=to_user.language or "en",
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return transfer


async def get_transfer_by_id(
    db: AsyncSession,
    transfer_id: UUID,
    user_id: UUID,
) -> Transfer | None:
    """Get transfer by ID (only if user is sender or recipient)."""
    result = await db.execute(
        select(Transfer).where(
            Transfer.id == transfer_id,
            or_(
                Transfer.from_user_id == user_id,
                Transfer.to_user_id == user_id,
            ),
        )
    )
    return result.scalar_one_or_none()


async def get_user_transfers(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[Transfer]:
    """Get user transfers (sent and received)."""
    result = await db.execute(
        select(Transfer)
        .where(
            or_(
                Transfer.from_user_id == user_id,
                Transfer.to_user_id == user_id,
            )
        )
        .order_by(Transfer.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


def format_transfer_list_item(
    transfer: Transfer,
    user_id: UUID,
) -> TransferListResponse:
    """Format transfer for list response."""
    is_sender = transfer.from_user_id == user_id

    return TransferListResponse(
        id=transfer.id,
        direction="sent" if is_sender else "received",
        counterparty=transfer.to_user.oltin_id
        if is_sender
        else transfer.from_user.oltin_id,
        amount=transfer.amount if is_sender else (transfer.amount - transfer.fee),
        fee=transfer.fee if is_sender else Decimal("0"),
        status=transfer.status,
        created_at=transfer.created_at,
    )
