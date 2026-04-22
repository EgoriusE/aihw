#!/usr/bin/env python3
"""
Минимальный CLI-чат через NeuroAPI.

Запуск:
  python3 chat_cli.py --api-key "ключ_из_кабинета_NeuroAPI" --model "название_модели"
"""

import argparse
import re
import shlex
import time
import uuid
from typing import Any, List, Optional, TypedDict

from openai import OpenAI

MAX_STOP_SEQUENCES = 4
_FLAG_TOKEN_RE = re.compile(r"^--([\w-]+)=(.*)$")


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
    print("Любой другой текст отправляется в активный чат.")
    print("\nОпциональные флаги в начале строки (токены --ключ=значение):")
    print("  --format=...              описание формата (добавляется к сообщению);")
    print("                            значение json включает JSON mode API")
    print("  --max-tokens=N            лимит max_tokens")
    print("  --temperature=X           температура генерации (число от 0 до 2)")
    print("  --stop=TEXT               стоп-последовательность (до 4 раз)")
    print('Пример: --format="краткий список" --max-tokens=200 --temperature=0.7 --stop=END Что такое Python?\n')


def new_chat() -> tuple[str, List[ChatMessage]]:
    """Создаёт локальную сессию чата (история хранится у клиента)."""
    chat_id = uuid.uuid4().hex[:10]
    print(f"Создан чат: {chat_id}")
    return chat_id, []


def parse_user_input(line: str) -> tuple[Optional[str], dict[str, Any], Optional[str]]:
    """
    Разбирает строку ввода: опциональные флаги --ключ=значение, затем текст сообщения.

    Возвращает (content, api_extras, error). content is None при ошибке разбора.
    """
    stripped = line.strip()
    if not stripped:
        return None, {}, "Пустой ввод"

    try:
        parts = shlex.split(stripped)
    except ValueError as exc:
        return None, {}, f"Ошибка разбора строки: {exc}"

    index = 0
    format_value: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stops: List[str] = []

    while index < len(parts):
        match = _FLAG_TOKEN_RE.match(parts[index])
        if not match:
            break
        raw_key = match.group(1)
        value = match.group(2)
        key = raw_key.lower().replace("-", "_")

        if key == "format":
            format_value = value
        elif key == "max_tokens":
            try:
                parsed = int(value)
            except ValueError:
                return None, {}, f"Неверное значение --max-tokens: ожидается целое число, получено {value!r}"
            if parsed <= 0:
                return None, {}, "Неверное значение --max-tokens: ожидается положительное целое"
            max_tokens = parsed
        elif key == "temperature":
            try:
                parsed = float(value)
            except ValueError:
                return None, {}, f"Неверное значение --temperature: ожидается число, получено {value!r}"
            if not 0 <= parsed <= 2:
                return None, {}, "Неверное значение --temperature: ожидается число в диапазоне от 0 до 2"
            temperature = parsed
        elif key == "stop":
            stops.append(value)
        else:
            return None, {}, f"Неизвестный флаг: --{raw_key}"

        index += 1

    message_tokens = parts[index:]
    body = " ".join(message_tokens).strip()

    if index > 0 and not body:
        return None, {}, "Укажите текст сообщения после флагов"

    if len(stops) > MAX_STOP_SEQUENCES:
        return (
            None,
            {},
            f"Слишком много --stop (максимум {MAX_STOP_SEQUENCES})",
        )

    api_extras: dict[str, Any] = {}
    if max_tokens is not None:
        api_extras["max_tokens"] = max_tokens
    if temperature is not None:
        api_extras["temperature"] = temperature

    if stops:
        api_extras["stop"] = stops[0] if len(stops) == 1 else stops

    content = body

    if format_value is not None:
        spec = format_value.strip()
        if spec.lower() == "json":
            api_extras["response_format"] = {"type": "json_object"}
            suffix = "\n\nОтветь только валидным JSON без текста вне JSON."
            content = f"{content}{suffix}" if content else suffix.strip()
        else:
            block = f"\n\nТребование к формату:\n{format_value}"
            content = f"{content}{block}" if content else block.strip()

    return content, api_extras, None


def send_message(
    client: OpenAI,
    messages: List[ChatMessage],
    model: str,
    text: str,
    extra_params: Optional[dict[str, Any]] = None,
) -> None:
    """Отправляет сообщение и дополняет историю ответом ассистента."""

    messages.append({"role": "user", "content": text})

    create_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if extra_params:
        create_kwargs.update(extra_params)

    start_time = time.perf_counter()
    try:
        completion = client.chat.completions.create(**create_kwargs)
    except Exception as error:
        messages.pop()
        print(f"Ошибка запроса к API: {error}")
        return
    elapsed_seconds = time.perf_counter() - start_time

    raw = completion.choices[0].message.content
    assistant_text = (raw or "").strip()
    if not assistant_text:
        assistant_text = "(пустой ответ)"

    messages.append({"role": "assistant", "content": assistant_text})

    print(f"\nАссистент: {assistant_text}\n")
    print(f"Скорость ответа сервера: {elapsed_seconds:.2f} c\n")


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

        content, api_extras, parse_error = parse_user_input(user_input)
        if parse_error:
            print(parse_error)
            continue

        send_message(client, active_messages, args.model, content, api_extras or None)


if __name__ == "__main__":
    main()