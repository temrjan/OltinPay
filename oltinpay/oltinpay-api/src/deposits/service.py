"""User deposit-intent service.

DEMO on-ramp: returns static bank requisites plus a per-user reference. The
actual UZD mint happens when the bank later calls POST /api/v1/bank/deposits
with the matching bankTxId. No DB row and no on-chain effect here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.deposits.schemas import (
    DepositIntentResponse,
    DepositRequisites,
)

if TYPE_CHECKING:
    from src.users.models import User

# Demo requisites — replaced by a real bank integration in production.
_DEMO_BANK_NAME = "OltinPay Demo Bank"
_DEMO_ACCOUNT_NUMBER = "20208000900000000001"
_DEMO_MFO = "00014"


def create_intent(user: User, amount_uzs: int) -> DepositIntentResponse:
    """Build demo deposit requisites for the user."""
    reference = f"OLTIN-{user.oltin_id}-{amount_uzs}"
    return DepositIntentResponse(
        amount_uzs=amount_uzs,
        requisites=DepositRequisites(
            bank_name=_DEMO_BANK_NAME,
            account_number=_DEMO_ACCOUNT_NUMBER,
            mfo=_DEMO_MFO,
            reference=reference,
        ),
        note=(
            "DEMO: transfer the amount to these requisites with the reference. "
            "The bank confirms via POST /api/v1/bank/deposits, which mints UZD."
        ),
    )
