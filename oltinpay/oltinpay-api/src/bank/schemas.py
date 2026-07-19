"""Bank connector schemas.

Bank-facing bodies use camelCase (``auditRef``, ``bankTxId``, ``uzsPerUsd``,
``txHash``) — the external bank API convention — via a camel alias generator.
``populate_by_name`` keeps snake_case acceptable too.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — runtime type for Pydantic field
from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003 — runtime type for Pydantic field

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from src.withdrawals.models import Withdrawal

_CAMEL = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# --------------------------------------------------------------------------- #
# attestations                                                                #
# --------------------------------------------------------------------------- #
class AttestationRequest(BaseModel):
    model_config = _CAMEL

    grams: int = Field(ge=0, lt=2**63, description="Attested gold reserve (feed units)")
    audit_ref: str = Field(min_length=1, max_length=128)


class AttestationResponse(BaseModel):
    model_config = _CAMEL

    id: UUID
    grams: int
    audit_ref: str
    tx_hash: str
    created_at: datetime


class LatestAttestationResponse(BaseModel):
    model_config = _CAMEL

    # Latest DB attestation (may be null if none posted yet).
    latest: AttestationResponse | None
    # Live on-chain reading from ReserveAttestor.latestRoundData().
    onchain_answer: str
    onchain_updated_at: int
    onchain_round_id: int


# --------------------------------------------------------------------------- #
# fx                                                                          #
# --------------------------------------------------------------------------- #
class FxRequest(BaseModel):
    model_config = _CAMEL

    uzs_per_usd: float | None = Field(default=None, gt=0)
    usd_per_uzs: float | None = Field(default=None, gt=0)
    source: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _exactly_one_rate(self) -> FxRequest:
        provided = [self.uzs_per_usd is not None, self.usd_per_uzs is not None]
        if sum(provided) != 1:
            raise ValueError("provide exactly one of uzsPerUsd or usdPerUzs")
        return self


class FxResponse(BaseModel):
    model_config = _CAMEL

    answer: str  # USD per UZS scaled to 8 decimals (the posted int256)
    decimals: int
    source: str
    tx_hash: str


# --------------------------------------------------------------------------- #
# deposits                                                                    #
# --------------------------------------------------------------------------- #
class DepositRequest(BaseModel):
    model_config = _CAMEL

    user_id: UUID | None = None
    oltin_id: str | None = None
    amount_uzs: int = Field(gt=0, lt=2**63)
    bank_tx_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def _exactly_one_subject(self) -> DepositRequest:
        provided = [self.user_id is not None, self.oltin_id is not None]
        if sum(provided) != 1:
            raise ValueError("provide exactly one of userId or oltinId")
        return self


class DepositResponse(BaseModel):
    model_config = _CAMEL

    id: UUID
    user_id: UUID
    bank_tx_id: str
    amount_uzs: int
    amount_wei: str
    tx_hash: str
    created_at: datetime


# --------------------------------------------------------------------------- #
# withdrawals (bank view)                                                     #
# --------------------------------------------------------------------------- #
class BankWithdrawalResponse(BaseModel):
    """A withdrawal as the bank sees it — includes the user's wallet/oltinId."""

    model_config = _CAMEL

    id: UUID
    user_id: UUID
    oltin_id: str
    wallet_address: str | None
    amount_uzd: int
    amount_wei: str
    status: str
    tx_hash: str | None
    created_at: datetime
    confirmed_at: datetime | None

    @classmethod
    def from_withdrawal(cls, withdrawal: Withdrawal) -> BankWithdrawalResponse:
        """Build from a Withdrawal with its ``user`` relationship loaded."""
        return cls(
            id=withdrawal.id,
            user_id=withdrawal.user_id,
            oltin_id=withdrawal.user.oltin_id,
            wallet_address=withdrawal.user.wallet_address,
            amount_uzd=withdrawal.amount_uzd,
            amount_wei=withdrawal.amount_wei,
            status=withdrawal.status,
            tx_hash=withdrawal.tx_hash,
            created_at=withdrawal.created_at,
            confirmed_at=withdrawal.confirmed_at,
        )
