import re
import shlex
from typing import Any, Optional

MAX_STOP_SEQUENCES = 4
_FLAG_TOKEN_RE = re.compile(r"^--([\w-]+)=(.*)$")


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
    stops: list[str] = []

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
