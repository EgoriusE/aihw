import time
from typing import Any, Optional, TypedDict

from openai import OpenAI


class ChatMessage(TypedDict):
    role: str
    content: str


def create_client(base_url: str, api_key: str) -> OpenAI:
    """Создаёт OpenAI-совместимый клиент."""
    return OpenAI(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
    )


def generate_reply(
    client: OpenAI,
    messages: list[ChatMessage],
    model: str,
    extra_params: Optional[dict[str, Any]] = None,
) -> tuple[Optional[str], float, Optional[str]]:
    """Запрашивает ответ модели без изменения внешнего состояния."""
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
        return None, 0.0, f"Ошибка запроса к API: {error}"
    elapsed_seconds = time.perf_counter() - start_time

    raw = completion.choices[0].message.content
    assistant_text = (raw or "").strip()
    if not assistant_text:
        assistant_text = "(пустой ответ)"

    return assistant_text, elapsed_seconds, None
