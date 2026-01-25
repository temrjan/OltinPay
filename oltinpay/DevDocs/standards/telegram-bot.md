# TELEGRAM BOT GUIDE
## Для Claude Code — aiogram 3.x

> **Цель:** Единый стиль разработки Telegram ботов
> **Референс:** aiogram 3.x официальная документация (docs.aiogram.dev)
> **Версия:** aiogram 3.x, Python 3.11+

---

## 🎯 КЛЮЧЕВЫЕ ПРИНЦИПЫ

```
ВСЕГДА                              НИКОГДА
────────────────────────────────    ────────────────────────────────
✓ Routers для модульности           ✗ Всё в одном файле
✓ FSM для многошаговых диалогов     ✗ Глобальные переменные для state
✓ Magic filters (F.text, F.photo)   ✗ Ручная проверка типов контента
✓ Middleware для cross-cutting      ✗ Дублирование логики в handlers
✓ Async/await везде                 ✗ Блокирующий код
✓ Dependency injection              ✗ Хардкод зависимостей
✓ Pydantic для конфигов             ✗ Голые env переменные
✓ Структурированное логирование     ✗ print() для отладки
✓ Graceful shutdown                 ✗ Жёсткое завершение
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
telegram_bot/
├── .env                          # Переменные окружения (НЕ в git!)
├── .env.example                  # Пример env файла
├── pyproject.toml                # Dependencies
├── README.md
│
├── bot/
│   ├── __init__.py
│   ├── __main__.py               # Entry point
│   │
│   ├── core/                     # Ядро бота
│   │   ├── __init__.py
│   │   ├── config.py             # Pydantic Settings
│   │   ├── loader.py             # Bot, Dispatcher, Storage
│   │   └── logging.py            # Настройка логирования
│   │
│   ├── handlers/                 # Обработчики событий
│   │   ├── __init__.py
│   │   ├── common.py             # /start, /help, /cancel
│   │   ├── user/                 # Пользовательские команды
│   │   │   ├── __init__.py
│   │   │   ├── profile.py
│   │   │   └── settings.py
│   │   └── admin/                # Админ команды
│   │       ├── __init__.py
│   │       └── broadcast.py
│   │
│   ├── keyboards/                # Клавиатуры
│   │   ├── __init__.py
│   │   ├── reply.py              # ReplyKeyboard
│   │   └── inline.py             # InlineKeyboard
│   │
│   ├── states/                   # FSM States
│   │   ├── __init__.py
│   │   └── user.py
│   │
│   ├── filters/                  # Кастомные фильтры
│   │   ├── __init__.py
│   │   └── admin.py
│   │
│   ├── middlewares/              # Middleware
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── throttling.py
│   │   └── logging.py
│   │
│   ├── services/                 # Бизнес-логика
│   │   ├── __init__.py
│   │   └── user.py
│   │
│   ├── database/                 # База данных
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── user.py
│   │
│   └── utils/                    # Утилиты
│       ├── __init__.py
│       └── text.py
│
└── tests/
    ├── __init__.py
    └── test_handlers.py
```

---

## ⚙️ КОНФИГУРАЦИЯ

### Pydantic Settings

```python
# bot/core/config.py

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bot
    bot_token: SecretStr

    # Database
    database_url: str = "sqlite+aiosqlite:///bot.db"

    # Redis (для FSM storage в production)
    redis_url: str | None = None

    # Admin
    admin_ids: list[int] = []

    # Debug
    debug: bool = False

    @property
    def is_production(self) -> bool:
        return not self.debug


# Singleton
settings = Settings()
```

### Loader (Bot и Dispatcher)

```python
# bot/core/loader.py

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from bot.core.config import settings


def get_storage():
    """Get FSM storage based on configuration."""
    if settings.redis_url:
        return RedisStorage.from_url(settings.redis_url)
    return MemoryStorage()


# Bot instance
bot = Bot(
    token=settings.bot_token.get_secret_value(),
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        link_preview_is_disabled=True,
    ),
)

# Dispatcher instance
dp = Dispatcher(
    storage=get_storage(),
    # Можно передать свои данные, доступные во всех handlers
    settings=settings,
)
```

---

## 🚀 ENTRY POINT

```python
# bot/__main__.py

import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

from bot.core.config import settings
from bot.core.loader import bot, dp

# Import routers
from bot.handlers import common, user, admin


async def set_commands(bot: Bot) -> None:
    """Set bot commands in menu."""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="cancel", description="❌ Отменить действие"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def on_startup(bot: Bot) -> None:
    """Actions on bot startup."""
    await set_commands(bot)

    # Notify admin about startup
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, "🟢 Бот запущен")
        except Exception:
            pass

    logging.info("Bot started")


async def on_shutdown(bot: Bot) -> None:
    """Actions on bot shutdown."""
    # Notify admin about shutdown
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, "🔴 Бот остановлен")
        except Exception:
            pass

    logging.info("Bot stopped")


async def main() -> None:
    """Main function."""
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Include routers (ORDER MATTERS!)
    dp.include_routers(
        common.router,      # /start, /help, /cancel first
        admin.router,       # Admin commands
        user.router,        # User commands last
    )

    # Start polling
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            # Skip updates that came while bot was offline
            # drop_pending_updates=True,
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🛤️ ROUTERS

### Базовый Router

```python
# bot/handlers/common.py

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.keyboards.reply import get_main_keyboard


router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command."""
    # Clear any existing state
    await state.clear()

    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        "Я — бот-помощник. Выбери действие:",
        reply_markup=get_main_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "<b>📚 Справка</b>\n\n"
        "/start — Начать работу\n"
        "/help — Показать справку\n"
        "/settings — Настройки\n"
        "/cancel — Отменить действие",
    )


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel any FSM state."""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=get_main_keyboard(),
    )
```

### Router с фильтрами

```python
# bot/handlers/admin/broadcast.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.filters.admin import IsAdmin


# Router с глобальным фильтром — все handlers только для админов
router = Router(name="admin")
router.message.filter(IsAdmin())


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    """Start broadcast to all users."""
    await message.answer("📢 Отправьте сообщение для рассылки:")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Show bot statistics."""
    await message.answer("📊 Статистика бота...")
```

### Подключение вложенных routers

```python
# bot/handlers/user/__init__.py

from aiogram import Router

from . import profile
from . import settings


# Родительский router для user handlers
router = Router(name="user")

# Подключаем вложенные routers
router.include_routers(
    profile.router,
    settings.router,
)
```

---

## 🔄 FSM (Finite State Machine)

### Определение States

```python
# bot/states/user.py

from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    """States for user registration flow."""
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_city = State()
    confirm = State()


class FeedbackState(StatesGroup):
    """States for feedback flow."""
    waiting_for_text = State()
    waiting_for_rating = State()


class OrderState(StatesGroup):
    """States for order flow."""
    selecting_product = State()
    entering_quantity = State()
    entering_address = State()
    confirm = State()
```

### FSM Handler

```python
# bot/handlers/user/profile.py

from aiogram import Router, F, html
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.states.user import RegistrationState
from bot.keyboards.reply import get_confirm_keyboard, get_cancel_keyboard


router = Router(name="profile")


# ═══════════════════════════════════════════════════════════════════
# Начало регистрации
# ═══════════════════════════════════════════════════════════════════

@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext) -> None:
    """Start registration process."""
    await state.set_state(RegistrationState.waiting_for_name)
    await message.answer(
        "📝 Давайте заполним профиль!\n\n"
        "Как вас зовут?",
        reply_markup=get_cancel_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 1: Имя
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationState.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    """Process user name."""
    name = message.text.strip()

    # Валидация
    if len(name) < 2 or len(name) > 50:
        await message.answer(
            "❌ Имя должно быть от 2 до 50 символов. Попробуйте ещё раз:"
        )
        return

    # Сохраняем данные и переходим к следующему шагу
    await state.update_data(name=name)
    await state.set_state(RegistrationState.waiting_for_age)

    await message.answer(
        f"Отлично, {html.quote(name)}! 👋\n\n"
        "Сколько вам лет?"
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 2: Возраст
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationState.waiting_for_age, F.text.regexp(r"^\d+$"))
async def process_age_valid(message: Message, state: FSMContext) -> None:
    """Process valid age."""
    age = int(message.text)

    if not 1 <= age <= 120:
        await message.answer("❌ Введите корректный возраст (1-120):")
        return

    await state.update_data(age=age)
    await state.set_state(RegistrationState.waiting_for_city)

    await message.answer("🏙️ Из какого вы города?")


@router.message(RegistrationState.waiting_for_age)
async def process_age_invalid(message: Message) -> None:
    """Handle invalid age input."""
    await message.answer(
        "❌ Пожалуйста, введите возраст числом.\n"
        "Например: 25"
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 3: Город
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationState.waiting_for_city, F.text)
async def process_city(message: Message, state: FSMContext) -> None:
    """Process user city."""
    city = message.text.strip()

    await state.update_data(city=city)
    await state.set_state(RegistrationState.confirm)

    # Получаем все данные для подтверждения
    data = await state.get_data()

    await message.answer(
        "📋 <b>Проверьте ваши данные:</b>\n\n"
        f"👤 Имя: {html.quote(data['name'])}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"🏙️ Город: {html.quote(city)}\n\n"
        "Всё верно?",
        reply_markup=get_confirm_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
# Шаг 4: Подтверждение
# ═══════════════════════════════════════════════════════════════════

@router.message(RegistrationState.confirm, F.text == "✅ Подтвердить")
async def process_confirm(message: Message, state: FSMContext) -> None:
    """Confirm registration."""
    data = await state.get_data()

    # Здесь сохраняем в БД
    # await user_service.create_user(
    #     telegram_id=message.from_user.id,
    #     name=data["name"],
    #     age=data["age"],
    #     city=data["city"],
    # )

    await state.clear()

    await message.answer(
        "✅ Регистрация завершена!\n\n"
        f"Добро пожаловать, {html.quote(data['name'])}!",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(RegistrationState.confirm, F.text == "🔄 Заполнить заново")
async def process_restart(message: Message, state: FSMContext) -> None:
    """Restart registration."""
    await state.clear()
    await cmd_register(message, state)
```

---

## 🎹 КЛАВИАТУРЫ

### Reply Keyboards

```python
# bot/keyboards/reply.py

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard."""
    keyboard = [
        [
            KeyboardButton(text="👤 Профиль"),
            KeyboardButton(text="⚙️ Настройки"),
        ],
        [
            KeyboardButton(text="📝 Регистрация"),
            KeyboardButton(text="❓ Помощь"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Cancel keyboard for FSM flows."""
    keyboard = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


def get_confirm_keyboard() -> ReplyKeyboardMarkup:
    """Confirm/Cancel keyboard."""
    keyboard = [
        [
            KeyboardButton(text="✅ Подтвердить"),
            KeyboardButton(text="🔄 Заполнить заново"),
        ],
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with phone request."""
    keyboard = [
        [KeyboardButton(text="📱 Отправить номер", request_contact=True)],
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


def get_location_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with location request."""
    keyboard = [
        [KeyboardButton(text="📍 Отправить локацию", request_location=True)],
        [KeyboardButton(text="❌ Отмена")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )
```

### Inline Keyboards

```python
# bot/keyboards/inline.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_url_keyboard(text: str, url: str) -> InlineKeyboardMarkup:
    """Single URL button keyboard."""
    keyboard = [
        [InlineKeyboardButton(text=text, url=url)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str = "page",
) -> InlineKeyboardMarkup:
    """Pagination keyboard."""
    builder = InlineKeyboardBuilder()

    buttons = []

    # Previous
    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"{callback_prefix}:{current_page - 1}",
            )
        )

    # Current page indicator
    buttons.append(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="noop",
        )
    )

    # Next
    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"{callback_prefix}:{current_page + 1}",
            )
        )

    builder.row(*buttons)
    return builder.as_markup()


def get_confirm_inline_keyboard(
    confirm_callback: str,
    cancel_callback: str,
) -> InlineKeyboardMarkup:
    """Confirm/Cancel inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да", callback_data=confirm_callback),
            InlineKeyboardButton(text="❌ Нет", callback_data=cancel_callback),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ═══════════════════════════════════════════════════════════════════
# Callback Data Factory (для типизированных callbacks)
# ═══════════════════════════════════════════════════════════════════

from aiogram.filters.callback_data import CallbackData


class ProductCallback(CallbackData, prefix="product"):
    """Callback data for product actions."""
    action: str  # view, buy, add_cart
    product_id: int
    quantity: int = 1


class PaginationCallback(CallbackData, prefix="page"):
    """Callback data for pagination."""
    page: int
    category: str | None = None


# Использование в keyboards
def get_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="👁️ Подробнее",
        callback_data=ProductCallback(action="view", product_id=product_id),
    )
    builder.button(
        text="🛒 В корзину",
        callback_data=ProductCallback(action="add_cart", product_id=product_id),
    )
    builder.button(
        text="💰 Купить",
        callback_data=ProductCallback(action="buy", product_id=product_id),
    )

    builder.adjust(2, 1)  # 2 кнопки в первом ряду, 1 во втором
    return builder.as_markup()
```

### Обработка Callback Query

```python
# bot/handlers/user/products.py

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.keyboards.inline import ProductCallback


router = Router(name="products")


@router.callback_query(ProductCallback.filter(F.action == "view"))
async def callback_view_product(
    callback: CallbackQuery,
    callback_data: ProductCallback,
) -> None:
    """Handle product view callback."""
    product_id = callback_data.product_id

    # Получаем продукт из БД
    # product = await product_service.get_by_id(product_id)

    await callback.message.edit_text(
        f"📦 Товар #{product_id}\n\n"
        "Описание товара...",
    )
    await callback.answer()


@router.callback_query(ProductCallback.filter(F.action == "add_cart"))
async def callback_add_to_cart(
    callback: CallbackQuery,
    callback_data: ProductCallback,
) -> None:
    """Handle add to cart callback."""
    product_id = callback_data.product_id
    quantity = callback_data.quantity

    # Добавляем в корзину
    # await cart_service.add_item(callback.from_user.id, product_id, quantity)

    await callback.answer(
        f"✅ Товар добавлен в корзину ({quantity} шт.)",
        show_alert=False,
    )


@router.callback_query(ProductCallback.filter(F.action == "buy"))
async def callback_buy_product(
    callback: CallbackQuery,
    callback_data: ProductCallback,
) -> None:
    """Handle buy callback."""
    await callback.answer(
        "🛒 Переходим к оформлению заказа...",
        show_alert=True,
    )

    # Начинаем FSM для оформления заказа
    # await state.set_state(OrderState.entering_address)
```

---

## 🔍 ФИЛЬТРЫ

### Кастомные фильтры

```python
# bot/filters/admin.py

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from bot.core.config import settings


class IsAdmin(BaseFilter):
    """Filter to check if user is admin."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id if event.from_user else None
        return user_id in settings.admin_ids


class IsChatAdmin(BaseFilter):
    """Filter to check if user is chat admin."""

    async def __call__(self, message: Message) -> bool:
        if message.chat.type == "private":
            return True

        member = await message.bot.get_chat_member(
            message.chat.id,
            message.from_user.id,
        )
        return member.status in ("creator", "administrator")
```

```python
# bot/filters/user.py

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.services.user import UserService


class IsRegistered(BaseFilter):
    """Filter to check if user is registered."""

    def __init__(self, is_registered: bool = True):
        self.is_registered = is_registered

    async def __call__(
        self,
        message: Message,
        user_service: UserService,
    ) -> bool:
        user = await user_service.get_by_telegram_id(message.from_user.id)
        return (user is not None) == self.is_registered


class HasPremium(BaseFilter):
    """Filter to check if user has premium subscription."""

    async def __call__(
        self,
        message: Message,
        user_service: UserService,
    ) -> bool:
        user = await user_service.get_by_telegram_id(message.from_user.id)
        return user is not None and user.is_premium
```

### Magic Filters (F)

```python
# Примеры использования Magic Filters

from aiogram import F

# ═══════════════════════════════════════════════════════════════════
# Фильтры для Message
# ═══════════════════════════════════════════════════════════════════

# Только текстовые сообщения
@router.message(F.text)
async def handle_text(message: Message): ...

# Только фото
@router.message(F.photo)
async def handle_photo(message: Message): ...

# Только документы
@router.message(F.document)
async def handle_document(message: Message): ...

# Документы определённого типа
@router.message(F.document.mime_type == "application/pdf")
async def handle_pdf(message: Message): ...

# Сообщения с определённым текстом
@router.message(F.text == "Привет")
async def handle_hello(message: Message): ...

# Текст начинается с...
@router.message(F.text.startswith("!"))
async def handle_command_like(message: Message): ...

# Текст содержит...
@router.message(F.text.contains("помощь"))
async def handle_help_request(message: Message): ...

# Регулярное выражение
@router.message(F.text.regexp(r"^\d{4}-\d{2}-\d{2}$"))
async def handle_date(message: Message): ...

# Приватный чат
@router.message(F.chat.type == "private")
async def handle_private(message: Message): ...

# Группа
@router.message(F.chat.type.in_({"group", "supergroup"}))
async def handle_group(message: Message): ...

# Ответ на сообщение
@router.message(F.reply_to_message)
async def handle_reply(message: Message): ...

# Forward
@router.message(F.forward_from | F.forward_from_chat)
async def handle_forward(message: Message): ...

# ═══════════════════════════════════════════════════════════════════
# Комбинирование фильтров
# ═══════════════════════════════════════════════════════════════════

# AND — оба условия
@router.message(F.text, F.chat.type == "private")
async def handle_private_text(message: Message): ...

# OR — любое условие
@router.message(F.photo | F.video)
async def handle_media(message: Message): ...

# NOT — отрицание
@router.message(~F.text)
async def handle_not_text(message: Message): ...

# Сложные комбинации
@router.message(
    F.text.len() > 10,
    F.chat.type == "private",
    ~F.forward_from,
)
async def handle_long_private_original(message: Message): ...
```

---

## 🔌 MIDDLEWARE

### Database Middleware

```python
# bot/middlewares/database.py

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database import async_session_maker
from bot.services.user import UserService


class DatabaseMiddleware(BaseMiddleware):
    """Inject database session and services into handler."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            # Inject session
            data["session"] = session

            # Inject services
            data["user_service"] = UserService(session)

            return await handler(event, data)
```

### Throttling Middleware

```python
# bot/middlewares/throttling.py

from typing import Any, Awaitable, Callable, Dict
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    """Simple throttling middleware."""

    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.user_last_message: Dict[int, datetime] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id
        now = datetime.now()

        last_message_time = self.user_last_message.get(user_id)

        if last_message_time:
            delta = (now - last_message_time).total_seconds()
            if delta < self.rate_limit:
                # Игнорируем слишком частые сообщения
                return

        self.user_last_message[user_id] = now
        return await handler(event, data)
```

### Logging Middleware

```python
# bot/middlewares/logging.py

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Log all incoming updates."""

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if event.message:
            user = event.message.from_user
        elif event.callback_query:
            user = event.callback_query.from_user

        user_info = f"user_id={user.id}" if user else "unknown"
        update_type = event.event_type

        logger.info(
            "Received update",
            extra={
                "update_id": event.update_id,
                "update_type": update_type,
                "user_id": user.id if user else None,
                "username": user.username if user else None,
            },
        )

        try:
            result = await handler(event, data)
            logger.debug(f"Handler completed: {user_info}")
            return result
        except Exception as e:
            logger.exception(
                f"Handler error: {user_info}",
                extra={"error": str(e)},
            )
            raise
```

### Регистрация Middleware

```python
# bot/__main__.py (в функции main)

from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.logging import LoggingMiddleware

async def main() -> None:
    # ...

    # Outer middleware (выполняется первым)
    dp.update.outer_middleware(LoggingMiddleware())

    # Message middleware
    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.message.middleware(DatabaseMiddleware())

    # Callback query middleware
    dp.callback_query.middleware(DatabaseMiddleware())

    # ...
```

---

## 📤 ОТПРАВКА МЕДИА

```python
# bot/handlers/user/media.py

from aiogram import Router, F
from aiogram.types import Message, FSInputFile, URLInputFile, BufferedInputFile
from pathlib import Path


router = Router(name="media")


# ═══════════════════════════════════════════════════════════════════
# Отправка файлов
# ═══════════════════════════════════════════════════════════════════

@router.message(F.text == "Фото")
async def send_photo(message: Message) -> None:
    """Send photo from file."""
    # Из локального файла
    photo = FSInputFile(Path("images/example.jpg"))
    await message.answer_photo(
        photo=photo,
        caption="📸 Фото из файла",
    )


@router.message(F.text == "Фото URL")
async def send_photo_url(message: Message) -> None:
    """Send photo from URL."""
    photo = URLInputFile("https://example.com/image.jpg")
    await message.answer_photo(photo=photo)


@router.message(F.text == "Документ")
async def send_document(message: Message) -> None:
    """Send document."""
    document = FSInputFile(
        Path("files/report.pdf"),
        filename="Отчёт.pdf",  # Кастомное имя файла
    )
    await message.answer_document(
        document=document,
        caption="📄 Ваш документ",
    )


@router.message(F.text == "Сгенерированный файл")
async def send_generated_file(message: Message) -> None:
    """Send dynamically generated file."""
    content = "Это содержимое файла\n" * 100

    file = BufferedInputFile(
        file=content.encode("utf-8"),
        filename="generated.txt",
    )
    await message.answer_document(document=file)


# ═══════════════════════════════════════════════════════════════════
# Получение файлов
# ═══════════════════════════════════════════════════════════════════

@router.message(F.photo)
async def receive_photo(message: Message) -> None:
    """Receive and save photo."""
    # Берём фото максимального размера (последнее в списке)
    photo = message.photo[-1]

    # Получаем file_id для повторной отправки
    file_id = photo.file_id

    # Скачиваем файл
    file = await message.bot.get_file(photo.file_id)
    file_path = Path(f"downloads/{photo.file_unique_id}.jpg")
    await message.bot.download_file(file.file_path, file_path)

    await message.answer(
        f"📸 Фото сохранено!\n"
        f"Size: {photo.width}x{photo.height}\n"
        f"File ID: <code>{file_id[:20]}...</code>",
    )


@router.message(F.document)
async def receive_document(message: Message) -> None:
    """Receive and process document."""
    document = message.document

    # Проверка типа файла
    if document.mime_type not in ("application/pdf", "text/plain"):
        await message.answer("❌ Поддерживаются только PDF и TXT файлы.")
        return

    # Проверка размера (10 MB max)
    if document.file_size > 10 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой (max 10 MB).")
        return

    # Скачиваем
    file = await message.bot.get_file(document.file_id)
    file_path = Path(f"downloads/{document.file_name}")
    await message.bot.download_file(file.file_path, file_path)

    await message.answer(
        f"📄 Документ получен!\n"
        f"Имя: {document.file_name}\n"
        f"Размер: {document.file_size / 1024:.1f} KB",
    )
```

---

## 🗄️ БАЗА ДАННЫХ

### SQLAlchemy Models

```python
# bot/database/models.py

from datetime import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(32))
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[str | None] = mapped_column(String(64))
    language_code: Mapped[str | None] = mapped_column(String(10))

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id})>"
```

### Repository Pattern

```python
# bot/database/repositories/user.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User


class UserRepository:
    """Repository for User model."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        """Create new user."""
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
            last_name=last_name,
            language_code=language_code,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_or_create(
        self,
        telegram_id: int,
        first_name: str,
        **kwargs,
    ) -> tuple[User, bool]:
        """Get existing user or create new one."""
        user = await self.get_by_telegram_id(telegram_id)

        if user:
            return user, False

        user = await self.create(
            telegram_id=telegram_id,
            first_name=first_name,
            **kwargs,
        )
        return user, True

    async def update(self, user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_all_active(self) -> list[User]:
        """Get all non-banned users."""
        result = await self.session.execute(
            select(User).where(User.is_banned == False)
        )
        return list(result.scalars().all())
```

---

## ✅ ЧЕКЛИСТ ПЕРЕД КОММИТОМ

```
СТРУКТУРА
□ Routers для модульности
□ Handlers разделены по функциональности
□ States в отдельных файлах
□ Keyboards в отдельных файлах
□ Filters переиспользуемые

FSM
□ StateGroup для каждого диалога
□ Валидация на каждом шаге
□ Обработка невалидного ввода
□ Cancel handler работает везде
□ state.clear() в конце диалога

БЕЗОПАСНОСТЬ
□ Токен в .env (не в коде)
□ Admin фильтры для админ-команд
□ Валидация user input
□ Rate limiting

КАЧЕСТВО
□ Type hints везде
□ Docstrings для handlers
□ Logging вместо print
□ Нет блокирующего кода
□ Graceful shutdown
```

---

## 🚀 БЫСТРЫЙ ПРОМПТ ДЛЯ CLAUDE CODE

```
Telegram бот на aiogram 3.x. Следуй официальной документации:

СТРУКТУРА:
- Routers для модульности (handlers/user/, handlers/admin/)
- FSM для многошаговых диалогов (StatesGroup)
- Pydantic Settings для конфигурации
- Middleware для cross-cutting (database, logging, throttling)

ОБЯЗАТЕЛЬНО:
✅ Magic filters (F.text, F.photo, F.document)
✅ CallbackData factory для inline кнопок
✅ state.clear() в конце FSM диалога
✅ Валидация на каждом шаге FSM
✅ Cancel handler (@router.message(Command("cancel")))
✅ Graceful shutdown (on_startup, on_shutdown)

ЗАПРЕЩЕНО:
❌ Глобальные переменные для state
❌ Блокирующий код в handlers
❌ Хардкод токена
❌ print() вместо logging
❌ Один файл для всего бота

ПАТТЕРНЫ:
- Router с глобальным фильтром для админов
- Callback Data Factory (prefix="action")
- Repository pattern для БД
- Dependency injection через middleware
```

---

**Версия:** 1.0
**Дата:** 01.12.2025
**Референс:** aiogram 3.x documentation (docs.aiogram.dev)
