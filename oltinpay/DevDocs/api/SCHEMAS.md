# OltinPay API Schemas

> Pydantic модели для запросов и ответов

---

## Auth

```python
class TelegramAuthRequest(BaseModel):
    init_data: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str
```

---

## Users

```python
class UserResponse(BaseModel):
    id: UUID
    telegram_id: int
    telegram_username: str | None
    oltin_id: str | None
    wallet_address: str
    language: str
    created_at: datetime

class SetOltinIdRequest(BaseModel):
    oltin_id: str = Field(
        min_length=3,
        max_length=32,
        pattern=r'^[a-z0-9_]+$'
    )

class UserSearchResponse(BaseModel):
    users: list[UserSearchItem]

class UserSearchItem(BaseModel):
    oltin_id: str
    telegram_username: str | None

class SetLanguageRequest(BaseModel):
    language: Literal["uz", "ru"]
```

---

## Wallet

```python
class AccountBalance(BaseModel):
    usd: Decimal
    oltin: Decimal

class StakingBalance(BaseModel):
    oltin: Decimal
    locked_until: datetime | None

class BalanceResponse(BaseModel):
    total_usd: Decimal
    accounts: dict[str, AccountBalance | StakingBalance]
    price_per_oltin: Decimal

class TransferRequest(BaseModel):
    to_oltin_id: str
    amount: Decimal = Field(gt=0)
    note: str | None = None

class TransferResponse(BaseModel):
    transaction_id: UUID
    tx_hash: str
    from_oltin_id: str = Field(alias="from")
    to_oltin_id: str = Field(alias="to")
    amount: Decimal
    fee: Decimal
    received: Decimal
    status: Literal["pending", "completed", "failed"]
    created_at: datetime

class InternalTransferRequest(BaseModel):
    from_account: Literal["wallet", "exchange", "staking"]
    to_account: Literal["wallet", "exchange", "staking"]
    asset: Literal["USD", "OLTIN"]
    amount: Decimal = Field(gt=0)

class Transaction(BaseModel):
    id: UUID
    type: Literal[
        "transfer_in", "transfer_out",
        "internal", "trade",
        "staking_reward", "staking_deposit", "staking_withdraw"
    ]
    asset: Literal["USD", "OLTIN"]
    amount: Decimal
    fee: Decimal
    counterparty: str | None
    tx_hash: str | None
    status: Literal["pending", "completed", "failed"]
    created_at: datetime

class TransactionsResponse(BaseModel):
    transactions: list[Transaction]
    total: int
    limit: int
    offset: int

class Contact(BaseModel):
    oltin_id: str
    last_transfer: datetime | None = None
    added_at: datetime | None = None

class ContactsResponse(BaseModel):
    recent: list[Contact]
    favorites: list[Contact]

class AddFavoriteRequest(BaseModel):
    oltin_id: str
```

---

## Exchange

```python
class PriceResponse(BaseModel):
    bid: Decimal
    ask: Decimal
    mid: Decimal
    spread: Decimal
    change_24h: str
    volume_24h: Decimal
    updated_at: datetime

class OrderbookLevel(BaseModel):
    price: Decimal
    quantity: Decimal
    total: Decimal

class OrderbookResponse(BaseModel):
    bids: list[OrderbookLevel]
    asks: list[OrderbookLevel]
    spread: Decimal
    updated_at: datetime

class CreateOrderRequest(BaseModel):
    side: Literal["buy", "sell"]
    type: Literal["market", "limit"]
    price: Decimal | None = None  # Required for limit
    quantity: Decimal | None = None  # For limit orders
    amount_usd: Decimal | None = None  # For market buy

    @model_validator(mode="after")
    def validate_order(self):
        if self.type == "limit" and (self.price is None or self.quantity is None):
            raise ValueError("Limit orders require price and quantity")
        if self.type == "market" and self.side == "buy" and self.amount_usd is None:
            raise ValueError("Market buy requires amount_usd")
        return self

class OrderResponse(BaseModel):
    order_id: UUID
    side: Literal["buy", "sell"]
    type: Literal["market", "limit"]
    price: Decimal | None
    quantity: Decimal | None
    filled_quantity: Decimal
    average_price: Decimal | None
    status: Literal["open", "partial", "filled", "cancelled"]
    fee: Decimal
    created_at: datetime

class OrdersResponse(BaseModel):
    orders: list[OrderResponse]

class Trade(BaseModel):
    trade_id: UUID
    side: Literal["buy", "sell"]
    price: Decimal
    quantity: Decimal
    total: Decimal
    fee: Decimal
    created_at: datetime

class TradesResponse(BaseModel):
    trades: list[Trade]
```

---

## Staking

```python
class StakingBalanceResponse(BaseModel):
    staked: Decimal
    pending_rewards: Decimal
    total_earned: Decimal
    apy: Decimal
    locked_until: datetime | None
    is_locked: bool
    days_remaining: int

class StakingDepositRequest(BaseModel):
    amount: Decimal = Field(gt=0)

class StakingDepositResponse(BaseModel):
    transaction_id: UUID
    amount: Decimal
    new_staked: Decimal
    locked_until: datetime
    estimated_daily_reward: Decimal

class StakingWithdrawRequest(BaseModel):
    amount: Decimal = Field(gt=0)

class StakingWithdrawResponse(BaseModel):
    transaction_id: UUID
    amount: Decimal
    new_staked: Decimal

class StakingReward(BaseModel):
    date: date
    staked: Decimal
    reward: Decimal
    apy: Decimal

class StakingRewardsResponse(BaseModel):
    rewards: list[StakingReward]
    total_earned: Decimal
```

---

## Assistant

```python
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: UUID | None = None

class ChatResponse(BaseModel):
    response: str
    session_id: UUID
```

---

## Errors

```python
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict | None = None

class ValidationErrorResponse(BaseModel):
    error: str = "validation_error"
    message: str = "Request validation failed"
    details: list[ValidationErrorItem]

class ValidationErrorItem(BaseModel):
    field: str
    message: str
```

---

## WebSocket Events

```python
class WSPriceEvent(BaseModel):
    event: Literal["price"] = "price"
    data: PriceResponse

class WSOrderbookEvent(BaseModel):
    event: Literal["orderbook"] = "orderbook"
    data: OrderbookResponse

class WSTradeEvent(BaseModel):
    event: Literal["trade"] = "trade"
    data: OrderResponse

class WSTransferEvent(BaseModel):
    event: Literal["transfer"] = "transfer"
    data: TransferNotification

class TransferNotification(BaseModel):
    from_oltin_id: str = Field(alias="from")
    amount: Decimal
    tx_hash: str
```

---

*Schemas v1.0 — OltinPay*
