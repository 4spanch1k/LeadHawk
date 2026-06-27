from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from config import Settings, load_settings
from db import Database
from utils import configure_logging

LOGGER = logging.getLogger(__name__)
COMMANDS = ("discover", "parse", "export", "run", "stats")


def discover(settings: Settings, database: Database) -> bool:
    if not settings.google_configured:
        LOGGER.error(
            "Google API не настроен: заполните GOOGLE_API_KEY и GOOGLE_CX в .env"
        )
        return False
    from google_finder import GoogleFinder

    try:
        found, saved = GoogleFinder(settings, database).discover()
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        return False
    print(f"Google: найдено ссылок — {found}, новых источников — {saved}")
    return True


def parse_sources(settings: Settings, database: Database) -> bool:
    if not settings.telegram_configured:
        LOGGER.error(
            "Telegram API не настроен: заполните TG_API_ID, TG_API_HASH и TG_PHONE"
        )
        return False
    from telegram_parser import TelegramParser

    try:
        checked, saved = asyncio.run(TelegramParser(settings, database).parse())
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        return False
    except (KeyboardInterrupt, EOFError):
        LOGGER.error("Авторизация Telegram прервана")
        return False
    print(f"Telegram: проверено сообщений — {checked}, сохранено лидов — {saved}")
    return True


def export(settings: Settings, database: Database) -> bool:
    from exporter import export_leads

    output_path = settings.data_dir / "leads.csv"
    count = export_leads(database, output_path)
    print(f"Экспортировано лидов: {count}. Файл: {output_path}")
    return True


def print_stats(database: Database) -> bool:
    stats = database.stats()
    statuses = stats["sources_by_status"]
    print(f"Источников всего: {stats['total_sources']}")
    print(f"Активных: {statuses.get('active', 0)}")
    print(f"Недоступных: {statuses.get('unavailable', 0)}")
    print(f"Новых: {statuses.get('new', 0)}")
    print(f"Лидов за 24 часа: {stats['recent_leads']}")
    print("Топ категорий:")
    if stats["top_categories"]:
        for category, count in stats["top_categories"]:
            print(f"  {category}: {count}")
    else:
        print("  нет данных")
    print("Топ источников:")
    if stats["top_sources"]:
        for source, count in stats["top_sources"]:
            print(f"  @{source}: {count}")
    else:
        print("  нет данных")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LeadHawk — поиск публичных заявок в Telegram"
    )
    parser.add_argument("command", choices=COMMANDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        return 2

    configure_logging(settings.logs_dir)
    database = Database(settings.database_path)
    database.initialize()

    if args.command == "discover":
        return 0 if discover(settings, database) else 1
    if args.command == "parse":
        return 0 if parse_sources(settings, database) else 1
    if args.command == "export":
        return 0 if export(settings, database) else 1
    if args.command == "stats":
        return 0 if print_stats(database) else 1

    steps = (
        ("discover", lambda: discover(settings, database)),
        ("parse", lambda: parse_sources(settings, database)),
        ("export", lambda: export(settings, database)),
    )
    success = True
    for name, step in steps:
        LOGGER.info("Запуск этапа: %s", name)
        success = step() and success
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
