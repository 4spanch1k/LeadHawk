from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from config import Settings, load_settings
from db import Database

LOGGER = logging.getLogger(__name__)
COMMANDS = ("discover", "parse", "export", "run", "stats", "bot")


def configure_logging(logs_dir: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "lead_parser.log", encoding="utf-8"),
        ],
    )


def discover(settings: Settings, database: Database) -> bool:
    from lead_collection import LeadCollection

    try:
        result = LeadCollection(settings, database).discover()
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        return False
    print(
        f"Google: найдено ссылок — {result.links_found}, "
        f"новых источников — {result.sources_saved}"
    )
    return True


def parse_sources(settings: Settings, database: Database) -> bool:
    from lead_collection import LeadCollection

    try:
        result = asyncio.run(LeadCollection(settings, database).parse())
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        return False
    except (KeyboardInterrupt, EOFError):
        LOGGER.error("Авторизация Telegram прервана")
        return False
    print(
        f"Telegram: проверено сообщений — {result.messages_checked}, "
        f"сохранено лидов — {result.leads_saved}"
    )
    return True


def export(settings: Settings, database: Database) -> None:
    from lead_collection import LeadCollection

    result = LeadCollection(settings, database).export()
    print(f"Экспортировано лидов: {result.leads_exported}. Файл: {result.output_path}")


def print_stats(database: Database) -> None:
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
        export(settings, database)
        return 0
    if args.command == "stats":
        print_stats(database)
        return 0
    if args.command == "bot":
        from telegram_bot import run_bot

        try:
            run_bot(settings, database)
        except RuntimeError as exc:
            LOGGER.error("%s", exc)
            return 1
        except KeyboardInterrupt:
            LOGGER.info("Telegram-бот остановлен")
        return 0

    LOGGER.info("Запуск этапа: discover")
    success = discover(settings, database)
    LOGGER.info("Запуск этапа: parse")
    success = parse_sources(settings, database) and success
    LOGGER.info("Запуск этапа: export")
    export(settings, database)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
