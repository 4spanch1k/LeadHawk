from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, LinkPreviewOptions, Message

from bot_messages import BOT_COMMANDS, HELP_TEXT, format_lead, format_stats
from config import Settings
from db import Database
from lead_collection import LeadCollection
from models import StoredLead

LOGGER = logging.getLogger(__name__)


class LeadHawkBot:
    def __init__(self, settings: Settings, database: Database) -> None:
        if not settings.bot_configured:
            raise RuntimeError(
                "Telegram-бот не настроен: заполните BOT_TOKEN и BOT_OWNER_ID"
            )
        self.settings = settings
        self.database = database
        self.collection = LeadCollection(settings, database)
        self.owner_id = settings.bot_owner_id
        self.auto_enabled = settings.bot_auto_run_interval_minutes > 0
        self.operation_lock = asyncio.Lock()
        self.router = Router(name=__name__)
        self.router.message.filter(
            F.from_user.id == self.owner_id,
            F.chat.type == ChatType.PRIVATE,
        )
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.router.message.register(self.handle_start, CommandStart())
        self.router.message.register(self.handle_help, Command("help"))
        self.router.message.register(self.handle_run, Command("run"))
        self.router.message.register(self.handle_discover, Command("discover"))
        self.router.message.register(self.handle_parse, Command("parse"))
        self.router.message.register(self.handle_stats, Command("stats"))
        self.router.message.register(self.handle_latest, Command("latest"))
        self.router.message.register(self.handle_export, Command("export"))
        self.router.message.register(self.handle_auto_on, Command("auto_on"))
        self.router.message.register(self.handle_auto_off, Command("auto_off"))
        self.router.message.register(self.handle_unknown)

    async def handle_start(self, message: Message) -> None:
        await message.answer(HELP_TEXT, parse_mode=ParseMode.HTML)

    async def handle_help(self, message: Message) -> None:
        await message.answer(HELP_TEXT, parse_mode=ParseMode.HTML)

    async def handle_stats(self, message: Message) -> None:
        text = format_stats(self.database.stats(), self.auto_enabled)
        await message.answer(text, parse_mode=ParseMode.HTML)

    async def handle_latest(self, message: Message) -> None:
        leads = self.database.list_latest_leads(
            limit=10,
            minimum_score=self.settings.bot_notification_min_score,
        )
        if not leads:
            await message.answer("Лидов пока нет.")
            return
        for lead in leads:
            await self._send_lead(message.bot, lead)

    async def handle_discover(self, message: Message) -> None:
        async def action() -> str:
            result = await asyncio.to_thread(self.collection.discover)
            return (
                f"Поиск завершён. Ссылок: {result.links_found}, "
                f"новых источников: {result.sources_saved}."
            )

        await self._execute(message, "Ищу новые источники…", action)

    async def handle_parse(self, message: Message) -> None:
        async def action() -> str:
            previous_lead_id = self.database.latest_lead_id()
            result = await self.collection.parse()
            await self._notify_new_leads(message.bot, previous_lead_id)
            return (
                f"Сбор завершён. Проверено сообщений: "
                f"{result.messages_checked}, новых лидов: {result.leads_saved}."
            )

        await self._execute(message, "Собираю свежие лиды…", action)

    async def handle_run(self, message: Message) -> None:
        async def action() -> str:
            return await self._run_collection(message.bot)

        await self._execute(message, "Запускаю полный сбор…", action)

    async def handle_export(self, message: Message) -> None:
        result = await asyncio.to_thread(self.collection.export)
        await message.answer_document(
            FSInputFile(result.output_path),
            caption=f"Экспортировано лидов: {result.leads_exported}",
        )

    async def handle_auto_on(self, message: Message) -> None:
        if self.settings.bot_auto_run_interval_minutes <= 0:
            await message.answer(
                "Автосбор отключён в конфигурации. Укажите "
                "BOT_AUTO_RUN_INTERVAL_MINUTES больше 0 и перезапустите бота."
            )
            return
        self.auto_enabled = True
        await message.answer("Автосбор включён.")

    async def handle_auto_off(self, message: Message) -> None:
        self.auto_enabled = False
        await message.answer("Автосбор приостановлен до перезапуска бота.")

    async def handle_unknown(self, message: Message) -> None:
        await message.answer("Неизвестная команда. Используйте /help.")

    async def _execute(
        self,
        message: Message,
        progress_text: str,
        action: Callable[[], Awaitable[str]],
    ) -> None:
        if self.operation_lock.locked():
            await message.answer("Другая операция уже выполняется.")
            return
        await message.answer(progress_text)
        async with self.operation_lock:
            try:
                result = await action()
            except RuntimeError as exc:
                await message.answer(str(exc))
                return
            except Exception:
                LOGGER.exception("Ошибка команды Telegram-бота")
                await message.answer(
                    "Операция завершилась ошибкой. Подробности записаны в лог."
                )
                return
        await message.answer(result)

    async def _run_collection(self, bot: Bot) -> str:
        previous_lead_id = self.database.latest_lead_id()
        discovery = await asyncio.to_thread(self.collection.discover)
        parsing = await self.collection.parse()
        await asyncio.to_thread(self.collection.export)
        await self._notify_new_leads(bot, previous_lead_id)
        return (
            "Полный сбор завершён.\n"
            f"Ссылок найдено: {discovery.links_found}\n"
            f"Источников добавлено: {discovery.sources_saved}\n"
            f"Сообщений проверено: {parsing.messages_checked}\n"
            f"Лидов добавлено: {parsing.leads_saved}"
        )

    async def _notify_new_leads(self, bot: Bot, after_id: int) -> None:
        leads = self.database.list_leads_after(
            after_id,
            minimum_score=self.settings.bot_notification_min_score,
        )
        notification_limit = self.settings.bot_max_notifications
        for lead in leads[:notification_limit]:
            await self._send_lead(bot, lead)
        hidden_count = len(leads) - notification_limit
        if hidden_count > 0:
            await bot.send_message(
                self.owner_id,
                f"Ещё {hidden_count} лидов доступны через /latest или /export.",
            )

    async def _send_lead(self, bot: Bot, lead: StoredLead) -> None:
        await bot.send_message(
            self.owner_id,
            format_lead(lead),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

    async def periodic_collection(self, bot: Bot) -> None:
        interval_seconds = self.settings.bot_auto_run_interval_minutes * 60
        if interval_seconds <= 0:
            return
        while True:
            await asyncio.sleep(interval_seconds)
            if not self.auto_enabled or self.operation_lock.locked():
                continue
            async with self.operation_lock:
                try:
                    summary = await self._run_collection(bot)
                    await bot.send_message(self.owner_id, summary)
                except Exception:
                    LOGGER.exception("Ошибка фонового сбора")
                    await bot.send_message(
                        self.owner_id,
                        "Фоновый сбор завершился ошибкой. Проверьте лог.",
                    )


async def start_bot(settings: Settings, database: Database) -> None:
    lead_bot = LeadHawkBot(settings, database)
    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(lead_bot.router)
    await bot.set_my_commands(BOT_COMMANDS)
    periodic_task = asyncio.create_task(lead_bot.periodic_collection(bot))
    try:
        await dispatcher.start_polling(bot, close_bot_session=False)
    finally:
        periodic_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await periodic_task
        await bot.session.close()


def run_bot(settings: Settings, database: Database) -> None:
    asyncio.run(start_bot(settings, database))
