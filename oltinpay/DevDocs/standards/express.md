# EXPRESS.JS GUIDE
## Для Claude Code — Express + TypeScript

> **Цель:** Единый стиль разработки Express.js приложений
> **Референс:** Express.js docs + TypeScript best practices
> **Версия:** Express 4.x, TypeScript 5+, Node.js 20+

---

## 🎯 КЛЮЧЕВЫЕ ПРИНЦИПЫ

```
ВСЕГДА                              НИКОГДА
────────────────────────────────    ────────────────────────────────
✓ TypeScript strict mode            ✗ any типы без причины
✓ Controller → Service → Repository ✗ Бизнес-логика в routes
✓ Zod для валидации                 ✗ Ручная проверка req.body
✓ Централизованная обработка ошибок ✗ try-catch в каждом route
✓ Async middleware wrapper          ✗ Забытый next(error)
✓ Environment variables             ✗ Хардкод конфигов
✓ Typed Request/Response            ✗ req: any, res: any
✓ Router для группировки            ✗ Все routes в одном файле
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
express-project/
├── .env
├── .env.example
├── package.json
├── tsconfig.json
├── nodemon.json
│
├── src/
│   ├── index.ts                  # Entry point
│   ├── app.ts                    # Express app setup
│   │
│   ├── config/                   # Configuration
│   │   ├── index.ts              # Export all configs
│   │   ├── env.ts                # Environment variables
│   │   └── database.ts           # Database config
│   │
│   ├── routes/                   # Route definitions
│   │   ├── index.ts              # Route aggregator
│   │   ├── auth.routes.ts
│   │   ├── users.routes.ts
│   │   └── products.routes.ts
│   │
│   ├── controllers/              # Request handlers
│   │   ├── auth.controller.ts
│   │   ├── users.controller.ts
│   │   └── products.controller.ts
│   │
│   ├── services/                 # Business logic
│   │   ├── auth.service.ts
│   │   ├── users.service.ts
│   │   └── products.service.ts
│   │
│   ├── repositories/             # Data access
│   │   ├── users.repository.ts
│   │   └── products.repository.ts
│   │
│   ├── middlewares/              # Express middlewares
│   │   ├── error.middleware.ts
│   │   ├── auth.middleware.ts
│   │   ├── validate.middleware.ts
│   │   └── async.middleware.ts
│   │
│   ├── schemas/                  # Zod schemas
│   │   ├── auth.schema.ts
│   │   ├── users.schema.ts
│   │   └── common.schema.ts
│   │
│   ├── models/                   # Database models
│   │   ├── user.model.ts
│   │   └── product.model.ts
│   │
│   ├── types/                    # TypeScript types
│   │   ├── index.ts
│   │   ├── express.d.ts          # Express augmentation
│   │   └── api.types.ts
│   │
│   ├── utils/                    # Utilities
│   │   ├── logger.ts
│   │   ├── jwt.ts
│   │   └── hash.ts
│   │
│   └── errors/                   # Custom errors
│       ├── index.ts
│       ├── app-error.ts
│       └── http-errors.ts
│
├── prisma/                       # Prisma (if used)
│   └── schema.prisma
│
└── tests/
    ├── setup.ts
    └── users.test.ts
```

---

## ⚙️ КОНФИГУРАЦИЯ

### Environment Variables

```typescript
// src/config/env.ts

import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.string().transform(Number).default('3000'),

  // Database
  DATABASE_URL: z.string().url(),

  // JWT
  JWT_SECRET: z.string().min(32),
  JWT_EXPIRES_IN: z.string().default('7d'),

  // Redis (optional)
  REDIS_URL: z.string().url().optional(),

  // CORS
  CORS_ORIGIN: z.string().default('http://localhost:3000'),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error('❌ Invalid environment variables:');
  console.error(parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const env = parsed.data;
export type Env = z.infer<typeof envSchema>;
```

### TypeScript Config

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### Package.json Scripts

```json
{
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "lint": "eslint src --ext .ts",
    "test": "vitest"
  }
}
```

---

## 🚀 APP SETUP

### Entry Point

```typescript
// src/index.ts

import { env } from './config/env';
import { createApp } from './app';
import { logger } from './utils/logger';

const app = createApp();

const server = app.listen(env.PORT, () => {
  logger.info(`🚀 Server running on http://localhost:${env.PORT}`);
  logger.info(`📚 Environment: ${env.NODE_ENV}`);
});

// Graceful shutdown
const shutdown = () => {
  logger.info('Shutting down gracefully...');
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
};

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
```

### Express App

```typescript
// src/app.ts

import express, { Express } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';

import { env } from './config/env';
import { routes } from './routes';
import { errorMiddleware } from './middlewares/error.middleware';
import { requestLogger } from './middlewares/logger.middleware';

export function createApp(): Express {
  const app = express();

  // ═══════════════════════════════════════════════════════════════
  // Security & Parsing
  // ═══════════════════════════════════════════════════════════════

  app.use(helmet());
  app.use(cors({
    origin: env.CORS_ORIGIN,
    credentials: true,
  }));
  app.use(compression());
  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true }));

  // ═══════════════════════════════════════════════════════════════
  // Logging
  // ═══════════════════════════════════════════════════════════════

  app.use(requestLogger);

  // ═══════════════════════════════════════════════════════════════
  // Health Check
  // ═══════════════════════════════════════════════════════════════

  app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // ═══════════════════════════════════════════════════════════════
  // API Routes
  // ═══════════════════════════════════════════════════════════════

  app.use('/api/v1', routes);

  // ═══════════════════════════════════════════════════════════════
  // Error Handling (MUST BE LAST)
  // ═══════════════════════════════════════════════════════════════

  app.use(errorMiddleware);

  return app;
}
```

---

## 🛤️ ROUTES

### Route Aggregator

```typescript
// src/routes/index.ts

import { Router } from 'express';
import authRoutes from './auth.routes';
import usersRoutes from './users.routes';
import productsRoutes from './products.routes';

const router = Router();

router.use('/auth', authRoutes);
router.use('/users', usersRoutes);
router.use('/products', productsRoutes);

export { router as routes };
```

### Route Definition

```typescript
// src/routes/users.routes.ts

import { Router } from 'express';
import { UsersController } from '../controllers/users.controller';
import { validate } from '../middlewares/validate.middleware';
import { authenticate, authorize } from '../middlewares/auth.middleware';
import {
  createUserSchema,
  updateUserSchema,
  getUserParamsSchema,
} from '../schemas/users.schema';

const router = Router();
const controller = new UsersController();

// Public routes
router.post(
  '/',
  validate(createUserSchema),
  controller.create
);

// Protected routes
router.use(authenticate);

router.get('/', controller.findAll);

router.get(
  '/:id',
  validate(getUserParamsSchema, 'params'),
  controller.findOne
);

router.patch(
  '/:id',
  validate(getUserParamsSchema, 'params'),
  validate(updateUserSchema),
  controller.update
);

router.delete(
  '/:id',
  authorize('admin'),
  validate(getUserParamsSchema, 'params'),
  controller.delete
);

export default router;
```

---

## 🎮 CONTROLLERS

```typescript
// src/controllers/users.controller.ts

import { Request, Response, NextFunction } from 'express';
import { UsersService } from '../services/users.service';
import { asyncHandler } from '../middlewares/async.middleware';
import { CreateUserDto, UpdateUserDto } from '../schemas/users.schema';
import { NotFoundError } from '../errors';

export class UsersController {
  private usersService: UsersService;

  constructor() {
    this.usersService = new UsersService();
  }

  /**
   * POST /users
   */
  create = asyncHandler(async (
    req: Request<unknown, unknown, CreateUserDto>,
    res: Response
  ) => {
    const user = await this.usersService.create(req.body);

    res.status(201).json({
      success: true,
      data: user,
    });
  });

  /**
   * GET /users
   */
  findAll = asyncHandler(async (
    req: Request,
    res: Response
  ) => {
    const { page = 1, limit = 20 } = req.query;

    const result = await this.usersService.findAll({
      page: Number(page),
      limit: Number(limit),
    });

    res.json({
      success: true,
      data: result.items,
      meta: {
        total: result.total,
        page: result.page,
        limit: result.limit,
        totalPages: result.totalPages,
      },
    });
  });

  /**
   * GET /users/:id
   */
  findOne = asyncHandler(async (
    req: Request<{ id: string }>,
    res: Response
  ) => {
    const user = await this.usersService.findById(req.params.id);

    if (!user) {
      throw new NotFoundError('User not found');
    }

    res.json({
      success: true,
      data: user,
    });
  });

  /**
   * PATCH /users/:id
   */
  update = asyncHandler(async (
    req: Request<{ id: string }, unknown, UpdateUserDto>,
    res: Response
  ) => {
    const user = await this.usersService.update(req.params.id, req.body);

    res.json({
      success: true,
      data: user,
    });
  });

  /**
   * DELETE /users/:id
   */
  delete = asyncHandler(async (
    req: Request<{ id: string }>,
    res: Response
  ) => {
    await this.usersService.delete(req.params.id);

    res.status(204).send();
  });
}
```

---

## 🔧 SERVICES

```typescript
// src/services/users.service.ts

import { UsersRepository } from '../repositories/users.repository';
import { CreateUserDto, UpdateUserDto } from '../schemas/users.schema';
import { hashPassword } from '../utils/hash';
import { ConflictError, NotFoundError } from '../errors';

interface PaginationParams {
  page: number;
  limit: number;
}

export class UsersService {
  private usersRepository: UsersRepository;

  constructor() {
    this.usersRepository = new UsersRepository();
  }

  async create(data: CreateUserDto) {
    // Check if email exists
    const existing = await this.usersRepository.findByEmail(data.email);
    if (existing) {
      throw new ConflictError('Email already registered');
    }

    // Hash password
    const hashedPassword = await hashPassword(data.password);

    // Create user
    return this.usersRepository.create({
      ...data,
      password: hashedPassword,
    });
  }

  async findAll(params: PaginationParams) {
    const { page, limit } = params;
    const skip = (page - 1) * limit;

    const [items, total] = await Promise.all([
      this.usersRepository.findMany({ skip, take: limit }),
      this.usersRepository.count(),
    ]);

    return {
      items,
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
    };
  }

  async findById(id: string) {
    return this.usersRepository.findById(id);
  }

  async update(id: string, data: UpdateUserDto) {
    const user = await this.usersRepository.findById(id);

    if (!user) {
      throw new NotFoundError('User not found');
    }

    // If updating email, check uniqueness
    if (data.email && data.email !== user.email) {
      const existing = await this.usersRepository.findByEmail(data.email);
      if (existing) {
        throw new ConflictError('Email already in use');
      }
    }

    return this.usersRepository.update(id, data);
  }

  async delete(id: string) {
    const user = await this.usersRepository.findById(id);

    if (!user) {
      throw new NotFoundError('User not found');
    }

    return this.usersRepository.delete(id);
  }
}
```

---

## 🗄️ REPOSITORIES (Prisma)

```typescript
// src/repositories/users.repository.ts

import { PrismaClient, User, Prisma } from '@prisma/client';

const prisma = new PrismaClient();

// Exclude password from responses
const userSelect = {
  id: true,
  email: true,
  name: true,
  role: true,
  createdAt: true,
  updatedAt: true,
} satisfies Prisma.UserSelect;

type SafeUser = Omit<User, 'password'>;

export class UsersRepository {
  async create(data: Prisma.UserCreateInput): Promise<SafeUser> {
    return prisma.user.create({
      data,
      select: userSelect,
    });
  }

  async findById(id: string): Promise<SafeUser | null> {
    return prisma.user.findUnique({
      where: { id },
      select: userSelect,
    });
  }

  async findByEmail(email: string): Promise<User | null> {
    return prisma.user.findUnique({
      where: { email },
    });
  }

  async findMany(params: { skip?: number; take?: number }): Promise<SafeUser[]> {
    return prisma.user.findMany({
      ...params,
      select: userSelect,
      orderBy: { createdAt: 'desc' },
    });
  }

  async count(): Promise<number> {
    return prisma.user.count();
  }

  async update(id: string, data: Prisma.UserUpdateInput): Promise<SafeUser> {
    return prisma.user.update({
      where: { id },
      data,
      select: userSelect,
    });
  }

  async delete(id: string): Promise<void> {
    await prisma.user.delete({
      where: { id },
    });
  }
}
```

---

## 🛡️ MIDDLEWARES

### Async Handler

```typescript
// src/middlewares/async.middleware.ts

import { Request, Response, NextFunction, RequestHandler } from 'express';

type AsyncRequestHandler = (
  req: Request,
  res: Response,
  next: NextFunction
) => Promise<void>;

/**
 * Wrap async route handlers to catch errors.
 * Eliminates need for try-catch in every controller.
 */
export function asyncHandler(fn: AsyncRequestHandler): RequestHandler {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}
```

### Error Handler

```typescript
// src/middlewares/error.middleware.ts

import { Request, Response, NextFunction, ErrorRequestHandler } from 'express';
import { ZodError } from 'zod';
import { AppError } from '../errors/app-error';
import { env } from '../config/env';
import { logger } from '../utils/logger';

export const errorMiddleware: ErrorRequestHandler = (
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  // Log error
  logger.error({
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
  });

  // Zod validation error
  if (err instanceof ZodError) {
    res.status(400).json({
      success: false,
      message: 'Validation error',
      errors: err.errors.map((e) => ({
        field: e.path.join('.'),
        message: e.message,
      })),
    });
    return;
  }

  // Custom app error
  if (err instanceof AppError) {
    res.status(err.statusCode).json({
      success: false,
      message: err.message,
      ...(err.errors && { errors: err.errors }),
    });
    return;
  }

  // Prisma errors
  if (err.name === 'PrismaClientKnownRequestError') {
    res.status(400).json({
      success: false,
      message: 'Database error',
    });
    return;
  }

  // Unknown error
  res.status(500).json({
    success: false,
    message: 'Internal server error',
    ...(env.NODE_ENV === 'development' && { stack: err.stack }),
  });
};
```

### Validation Middleware

```typescript
// src/middlewares/validate.middleware.ts

import { Request, Response, NextFunction } from 'express';
import { AnyZodObject, ZodError } from 'zod';

type RequestPart = 'body' | 'query' | 'params';

export function validate(
  schema: AnyZodObject,
  part: RequestPart = 'body'
) {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      const data = await schema.parseAsync(req[part]);
      req[part] = data;
      next();
    } catch (error) {
      next(error);
    }
  };
}
```

### Auth Middleware

```typescript
// src/middlewares/auth.middleware.ts

import { Request, Response, NextFunction } from 'express';
import { verifyToken } from '../utils/jwt';
import { UnauthorizedError, ForbiddenError } from '../errors';

// Extend Express Request
declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        email: string;
        role: string;
      };
    }
  }
}

export async function authenticate(
  req: Request,
  res: Response,
  next: NextFunction
) {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader?.startsWith('Bearer ')) {
      throw new UnauthorizedError('Missing or invalid token');
    }

    const token = authHeader.split(' ')[1];
    const payload = await verifyToken(token);

    req.user = {
      id: payload.sub,
      email: payload.email,
      role: payload.role,
    };

    next();
  } catch (error) {
    next(new UnauthorizedError('Invalid token'));
  }
}

export function authorize(...roles: string[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return next(new UnauthorizedError('Not authenticated'));
    }

    if (!roles.includes(req.user.role)) {
      return next(new ForbiddenError('Insufficient permissions'));
    }

    next();
  };
}
```

---

## ✅ ZOD SCHEMAS

```typescript
// src/schemas/users.schema.ts

import { z } from 'zod';

// ═══════════════════════════════════════════════════════════════════
// Create User
// ═══════════════════════════════════════════════════════════════════

export const createUserSchema = z.object({
  email: z.string().email('Invalid email format'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain uppercase letter')
    .regex(/[0-9]/, 'Password must contain number'),
  name: z.string().min(2).max(100),
});

export type CreateUserDto = z.infer<typeof createUserSchema>;

// ═══════════════════════════════════════════════════════════════════
// Update User
// ═══════════════════════════════════════════════════════════════════

export const updateUserSchema = z.object({
  email: z.string().email().optional(),
  name: z.string().min(2).max(100).optional(),
});

export type UpdateUserDto = z.infer<typeof updateUserSchema>;

// ═══════════════════════════════════════════════════════════════════
// Params
// ═══════════════════════════════════════════════════════════════════

export const getUserParamsSchema = z.object({
  id: z.string().uuid('Invalid user ID'),
});

// ═══════════════════════════════════════════════════════════════════
// Query
// ═══════════════════════════════════════════════════════════════════

export const listUsersQuerySchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
  search: z.string().optional(),
});
```

---

## ❌ CUSTOM ERRORS

```typescript
// src/errors/app-error.ts

export class AppError extends Error {
  public readonly statusCode: number;
  public readonly isOperational: boolean;
  public readonly errors?: Record<string, string>[];

  constructor(
    message: string,
    statusCode: number,
    errors?: Record<string, string>[]
  ) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    this.errors = errors;

    Error.captureStackTrace(this, this.constructor);
  }
}
```

```typescript
// src/errors/http-errors.ts

import { AppError } from './app-error';

export class BadRequestError extends AppError {
  constructor(message = 'Bad request') {
    super(message, 400);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message = 'Unauthorized') {
    super(message, 401);
  }
}

export class ForbiddenError extends AppError {
  constructor(message = 'Forbidden') {
    super(message, 403);
  }
}

export class NotFoundError extends AppError {
  constructor(message = 'Not found') {
    super(message, 404);
  }
}

export class ConflictError extends AppError {
  constructor(message = 'Conflict') {
    super(message, 409);
  }
}

export class InternalError extends AppError {
  constructor(message = 'Internal server error') {
    super(message, 500);
  }
}
```

```typescript
// src/errors/index.ts

export * from './app-error';
export * from './http-errors';
```

---

## 🔐 JWT UTILITIES

```typescript
// src/utils/jwt.ts

import jwt from 'jsonwebtoken';
import { env } from '../config/env';

interface TokenPayload {
  sub: string;
  email: string;
  role: string;
}

export function signToken(payload: TokenPayload): string {
  return jwt.sign(payload, env.JWT_SECRET, {
    expiresIn: env.JWT_EXPIRES_IN,
  });
}

export function verifyToken(token: string): TokenPayload {
  return jwt.verify(token, env.JWT_SECRET) as TokenPayload;
}
```

---

## 📝 LOGGER

```typescript
// src/utils/logger.ts

import pino from 'pino';
import { env } from '../config/env';

export const logger = pino({
  level: env.NODE_ENV === 'production' ? 'info' : 'debug',
  transport: env.NODE_ENV === 'development'
    ? {
        target: 'pino-pretty',
        options: {
          colorize: true,
          translateTime: 'SYS:standard',
        },
      }
    : undefined,
});
```

---

## 🧪 TESTING

```typescript
// tests/users.test.ts

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import { createApp } from '../src/app';

const app = createApp();

describe('Users API', () => {
  let authToken: string;
  let userId: string;

  beforeAll(async () => {
    // Login to get token
    const res = await request(app)
      .post('/api/v1/auth/login')
      .send({ email: 'admin@test.com', password: 'password123' });

    authToken = res.body.data.accessToken;
  });

  describe('POST /api/v1/users', () => {
    it('should create a new user', async () => {
      const res = await request(app)
        .post('/api/v1/users')
        .send({
          email: 'test@example.com',
          password: 'Password123',
          name: 'Test User',
        });

      expect(res.status).toBe(201);
      expect(res.body.success).toBe(true);
      expect(res.body.data).toHaveProperty('id');

      userId = res.body.data.id;
    });

    it('should return 400 for invalid email', async () => {
      const res = await request(app)
        .post('/api/v1/users')
        .send({
          email: 'invalid-email',
          password: 'Password123',
          name: 'Test User',
        });

      expect(res.status).toBe(400);
      expect(res.body.success).toBe(false);
    });
  });

  describe('GET /api/v1/users', () => {
    it('should return list of users', async () => {
      const res = await request(app)
        .get('/api/v1/users')
        .set('Authorization', `Bearer ${authToken}`);

      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(Array.isArray(res.body.data)).toBe(true);
    });

    it('should return 401 without token', async () => {
      const res = await request(app).get('/api/v1/users');

      expect(res.status).toBe(401);
    });
  });
});
```

---

## ✅ ЧЕКЛИСТ

```
СТРУКТУРА
□ routes → controllers → services → repositories
□ Zod schemas для валидации
□ Typed Request/Response
□ Custom error classes

MIDDLEWARE
□ asyncHandler для async routes
□ Централизованный error handler
□ validate middleware с Zod
□ authenticate/authorize

БЕЗОПАСНОСТЬ
□ helmet для HTTP headers
□ cors настроен
□ rate limiting
□ JWT validation

КАЧЕСТВО
□ TypeScript strict mode
□ Logger (pino/winston)
□ Environment validation (Zod)
□ Tests (vitest + supertest)
```

---

## 🚀 БЫСТРЫЙ ПРОМПТ

```
Express.js + TypeScript приложение:

СТРУКТУРА:
routes/ → controllers/ → services/ → repositories/
schemas/ для Zod валидации
middlewares/ для auth, error handling, validation

ОБЯЗАТЕЛЬНО:
✅ asyncHandler wrapper для async routes
✅ Централизованный errorMiddleware (ПОСЛЕДНИЙ app.use)
✅ Zod для валидации req.body/params/query
✅ Custom AppError классы
✅ Request типизация: Request<Params, ResBody, ReqBody, Query>

PATTERNS:
- Controller: только req/res, вызов service
- Service: бизнес-логика, вызов repository
- Repository: только data access (Prisma)

ENV: Zod schema для process.env с validation
JWT: signToken/verifyToken utilities
```

---

**Версия:** 1.0
**Дата:** 01.12.2025
