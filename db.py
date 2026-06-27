from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from constants import SOURCE_NEW
from models import Lead, Source


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    url TEXT NOT NULL,
                    discovered_from TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_checked_at TEXT,
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_username TEXT NOT NULL,
                    message_id INTEGER,
                    message_link TEXT,
                    published_at TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    sender_username TEXT,
                    task_summary TEXT NOT NULL,
                    category TEXT NOT NULL,
                    budget TEXT,
                    currency TEXT NOT NULL,
                    contact_usernames TEXT NOT NULL,
                    phone_numbers TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    lead_score INTEGER NOT NULL,
                    unique_hash TEXT NOT NULL UNIQUE
                );

                CREATE INDEX IF NOT EXISTS idx_sources_status
                    ON sources(status);
                CREATE INDEX IF NOT EXISTS idx_leads_published_score
                    ON leads(published_at DESC, lead_score DESC);
                CREATE INDEX IF NOT EXISTS idx_leads_category
                    ON leads(category);
                """
            )

    def save_source(self, source: Source) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sources (
                    username, url, discovered_from, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO NOTHING
                """,
                (
                    source.username,
                    source.url,
                    source.discovered_from,
                    SOURCE_NEW,
                    now,
                    now,
                ),
            )
            return cursor.rowcount > 0

    def list_sources(self) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM sources ORDER BY created_at ASC"
                ).fetchall()
            )

    def update_source_status(
        self,
        username: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE sources
                SET status = ?, updated_at = ?, last_checked_at = ?, error_message = ?
                WHERE username = ?
                """,
                (status, now, now, error_message, username),
            )

    def save_lead(self, lead: Lead) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO leads (
                    source_username, message_id, message_link, published_at,
                    collected_at, sender_username, task_summary, category,
                    budget, currency, contact_usernames, phone_numbers,
                    raw_text, lead_score, unique_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(unique_hash) DO NOTHING
                """,
                (
                    lead.source_username,
                    lead.message_id,
                    lead.message_link,
                    lead.published_at.isoformat(),
                    lead.collected_at.isoformat(),
                    lead.sender_username,
                    lead.task_summary,
                    lead.category,
                    lead.budget,
                    lead.currency,
                    json.dumps(lead.contact_usernames, ensure_ascii=False),
                    json.dumps(lead.phone_numbers, ensure_ascii=False),
                    lead.raw_text,
                    lead.lead_score,
                    lead.unique_hash,
                ),
            )
            return cursor.rowcount > 0

    def export_rows(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT published_at, source_username, category, lead_score,
                       task_summary, budget, currency, contact_usernames,
                       sender_username, message_link, raw_text
                FROM leads
                ORDER BY published_at DESC, lead_score DESC
                """
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            record["contact_usernames"] = ", ".join(
                json.loads(record["contact_usernames"])
            )
            result.append(record)
        return result

    def stats(self) -> dict[str, Any]:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with self.connect() as connection:
            total_sources = connection.execute(
                "SELECT COUNT(*) FROM sources"
            ).fetchone()[0]
            status_rows = connection.execute(
                "SELECT status, COUNT(*) count FROM sources GROUP BY status"
            ).fetchall()
            recent_leads = connection.execute(
                "SELECT COUNT(*) FROM leads WHERE published_at >= ?", (since,)
            ).fetchone()[0]
            top_categories = connection.execute(
                """
                SELECT category, COUNT(*) count
                FROM leads GROUP BY category
                ORDER BY count DESC, category ASC LIMIT 5
                """
            ).fetchall()
            top_sources = connection.execute(
                """
                SELECT source_username, COUNT(*) count
                FROM leads GROUP BY source_username
                ORDER BY count DESC, source_username ASC LIMIT 5
                """
            ).fetchall()
        return {
            "total_sources": total_sources,
            "sources_by_status": {row["status"]: row["count"] for row in status_rows},
            "recent_leads": recent_leads,
            "top_categories": [(row["category"], row["count"]) for row in top_categories],
            "top_sources": [(row["source_username"], row["count"]) for row in top_sources],
        }

