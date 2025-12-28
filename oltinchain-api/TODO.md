# OltinChain API - Development Progress

## Current Day: Day 8-9 - Orders Service ✅ COMPLETED

### Completed (Days 1-9)
- [x] Project initialization with Poetry
- [x] Docker Compose setup (PostgreSQL, Redis)
- [x] FastAPI base app with health endpoint
- [x] Config with pydantic-settings
- [x] SQLAlchemy async database setup
- [x] Models: User, Balance, Order, GoldBar, Alert
- [x] Alembic migrations initialized
- [x] Domain exceptions
- [x] Security module (JWT + bcrypt)
- [x] User repository
- [x] Auth service + router
- [x] Users router (GET/PATCH /users/me)
- [x] **OltinToken Smart Contract** deployed to zkSync Sepolia
- [x] **Blockchain Service** - mint/burn integration working!
- [x] **Price Service** - gold price + fee calculation
- [x] **Price Router** - /price/gold, /price/quote/buy, /price/quote/sell
- [x] **Order Repository** - CRUD for orders
- [x] **Balance Repository** - balance management with lock/unlock
- [x] **Order Service** - buy/sell flow with blockchain integration
- [x] **Orders Router** - POST /orders/buy, POST /orders/sell, GET /orders

### 🎉 Stats
| Metric | Value |
|--------|-------|
| Unit Tests | 68 passing |
| Contract Tests | 17 passing |
| API Endpoints | 16 |
| Blockchain Txns | Mint ✅ Burn ✅ |

### Smart Contract
| Item | Value |
|------|-------|
| Contract | OltinToken |
| Address | `0xA7E92168517864359B6Fa9e2247B01e0280A7dAa` |
| Network | zkSync Sepolia |
| Explorer | https://sepolia.explorer.zksync.io/address/0xA7E92168517864359B6Fa9e2247B01e0280A7dAa |

### API Endpoints
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/register | No | Register |
| POST | /auth/login | No | Login |
| POST | /auth/refresh | No | Refresh tokens |
| GET | /users/me | Yes | Get profile |
| PATCH | /users/me | Yes | Update profile |
| GET | /blockchain/token | No | Token info |
| GET | /blockchain/balance/{addr} | No | Get balance |
| POST | /blockchain/mint | Admin | Mint tokens |
| POST | /blockchain/burn | Admin | Burn tokens |
| GET | /price/gold | No | Current gold price |
| POST | /price/quote/buy | No | Buy quote |
| POST | /price/quote/sell | No | Sell quote |
| POST | /orders/buy | Yes | Buy OLTIN with UZS |
| POST | /orders/sell | Yes | Sell OLTIN for UZS |
| GET | /orders | Yes | Order history |

### Buy/Sell Flow
1. User requests quote (/price/quote/buy or /sell)
2. User places order (/orders/buy or /sell)
3. System locks user funds (UZS or OLTIN)
4. System calls blockchain (mint or burn)
5. On success: update balances, complete order
6. On failure: unlock funds, mark order as failed

### Price Configuration
| Parameter | Value |
|-----------|-------|
| Gold price | 650,000 UZS/gram |
| Fee percent | 1.5% |
| Min fee | 3,800 UZS |

### Pending
- [ ] Day 10+: Deposit/Withdrawal endpoints
- [ ] KYC verification flow
- [ ] Real gold price API integration
- [ ] Admin dashboard

---
Last updated: 2025-12-26
