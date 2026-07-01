from __future__ import annotations

import html

from aiogram.types import BotCommand

from models import DatabaseStats, StoredLead

HELP_TEXT = """<b>LeadHawk</b>

/run — найти источники, собрать лиды и экспортировать CSV
/discover — найти новые публичные Telegram-источники
/parse — собрать свежие лиды из известных источников
/stats — показать статистику
/latest — показать последние лиды
/export — получить CSV-файл
/auto_on — включить фоновый сбор
/auto_off — приостановить фоновый сбор
/help — показать команды"""

BOT_COMMANDS = (
    BotCommand(command="run", description="Запустить полный сбор"),
    BotCommand(command="discover", description="Найти новые источники"),
    BotCommand(command="parse", description="Собрать свежие лиды"),
    BotCommand(command="stats", description="Показать статистику"),
    BotCommand(command="latest", description="Показать последние лиды"),
    BotCommand(command="export", description="Получить CSV"),
    BotCommand(command="auto_on", description="Включить автосбор"),
    BotCommand(command="auto_off", description="Остановить автосбор"),
    BotCommand(command="help", description="Показать справку"),
)


def format_lead(lead: StoredLead) -> str:
    budget = lead.get("budget") or "не указан"
    currency = lead.get("currency")
    if currency and currency != "unknown" and lead.get("budget"):
        budget = f"{budget} {currency}"

    contacts = lead.get("contact_usernames") or ()
    contact_text = ", ".join(contacts) if contacts else "не указан"
    sender = lead.get("sender_username")
    if sender:
        sender_contact = sender if str(sender).startswith("@") else f"@{sender}"
        if sender_contact not in contacts:
            contact_text = (
                f"{contact_text}, {sender_contact}" if contacts else sender_contact
            )

    link_line = ""
    if message_link := lead.get("message_link"):
        safe_link = html.escape(str(message_link), quote=True)
        link_line = f'\n<a href="{safe_link}">Открыть сообщение</a>'

    return (
        f"<b>Новый лид · {int(lead['lead_score'])}/100</b>\n"
        f"Категория: {html.escape(str(lead['category']))}\n"
        f"Источник: @{html.escape(str(lead['source_username']))}\n"
        f"Бюджет: {html.escape(str(budget))}\n"
        f"Контакт: {html.escape(contact_text)}\n\n"
        f"{html.escape(str(lead['task_summary']))}"
        f"{link_line}"
    )


def format_stats(stats: DatabaseStats, auto_enabled: bool) -> str:
    statuses = stats["sources_by_status"]
    categories = stats["top_categories"]
    sources = stats["top_sources"]
    category_lines = (
        "\n".join(f"• {name}: {count}" for name, count in categories)
        if categories
        else "• нет данных"
    )
    source_lines = (
        "\n".join(f"• @{name}: {count}" for name, count in sources)
        if sources
        else "• нет данных"
    )
    return (
        "<b>Статистика LeadHawk</b>\n"
        f"Источников: {stats['total_sources']}\n"
        f"Активных: {statuses.get('active', 0)}\n"
        f"Недоступных: {statuses.get('unavailable', 0)}\n"
        f"Новых: {statuses.get('new', 0)}\n"
        f"Лидов за 24 часа: {stats['recent_leads']}\n"
        f"Автосбор: {'включён' if auto_enabled else 'выключен'}\n\n"
        f"<b>Категории</b>\n{html.escape(category_lines)}\n\n"
        f"<b>Источники</b>\n{html.escape(source_lines)}"
    )
