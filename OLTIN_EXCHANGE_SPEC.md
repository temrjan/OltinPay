# OLTIN Exchange - Спецификация

## 🎯 Идея

Создать собственную биржу с независимым курсом OLTIN, который движется по циклам подобно Bitcoin.
Цена генерируется алгоритмом Price Oracle, а боты обеспечивают ликвидность.

---

## 📊 Существующая Инфраструктура

### Кошелек (Wallet) ✅ Готов
```
Файлы:
- /app/api/wallet/router.py
- /app/api/wallet/schemas.py
- /app/application/services/wallet_service.py

Функционал:
- Балансы: USD (фиат), OLTIN (токены)
- Депозит USD
- Переводы OLTIN (gasless через adminTransfer)
- Синхронизация с блокчейном (zkSync)
- История транзакций
```

### Ордера (Orders) ✅ Готов
```
Файлы:
- /app/api/orders/router.py
- /app/application/services/order_service.py

Функционал:
- Buy: USD → OLTIN (mint на блокчейн)
- Sell: OLTIN → USD (burn с блокчейна)
- Broadcast событий
```

### Ценообразование (PriceService) ⚠️ Требует замены
```
Файл: /app/application/services/price_service.py

Текущее:
- Фиксированная base_price из settings
- Spread 1% (0.5% в каждую сторону)
- Fee 1.5% или мин 3800 USD

Нужно:
- Динамическая цена от Price Oracle
- Циклы Wyckoff
```

---

## 🔄 Модель Цикла (Wyckoff + Bitcoin)

### Параметры
```python
# Формулы для цикла N (N начинается с 1)
start_price = 100 * (1.8 ** (N - 1))
peak_multiplier = 4.5 - (N * 0.3)
peak_price = start_price * peak_multiplier
drawdown = 0.70 - (N * 0.05)  # Уменьшается каждый цикл
bottom_price = peak_price * (1 - drawdown)
end_price = start_price * 1.8  # +80% за цикл

# 1 неделя = 1 год Bitcoin
# 7 дней = 365 дней Bitcoin
# 1 день ≈ 52 дня Bitcoin
```

### Примеры циклов
```
Цикл 1:  →  (peak) →  (bottom) →  (end)
  - Рост: x4.2
  - Просадка: -70%
  - Итого: +80%

Цикл 2:  →  (peak) →  (bottom) →  (end)
  - Рост: x3.8
  - Просадка: -67%
  - Итого: +80%

Цикл 3:  →  (peak) →  (bottom) →  (end)
  - Рост: x3.4
  - Просадка: -65%
  - Итого: +80%
```

### Фазы Wyckoff (1 неделя)
```
День 1-2: Accumulation (Накопление)
  - Цена: start → start * 1.1
  - Волатильность: низкая
  - Характер: боковик, Spring (bear trap)

День 2-4: Markup (Рост)
  - Цена: → peak
  - Волатильность: растущая
  - Характер: импульсный рост, FOMO

День 4-5: Distribution (Распределение)
  - Цена: peak → peak * 0.95
  - Волатильность: высокая
  - Характер: боковик на хаях, Upthrust (bull trap)

День 5-6: Markdown (Падение)
  - Цена: → bottom
  - Волатильность: очень высокая
  - Характер: паника, capitulation

День 7: Re-Accumulation
  - Цена: bottom → end (start * 1.8)
  - Волатильность: снижается
  - Характер: умные деньги покупают
```

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Dashboard)                    │
│  - Trading Widget (Buy/Sell)                                │
│  - OrderBook (Asks/Bids)                                    │
│  - Price Chart                                              │
│  - Wallet Balance                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket / REST
┌──────────────────────────▼──────────────────────────────────┐
│                      API (FastAPI)                          │
│  /orders/buy, /orders/sell (Market)                         │
│  /orders/limit (Limit Orders) - NEW                         │
│  /wallet/balance                                            │
│  /price/current, /price/history                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Price Oracle Service                       │
│  - Генерация цены по Wyckoff циклам                         │
│  - Volatility engine                                        │
│  - Mean reversion + Trend following                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Matching Engine                            │
│  - Match limit orders                                       │
│  - Price-time priority                                      │
│  - OrderBook management                                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   Bot System                                 │
│  - Market Maker Bot (spread)                                │
│  - Trend Bot (momentum)                                     │
│  - Noise Bot (organic trading)                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Структура файлов

```
/root/server/oltinchain-api/
├── app/
│   ├── api/
│   │   ├── orders/
│   │   │   ├── router.py        # + limit orders
│   │   │   └── schemas.py       # + LimitOrderRequest
│   │   ├── price/               # NEW
│   │   │   ├── router.py        # GET /current, /history
│   │   │   └── schemas.py
│   │   └── wallet/              # ✅ Готов
│   │
│   ├── application/
│   │   └── services/
│   │       ├── price_oracle.py  # NEW - генератор цены
│   │       ├── matching_engine.py # NEW - matching
│   │       └── order_service.py # Модифицировать
│   │
│   └── domain/
│       └── models/
│           └── order_book.py    # NEW - OrderBook entity

/root/server/oltinchain-bots/
├── orchestrator/
│   ├── engine.py               # Модифицировать
│   └── price_oracle.py         # NEW - основной алгоритм
├── strategies/
│   ├── market_maker.py         # NEW
│   ├── trend_follower.py       # NEW
│   └── noise_trader.py         # NEW
```

---

## 🎨 Дизайн (oltinchain.com стиль)

```css
/* Цветовая схема */
--background: #0a0a0a;
--card-bg: #111111;
--border: #222222;
--gold: #D4AF37;
--gold-light: #F4D03F;
--gold-dark: #996515;
--text: #ffffff;
--text-muted: #888888;
--green: #22c55e;
--red: #ef4444;

/* Компоненты */
- Тёмные карточки с золотыми акцентами
- Минималистичный UI
- Иконка Au в логотипе
- Градиенты gold → gold-light
```

---

## 📋 Этапы Реализации

### Этап 1: Price Oracle (Backend)
```
□ Создать price_oracle.py с Wyckoff циклами
□ Реализовать генератор цены с volatility
□ Добавить API endpoints /price/current, /price/history
□ Интегрировать с существующим PriceService
□ Тесты
```

### Этап 2: OrderBook & Matching Engine
```
□ Создать модель OrderBook
□ Реализовать Limit Orders API
□ Создать Matching Engine
□ Интегрировать с Wallet (lock/unlock)
□ WebSocket для real-time updates
```

### Этап 3: Bot System
```
□ Market Maker Bot (spread management)
□ Trend Bot (follow price oracle)
□ Noise Bot (organic trading simulation)
□ Интеграция с Redis pub/sub
```

### Этап 4: Frontend Trading Widget
```
□ Trading форма (Buy/Sell tabs)
□ Market/Limit order переключатель
□ OrderBook визуализация (Asks/Bids)
□ Price Chart (candlestick)
□ Интеграция с Wallet balance
```

### Этап 5: Интеграция & Тестирование
```
□ E2E тесты полного цикла торговли
□ Нагрузочное тестирование
□ Мониторинг и алерты
□ Документация API
```

---

## 🔑 Ключевые Принципы

1. **Higher Lows** - каждый цикл заканчивается выше предыдущего
2. **Decreasing Volatility** - со временем рынок взрослеет
3. **Organic Trading** - боты создают естественную активность
4. **Real Integration** - кошелек и блокчейн уже работают

---

## 🚀 Следующий Шаг

Начинаем с **Этапа 1: Price Oracle**

```bash
# Файл для создания:
/root/server/oltinchain-api/app/application/services/price_oracle.py
```
