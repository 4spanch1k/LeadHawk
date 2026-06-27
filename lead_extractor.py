from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from models import Lead, PublicMessage
from scoring import score_lead
from text_processing import normalize_text

USERNAME_PATTERN = re.compile(r"(?<![\w@])@([A-Za-z][A-Za-z0-9_]{4,31})")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\s()\-]*){10,15}(?!\d)")
BUDGET_PATTERN = re.compile(
    r"(?ix)"
    r"(?:бюджет|оплата)?\s*:?\s*"
    r"((?:от\s+)?(?:[$€]\s*)?\d[\d\s.,]*(?:\s*(?:до|-)\s*"
    r"(?:[$€]\s*)?\d[\d\s.,]*)?\s*(?:к|k|тыс\.?)?\s*"
    r"(?:тг|₸|руб(?:лей|ля)?|₽|usd|\$|eur|€)?)"
)

CATEGORY_KEYWORDS = (
    ("mini_app", ("telegram mini app", "mini app", "мини апп")),
    (
        "telegram_bot",
        ("telegram bot", "телеграм бот", "тг бот", "tg bot", "бот в телеграм"),
    ),
    ("landing", ("лендинг", "landing page")),
    ("website", ("сайт",)),
    ("parser", ("парсер", "скрапер", "scraping", "parser")),
    ("crm", ("amocrm", "amo crm", "crm", "bitrix", "битрикс")),
    ("frontend", ("frontend", "фронтенд", "верстк", "вёрстк", "сверстать")),
    ("integration", ("интеграци",)),
    ("design", ("дизайн", "figma", "макет")),
    ("other", ()),
)


def detect_category(text: str) -> str:
    normalized = normalize_text(text)
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "other"


def extract_budget(text: str) -> tuple[str | None, str]:
    for match in BUDGET_PATTERN.finditer(text):
        value = match.group(1).strip(" :,.")
        if not re.search(r"\d", value):
            continue
        context = text[max(0, match.start() - 12) : match.end() + 8].lower()
        if "₸" in value or "тг" in value.lower():
            currency = "KZT"
        elif "₽" in value or "руб" in value.lower():
            currency = "RUB"
        elif "$" in value or "usd" in value.lower():
            currency = "USD"
        elif "€" in value or "eur" in value.lower():
            currency = "EUR"
        elif (
            re.search(r"\d\s*(?:к|k|тыс\.?)\b", value.lower())
            or "бюджет" in context
            or "оплата" in context
            or " до " in context
        ):
            currency = "unknown"
        else:
            continue
        return value, currency
    return None, "unknown"


def build_unique_hash(
    source_username: str,
    message_id: int | None,
    raw_text: str,
) -> str:
    identity = (
        f"{source_username.lower()}:{message_id}"
        if message_id is not None
        else f"{source_username.lower()}:{normalize_text(raw_text)}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def summarize_task(text: str, max_length: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_length:
        return compact
    shortened = compact[: max_length + 1].rsplit(" ", 1)[0]
    return f"{shortened}…"


def extract_lead(
    message: PublicMessage,
    *,
    collected_at: datetime | None = None,
) -> Lead:
    contacts = tuple(
        sorted({f"@{value}" for value in USERNAME_PATTERN.findall(message.raw_text)})
    )
    phones = tuple(
        sorted(
            {
                re.sub(r"\s+", " ", value).strip()
                for value in PHONE_PATTERN.findall(message.raw_text)
            }
        )
    )
    budget, currency = extract_budget(message.raw_text)
    category = detect_category(message.raw_text)
    summary = summarize_task(message.raw_text)
    collected = collected_at or datetime.now(timezone.utc)
    score = score_lead(
        text=message.raw_text,
        task_summary=summary,
        category=category,
        budget=budget,
        contact_usernames=contacts,
        sender_username=message.sender_username,
        published_at=message.published_at,
        now=collected,
    )
    return Lead(
        source_username=message.source_username,
        message_id=message.message_id,
        message_link=message.message_link,
        published_at=message.published_at,
        collected_at=collected,
        sender_username=message.sender_username,
        task_summary=summary,
        category=category,
        budget=budget,
        currency=currency,
        contact_usernames=contacts,
        phone_numbers=phones,
        raw_text=message.raw_text,
        lead_score=score,
        unique_hash=build_unique_hash(
            message.source_username,
            message.message_id,
            message.raw_text,
        ),
    )
