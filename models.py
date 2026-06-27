from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Source:
    username: str
    url: str
    discovered_from: str


@dataclass(frozen=True, slots=True)
class PublicMessage:
    source_username: str
    message_id: int | None
    message_link: str | None
    published_at: datetime
    sender_username: str | None
    raw_text: str


@dataclass(frozen=True, slots=True)
class Lead:
    source_username: str
    message_id: int | None
    message_link: str | None
    published_at: datetime
    collected_at: datetime
    sender_username: str | None
    task_summary: str
    category: str
    budget: str | None
    currency: str
    contact_usernames: tuple[str, ...]
    phone_numbers: tuple[str, ...]
    raw_text: str
    lead_score: int
    unique_hash: str
