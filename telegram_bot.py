#!/usr/bin/env python3
"""Telegram-бот с тем же функционалом, что и CLI-чат."""

import hashlib
import secrets

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.chat_service import ChatService
from app.config import load_bot_config
from app.llm_client import create_client

_USER_DATA_AUTH_KEY = "tg_llm_auth"


def _expected_password(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.application.bot_data["telegram_bot_password"]


def _is_authenticated(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.user_data.get(_USER_DATA_AUTH_KEY))


def _set_authenticated(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[_USER_DATA_AUTH_KEY] = True


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _password_ok(context: ContextTypes.DEFAULT_TYPE, attempt: str) -> bool:
    """Сравнение через хеш фиксированной длины (сырые строки разной длины нельзя передать в compare_digest)."""
    expected = _expected_password(context)
    return secrets.compare_digest(_sha256_hex(attempt.strip()), _sha256_hex(expected))


def _help_text() -> str:
    return (
        "Команды:\n"
        "/start - приветствие\n"
        "/help - показать справку\n"
        "/new - создать новый чат\n\n"
        "Опциональные флаги в начале сообщения:\n"
        "--format=... (значение json включает JSON mode API)\n"
        "--max-tokens=N\n"
        "--temperature=X (0..2)\n"
        "--stop=TEXT (до 4 раз)\n\n"
        'Пример:\n--format="краткий список" --max-tokens=200 --temperature=0.7 --stop=END Что такое Python?'
    )


def _service(context: ContextTypes.DEFAULT_TYPE) -> ChatService:
    return context.application.bot_data["chat_service"]


def _session_key(update: Update) -> str:
    user = update.effective_user
    return f"tg:{user.id}" if user else "tg:unknown"


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authenticated(context):
        await update.message.reply_text(
            "Привет! Это NeuroAPI Telegram-бот.\n\n"
            "Чтобы пользоваться чатом с нейросетью, введите пароль одним сообщением"
        )
        return

    service = _service(context)
    chat_id = service.get_or_create_chat_id(_session_key(update))
    await update.message.reply_text(
        "Привет! Это NeuroAPI Telegram-бот.\n"
        f"Текущий чат: {chat_id}\n\n"
        f"{_help_text()}"
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prefix = ""
    if not _is_authenticated(context):
        prefix = (
            "Доступ к нейросети закрыт паролем. Введите пароль одним сообщением "
            "(см. `TELEGRAM_BOT_PASSWORD` в окружении).\n\n"
        )
    await update.message.reply_text(prefix + _help_text())


async def new_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authenticated(context):
        await update.message.reply_text(
            "Сначала введите пароль в чат (без команд), затем можно будет создавать чаты и писать боту."
        )
        return

    service = _service(context)
    chat_id = service.new_chat(_session_key(update))
    await update.message.reply_text(f"Создан новый чат: {chat_id}")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or not message.text:
        return

    if not _is_authenticated(context):
        if _password_ok(context, message.text):
            _set_authenticated(context)
            service = _service(context)
            chat_id = service.get_or_create_chat_id(_session_key(update))
            await message.reply_text(
                "Пароль принят. Доступ к чату открыт.\n\n"
                f"Текущий чат: {chat_id}\n\n"
                f"{_help_text()}"
            )
            return

        await message.reply_text("Неверный пароль. Попробуйте ещё раз или отправьте /start.")
        return

    service = _service(context)
    result = service.process_message(_session_key(update), message.text)
    if result.error:
        await message.reply_text(result.error)
        return

    await message.reply_text(
        f"{result.assistant_text}\n\nСкорость ответа сервера: {result.elapsed_seconds:.2f} c"
    )


def main() -> None:
    config = load_bot_config()
    client = create_client(base_url=config.base_url, api_key=config.neuroapi_key)
    chat_service = ChatService(client=client, model=config.model)

    application = Application.builder().token(config.telegram_bot_token).build()
    application.bot_data["chat_service"] = chat_service
    application.bot_data["telegram_bot_password"] = config.telegram_bot_password

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("new", new_chat_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Telegram bot is running (polling)...")
    application.run_polling()


if __name__ == "__main__":
    main()
