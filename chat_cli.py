#!/usr/bin/env python3
"""Минимальный CLI-чат через NeuroAPI."""

import argparse

from app.chat_service import ChatService
from app.llm_client import create_client

DEFAULT_BASE_URL = "https://neuroapi.host/v1"
DEFAULT_MODEL = "gpt-4.1-nano"


def print_help() -> None:
    """Показывает доступные команды."""
    print("\nКоманды:")
    print("  /new   - создать новый чат и перейти в него")
    print("  /exit  - выйти из программы")
    print("Любой другой текст отправляется в активный чат.")
    print("\nОпциональные флаги в начале строки (токены --ключ=значение):")
    print("  --format=...              описание формата (добавляется к сообщению);")
    print("                            значение json включает JSON mode API")
    print("  --max-tokens=N            лимит max_tokens")
    print("  --temperature=X           температура генерации (число от 0 до 2)")
    print("  --stop=TEXT               стоп-последовательность (до 4 раз)")
    print('Пример: --format="краткий список" --max-tokens=200 --temperature=0.7 --stop=END Что такое Python?\n')


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

    client = create_client(base_url=args.base_url, api_key=args.api_key)
    service = ChatService(client=client, model=args.model)
    session_key = "cli"
    active_chat_id = service.new_chat(session_key)
    print(f"Создан чат: {active_chat_id}")

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
            active_chat_id = service.new_chat(session_key)
            print(f"Создан чат: {active_chat_id}")
            continue

        result = service.process_message(session_key, user_input)
        if result.error:
            print(result.error)
            continue

        print(f"\nАссистент: {result.assistant_text}\n")
        print(f"Скорость ответа сервера: {result.elapsed_seconds:.2f} c\n")


if __name__ == "__main__":
    main()