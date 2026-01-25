# REACT CODE STYLE GUIDE
## Для Claude Code — React.dev + Zustand

> **Цель:** Единый стиль React кода во всех проектах
> **Референс:** React.dev (официальная документация) + Zustand для state management
> **Версия React:** 18+, TypeScript

---

## 🎯 КЛЮЧЕВЫЕ ПРИНЦИПЫ

```
ВСЕГДА                              НИКОГДА
────────────────────────────────    ────────────────────────────────
✓ Функциональные компоненты         ✗ Классовые компоненты
✓ TypeScript с strict mode          ✗ any в пропсах/стейте
✓ Named exports компонентов         ✗ Default exports
✓ Hooks на верхнем уровне           ✗ Hooks в условиях/циклах
✓ Иммутабельные обновления стейта   ✗ Прямая мутация state/props
✓ Zustand для глобального стейта    ✗ Prop drilling > 2 уровней
✓ Композиция компонентов            ✗ Глубокое наследование
✓ Мемоизация дорогих вычислений     ✗ Преждевременная оптимизация
✓ Семантический HTML                ✗ <div> для всего
✓ Единый источник правды            ✗ Дублирование стейта
```

---

## 📦 СТРУКТУРА КОМПОНЕНТА

### Порядок элементов в файле

```tsx
// ═══════════════════════════════════════════════════════════════════
// 1. Imports
// ═══════════════════════════════════════════════════════════════════
import {useState, useEffect, useCallback, useMemo} from 'react';
import type {FC, ReactNode} from 'react';

// External libraries
import {useQuery} from '@tanstack/react-query';
import {z} from 'zod';

// Internal imports
import {Button} from '@/components/ui';
import {useUserStore} from '@/stores/user';
import type {User} from '@/types';

// Relative imports
import {UserAvatar} from './UserAvatar';
import styles from './UserCard.module.css';

// ═══════════════════════════════════════════════════════════════════
// 2. Types/Interfaces
// ═══════════════════════════════════════════════════════════════════
interface UserCardProps {
  user: User;
  variant?: 'default' | 'compact';
  onSelect?: (user: User) => void;
  children?: ReactNode;
}

// ═══════════════════════════════════════════════════════════════════
// 3. Constants
// ═══════════════════════════════════════════════════════════════════
const ANIMATION_DURATION_MS = 300;
const MAX_NAME_LENGTH = 50;

// ═══════════════════════════════════════════════════════════════════
// 4. Helper functions (если нужны только этому компоненту)
// ═══════════════════════════════════════════════════════════════════
function formatUserName(name: string): string {
  return name.length > MAX_NAME_LENGTH
    ? `${name.slice(0, MAX_NAME_LENGTH)}...`
    : name;
}

// ═══════════════════════════════════════════════════════════════════
// 5. Component
// ═══════════════════════════════════════════════════════════════════
export function UserCard({
  user,
  variant = 'default',
  onSelect,
  children,
}: UserCardProps) {
  // 5.1. Hooks (в определённом порядке)
  // — Zustand/Redux stores
  const currentUser = useUserStore((state) => state.currentUser);

  // — React Query / data fetching
  const {data: posts} = useQuery({
    queryKey: ['posts', user.id],
    queryFn: () => fetchUserPosts(user.id),
  });

  // — Local state
  const [isExpanded, setIsExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // — Refs
  const cardRef = useRef<HTMLDivElement>(null);

  // — Computed values (useMemo)
  const displayName = useMemo(
    () => formatUserName(user.name),
    [user.name]
  );

  const isOwnProfile = useMemo(
    () => currentUser?.id === user.id,
    [currentUser?.id, user.id]
  );

  // — Callbacks (useCallback)
  const handleSelect = useCallback(() => {
    onSelect?.(user);
  }, [onSelect, user]);

  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  // — Effects
  useEffect(() => {
    if (isExpanded) {
      cardRef.current?.scrollIntoView({behavior: 'smooth'});
    }
  }, [isExpanded]);

  // 5.2. Early returns
  if (!user) {
    return null;
  }

  // 5.3. Render
  return (
    <article
      ref={cardRef}
      className={styles.card}
      data-variant={variant}
      aria-expanded={isExpanded}
    >
      <header className={styles.header}>
        <UserAvatar user={user} size="md" />
        <h2 className={styles.name}>{displayName}</h2>
        {isOwnProfile && <span className={styles.badge}>You</span>}
      </header>

      <div className={styles.content}>
        {children}
      </div>

      <footer className={styles.footer}>
        <Button onClick={handleSelect}>Select</Button>
        <Button variant="ghost" onClick={handleToggle}>
          {isExpanded ? 'Collapse' : 'Expand'}
        </Button>
      </footer>
    </article>
  );
}
```

---

## 🏷 ТИПИЗАЦИЯ КОМПОНЕНТОВ

### Props

```tsx
// ═══════════════════════════════════════════════════════════════════
// ✅ ПРАВИЛЬНО — interface для props
// ═══════════════════════════════════════════════════════════════════

interface ButtonProps {
  // Обязательные props
  children: ReactNode;

  // Опциональные props с дефолтами в деструктуризации
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;

  // Event handlers
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;

  // Расширение HTML атрибутов (когда нужно)
  className?: string;
  type?: 'button' | 'submit' | 'reset';
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  className,
  type = 'button',
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={className}
      data-variant={variant}
      data-size={size}
    >
      {loading ? <Spinner /> : children}
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════
// ✅ Расширение нативных HTML props
// ═══════════════════════════════════════════════════════════════════

interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label: string;
  error?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Input({
  label,
  error,
  size = 'md',
  id,
  className,
  ...rest  // Остальные HTML атрибуты
}: InputProps) {
  const inputId = id ?? useId();

  return (
    <div className={className} data-size={size}>
      <label htmlFor={inputId}>{label}</label>
      <input id={inputId} aria-invalid={!!error} {...rest} />
      {error && <span role="alert">{error}</span>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// ✅ Полиморфные компоненты (as prop)
// ═══════════════════════════════════════════════════════════════════

type BoxProps<T extends React.ElementType> = {
  as?: T;
  children: ReactNode;
} & Omit<React.ComponentPropsWithoutRef<T>, 'as' | 'children'>;

export function Box<T extends React.ElementType = 'div'>({
  as,
  children,
  ...props
}: BoxProps<T>) {
  const Component = as ?? 'div';
  return <Component {...props}>{children}</Component>;
}

// Использование
<Box as="section" className="container">Content</Box>
<Box as="article">Article</Box>
<Box as={Link} href="/about">Link</Box>
```

### Children patterns

```tsx
// ═══════════════════════════════════════════════════════════════════
// Разные типы children
// ═══════════════════════════════════════════════════════════════════

// ReactNode — любой валидный JSX
interface CardProps {
  children: ReactNode;
}

// ReactElement — только React элементы (не строки/числа)
interface TabsProps {
  children: ReactElement<TabProps> | ReactElement<TabProps>[];
}

// Render props pattern
interface DataListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
  renderEmpty?: () => ReactNode;
}

export function DataList<T>({
  items,
  renderItem,
  renderEmpty,
}: DataListProps<T>) {
  if (items.length === 0) {
    return renderEmpty?.() ?? <p>No items</p>;
  }

  return (
    <ul>
      {items.map((item, index) => (
        <li key={index}>{renderItem(item, index)}</li>
      ))}
    </ul>
  );
}

// Использование
<DataList
  items={users}
  renderItem={(user) => <UserCard user={user} />}
  renderEmpty={() => <EmptyState />}
/>
```

---

## 🪝 HOOKS

### Rules of Hooks

```tsx
// ═══════════════════════════════════════════════════════════════════
// ✅ ПРАВИЛЬНО — Hooks на верхнем уровне
// ═══════════════════════════════════════════════════════════════════

function UserProfile({userId}: {userId: string}) {
  // ✅ Все hooks в начале, безусловно
  const [name, setName] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  const user = useUserStore((state) => state.users[userId]);

  useEffect(() => {
    if (userId) {
      fetchUser(userId);
    }
  }, [userId]);

  // Условная логика ПОСЛЕ hooks
  if (!user) {
    return <Loading />;
  }

  return <div>{user.name}</div>;
}

// ═══════════════════════════════════════════════════════════════════
// ❌ НЕПРАВИЛЬНО — Hooks в условиях
// ═══════════════════════════════════════════════════════════════════

function BadComponent({userId}: {userId: string | null}) {
  // ❌ Hook в условии — нарушает правила
  if (userId) {
    const [name, setName] = useState('');  // ❌
  }

  // ❌ Hook после раннего return
  if (!userId) {
    return null;
  }
  const [data, setData] = useState(null);  // ❌

  return <div>{data}</div>;
}
```

### useState

```tsx
// ═══════════════════════════════════════════════════════════════════
// Правильное использование useState
// ═══════════════════════════════════════════════════════════════════

// ✅ Отдельные state для разных данных
const [name, setName] = useState('');
const [email, setEmail] = useState('');
const [age, setAge] = useState(0);

// ✅ Объединённый state для связанных данных
interface FormData {
  name: string;
  email: string;
  age: number;
}

const [formData, setFormData] = useState<FormData>({
  name: '',
  email: '',
  age: 0,
});

// ✅ Функциональное обновление для зависимости от предыдущего значения
const handleIncrement = () => {
  setCount((prev) => prev + 1);
};

// ✅ Lazy initialization для дорогих вычислений
const [data, setData] = useState(() => {
  return expensiveComputation();
});

// ═══════════════════════════════════════════════════════════════════
// ❌ НЕПРАВИЛЬНО
// ═══════════════════════════════════════════════════════════════════

// ❌ Дорогое вычисление без lazy init
const [data, setData] = useState(expensiveComputation());  // Выполняется каждый рендер!

// ❌ Мутация объекта напрямую
const handleUpdate = () => {
  formData.name = 'New Name';  // ❌ Мутация!
  setFormData(formData);        // ❌ Тот же референс!
};

// ✅ ПРАВИЛЬНО — новый объект
const handleUpdate = () => {
  setFormData((prev) => ({
    ...prev,
    name: 'New Name',
  }));
};
```

### useEffect

```tsx
// ═══════════════════════════════════════════════════════════════════
// Правильное использование useEffect
// ═══════════════════════════════════════════════════════════════════

// ✅ Fetch data
useEffect(() => {
  const controller = new AbortController();

  async function fetchData() {
    try {
      const response = await fetch(`/api/users/${userId}`, {
        signal: controller.signal,
      });
      const data = await response.json();
      setUser(data);
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        setError(error.message);
      }
    }
  }

  fetchData();

  // Cleanup
  return () => {
    controller.abort();
  };
}, [userId]);

// ✅ Event listener
useEffect(() => {
  function handleResize() {
    setWindowWidth(window.innerWidth);
  }

  window.addEventListener('resize', handleResize);

  return () => {
    window.removeEventListener('resize', handleResize);
  };
}, []);

// ✅ Синхронизация с внешней системой
useEffect(() => {
  const subscription = externalStore.subscribe((state) => {
    setLocalState(state);
  });

  return () => {
    subscription.unsubscribe();
  };
}, []);

// ═══════════════════════════════════════════════════════════════════
// ❌ НЕПРАВИЛЬНО — Это НЕ нужно делать в useEffect
// ═══════════════════════════════════════════════════════════════════

// ❌ Трансформация данных для рендера — используйте useMemo
useEffect(() => {
  setFilteredItems(items.filter((item) => item.active));
}, [items]);

// ✅ ПРАВИЛЬНО
const filteredItems = useMemo(
  () => items.filter((item) => item.active),
  [items]
);

// ❌ Обработка user events — используйте event handlers
useEffect(() => {
  if (submitted) {
    sendToServer(formData);
    setSubmitted(false);
  }
}, [submitted, formData]);

// ✅ ПРАВИЛЬНО
const handleSubmit = async () => {
  await sendToServer(formData);
};

// ❌ Инициализация, которая не зависит от props
useEffect(() => {
  setDefaultValue(calculateDefault());
}, []);

// ✅ ПРАВИЛЬНО — в useState с lazy init
const [value, setValue] = useState(() => calculateDefault());
```

### useCallback и useMemo

```tsx
// ═══════════════════════════════════════════════════════════════════
// Когда использовать useCallback
// ═══════════════════════════════════════════════════════════════════

// ✅ Передача callback в мемоизированный дочерний компонент
const MemoizedChild = memo(function Child({onClick}: {onClick: () => void}) {
  return <button onClick={onClick}>Click</button>;
});

function Parent() {
  // ✅ useCallback нужен, чтобы Child не перерендеривался
  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []);

  return <MemoizedChild onClick={handleClick} />;
}

// ✅ Callback в зависимостях useEffect
function Component({userId}: {userId: string}) {
  const fetchUser = useCallback(async () => {
    const response = await fetch(`/api/users/${userId}`);
    return response.json();
  }, [userId]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);
}

// ❌ НЕ нужен useCallback
function Component() {
  // ❌ Не передаётся детям, не в dependencies
  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []);  // Бессмысленная мемоизация

  return <button onClick={handleClick}>Click</button>;
}

// ═══════════════════════════════════════════════════════════════════
// Когда использовать useMemo
// ═══════════════════════════════════════════════════════════════════

// ✅ Дорогие вычисления
const sortedItems = useMemo(() => {
  return [...items].sort((a, b) => a.name.localeCompare(b.name));
}, [items]);

// ✅ Сохранение референса объекта для useEffect dependencies
const options = useMemo(() => ({
  threshold: 0.5,
  rootMargin: '10px',
}), []);

useEffect(() => {
  const observer = new IntersectionObserver(callback, options);
  // ...
}, [options]);

// ✅ Передача объекта в memo-компонент
const style = useMemo(() => ({
  color: isActive ? 'blue' : 'gray',
  fontSize: size,
}), [isActive, size]);

return <MemoizedComponent style={style} />;

// ❌ НЕ нужен useMemo для простых вычислений
const fullName = useMemo(() => {
  return `${firstName} ${lastName}`;  // ❌ Слишком простое
}, [firstName, lastName]);

// ✅ ПРАВИЛЬНО — просто переменная
const fullName = `${firstName} ${lastName}`;
```

### Custom Hooks

```tsx
// ═══════════════════════════════════════════════════════════════════
// Создание custom hooks
// ═══════════════════════════════════════════════════════════════════

// ✅ Naming: use + описание
// ✅ Возвращает объект или tuple

// Пример: useLocalStorage
function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return initialValue;
    }

    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    setStoredValue((prev) => {
      const valueToStore = value instanceof Function ? value(prev) : value;

      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }

      return valueToStore;
    });
  }, [key]);

  return [storedValue, setValue];
}

// Использование
const [theme, setTheme] = useLocalStorage('theme', 'light');

// ═══════════════════════════════════════════════════════════════════
// Пример: useDebounce
// ═══════════════════════════════════════════════════════════════════

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Использование
function SearchInput() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery) {
      searchAPI(debouncedQuery);
    }
  }, [debouncedQuery]);

  return <input value={query} onChange={(e) => setQuery(e.target.value)} />;
}

// ═══════════════════════════════════════════════════════════════════
// Пример: useToggle
// ═══════════════════════════════════════════════════════════════════

function useToggle(initialValue = false): [boolean, () => void, (value: boolean) => void] {
  const [value, setValue] = useState(initialValue);

  const toggle = useCallback(() => {
    setValue((prev) => !prev);
  }, []);

  const set = useCallback((newValue: boolean) => {
    setValue(newValue);
  }, []);

  return [value, toggle, set];
}

// Использование
const [isOpen, toggleOpen, setOpen] = useToggle(false);
```

---

## 🐻 STATE MANAGEMENT (Zustand)

### Создание store

```tsx
// ═══════════════════════════════════════════════════════════════════
// stores/user.ts — Базовый store
// ═══════════════════════════════════════════════════════════════════

import {create} from 'zustand';
import {devtools, persist} from 'zustand/middleware';
import type {User} from '@/types';

// Types
interface UserState {
  // State
  currentUser: User | null;
  users: Record<string, User>;
  isLoading: boolean;
  error: string | null;

  // Actions
  setCurrentUser: (user: User | null) => void;
  fetchUser: (userId: string) => Promise<void>;
  updateUser: (userId: string, data: Partial<User>) => void;
  logout: () => void;
}

// Initial state (для reset)
const initialState = {
  currentUser: null,
  users: {},
  isLoading: false,
  error: null,
};

// Store
export const useUserStore = create<UserState>()(
  devtools(
    persist(
      (set, get) => ({
        // State
        ...initialState,

        // Actions
        setCurrentUser: (user) => {
          set({currentUser: user}, false, 'setCurrentUser');
        },

        fetchUser: async (userId) => {
          set({isLoading: true, error: null}, false, 'fetchUser/pending');

          try {
            const response = await fetch(`/api/users/${userId}`);
            if (!response.ok) {
              throw new Error('Failed to fetch user');
            }
            const user = await response.json();

            set(
              (state) => ({
                users: {...state.users, [userId]: user},
                isLoading: false,
              }),
              false,
              'fetchUser/fulfilled'
            );
          } catch (error) {
            set(
              {
                error: error instanceof Error ? error.message : 'Unknown error',
                isLoading: false,
              },
              false,
              'fetchUser/rejected'
            );
          }
        },

        updateUser: (userId, data) => {
          set(
            (state) => ({
              users: {
                ...state.users,
                [userId]: {...state.users[userId], ...data},
              },
            }),
            false,
            'updateUser'
          );
        },

        logout: () => {
          set(initialState, false, 'logout');
        },
      }),
      {
        name: 'user-storage',
        partialize: (state) => ({
          currentUser: state.currentUser,
        }),
      }
    ),
    {name: 'UserStore'}
  )
);
```

### Использование store в компонентах

```tsx
// ═══════════════════════════════════════════════════════════════════
// ✅ ПРАВИЛЬНО — Селекторы для избежания лишних ре-рендеров
// ═══════════════════════════════════════════════════════════════════

function UserProfile() {
  // ✅ Выбираем только нужное поле — компонент ре-рендерится
  // только когда это конкретное поле меняется
  const currentUser = useUserStore((state) => state.currentUser);
  const isLoading = useUserStore((state) => state.isLoading);

  // ✅ Actions можно доставать без селектора (они стабильны)
  const logout = useUserStore((state) => state.logout);

  if (isLoading) {
    return <Loading />;
  }

  if (!currentUser) {
    return <LoginPrompt />;
  }

  return (
    <div>
      <h1>{currentUser.name}</h1>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// ✅ Множественные значения — shallow compare
// ═══════════════════════════════════════════════════════════════════

import {useShallow} from 'zustand/react/shallow';

function UserStats() {
  // ✅ useShallow для объектов — сравнивает поверхностно
  const {users, isLoading} = useUserStore(
    useShallow((state) => ({
      users: state.users,
      isLoading: state.isLoading,
    }))
  );

  return <div>Users: {Object.keys(users).length}</div>;
}

// ═══════════════════════════════════════════════════════════════════
// ✅ Computed/Derived state
// ═══════════════════════════════════════════════════════════════════

function ActiveUsersCount() {
  // ✅ Вычисляем в селекторе
  const activeCount = useUserStore((state) =>
    Object.values(state.users).filter((u) => u.isActive).length
  );

  return <span>{activeCount} active users</span>;
}

// ═══════════════════════════════════════════════════════════════════
// ❌ НЕПРАВИЛЬНО
// ═══════════════════════════════════════════════════════════════════

function BadComponent() {
  // ❌ Весь store — ре-рендер при ЛЮБОМ изменении
  const store = useUserStore();

  // ❌ Новый объект каждый рендер без useShallow
  const {users, isLoading} = useUserStore((state) => ({
    users: state.users,
    isLoading: state.isLoading,
  }));  // ❌ Ре-рендер каждый раз!

  return <div>{store.currentUser?.name}</div>;
}
```

### Slices pattern (разделение большого store)

```tsx
// ═══════════════════════════════════════════════════════════════════
// stores/slices/userSlice.ts
// ═══════════════════════════════════════════════════════════════════

import type {StateCreator} from 'zustand';

export interface UserSlice {
  currentUser: User | null;
  setCurrentUser: (user: User | null) => void;
}

export const createUserSlice: StateCreator<
  UserSlice & CartSlice,  // Все slices
  [],
  [],
  UserSlice
> = (set) => ({
  currentUser: null,
  setCurrentUser: (user) => set({currentUser: user}),
});

// ═══════════════════════════════════════════════════════════════════
// stores/slices/cartSlice.ts
// ═══════════════════════════════════════════════════════════════════

export interface CartSlice {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (itemId: string) => void;
  clearCart: () => void;
}

export const createCartSlice: StateCreator<
  UserSlice & CartSlice,
  [],
  [],
  CartSlice
> = (set, get) => ({
  items: [],

  addItem: (item) => {
    set((state) => ({
      items: [...state.items, item],
    }));
  },

  removeItem: (itemId) => {
    set((state) => ({
      items: state.items.filter((i) => i.id !== itemId),
    }));
  },

  clearCart: () => {
    // Можем получить доступ к другим slices через get()
    const user = get().currentUser;
    console.log(`Clearing cart for ${user?.name}`);
    set({items: []});
  },
});

// ═══════════════════════════════════════════════════════════════════
// stores/index.ts — Объединение slices
// ═══════════════════════════════════════════════════════════════════

import {create} from 'zustand';
import {createUserSlice, type UserSlice} from './slices/userSlice';
import {createCartSlice, type CartSlice} from './slices/cartSlice';

type StoreState = UserSlice & CartSlice;

export const useStore = create<StoreState>()((...args) => ({
  ...createUserSlice(...args),
  ...createCartSlice(...args),
}));
```

### Actions вне React компонентов

```tsx
// ═══════════════════════════════════════════════════════════════════
// Доступ к store вне React
// ═══════════════════════════════════════════════════════════════════

// В утилитах, API клиентах и т.д.
import {useUserStore} from '@/stores/user';

// ✅ getState() для чтения
export async function apiClient(endpoint: string) {
  const token = useUserStore.getState().currentUser?.token;

  return fetch(endpoint, {
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
    },
  });
}

// ✅ setState() для записи
export function handleAuthError() {
  useUserStore.setState({
    currentUser: null,
    error: 'Session expired',
  });
}

// ✅ subscribe() для реакции на изменения
const unsubscribe = useUserStore.subscribe(
  (state) => state.currentUser,
  (currentUser, previousUser) => {
    if (currentUser && !previousUser) {
      analytics.track('user_logged_in', {userId: currentUser.id});
    }
  }
);
```

---

## 🎨 ПАТТЕРНЫ КОМПОНЕНТОВ

### Compound Components

```tsx
// ═══════════════════════════════════════════════════════════════════
// Compound Components — компоненты работают вместе
// ═══════════════════════════════════════════════════════════════════

// Контекст для shared state
interface TabsContextValue {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error('Tabs components must be used within Tabs');
  }
  return context;
}

// Root component
interface TabsProps {
  defaultValue: string;
  children: ReactNode;
  onChange?: (value: string) => void;
}

export function Tabs({defaultValue, children, onChange}: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultValue);

  const handleChange = useCallback((tab: string) => {
    setActiveTab(tab);
    onChange?.(tab);
  }, [onChange]);

  const value = useMemo(
    () => ({activeTab, setActiveTab: handleChange}),
    [activeTab, handleChange]
  );

  return (
    <TabsContext.Provider value={value}>
      <div role="tablist">{children}</div>
    </TabsContext.Provider>
  );
}

// Tab trigger
interface TabProps {
  value: string;
  children: ReactNode;
}

function Tab({value, children}: TabProps) {
  const {activeTab, setActiveTab} = useTabsContext();
  const isActive = activeTab === value;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      onClick={() => setActiveTab(value)}
      data-state={isActive ? 'active' : 'inactive'}
    >
      {children}
    </button>
  );
}

// Tab content
interface TabPanelProps {
  value: string;
  children: ReactNode;
}

function TabPanel({value, children}: TabPanelProps) {
  const {activeTab} = useTabsContext();

  if (activeTab !== value) {
    return null;
  }

  return (
    <div role="tabpanel" data-state="active">
      {children}
    </div>
  );
}

// Attach sub-components
Tabs.Tab = Tab;
Tabs.Panel = TabPanel;

// Использование
function App() {
  return (
    <Tabs defaultValue="tab1" onChange={(tab) => console.log(tab)}>
      <Tabs.Tab value="tab1">Tab 1</Tabs.Tab>
      <Tabs.Tab value="tab2">Tab 2</Tabs.Tab>

      <Tabs.Panel value="tab1">Content 1</Tabs.Panel>
      <Tabs.Panel value="tab2">Content 2</Tabs.Panel>
    </Tabs>
  );
}
```

### Controlled vs Uncontrolled

```tsx
// ═══════════════════════════════════════════════════════════════════
// Поддержка обоих режимов
// ═══════════════════════════════════════════════════════════════════

interface ToggleProps {
  // Controlled
  checked?: boolean;
  onChange?: (checked: boolean) => void;

  // Uncontrolled
  defaultChecked?: boolean;

  // Common
  disabled?: boolean;
  children: ReactNode;
}

export function Toggle({
  checked: controlledChecked,
  onChange,
  defaultChecked = false,
  disabled = false,
  children,
}: ToggleProps) {
  // Определяем режим
  const isControlled = controlledChecked !== undefined;

  // Internal state для uncontrolled режима
  const [internalChecked, setInternalChecked] = useState(defaultChecked);

  // Используем controlled или internal значение
  const checked = isControlled ? controlledChecked : internalChecked;

  const handleToggle = () => {
    if (disabled) return;

    const newValue = !checked;

    // В uncontrolled режиме обновляем internal state
    if (!isControlled) {
      setInternalChecked(newValue);
    }

    // Вызываем onChange в любом режиме
    onChange?.(newValue);
  };

  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={handleToggle}
    >
      {children}
    </button>
  );
}

// Использование — Controlled
function ControlledExample() {
  const [isOn, setIsOn] = useState(false);

  return (
    <Toggle checked={isOn} onChange={setIsOn}>
      {isOn ? 'ON' : 'OFF'}
    </Toggle>
  );
}

// Использование — Uncontrolled
function UncontrolledExample() {
  return (
    <Toggle defaultChecked onChange={(checked) => console.log(checked)}>
      Toggle me
    </Toggle>
  );
}
```

### Error Boundary

```tsx
// ═══════════════════════════════════════════════════════════════════
// components/ErrorBoundary.tsx
// ═══════════════════════════════════════════════════════════════════

import {Component, type ReactNode, type ErrorInfo} from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = {error: null};

  static getDerivedStateFromError(error: Error): State {
    return {error};
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.props.onError?.(error, errorInfo);

    // Логирование в сервис (Sentry, etc.)
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  reset = () => {
    this.setState({error: null});
  };

  render() {
    const {error} = this.state;
    const {children, fallback} = this.props;

    if (error) {
      if (typeof fallback === 'function') {
        return fallback(error, this.reset);
      }

      return fallback ?? (
        <div role="alert">
          <h2>Something went wrong</h2>
          <button onClick={this.reset}>Try again</button>
        </div>
      );
    }

    return children;
  }
}

// Использование
function App() {
  return (
    <ErrorBoundary
      fallback={(error, reset) => (
        <div>
          <p>Error: {error.message}</p>
          <button onClick={reset}>Retry</button>
        </div>
      )}
      onError={(error) => {
        Sentry.captureException(error);
      }}
    >
      <MainContent />
    </ErrorBoundary>
  );
}
```

---

## ⚡ ПРОИЗВОДИТЕЛЬНОСТЬ

### React.memo

```tsx
// ═══════════════════════════════════════════════════════════════════
// Когда использовать memo
// ═══════════════════════════════════════════════════════════════════

// ✅ Компонент рендерится часто с теми же props
const UserListItem = memo(function UserListItem({
  user,
  onSelect,
}: {
  user: User;
  onSelect: (user: User) => void;
}) {
  return (
    <li onClick={() => onSelect(user)}>
      {user.name}
    </li>
  );
});

// ✅ Дорогой для рендера компонент
const ExpensiveChart = memo(function ExpensiveChart({
  data,
}: {
  data: ChartData[];
}) {
  // Сложные вычисления, Canvas/SVG рендеринг
  return <canvas>{/* ... */}</canvas>;
});

// ✅ Custom comparison для сложных props
const UserCard = memo(
  function UserCard({user, style}: {user: User; style: CSSProperties}) {
    return <div style={style}>{user.name}</div>;
  },
  (prevProps, nextProps) => {
    // Возвращаем true если props равны (не нужен ре-рендер)
    return (
      prevProps.user.id === nextProps.user.id &&
      prevProps.user.name === nextProps.user.name
      // style сравниваем поверхностно или игнорируем
    );
  }
);

// ❌ НЕ нужен memo
// — Для компонентов которые всегда получают разные props
// — Для очень простых компонентов
// — Когда родитель редко ре-рендерится
```

### Виртуализация списков

```tsx
// ═══════════════════════════════════════════════════════════════════
// Для больших списков используйте @tanstack/react-virtual
// ═══════════════════════════════════════════════════════════════════

import {useVirtualizer} from '@tanstack/react-virtual';

interface VirtualListProps {
  items: User[];
  renderItem: (user: User) => ReactNode;
}

export function VirtualList({items, renderItem}: VirtualListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,  // Примерная высота элемента
    overscan: 5,              // Сколько элементов рендерить за пределами viewport
  });

  return (
    <div
      ref={parentRef}
      style={{height: '400px', overflow: 'auto'}}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            {renderItem(items[virtualItem.index])}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Code Splitting

```tsx
// ═══════════════════════════════════════════════════════════════════
// Lazy loading компонентов
// ═══════════════════════════════════════════════════════════════════

import {lazy, Suspense} from 'react';

// ✅ Lazy load тяжёлых компонентов
const AdminDashboard = lazy(() => import('./AdminDashboard'));
const UserSettings = lazy(() => import('./UserSettings'));
const ChartComponent = lazy(() =>
  import('./ChartComponent').then((module) => ({
    default: module.ChartComponent,  // Для named exports
  }))
);

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/settings" element={<UserSettings />} />
      </Routes>
    </Suspense>
  );
}

// ✅ Preload при hover
function NavLink({to, children}: {to: string; children: ReactNode}) {
  const handleMouseEnter = () => {
    // Preload компонент при наведении
    if (to === '/admin') {
      import('./AdminDashboard');
    }
  };

  return (
    <Link to={to} onMouseEnter={handleMouseEnter}>
      {children}
    </Link>
  );
}
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
src/
├── app/                      # App Router (Next.js) или entry point
│   ├── layout.tsx
│   └── page.tsx
│
├── components/               # Компоненты
│   ├── ui/                   # Базовые UI компоненты
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx
│   │   │   └── index.ts
│   │   ├── Input/
│   │   └── index.ts          # Re-export всех UI
│   │
│   ├── features/             # Feature-specific компоненты
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   └── UserMenu.tsx
│   │   └── dashboard/
│   │       └── DashboardCard.tsx
│   │
│   └── layouts/              # Layout компоненты
│       ├── MainLayout.tsx
│       └── AuthLayout.tsx
│
├── hooks/                    # Custom hooks
│   ├── useDebounce.ts
│   ├── useLocalStorage.ts
│   └── index.ts
│
├── stores/                   # Zustand stores
│   ├── user.ts
│   ├── cart.ts
│   └── index.ts
│
├── lib/                      # Утилиты и конфигурации
│   ├── api.ts                # API client
│   ├── utils.ts
│   └── constants.ts
│
├── types/                    # TypeScript типы
│   ├── user.ts
│   ├── api.ts
│   └── index.ts
│
└── styles/                   # Глобальные стили
    └── globals.css
```

---

## ✅ ЧЕКЛИСТ ПЕРЕД КОММИТОМ

```
КОМПОНЕНТЫ
□ Функциональные компоненты (не классы)
□ TypeScript типы для всех props
□ Named exports (не default)
□ Hooks в правильном порядке
□ Нет логики в JSX — вынесено в переменные/функции
□ Семантический HTML (article, section, header, nav)
□ Aria атрибуты для accessibility

STATE MANAGEMENT
□ Локальный state где возможно
□ Zustand селекторы для оптимизации
□ Иммутабельные обновления
□ Нет дублирования state

ПРОИЗВОДИТЕЛЬНОСТЬ
□ memo только где нужно
□ useCallback для callbacks в memo-компонентах
□ useMemo для дорогих вычислений
□ Lazy loading для тяжёлых компонентов
□ key для списков

КАЧЕСТВО
□ Нет console.log
□ Нет any
□ ESLint без ошибок
□ Компонент < 200 строк
```

---

## 🚀 БЫСТРЫЙ ПРОМПТ ДЛЯ CLAUDE CODE

```
React + TypeScript проект. Следуй React.dev + Zustand:

КОМПОНЕНТЫ:
- Функциональные компоненты, Named exports
- interface для props, TypeScript strict
- Порядок: hooks → early returns → render
- Семантический HTML + aria атрибуты

HOOKS:
- На верхнем уровне, в одном порядке
- useCallback для callbacks в memo-компонентах
- useMemo для дорогих вычислений
- Custom hooks с use- префиксом

ZUSTAND:
- Селекторы для подписки на части state
- useShallow для объектов
- Слайсы для больших stores
- Иммутабельные обновления через set()

ОБЯЗАТЕЛЬНО:
✅ Типизация всех props и state
✅ Мемоизация где реально нужно
✅ Controlled/Uncontrolled паттерн для форм
✅ Error boundaries для критических секций

ЗАПРЕЩЕНО:
❌ Классовые компоненты
❌ Default exports
❌ Hooks в условиях/циклах
❌ Мутация state/props напрямую
❌ Prop drilling > 2 уровней
```

---

**Версия:** 1.0
**Дата:** 01.12.2025
**Референс:** React.dev + Zustand
