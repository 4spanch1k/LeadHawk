from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable
from urllib.parse import unquote

import requests

from config import Settings
from constants import GOOGLE_QUERIES, GOOGLE_SEARCH_URL
from db import Database
from models import Source

LOGGER = logging.getLogger(__name__)
TELEGRAM_LINK_PATTERN = re.compile(
    r"(?i)(?:https?://)?(?:www\.)?t\.me/(?:s/)?([A-Za-z][A-Za-z0-9_]{4,31})"
)
RESERVED_PATHS = {"c", "joinchat", "share", "addstickers", "proxy", "iv", "login"}


def extract_public_sources(value: str, discovered_from: str) -> list[Source]:
    decoded = unquote(value)
    sources: dict[str, Source] = {}
    for match in TELEGRAM_LINK_PATTERN.finditer(decoded):
        username = match.group(1)
        if username.lower() in RESERVED_PATHS:
            continue
        normalized = username.lower()
        sources[normalized] = Source(
            username=username,
            url=f"https://t.me/{username}",
            discovered_from=discovered_from,
        )
    return list(sources.values())


class GoogleFinder:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.session = requests.Session()

    def discover(self, queries: Iterable[str] = GOOGLE_QUERIES) -> tuple[int, int]:
        if not self.settings.google_configured:
            raise RuntimeError(
                "Google API не настроен: заполните GOOGLE_API_KEY и GOOGLE_CX в .env"
            )

        found_count = 0
        saved_count = 0
        request_count = 0
        for query in queries:
            for page in range(self.settings.google_pages_per_query):
                if request_count:
                    time.sleep(self.settings.request_delay_seconds)
                params = {
                    "key": self.settings.google_api_key,
                    "cx": self.settings.google_cx,
                    "q": query,
                    "start": page * 10 + 1,
                    "num": 10,
                }
                try:
                    response = self.session.get(
                        GOOGLE_SEARCH_URL,
                        params=params,
                        timeout=30,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    request_count += 1
                except requests.HTTPError as exc:
                    status_code = (
                        exc.response.status_code if exc.response else "unknown"
                    )
                    if status_code in {401, 403}:
                        raise RuntimeError(
                            f"Google API отклонил запрос ({status_code}). "
                            "Проверьте API key, ограничения ключа, CX и квоту."
                        ) from exc
                    LOGGER.error(
                        "Google API вернул HTTP %s для запроса %r",
                        status_code,
                        query,
                    )
                    break
                except requests.RequestException as exc:
                    LOGGER.error(
                        "Сетевая ошибка Google API (%s) для запроса %r",
                        type(exc).__name__,
                        query,
                    )
                    break

                items = payload.get("items", [])
                for item in items:
                    candidates = " ".join(
                        str(item.get(field, "")) for field in ("link", "formattedUrl")
                    )
                    for source in extract_public_sources(candidates, query):
                        found_count += 1
                        if self.database.save_source(source):
                            saved_count += 1

                if len(items) < 10:
                    break
        return found_count, saved_count
