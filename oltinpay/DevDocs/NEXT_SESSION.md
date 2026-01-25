# Следующая сессия — OltinPay

**Дата:** 2026-01-25
**Статус:** MVP готов, нужна интеграция

---

## Что сделано

✅ Backend API (FastAPI) — 8 модулей, 33 теста
✅ Frontend (Next.js) — 6 страниц, i18n (UZ/RU/EN)
✅ Telegram Bot — inline выбор языка
✅ Deploy — api.oltinpay.com, app.oltinpay.com, @Oltin_Paybot

---

## Что нужно сделать

### 1. Интеграция Frontend ↔ Backend

Сейчас frontend использует mock данные. Нужно:

```typescript
// src/app/wallet/page.tsx
// Заменить mock на реальные запросы:
const { data: balances } = useQuery({
  queryKey: ['balances'],
  queryFn: () => api.getBalances(),
});
```

**Файлы для обновления:**
- `src/app/wallet/page.tsx` — балансы, транзакции
- `src/app/exchange/page.tsx` — orderbook, trades
- `src/app/staking/page.tsx` — staking info, rewards
- `src/app/send/page.tsx` — поиск пользователей, отправка

### 2. Авторизация через Telegram initData

```typescript
// src/app/providers.tsx
// При загрузке отправить initData на backend:
useEffect(() => {
  const initData = window.Telegram?.WebApp?.initData;
  if (initData) {
    api.auth(initData).then(({ token }) => {
      setToken(token);
    });
  }
}, []);
```

### 3. Настройка znai-cloud для Aylin

```bash
# .env
ZNAI_CLOUD_URL=https://api.znai.cloud
ZNAI_CLOUD_API_KEY=your-api-key

# Создать knowledge base с документацией OltinPay
```

### 4. Блокчейн интеграция

```bash
# .env
ZKSYNC_RPC_URL=https://mainnet.era.zksync.io  # или testnet
OLTIN_CONTRACT_ADDRESS=0x...
ADMIN_PRIVATE_KEY=...
```

### 5. Landing Page

```
oltinpay.com → статичная страница
├── Hero с описанием
├── Features
├── How it works
└── CTA → открыть бота
```

---

## Структура проекта

```
/root/server/oltinpay/
├── DevDocs/                    # Документация
├── oltinpay-api/               # Backend ✅
├── oltinpay-webapp/            # Frontend ✅
├── oltinpay-bot/               # Bot ✅
└── oltinpay-landing/           # TODO
```

---

## Как начать

```bash
# 1. Подключиться
ssh oltinkey
cd /root/server/oltinpay

# 2. Прочитать контекст
cat DevDocs/SESSION_CONTEXT.md
cat DevDocs/CLAUDE.md

# 3. Прочитать стандарты
cat DevDocs/standards/_INDEX.md
```

---

## Ссылки

- API: https://api.oltinpay.com
- WebApp: https://app.oltinpay.com
- Bot: @Oltin_Paybot
- API Docs: https://api.oltinpay.com/docs
