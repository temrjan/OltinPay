"""OltinPay Mini App Bot with language selection."""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://app.oltinpay.com")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# User language storage (in production use Redis/DB)
user_languages: dict[int, str] = {}

# Translations
MESSAGES = {
    "uz": {
        "select_language": "🌐 Tilni tanlang:",
        "welcome": """Salom, {name}! 👋

🥇 **OltinPay** — tokenizatsiyalangan oltin savdo platformasi.

Imkoniyatlar:
• OLTIN sotib olish va sotish
• Boshqa foydalanuvchilarga yuborish
• Steyking qilish va 7% APY olish
• Aylin AI yordamchisi

Pastdagi tugmani bosing:""",
        "open_wallet": "🥇 Hamyonni ochish",
        "exchange": "📊 Birja",
        "staking": "💎 Steyking",
        "send": "📤 Yuborish",
        "aylin": "👩 Aylin",
        "help": "📚 Yordam",
        "language_set": "✅ Til o'rnatildi: O'zbekcha",
    },
    "ru": {
        "select_language": "🌐 Выберите язык:",
        "welcome": """Привет, {name}! 👋

🥇 **OltinPay** — платформа торговли токенизированным золотом.

Возможности:
• Покупка и продажа OLTIN
• Переводы другим пользователям
• Стейкинг с доходом 7% APY
• AI-помощник Aylin

Нажмите кнопку ниже:""",
        "open_wallet": "🥇 Открыть кошелёк",
        "exchange": "📊 Биржа",
        "staking": "💎 Стейкинг",
        "send": "📤 Отправить",
        "aylin": "👩 Aylin",
        "help": "📚 Помощь",
        "language_set": "✅ Язык установлен: Русский",
    },
    "en": {
        "select_language": "🌐 Select language:",
        "welcome": """Hello, {name}! 👋

🥇 **OltinPay** — tokenized gold trading platform.

Features:
• Buy and sell OLTIN
• Send to other users
• Stake and earn 7% APY
• Aylin AI assistant

Press the button below:""",
        "open_wallet": "🥇 Open Wallet",
        "exchange": "📊 Exchange",
        "staking": "💎 Staking",
        "send": "📤 Send",
        "aylin": "👩 Aylin",
        "help": "📚 Help",
        "language_set": "✅ Language set: English",
    },
}


def get_lang(user_id: int) -> str:
    return user_languages.get(user_id, "uz")


def get_text(user_id: int, key: str, **kwargs) -> str:
    lang = get_lang(user_id)
    text = MESSAGES.get(lang, MESSAGES["uz"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        ]
    )


def webapp_keyboard(user_id: int) -> InlineKeyboardMarkup:
    lang = get_lang(user_id)
    m = MESSAGES[lang]
    url = f"{WEBAPP_URL}?lang={lang}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=m["open_wallet"], web_app=WebAppInfo(url=url))],
            [
                InlineKeyboardButton(
                    text=m["exchange"], web_app=WebAppInfo(url=f"{url}&tab=exchange")
                ),
                InlineKeyboardButton(
                    text=m["staking"], web_app=WebAppInfo(url=f"{url}&tab=staking")
                ),
            ],
            [
                InlineKeyboardButton(
                    text=m["send"], web_app=WebAppInfo(url=f"{url}&tab=send")
                ),
                InlineKeyboardButton(
                    text=m["aylin"], web_app=WebAppInfo(url=f"{url}&tab=aylin")
                ),
            ],
        ]
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    # If language not set, show language selection
    if user_id not in user_languages:
        await message.answer(
            "🌐 Tilni tanlang / Выберите язык / Select language:",
            reply_markup=language_keyboard(),
        )
    else:
        # Show welcome in selected language
        await message.answer(
            get_text(user_id, "welcome", name=message.from_user.first_name),
            reply_markup=webapp_keyboard(user_id),
            parse_mode="Markdown",
        )


@dp.callback_query(F.data.startswith("lang_"))
async def on_language_select(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    lang = callback.data.split("_")[1]  # lang_uz -> uz
    user_languages[user_id] = lang

    # Delete language selection message
    await callback.message.delete()

    # Send welcome in selected language
    await callback.message.answer(
        get_text(user_id, "welcome", name=callback.from_user.first_name),
        reply_markup=webapp_keyboard(user_id),
        parse_mode="Markdown",
    )
    await callback.answer(get_text(user_id, "language_set"))


@dp.message(Command("lang"))
async def cmd_lang(message: types.Message):
    await message.answer(
        "🌐 Tilni tanlang / Выберите язык / Select language:",
        reply_markup=language_keyboard(),
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    lang = get_lang(user_id)

    help_texts = {
        "uz": """📚 **Yordam**

/start — Asosiy menyu
/lang — Tilni o'zgartirish
/help — Ushbu xabar

💡 Hamyonni ochish uchun tugmani bosing.""",
        "ru": """📚 **Помощь**

/start — Главное меню
/lang — Сменить язык
/help — Это сообщение

💡 Нажмите кнопку, чтобы открыть кошелёк.""",
        "en": """📚 **Help**

/start — Main menu
/lang — Change language
/help — This message

💡 Press the button to open your wallet.""",
    }

    await message.answer(help_texts.get(lang, help_texts["uz"]), parse_mode="Markdown")


async def main():
    logger.info("Starting OltinPay Bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
