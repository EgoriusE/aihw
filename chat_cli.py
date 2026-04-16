#!/usr/bin/env python3
"""
Минимальный CLI-чат через NeuroAPI.

Запуск:
  python3 chat_cli.py --api-key "ключ_из_кабинета_NeuroAPI" --model "название_модели"
"""

import argparse
import uuid
from typing import List, TypedDict

from openai import OpenAI


class ChatMessage(TypedDict):
    role: str
    content: str


DEFAULT_BASE_URL = "https://neuroapi.host/v1"
DEFAULT_MODEL = "gpt-4.1-nano"


def print_help() -> None:
    """Показывает доступные команды."""
    print("\nКоманды:")
    print("  /new   - создать новый чат и перейти в него")
    print("  /exit  - выйти из программы")
    print("Любой другой текст отправляется в активный чат.\n")


def new_chat() -> tuple[str, List[ChatMessage]]:
    """Создаёт локальную сессию чата (история хранится у клиента)."""
    chat_id = uuid.uuid4().hex[:10]
    print(f"Создан чат: {chat_id}")
    return chat_id, []


def send_message(
    client: OpenAI,
    messages: List[ChatMessage],
    model: str,
    text: str,
) -> None:
    """Отправляет сообщение и дополняет историю ответом ассистента."""

    messages.append({"role": "user", "content": text})

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except Exception as error:
        messages.pop()
        print(f"Ошибка запроса к API: {error}")
        return

    raw = completion.choices[0].message.content
    assistant_text = (raw or "").strip()
    if not assistant_text:
        assistant_text = "(пустой ответ)"

    messages.append({"role": "assistant", "content": assistant_text})

    print(f"\nАссистент: {assistant_text}\n")


def parse_args() -> argparse.Namespace:
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description="Минимальный CLI-чат через NeuroAPI (OpenAI SDK)",
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="API-ключ из кабинета NeuroAPI",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Базовый URL API (по умолчанию: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Идентификатор модели на стороне провайдера (по умолчанию: {DEFAULT_MODEL})",
    )
    return parser.parse_args()


def main() -> None:
    """Точка входа в программу."""
    args = parse_args()

    client = OpenAI(
        base_url=args.base_url.rstrip("/"),
        api_key=args.api_key,
    )

    active_chat_id, active_messages = new_chat()

    print("NeuroAPI CLI чат")
    print(f"Endpoint: {args.base_url}")
    print(f"Модель: {args.model}")
    print_help()

    while True:
        short_id = active_chat_id[-8:] if len(active_chat_id) > 8 else active_chat_id
        prompt = f"chat[{short_id}]> "
        user_input = input(prompt).strip()

        if not user_input:
            continue

        if user_input == "/exit":
            print("Пока!")
            break

        if user_input == "/new":
            active_chat_id, active_messages = new_chat()
            continue

        send_message(client, active_messages, args.model, user_input)


if __name__ == "__main__":
    main()