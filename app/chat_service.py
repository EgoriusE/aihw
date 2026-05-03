import uuid
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from app.llm_client import ChatMessage, generate_reply
from app.message_parser import parse_user_input


@dataclass
class ServiceResult:
    assistant_text: Optional[str]
    elapsed_seconds: float
    error: Optional[str]


class ChatService:
    """Простой менеджер чатов в памяти по ключу сессии."""

    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model
        self._sessions: dict[str, list[ChatMessage]] = {}
        self._chat_ids: dict[str, str] = {}

    def new_chat(self, session_key: str) -> str:
        chat_id = uuid.uuid4().hex[:10]
        self._sessions[session_key] = []
        self._chat_ids[session_key] = chat_id
        return chat_id

    def get_or_create_chat_id(self, session_key: str) -> str:
        chat_id = self._chat_ids.get(session_key)
        if chat_id:
            return chat_id
        return self.new_chat(session_key)

    def process_message(self, session_key: str, raw_input: str) -> ServiceResult:
        self.get_or_create_chat_id(session_key)
        messages = self._sessions[session_key]

        content, api_extras, parse_error = parse_user_input(raw_input)
        if parse_error:
            return ServiceResult(
                assistant_text=None,
                elapsed_seconds=0.0,
                error=parse_error,
            )

        messages.append({"role": "user", "content": content})
        assistant_text, elapsed_seconds, api_error = generate_reply(
            client=self.client,
            messages=messages,
            model=self.model,
            extra_params=api_extras or None,
        )
        if api_error:
            messages.pop()
            return ServiceResult(
                assistant_text=None,
                elapsed_seconds=0.0,
                error=api_error,
            )

        messages.append({"role": "assistant", "content": assistant_text or "(пустой ответ)"})
        return ServiceResult(
            assistant_text=assistant_text or "(пустой ответ)",
            elapsed_seconds=elapsed_seconds,
            error=None,
        )
