from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict


class StoredLead(TypedDict):
    id: int
    published_at: str
    source_username: str
    category: str
    lead_score: int
    task_summary: str
    budget: str | None
    currency: str
    contact_usernames: tuple[str, ...]
    sender_username: str | None
    message_link: str | None
    raw_text: str


class DatabaseStats(TypedDict):
    total_sources: int
    sources_by_status: dict[str, int]
    recent_leads: int
    top_categories: list[tuple[str, int]]
    top_sources: list[tuple[str, int]]


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
