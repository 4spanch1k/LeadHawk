from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)

from config import Settings
from constants import SOURCE_ACTIVE, SOURCE_UNAVAILABLE
from db import Database
from lead_extractor import extract_lead
from lead_filter import is_lead
from models import PublicMessage

LOGGER = logging.getLogger(__name__)
UNAVAILABLE_ERRORS = (
    ChannelPrivateError,
    ChatAdminRequiredError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)


class TelegramParser:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    async def parse(self) -> tuple[int, int]:
        if not self.settings.telegram_configured:
            raise RuntimeError(
                "Telegram API не настроен: заполните TG_API_ID, TG_API_HASH и TG_PHONE"
            )
        session_path = self.settings.sessions_dir / "lead_parser"
        client = TelegramClient(
            str(session_path),
            self.settings.tg_api_id,
            self.settings.tg_api_hash,
        )
        checked_messages = 0
        saved_leads = 0
        await client.start(phone=self.settings.tg_phone)
        try:
            for source in self.database.list_sources():
                checked, saved = await self._parse_source(client, source["username"])
                checked_messages += checked
                saved_leads += saved
                await asyncio.sleep(self.settings.request_delay_seconds)
        finally:
            await client.disconnect()
        return checked_messages, saved_leads

    async def _parse_source(
        self,
        client: TelegramClient,
        username: str,
    ) -> tuple[int, int]:
        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=self.settings.hours_lookback
        )
        checked = 0
        saved = 0
        try:
            entity = await client.get_entity(username)
            async for message in client.iter_messages(
                entity,
                limit=self.settings.max_messages_per_source,
            ):
                if not message.date:
                    continue
                published_at = message.date.astimezone(timezone.utc)
                if published_at < cutoff:
                    break
                checked += 1
                text = message.message or ""
                if not is_lead(text):
                    continue
                sender = await message.get_sender()
                sender_username = getattr(sender, "username", None)
                public_message = PublicMessage(
                    source_username=username,
                    message_id=message.id,
                    message_link=f"https://t.me/{username}/{message.id}",
                    published_at=published_at,
                    sender_username=sender_username,
                    raw_text=text,
                )
                if self.database.save_lead(extract_lead(public_message)):
                    saved += 1
            self.database.update_source_status(username, SOURCE_ACTIVE)
        except FloodWaitError as exc:
            wait_seconds = min(exc.seconds, 300)
            LOGGER.warning("FloodWait для %s: пауза %s сек.", username, wait_seconds)
            await asyncio.sleep(wait_seconds)
            self.database.update_source_status(
                username, SOURCE_ACTIVE, f"FloodWait: {exc.seconds}s"
            )
        except UNAVAILABLE_ERRORS as exc:
            LOGGER.warning("Источник @%s недоступен: %s", username, exc)
            self.database.update_source_status(username, SOURCE_UNAVAILABLE, str(exc))
        except (TimeoutError, asyncio.TimeoutError) as exc:
            LOGGER.warning("Таймаут источника @%s: %s", username, exc)
            self.database.record_source_error(username, "Timeout")
        except Exception as exc:
            LOGGER.exception("Ошибка парсинга @%s", username)
            self.database.record_source_error(username, str(exc))
        return checked, saved
