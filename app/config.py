import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://neuroapi.host/v1"
DEFAULT_MODEL = "gpt-4.1-nano"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Не задана переменная окружения {name}")
    return value


@dataclass(frozen=True)
class AppConfig:
    neuroapi_key: str
    telegram_bot_token: str
    base_url: str
    model: str
    telegram_bot_password: str


def load_bot_config() -> AppConfig:
    return AppConfig(
        neuroapi_key=_required_env("NEUROAPI_KEY"),
        telegram_bot_token=_required_env("TELEGRAM_BOT_TOKEN"),
        base_url=os.getenv("NEUROAPI_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
        model=os.getenv("NEUROAPI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        telegram_bot_password=_required_env("TELEGRAM_BOT_PASSWORD"),
    )
