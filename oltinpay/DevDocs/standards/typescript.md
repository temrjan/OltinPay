# TYPESCRIPT CODE STYLE GUIDE
## Для Claude Code — Google TypeScript Style Guide

> **Цель:** Единый стиль TypeScript кода во всех проектах
> **Референс:** Google TypeScript Style Guide (https://google.github.io/styleguide/tsguide.html)
> **Версия TypeScript:** 5.0+

---

## 🎯 КЛЮЧЕВЫЕ ПРИНЦИПЫ

```
ВСЕГДА                              НИКОГДА
────────────────────────────────    ────────────────────────────────
✓ const/let (НЕ var)                ✗ var (устарел, function-scoped)
✓ Одинарные кавычки 'string'        ✗ Двойные кавычки "string"
✓ Точка с запятой в конце ;         ✗ Без точки с запятой
✓ 2 пробела для отступов            ✗ Табы или 4 пробела
✓ Named exports                     ✗ Default exports
✓ === и !==                         ✗ == и !=
✓ interface для объектов            ✗ type для объектов
✓ T[] для простых массивов          ✗ Array<T> для простых типов
✓ undefined для отсутствия          ✗ null без необходимости
✓ Фигурные скобки везде             ✗ Однострочные if/for без {}
```

---

## 📦 ИМЕНОВАНИЕ

### Стили именования

| Тип | Стиль | Примеры |
|-----|-------|---------|
| Классы, интерфейсы, типы, enum | `UpperCamelCase` | `UserService`, `HttpClient` |
| Переменные, параметры, функции, методы | `lowerCamelCase` | `userId`, `getUserById` |
| Глобальные константы, enum values | `CONSTANT_CASE` | `MAX_RETRIES`, `API_URL` |
| Приватные поля | `lowerCamelCase` | `private userId` (НЕ `_userId`) |

### Правила

```typescript
// ═══════════════════════════════════════════════════════════════════
// ✅ ПРАВИЛЬНО
// ═══════════════════════════════════════════════════════════════════

// Константы — CONSTANT_CASE
const MAX_CONNECTIONS = 100;
const DEFAULT_TIMEOUT_MS = 30_000;

// Классы — UpperCamelCase
class UserRepository {
  // Приватные поля — БЕЗ подчёркивания
  private readonly cache = new Map<string, User>();

  // Методы — lowerCamelCase
  async getUserById(userId: string): Promise<User | undefined> {
    return this.cache.get(userId);
  }
}

// Интерфейсы — UpperCamelCase, БЕЗ префикса I
interface UserService {
  getUser(id: string): Promise<User>;
}

// Типы — UpperCamelCase
type UserId = string;
type UserCallback = (user: User) => void;

// Enum — UpperCamelCase, значения CONSTANT_CASE
enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  GUEST = 'guest',
}

// Аббревиатуры как слова
function loadHttpUrl(url: string): void {}  // НЕ loadHTTPURL
class XmlParser {}                          // НЕ XMLParser

// ═══════════════════════════════════════════════════════════════════
// ❌ НЕПРАВИЛЬНО
// ═══════════════════════════════════════════════════════════════════

const max_connections = 100;      // ❌ snake_case
class user_repository {}          // ❌ snake_case
interface IUserService {}         // ❌ Префикс I
private _cache = new Map();       // ❌ Подчёркивание
function loadHTTPURL() {}         // ❌ Аббревиатура не как слово
```

---

## 📦 ИМПОРТЫ И ЭКСПОРТЫ

### Порядок импортов

```typescript
// ═══════════════════════════════════════════════════════════════════
// 1. Сторонние библиотеки (node_modules)
// ═══════════════════════════════════════════════════════════════════
import React, {useState, useEffect} from 'react';
import {z} from 'zod';
import * as path from 'path';

// ═══════════════════════════════════════════════════════════════════
// 2. Абсолютные импорты из проекта (aliases)
// ═══════════════════════════════════════════════════════════════════
import {UserService} from '@/services/user';
import {Button} from '@/components/ui';
import type {User} from '@/types';

// ═══════════════════════════════════════════════════════════════════
// 3. Относительные импорты
// ═══════════════════════════════════════════════════════════════════
import {validateEmail} from './utils';
import {UserCard} from './UserCard';
```

### Named vs Default exports

```typescript
// ═══════════════════════════════════════════════════════════════════
// ✅ ПРАВИЛЬНО — Named exports
// ═══════════════════════════════════════════════════════════════════

// user.ts
export class UserService {
  // ...
}

export interface User {
  id: string;
  name: string;
}

export const DEFAULT_USER: User = {
  id: '',
  name: 'Guest',
};

// Импорт
import {UserService, User, DEFAULT_USER} from './user';

// ═══════════════════════════════════════════════════════════════════
// ❌ НЕПРАВИЛЬНО — Default exports
// ═══════════════════════════════════════════════════════════════════

// user.ts
export default class UserService {}  // ❌

// Импорт — можно назвать как угодно, это плохо
import Foo from './user';  // Где тут UserService?
import Bar from './user';  // Тот же файл, другое имя
```

**Почему Named exports лучше:**
- Ошибка при неправильном имени импорта
- Автодополнение IDE работает лучше
- Рефакторинг проще

### import type

```typescript
// ═══════════════════════════════════════════════════════════════════
// Используйте import type для типов
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
import type {User, UserRole} from './types';
import {UserService} from './services';

// Или комбинированно
import {UserService, type User} from './user';

// ❌ Не импортируйте типы как значения, если не нужны в runtime
import {User} from './types';  // User используется только как тип
```

---

## 🏷 ТИПИЗАЦИЯ

### Базовые правила

```typescript
// ═══════════════════════════════════════════════════════════════════
// Используйте type inference где возможно
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО — тип выводится автоматически
const count = 15;
const name = 'John';
const isActive = true;
const users = new Set<string>();

// ❌ НЕПРАВИЛЬНО — избыточная типизация
const count: number = 15;
const name: string = 'John';
const isActive: boolean = true;

// ═══════════════════════════════════════════════════════════════════
// Явно типизируйте сложные структуры
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО — явный тип помогает читаемости
const config: ServerConfig = {
  host: 'localhost',
  port: 3000,
  ssl: false,
};

// ✅ Типизируйте параметры функций и (опционально) возвращаемые значения
function processUser(user: User): ProcessedUser {
  return {
    ...user,
    processed: true,
  };
}
```

### interface vs type

```typescript
// ═══════════════════════════════════════════════════════════════════
// Используйте interface для объектов
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
interface User {
  id: string;
  name: string;
  email: string;
}

interface UserService {
  getUser(id: string): Promise<User>;
  updateUser(id: string, data: Partial<User>): Promise<User>;
}

// Расширение интерфейсов
interface AdminUser extends User {
  permissions: string[];
}

// ═══════════════════════════════════════════════════════════════════
// Используйте type для unions, intersections, примитивов
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
type UserId = string;
type UserRole = 'admin' | 'user' | 'guest';
type Callback<T> = (value: T) => void;
type UserOrNull = User | null;

// ❌ НЕПРАВИЛЬНО — type для объектов
type User = {
  id: string;
  name: string;
};
```

### Массивы

```typescript
// ═══════════════════════════════════════════════════════════════════
// T[] для простых типов, Array<T> для сложных
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
const names: string[] = [];
const users: User[] = [];
const matrix: number[][] = [];

// ✅ Array<T> для сложных типов
const pairs: Array<[string, number]> = [];
const callbacks: Array<() => void> = [];
const results: Array<{success: boolean; data?: unknown}> = [];

// ❌ НЕПРАВИЛЬНО
const names: Array<string> = [];  // Слишком verbose для простого типа
const pairs: [string, number][] = [];  // Трудно читать
```

### null и undefined

```typescript
// ═══════════════════════════════════════════════════════════════════
// Предпочитайте undefined для отсутствия значения
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО — используйте optional
interface User {
  name: string;
  middleName?: string;  // undefined, если отсутствует
}

function getUser(id: string): User | undefined {
  return users.get(id);  // undefined если не найден
}

// ✅ null — когда API возвращает null (DOM, JSON)
const element = document.getElementById('app');  // HTMLElement | null

// ═══════════════════════════════════════════════════════════════════
// Проверка на null/undefined
// ═══════════════════════════════════════════════════════════════════

// ✅ Используйте == null для проверки на null И undefined
if (value == null) {
  // value is null or undefined
}

// ✅ Используйте truthiness для boolean контекста
if (user) {
  // user is truthy (not null, undefined, '', 0, false)
}

// ✅ Optional chaining
const name = user?.profile?.name;
const first = items?.[0];
const result = callback?.();

// ✅ Nullish coalescing
const name = user.name ?? 'Anonymous';
const count = config.count ?? 0;
```

---

## 📝 ФУНКЦИИ

### Объявление функций

```typescript
// ═══════════════════════════════════════════════════════════════════
// Используйте function declaration для именованных функций
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО — function declaration
function calculateTotal(items: Item[]): number {
  return items.reduce((sum, item) => sum + item.price, 0);
}

// ✅ Arrow function — для callbacks и коротких функций
const doubled = numbers.map((n) => n * 2);

items.forEach((item) => {
  processItem(item);
});

// ✅ Arrow function — когда нужен явный тип
const handler: EventHandler = (event) => {
  console.log(event.target);
};

// ═══════════════════════════════════════════════════════════════════
// ❌ НЕПРАВИЛЬНО
// ═══════════════════════════════════════════════════════════════════

// ❌ Не используйте function expression
const calculateTotal = function(items: Item[]): number {
  return items.reduce((sum, item) => sum + item.price, 0);
};

// ❌ Не присваивайте именованную функцию переменной
const calculate = () => {
  return 42;
};
```

### Arrow functions

```typescript
// ═══════════════════════════════════════════════════════════════════
// Concise body vs Block body
// ═══════════════════════════════════════════════════════════════════

// ✅ Concise body — когда возвращаем значение
const double = (n: number) => n * 2;
const getName = (user: User) => user.name;

// ✅ Block body — когда есть side effects или сложная логика
const processItems = (items: Item[]) => {
  const validated = items.filter((item) => item.isValid);
  return validated.map((item) => transform(item));
};

// ✅ Block body — когда void (нет возвращаемого значения)
promise.then((result) => {
  console.log(result);
});

// ❌ НЕПРАВИЛЬНО — concise body с side effects
promise.then((result) => console.log(result));  // Может случайно вернуть значение

// ✅ Используйте void для явного указания
promise.then((result) => void console.log(result));
```

### Параметры функций

```typescript
// ═══════════════════════════════════════════════════════════════════
// Default параметры
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
function createUser(name: string, role: UserRole = UserRole.USER): User {
  return {name, role};
}

function fetchData(url: string, options: RequestOptions = {}): Promise<Data> {
  // ...
}

// ═══════════════════════════════════════════════════════════════════
// Деструктуризация параметров
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО — деструктуризация с типом
function processUser({name, email, age = 0}: {
  name: string;
  email: string;
  age?: number;
}): void {
  // ...
}

// ✅ Лучше — отдельный interface
interface ProcessUserParams {
  name: string;
  email: string;
  age?: number;
}

function processUser({name, email, age = 0}: ProcessUserParams): void {
  // ...
}

// ═══════════════════════════════════════════════════════════════════
// Rest параметры
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
function log(message: string, ...args: unknown[]): void {
  console.log(message, ...args);
}

// ✅ Spread при вызове
const numbers = [1, 2, 3];
Math.max(...numbers);
```

---

## 🏗 КЛАССЫ

### Структура класса

```typescript
// ═══════════════════════════════════════════════════════════════════
// Порядок членов класса
// ═══════════════════════════════════════════════════════════════════

class UserService {
  // 1. Static поля
  static readonly DEFAULT_TIMEOUT = 5000;

  // 2. Instance поля (в порядке: public, protected, private)
  readonly name: string;
  protected cache = new Map<string, User>();
  private readonly db: Database;

  // 3. Конструктор
  constructor(db: Database) {
    this.db = db;
    this.name = 'UserService';
  }

  // 4. Static методы
  static create(config: Config): UserService {
    return new UserService(new Database(config));
  }

  // 5. Instance методы (в порядке: public, protected, private)
  async getUser(id: string): Promise<User | undefined> {
    return this.fetchFromCache(id) ?? this.fetchFromDb(id);
  }

  protected async fetchFromCache(id: string): Promise<User | undefined> {
    return this.cache.get(id);
  }

  private async fetchFromDb(id: string): Promise<User | undefined> {
    return this.db.query('SELECT * FROM users WHERE id = ?', [id]);
  }
}
```

### Parameter properties

```typescript
// ═══════════════════════════════════════════════════════════════════
// Используйте parameter properties для краткости
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО — parameter properties
class UserService {
  constructor(
    private readonly db: Database,
    private readonly cache: Cache,
  ) {}
}

// ❌ НЕПРАВИЛЬНО — избыточно
class UserService {
  private readonly db: Database;
  private readonly cache: Cache;

  constructor(db: Database, cache: Cache) {
    this.db = db;
    this.cache = cache;
  }
}
```

### readonly

```typescript
// ═══════════════════════════════════════════════════════════════════
// Используйте readonly для неизменяемых полей
// ═══════════════════════════════════════════════════════════════════

class Config {
  // ✅ readonly для полей, которые не меняются после конструктора
  readonly apiUrl: string;
  readonly timeout: number;

  // Обычное поле — может измениться
  retryCount = 3;

  constructor(apiUrl: string, timeout: number) {
    this.apiUrl = apiUrl;
    this.timeout = timeout;
  }
}
```

### Visibility

```typescript
// ═══════════════════════════════════════════════════════════════════
// НЕ используйте public — это default
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
class User {
  name: string;                    // public by default
  protected id: string;
  private password: string;

  constructor(public readonly email: string) {}  // public в parameter property OK
}

// ❌ НЕПРАВИЛЬНО
class User {
  public name: string;             // ❌ public избыточен
  public readonly email: string;   // ❌ public избыточен
}
```

---

## 🔀 CONTROL FLOW

### Фигурные скобки

```typescript
// ═══════════════════════════════════════════════════════════════════
// ВСЕГДА используйте фигурные скобки
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
if (condition) {
  doSomething();
}

for (const item of items) {
  process(item);
}

while (hasMore) {
  fetchNext();
}

// ✅ Исключение — однострочный if без else
if (condition) return early;
if (error) throw error;

// ❌ НЕПРАВИЛЬНО
if (condition)
  doSomething();

for (const item of items)
  process(item);
```

### Сравнения

```typescript
// ═══════════════════════════════════════════════════════════════════
// ВСЕГДА используйте === и !==
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
if (value === 'active') {}
if (count !== 0) {}

// ✅ Исключение — проверка на null/undefined
if (value == null) {}   // Проверяет и null, и undefined
if (value != null) {}

// ❌ НЕПРАВИЛЬНО
if (value == 'active') {}
if (count != 0) {}
```

### Циклы

```typescript
// ═══════════════════════════════════════════════════════════════════
// Предпочитайте for...of
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО — for...of для массивов
for (const item of items) {
  process(item);
}

// ✅ С индексом
for (const [index, item] of items.entries()) {
  console.log(index, item);
}

// ✅ for...of для Object.keys/values/entries
for (const key of Object.keys(obj)) {
  console.log(key, obj[key]);
}

for (const [key, value] of Object.entries(obj)) {
  console.log(key, value);
}

// ✅ Обычный for — когда нужен контроль над индексом
for (let i = 0; i < items.length; i += 2) {
  process(items[i]);
}

// ❌ НЕПРАВИЛЬНО — for...in для массивов (даёт индексы как строки!)
for (const i in items) {
  // i — это '0', '1', '2', а не 0, 1, 2
}
```

### Switch

```typescript
// ═══════════════════════════════════════════════════════════════════
// Switch ВСЕГДА с default
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
switch (status) {
  case Status.PENDING:
    return 'Pending...';
  case Status.ACTIVE:
    return 'Active';
  case Status.COMPLETED:
    return 'Done';
  default:
    // Exhaustiveness check
    const _exhaustive: never = status;
    throw new Error(`Unknown status: ${status}`);
}

// ✅ Fall-through только для пустых case
switch (day) {
  case 'Saturday':
  case 'Sunday':
    return 'Weekend';
  default:
    return 'Weekday';
}
```

---

## 🔥 ОБРАБОТКА ОШИБОК

### Throw только Error

```typescript
// ═══════════════════════════════════════════════════════════════════
// ВСЕГДА throw только Error (или его подклассы)
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
throw new Error('Something went wrong');
throw new TypeError('Expected string');
throw new ValidationError('Invalid email format');

// ✅ Кастомные ошибки
class ValidationError extends Error {
  constructor(
    message: string,
    readonly field: string,
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}

throw new ValidationError('Invalid email', 'email');

// ❌ НЕПРАВИЛЬНО
throw 'error';           // ❌ строка
throw 404;               // ❌ число
throw {message: 'err'};  // ❌ объект
```

### try/catch

```typescript
// ═══════════════════════════════════════════════════════════════════
// Типизируйте catch как unknown
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
try {
  await fetchData();
} catch (error: unknown) {
  // Type guard
  if (error instanceof Error) {
    console.error(error.message);
  } else {
    console.error('Unknown error:', error);
  }
}

// ✅ С helper функцией
function isError(value: unknown): value is Error {
  return value instanceof Error;
}

try {
  await fetchData();
} catch (error: unknown) {
  if (isError(error)) {
    logger.error(error.message, {stack: error.stack});
  }
  throw error;  // Re-throw если не можем обработать
}

// ❌ НЕПРАВИЛЬНО — пустой catch
try {
  await fetchData();
} catch {
  // Молчаливое игнорирование ошибок
}
```

### Promise rejection

```typescript
// ═══════════════════════════════════════════════════════════════════
// Reject только с Error
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
new Promise((resolve, reject) => {
  if (error) {
    reject(new Error('Operation failed'));
  }
  resolve(result);
});

// ✅ Async/await
async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/users/${id}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

// ❌ НЕПРАВИЛЬНО
Promise.reject('error');           // ❌ строка
Promise.reject({code: 'ERR'});     // ❌ объект
```

---

## 📝 КОММЕНТАРИИ И ДОКУМЕНТАЦИЯ

### JSDoc

```typescript
// ═══════════════════════════════════════════════════════════════════
// JSDoc для публичного API
// ═══════════════════════════════════════════════════════════════════

/**
 * Fetches user data from the API.
 *
 * This function handles caching and retries automatically.
 * Throws if the user is not found after all retries.
 *
 * @param userId - The unique identifier of the user.
 * @param options - Optional configuration.
 * @returns The user data if found.
 * @throws {NotFoundError} If user doesn't exist.
 * @throws {NetworkError} If API is unreachable.
 *
 * @example
 * ```typescript
 * const user = await fetchUser('123');
 * console.log(user.name);
 * ```
 */
async function fetchUser(
  userId: string,
  options?: FetchOptions,
): Promise<User> {
  // ...
}

// ═══════════════════════════════════════════════════════════════════
// НЕ дублируйте типы в JSDoc
// ═══════════════════════════════════════════════════════════════════

// ❌ НЕПРАВИЛЬНО — типы уже в TypeScript
/**
 * @param {string} userId - The user ID.
 * @returns {Promise<User>} The user.
 */
async function fetchUser(userId: string): Promise<User> {}

// ✅ ПРАВИЛЬНО — только описание
/**
 * Fetches user by ID.
 * @param userId - Unique identifier of the user.
 */
async function fetchUser(userId: string): Promise<User> {}
```

### Комментарии

```typescript
// ═══════════════════════════════════════════════════════════════════
// // для обычных комментариев
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
// Calculate the total including tax
const total = subtotal * (1 + TAX_RATE);

// TODO(user): Implement retry logic
// FIXME(user): Handle edge case when array is empty

// ❌ НЕПРАВИЛЬНО — бесполезные комментарии
const count = 0;  // Initialize count to zero
i++;              // Increment i
```

---

## ⚡ ASYNC/AWAIT

### Основные правила

```typescript
// ═══════════════════════════════════════════════════════════════════
// Предпочитайте async/await над .then()
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
async function fetchUserData(userId: string): Promise<UserData> {
  const user = await fetchUser(userId);
  const posts = await fetchUserPosts(userId);
  return {user, posts};
}

// ❌ НЕПРАВИЛЬНО — цепочка .then()
function fetchUserData(userId: string): Promise<UserData> {
  return fetchUser(userId)
    .then((user) => fetchUserPosts(userId)
      .then((posts) => ({user, posts})));
}

// ═══════════════════════════════════════════════════════════════════
// Параллельное выполнение
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО — Promise.all для независимых операций
async function fetchAllData(userId: string): Promise<AllData> {
  const [user, posts, comments] = await Promise.all([
    fetchUser(userId),
    fetchPosts(userId),
    fetchComments(userId),
  ]);
  return {user, posts, comments};
}

// ❌ НЕПРАВИЛЬНО — последовательное выполнение независимых операций
async function fetchAllData(userId: string): Promise<AllData> {
  const user = await fetchUser(userId);
  const posts = await fetchPosts(userId);      // Ждёт user, хотя не зависит
  const comments = await fetchComments(userId); // Ждёт posts, хотя не зависит
  return {user, posts, comments};
}

// ═══════════════════════════════════════════════════════════════════
// Promise.allSettled для обработки частичных ошибок
// ═══════════════════════════════════════════════════════════════════

const results = await Promise.allSettled([
  fetchUser('1'),
  fetchUser('2'),
  fetchUser('3'),
]);

const users = results
  .filter((r): r is PromiseFulfilledResult<User> => r.status === 'fulfilled')
  .map((r) => r.value);

const errors = results
  .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
  .map((r) => r.reason);
```

---

## 🔒 TYPE SAFETY

### Type guards

```typescript
// ═══════════════════════════════════════════════════════════════════
// Пользовательские type guards
// ═══════════════════════════════════════════════════════════════════

// ✅ ПРАВИЛЬНО
function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'name' in value
  );
}

// Использование
function processValue(value: unknown): void {
  if (isString(value)) {
    console.log(value.toUpperCase());  // value is string
  }

  if (isUser(value)) {
    console.log(value.name);  // value is User
  }
}
```

### Type assertions

```typescript
// ═══════════════════════════════════════════════════════════════════
// Избегайте type assertions, используйте type guards
// ═══════════════════════════════════════════════════════════════════

// ❌ НЕПРАВИЛЬНО — type assertion без проверки
const user = response.data as User;
const element = document.getElementById('app') as HTMLDivElement;

// ✅ ПРАВИЛЬНО — проверка + assertion с комментарием
const data = response.data;
if (!isUser(data)) {
  throw new Error('Invalid user data');
}
// data is now User

// ✅ Если assertion неизбежен — добавьте комментарий
// Element exists because it's defined in index.html
const element = document.getElementById('app') as HTMLDivElement;

// ═══════════════════════════════════════════════════════════════════
// НЕ используйте ! без веской причины
// ═══════════════════════════════════════════════════════════════════

// ❌ НЕПРАВИЛЬНО
const name = user.profile!.name!;

// ✅ ПРАВИЛЬНО — optional chaining + default
const name = user.profile?.name ?? 'Anonymous';

// ✅ Если ! неизбежен — добавьте комментарий
// Map always contains this key after initialization
const value = map.get(key)!;
```

---

## 🚫 ЗАПРЕЩЁННЫЕ ПРАКТИКИ

```typescript
// ═══════════════════════════════════════════════════════════════════
// ❌ НИКОГДА не используйте
// ═══════════════════════════════════════════════════════════════════

// ❌ var
var x = 1;  // Используйте const или let

// ❌ any без явной необходимости
function process(data: any) {}  // Используйте unknown

// ❌ @ts-ignore / @ts-nocheck
// @ts-ignore
const x: string = 123;

// ❌ eval / new Function
eval('alert("xss")');
new Function('return 1')();

// ❌ delete для удаления свойств (в большинстве случаев)
delete obj.property;  // Используйте деструктуризацию или Object.assign

// ❌ with
with (obj) {}

// ❌ arguments (используйте rest parameters)
function sum() {
  return Array.from(arguments).reduce((a, b) => a + b, 0);
}

// ✅ ПРАВИЛЬНО
function sum(...numbers: number[]): number {
  return numbers.reduce((a, b) => a + b, 0);
}

// ❌ namespace
namespace MyNamespace {}  // Используйте ES modules

// ❌ const enum
const enum Status {}  // Используйте обычный enum

// ❌ Array constructor
new Array(3);           // [undefined, undefined, undefined]
new Array(1, 2, 3);     // [1, 2, 3] — непоследовательное поведение

// ✅ ПРАВИЛЬНО
Array.from({length: 3}, () => 0);  // [0, 0, 0]
[1, 2, 3];
```

---

## 📁 СТРУКТУРА ФАЙЛА

```typescript
// ═══════════════════════════════════════════════════════════════════
// Порядок элементов в файле
// ═══════════════════════════════════════════════════════════════════

// 1. Copyright/License (если есть)
/**
 * @license
 * Copyright 2024 BIOTACT
 */

// 2. @fileoverview (опционально)
/**
 * @fileoverview User service module.
 */

// 3. Imports
import type {Database} from '@/types';
import {logger} from '@/utils';

// 4. Types/Interfaces (локальные для файла)
interface UserData {
  id: string;
  name: string;
}

// 5. Constants
const DEFAULT_LIMIT = 10;
const CACHE_TTL_MS = 60_000;

// 6. Classes/Functions
export class UserService {
  // ...
}

export function createUserService(db: Database): UserService {
  return new UserService(db);
}

// 7. Exports (если не inline)
// export {UserService, createUserService};
```

---

## 🛠 ИНСТРУМЕНТЫ

### ESLint конфигурация

```javascript
// eslint.config.js (ESLint 9+ flat config)
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        project: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // Google Style специфичные правила
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/no-unused-vars': ['error', {argsIgnorePattern: '^_'}],
      '@typescript-eslint/consistent-type-imports': ['error', {prefer: 'type-imports'}],
      '@typescript-eslint/consistent-type-definitions': ['error', 'interface'],
      '@typescript-eslint/array-type': ['error', {default: 'array-simple'}],
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/await-thenable': 'error',
      'no-console': ['warn', {allow: ['warn', 'error']}],
      'eqeqeq': ['error', 'always', {null: 'ignore'}],
    },
  },
);
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "lib": ["ES2022"],

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true,

    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,

    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,

    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### Prettier (опционально)

```json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "bracketSpacing": false,
  "printWidth": 100,
  "tabWidth": 2
}
```

---

## ✅ ЧЕКЛИСТ ПЕРЕД КОММИТОМ

```
□ Нет any (только unknown или конкретные типы)
□ Нет @ts-ignore
□ Нет var (только const/let)
□ Named exports (не default)
□ interface для объектов, type для остального
□ === везде (кроме == null)
□ Фигурные скобки для всех блоков
□ throw только Error
□ catch типизирован как unknown
□ Нет console.log (только logger)
□ ESLint без ошибок
□ TypeScript без ошибок (strict: true)
```

---

## 🚀 БЫСТРЫЙ ПРОМПТ ДЛЯ CLAUDE CODE

```
TypeScript проект. Следуй Google TypeScript Style Guide:

СТИЛЬ:
- const/let (НЕ var), 2 пробела, одинарные кавычки
- Named exports (НЕ default), точка с запятой обязательна
- interface для объектов, type для unions/primitives
- T[] для простых типов, Array<T> для сложных

ИМЕНОВАНИЕ:
- UpperCamelCase: классы, интерфейсы, типы, enum
- lowerCamelCase: переменные, функции, методы
- CONSTANT_CASE: глобальные константы

ОБЯЗАТЕЛЬНО:
✅ === и !== (кроме == null)
✅ Фигурные скобки для всех блоков
✅ throw только Error
✅ catch (error: unknown)
✅ import type для типов
✅ async/await вместо .then()
✅ Optional chaining (?.) и nullish coalescing (??)

ЗАПРЕЩЕНО:
❌ any (используй unknown)
❌ @ts-ignore / @ts-nocheck
❌ default export
❌ var
❌ == / != (кроме проверки на null)
❌ eval() / new Function()
```

---

**Версия:** 1.0
**Дата:** 01.12.2025
**Референс:** Google TypeScript Style Guide
