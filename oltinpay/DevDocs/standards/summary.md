# DEV STANDARDS SUMMARY

Сводка строгих правил из 6 гайдов для рефакторинга ai-prikorm и будущих проектов.

---

## 1. TYPESCRIPT STYLE GUIDE

### Структура проекта
```
src/
├── config/          # Конфигурация, переменные окружения
├── services/        # Бизнес-логика
├── routes/          # Express роуты (или handlers для бота)
├── middleware/      # Express middleware
├── models/          # Типы и интерфейсы
├── utils/           # Утилиты
├── bot/             # Telegram bot (handlers, commands, keyboards)
└── index.ts         # Entry point
```

### Строгие правила
- **Всегда** использовать `strict: true` в tsconfig.json
- **Никогда** не использовать `any` - только `unknown` с type guards
- **Всегда** явно типизировать параметры функций и возвращаемые значения
- **Интерфейсы** для объектов, **типы** для union/intersection
- **Константы** в UPPER_SNAKE_CASE
- **Функции и переменные** в camelCase
- **Классы и интерфейсы** в PascalCase

### Обработка ошибок
```typescript
// Правильно - кастомные ошибки
class AppError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code: string
  ) {
    super(message);
  }
}

// Правильно - Result pattern для операций
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };
```

### Async/Await
- **Всегда** оборачивать в try-catch
- **Никогда** не игнорировать rejected promises
- Использовать `Promise.all()` для параллельных операций

---

## 2. EXPRESS GUIDE

### Структура роутов
```typescript
// routes/user.routes.ts
import { Router } from 'express';
const router = Router();

router.get('/', userController.getAll);
router.post('/', validateBody(createUserSchema), userController.create);

export default router;
```

### Middleware порядок
1. Security (helmet, cors)
2. Body parsing (express.json)
3. Logging
4. Routes
5. Error handler (последний!)

### Валидация
- **Всегда** валидировать входящие данные (Zod/Joi)
- **Никогда** не доверять req.body/req.params напрямую
- Санитизировать все строки от XSS

### Error Handler
```typescript
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  const statusCode = err instanceof AppError ? err.statusCode : 500;
  res.status(statusCode).json({
    success: false,
    error: err.message,
    code: err instanceof AppError ? err.code : 'INTERNAL_ERROR'
  });
});
```

### Security checklist
- [ ] helmet() подключен
- [ ] CORS настроен для конкретных доменов
- [ ] Rate limiting на API endpoints
- [ ] Нет секретов в логах
- [ ] HTTPS в продакшене

---

## 3. POSTGRESQL GUIDE

### Подключение
```typescript
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```

### Транзакции
```typescript
const client = await pool.connect();
try {
  await client.query('BEGIN');
  // операции
  await client.query('COMMIT');
} catch (e) {
  await client.query('ROLLBACK');
  throw e;
} finally {
  client.release();
}
```

### Строгие правила
- **Всегда** использовать параметризованные запросы ($1, $2...)
- **Никогда** не конкатенировать SQL строки (SQL injection!)
- **Всегда** освобождать клиента в finally
- Индексы на часто используемые поля в WHERE/JOIN
- JSONB вместо JSON для поиска внутри

### Миграции
- Каждое изменение схемы = отдельная миграция
- Миграции идемпотентные (можно запускать повторно)
- Версионирование: `001_create_users.sql`, `002_add_subscriptions.sql`

---

## 4. TELEGRAM BOT GUIDE (адаптировано для Grammy)

### Структура
```
bot/
├── handlers/        # Обработчики callback_query, messages
├── commands/        # /start, /help, /profile
├── keyboards/       # InlineKeyboard, Keyboard builders
├── middleware/      # Логирование, auth, rate limit
└── index.ts         # Bot initialization
```

### Middleware
```typescript
// Логирование всех апдейтов
bot.use(async (ctx, next) => {
  const start = Date.now();
  await next();
  console.log(`Update ${ctx.update.update_id} processed in ${Date.now() - start}ms`);
});
```

### Клавиатуры
```typescript
// Inline keyboard
const keyboard = new InlineKeyboard()
  .text('Кнопка', 'callback_data')
  .row()
  .url('Ссылка', 'https://...');
```

### Строгие правила
- **Всегда** отвечать на callback_query через `ctx.answerCallbackQuery()`
- **Экранировать** спецсимволы в Markdown: `_`, `*`, `[`, `]`, `` ` ``
- **Хранить состояние** в БД, не в памяти
- Rate limiting для защиты от спама
- Graceful shutdown: `bot.stop()` в SIGINT/SIGTERM

### Markdown escaping
```typescript
function escapeMarkdown(text: string): string {
  return text.replace(/[_*[\]`]/g, '\\$&');
}
```

---

## 5. RAG SYSTEM GUIDE

### Архитектура
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Ingest    │────>│   Vector    │────>│   Query     │
│  Pipeline   │     │    Store    │     │   Engine    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Компоненты
1. **Document Loader** - загрузка из PDF, TXT, URL
2. **Text Splitter** - chunk_size: 512-1024, overlap: 50-100
3. **Embedding Model** - text-embedding-3-small (OpenAI) или локальные
4. **Vector Store** - Qdrant, pgvector, Chroma
5. **Retriever** - top_k: 3-5 документов
6. **LLM** - генерация ответа с контекстом

### Qdrant настройка
```typescript
const client = new QdrantClient({ url: 'http://localhost:6333' });

// Создание коллекции
await client.createCollection('my_collection', {
  vectors: {
    size: 1536,  // размер embedding
    distance: 'Cosine'
  }
});
```

### Строгие правила
- **Одна коллекция** на проект/домен
- **Metadata** обязательна: source, timestamp, chunk_id
- **Chunk overlap** для сохранения контекста между частями
- Тестировать retrieval quality до продакшена
- Логировать запросы и retrieved chunks

### Simple RAG pipeline
```typescript
async function query(question: string): Promise<string> {
  // 1. Embed вопрос
  const embedding = await embedText(question);

  // 2. Поиск похожих
  const results = await qdrant.search('collection', {
    vector: embedding,
    limit: 5
  });

  // 3. Формируем контекст
  const context = results.map(r => r.payload.text).join('\n\n');

  // 4. Генерируем ответ
  return await llm.chat([
    { role: 'system', content: `Context:\n${context}` },
    { role: 'user', content: question }
  ]);
}
```

---

## 6. DEVOPS GUIDE

### PM2 конфигурация
```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'app-name',
    script: 'dist/index.js',
    instances: 1,           // или 'max' для кластера
    exec_mode: 'fork',      // или 'cluster'
    env_production: {
      NODE_ENV: 'production'
    },
    max_memory_restart: '500M',
    error_file: './logs/error.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss'
  }]
};
```

### PM2 команды
```bash
pm2 start ecosystem.config.js --env production
pm2 restart app-name
pm2 logs app-name --lines 100
pm2 monit                    # мониторинг в реальном времени
pm2 save                     # сохранить конфиг
pm2 startup                  # автозапуск при перезагрузке
```

### Nginx reverse proxy
```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL с Certbot
```bash
sudo certbot --nginx -d api.example.com --non-interactive --agree-tos -m email@example.com
```

### Строгие правила
- **Никогда** не запускать Node.js на порту 80/443 напрямую
- **Всегда** использовать process manager (PM2)
- **Всегда** HTTPS в продакшене
- Логи ротировать (logrotate или PM2 log-rotate)
- Мониторинг: CPU, RAM, disk, response time

### Deployment checklist
- [ ] NODE_ENV=production
- [ ] PM2 настроен и запущен
- [ ] Nginx reverse proxy
- [ ] SSL сертификат
- [ ] Firewall (ufw) настроен
- [ ] Логи пишутся
- [ ] Бэкапы БД настроены
- [ ] Мониторинг работает

---

## QUICK REFACTORING CHECKLIST

### Перед началом
- [ ] Прочитать весь код проекта
- [ ] Понять текущую архитектуру
- [ ] Определить критические проблемы

### TypeScript
- [ ] strict: true в tsconfig
- [ ] Нет any, использовать unknown
- [ ] Все функции типизированы
- [ ] Кастомные Error классы

### API/Express
- [ ] Валидация входных данных
- [ ] Централизованный error handler
- [ ] helmet, cors, rate-limit
- [ ] Параметризованные SQL запросы

### Telegram Bot
- [ ] Экранирование Markdown
- [ ] answerCallbackQuery везде
- [ ] Состояние в БД, не в памяти
- [ ] Graceful shutdown

### RAG
- [ ] Правильный chunk_size и overlap
- [ ] Metadata на всех документах
- [ ] Логирование retrieval

### DevOps
- [ ] PM2 ecosystem.config.js
- [ ] Nginx + SSL
- [ ] Логирование настроено
- [ ] Бэкапы БД

---

*Создано: 2024-12-01*
*Источники: TYPESCRIPT_STYLE_GUIDE.md, EXPRESS_GUIDE.md, POSTGRESQL_GUIDE.md, TELEGRAM_BOT_GUIDE.md, RAG_SYSTEM_GUIDE.md, DEVOPS_GUIDE.md*
