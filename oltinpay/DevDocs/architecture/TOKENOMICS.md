# OltinPay — Tokenomics

> **Version:** 1.0 | **Date:** 2026-01-25

## Token Overview

| Parameter | Value |
|-----------|-------|
| Name | OltinToken |
| Symbol | OLTIN |
| Decimals | 18 |
| Total Supply | 1,000,000 OLTIN |
| Type | Fixed (no mint/burn in Demo) |
| Value | 1 OLTIN = 1 gram gold |

---

## Supply Distribution

```
Total: 1,000,000 OLTIN (100%)

┌────────────────────────────────────────┐
│  TREASURY      │  200,000  │   20%    │
│  ──────────────────────────────────    │
│  Staking rewards                       │
│  Referral bonuses                      │
│  Promotions                            │
├────────────────────────────────────────┤
│  LIQUIDITY     │  500,000  │   50%    │
│  ──────────────────────────────────    │
│  Exchange orderbook                    │
│  Market maker bots                     │
│  User trading                          │
├────────────────────────────────────────┤
│  RESERVE       │  300,000  │   30%    │
│  ──────────────────────────────────    │
│  Future development                    │
│  Partnerships                          │
│  Team allocation                       │
└────────────────────────────────────────┘
```

---

## Fee Structure

### Transfer Fee (User → User)

```
Rate:        1%
Minimum:     0.05 USD equivalent
Destination: Treasury Pool

Example (price 100 USD/OLTIN):
Send:    10 OLTIN
Fee:     0.1 OLTIN (1%)
Receive: 9.9 OLTIN
```

### Trading Fee (Exchange)

```
Rate:        0.1% per trade
Applies to:  Both buyer and seller
Destination: Treasury Pool

Example:
Trade:      10 OLTIN @ 100 USD
Buyer fee:  0.01 OLTIN
Seller fee: 0.1 USD
```

### Internal Transfer Fee

```
Rate: 0% (free)
Wallet ↔ Exchange ↔ Staking
```

---

## Staking Economics

### Parameters

```
APY:           7% (fixed)
Lock period:   7 days
Rewards:       Daily at 07:00 UTC+5
Source:        Treasury Pool
```

### Daily Reward Formula

```
daily_reward = staked_balance × (APY / 365)
daily_reward = staked_balance × (0.07 / 365)
daily_reward = staked_balance × 0.00019178
```

### Examples

| Staked | Daily | Monthly | Yearly |
|--------|-------|---------|--------|
| 1 OLTIN | 0.00019 | 0.0058 | 0.07 |
| 10 OLTIN | 0.0019 | 0.058 | 0.7 |
| 100 OLTIN | 0.019 | 0.58 | 7.0 |
| 1,000 OLTIN | 0.19 | 5.8 | 70.0 |

### Treasury Sustainability

```
Scenario: 100,000 OLTIN staked (10% of supply)
Annual rewards: 7,000 OLTIN
Treasury: 200,000 OLTIN
Runway: 200,000 / 7,000 = 28.5 years

Fee income (estimated):
- 1,000 transfers/month × 0.1 OLTIN avg fee = 100 OLTIN/month
- 10,000 trades/month × 0.01 OLTIN avg fee = 100 OLTIN/month
- Total: ~200 OLTIN/month replenishment
```

---

## Price Discovery

### Phase 1: Fixed Price (Demo)

```
1 OLTIN = 100 USD (hardcoded)
Used for: Balance display, fee calculation
```

### Phase 2: Market Price (Exchange)

```
Price = (Best Bid + Best Ask) / 2

Orderbook:
SELL: 101, 102, 103...
      ↑ Best Ask = 101
      ↓ Best Bid = 99
BUY:  99, 98, 97...

Mid Price = (101 + 99) / 2 = 100 USD
```

---

## Token Flow Diagrams

### Staking Flow

```
User Wallet OLTIN
       │
       │ deposit
       ▼
User Staking Balance ←──── Treasury Pool
       │                   (daily rewards)
       │ withdraw (after 7 days)
       ▼
User Wallet OLTIN
```

### Trading Flow

```
Buyer USD ────────────► Seller USD
    │                       ▲
    │    EXCHANGE           │
    │    ┌─────────┐        │
    └───►│ Match   │────────┘
         │ Engine  │
    ┌───►│         │◄───┐
    │    └─────────┘    │
    │                   │
Seller OLTIN ─────► Buyer OLTIN
```

### Transfer Flow

```
Sender Wallet OLTIN
       │
       │ send (amount)
       ├────────────────► Treasury Pool
       │                  (1% fee)
       │
       │ (amount - fee)
       ▼
Receiver Wallet OLTIN
       │
       │ blockchain
       ▼
zkSync Transaction (adminTransfer)
```
