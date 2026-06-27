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
    r"(?i)(?:https?://)?(?:www\.)?t\.me/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,31})"
)
RESERVED_PATHS = {"joinchat", "share", "addstickers", "proxy", "iv", "login"}


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
        for query in queries:
            for page in range(self.settings.google_pages_per_query):
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
                except requests.RequestException as exc:
                    LOGGER.error("Ошибка Google API для запроса %r: %s", query, exc)
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
                time.sleep(self.settings.request_delay_seconds)
            time.sleep(self.settings.request_delay_seconds)
        return found_count, saved_count
