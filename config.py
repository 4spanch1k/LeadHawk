from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} должен быть целым числом") from exc
    if value <= 0:
        raise ValueError(f"{name} должен быть больше нуля")
    return value


def _non_negative_float(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} должен быть числом") from exc
    if value < 0:
        raise ValueError(f"{name} не может быть отрицательным")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    tg_api_id: int | None
    tg_api_hash: str | None
    tg_phone: str | None
    google_api_key: str | None
    google_cx: str | None
    database_path: Path
    hours_lookback: int
    max_messages_per_source: int
    google_pages_per_query: int
    request_delay_seconds: float
    data_dir: Path
    logs_dir: Path
    sessions_dir: Path

    @property
    def telegram_configured(self) -> bool:
        return bool(self.tg_api_id and self.tg_api_hash and self.tg_phone)

    @property
    def google_configured(self) -> bool:
        return bool(self.google_api_key and self.google_cx)

    def ensure_directories(self) -> None:
        for path in (
            self.database_path.parent,
            self.data_dir,
            self.logs_dir,
            self.sessions_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    load_dotenv()
    database_path = Path(os.getenv("DATABASE_PATH", "data/leads.db")).expanduser()
    tg_api_id_raw = os.getenv("TG_API_ID", "").strip()
    tg_api_id = int(tg_api_id_raw) if tg_api_id_raw.isdigit() else None
    settings = Settings(
        tg_api_id=tg_api_id,
        tg_api_hash=os.getenv("TG_API_HASH") or None,
        tg_phone=os.getenv("TG_PHONE") or None,
        google_api_key=os.getenv("GOOGLE_API_KEY") or None,
        google_cx=os.getenv("GOOGLE_CX") or None,
        database_path=database_path,
        hours_lookback=_positive_int("HOURS_LOOKBACK", 24),
        max_messages_per_source=_positive_int("MAX_MESSAGES_PER_SOURCE", 300),
        google_pages_per_query=_positive_int("GOOGLE_PAGES_PER_QUERY", 2),
        request_delay_seconds=_non_negative_float("REQUEST_DELAY_SECONDS", 2),
        data_dir=Path("data"),
        logs_dir=Path("logs"),
        sessions_dir=Path("sessions"),
    )
    settings.ensure_directories()
    return settings

