"""OltinChain Mini App Bot.

Opens the wallet Mini App with proper initData.
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Config
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://app.oltinchain.com")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Bot setup
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_webapp_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with Mini App button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Открыть кошелёк",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Купить OLTIN",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/buy"),
                ),
                InlineKeyboardButton(
                    text="💸 Продать",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/sell"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📤 Перевести",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/send"),
                ),
                InlineKeyboardButton(
                    text="📜 История",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/history"),
                ),
            ],
        ]
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command."""
    user = message.from_user
    welcome_text = f"""
👋 Привет, {user.first_name}!

🥇 **OltinChain** — токенизированное золото на блокчейне.

Что можно делать:
• Покупать и продавать OLTIN
• Переводить другим пользователям по @username
• Отслеживать историю операций

Нажми кнопку ниже, чтобы открыть кошелёк:
"""
    await message.answer(
        welcome_text,
        reply_markup=get_webapp_keyboard(),
        parse_mode="Markdown",
    )


@dp.message(Command("wallet"))
async def cmd_wallet(message: types.Message):
    """Handle /wallet command."""
    await message.answer(
        "💰 Открой кошелёк:",
        reply_markup=get_webapp_keyboard(),
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command."""
    help_text = """
📚 **Команды:**

/start — Главное меню
/wallet — Открыть кошелёк
/help — Помощь

💡 **Как пользоваться:**

1. Нажми "Открыть кошелёк"
2. При первом входе тебе начислится 1000 USD
3. Покупай OLTIN по текущему курсу золота
4. Переводи друзьям по @username — мгновенно и без комиссии!

🔒 Все операции защищены блокчейном zkSync Era.
"""
    await message.answer(help_text, parse_mode="Markdown")


async def main():
    """Start bot."""
    logger.info("Starting OltinChain Mini App Bot...")
    logger.info(f"WebApp URL: {WEBAPP_URL}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
