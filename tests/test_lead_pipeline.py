from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from db import Database
from exporter import EXPORT_COLUMNS, export_leads
from google_finder import extract_public_sources
from lead_extractor import detect_category, extract_budget, extract_lead
from lead_filter import is_lead
from models import PublicMessage
from bot_messages import format_lead


class LeadFilterTests(unittest.TestCase):
    def test_accepts_project_request(self) -> None:
        self.assertTrue(
            is_lead(
                "Нужно сделать Telegram bot, бюджет 100 000 тг. Пишите @client_user"
            )
        )

    def test_rejects_job_post(self) -> None:
        self.assertFalse(
            is_lead(
                "Вакансия: ищем frontend senior в штат, зарплата по итогам интервью"
            )
        )

    def test_project_signal_can_override_generic_job_word(self) -> None:
        self.assertTrue(
            is_lead(
                "Ищу разработчика. Разовая задача: сделать лендинг, бюджет 50000 тг"
            )
        )

    def test_strong_job_signal_is_not_overridden_by_project_word(self) -> None:
        self.assertFalse(
            is_lead("Вакансия frontend-разработчика в проект, зарплата 300 000 руб")
        )


class LeadExtractionTests(unittest.TestCase):
    def test_extracts_budget_currency_and_category(self) -> None:
        budget, currency = extract_budget("Нужен лендинг. Бюджет: 50 000 тг")
        self.assertEqual(budget, "50 000 тг")
        self.assertEqual(currency, "KZT")
        self.assertEqual(detect_category("Нужен telegram mini app"), "mini_app")

    def test_extracts_short_budget_without_currency(self) -> None:
        budget, currency = extract_budget("Нужно сделать сайт за 50к")
        self.assertEqual(budget, "50к")
        self.assertEqual(currency, "unknown")

    def test_builds_complete_lead(self) -> None:
        now = datetime.now(timezone.utc)
        message = PublicMessage(
            source_username="public_chat",
            message_id=42,
            message_link="https://t.me/public_chat/42",
            published_at=now,
            sender_username="author",
            raw_text="Нужно сделать сайт. Бюджет 1000 USD. Контакт @client_user",
        )
        lead = extract_lead(message, collected_at=now)
        self.assertEqual(lead.currency, "USD")
        self.assertIn("@client_user", lead.contact_usernames)
        self.assertGreater(lead.lead_score, 0)


class DatabaseTests(unittest.TestCase):
    def test_empty_database_stats_and_export_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "leads.db")
            database.initialize()
            self.assertEqual(database.stats()["total_sources"], 0)
            self.assertEqual(database.export_rows(), [])

    def test_prevents_duplicate_leads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "leads.db")
            database.initialize()
            now = datetime.now(timezone.utc)
            lead = extract_lead(
                PublicMessage(
                    source_username="public_chat",
                    message_id=1,
                    message_link="https://t.me/public_chat/1",
                    published_at=now,
                    sender_username=None,
                    raw_text="Нужно сделать сайт, бюджет 100 000 тг",
                ),
                collected_at=now,
            )
            self.assertTrue(database.save_lead(lead))
            self.assertFalse(database.save_lead(lead))

    def test_lists_only_leads_after_given_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "leads.db")
            database.initialize()
            now = datetime.now(timezone.utc)
            first_lead = extract_lead(
                PublicMessage(
                    source_username="public_chat",
                    message_id=1,
                    message_link="https://t.me/public_chat/1",
                    published_at=now,
                    sender_username=None,
                    raw_text="Нужно сделать сайт, бюджет 100 000 тг",
                ),
                collected_at=now,
            )
            database.save_lead(first_lead)
            previous_id = database.latest_lead_id()
            second_lead = extract_lead(
                PublicMessage(
                    source_username="public_chat",
                    message_id=2,
                    message_link="https://t.me/public_chat/2",
                    published_at=now,
                    sender_username="client",
                    raw_text="Нужен telegram bot, бюджет 500 USD",
                ),
                collected_at=now,
            )
            database.save_lead(second_lead)

            leads = database.list_leads_after(previous_id)

            self.assertEqual(len(leads), 1)
            self.assertEqual(leads[0]["message_link"], second_lead.message_link)


class GoogleSourceExtractionTests(unittest.TestCase):
    def test_extracts_supported_public_links_and_removes_duplicates(self) -> None:
        sources = extract_public_sources(
            "https://t.me/s/PublicChannel/123 и t.me/publicchannel",
            "query",
        )
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].username, "publicchannel")
        self.assertEqual(sources[0].url, "https://t.me/publicchannel")

    def test_ignores_internal_and_invalid_paths(self) -> None:
        sources = extract_public_sources(
            "https://t.me/c/123/4 https://t.me/share/url https://t.me/abcd",
            "query",
        )
        self.assertEqual(sources, [])


class ExportTests(unittest.TestCase):
    def test_exports_empty_csv_with_headers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = Database(root / "leads.db")
            database.initialize()
            output_path = root / "leads.csv"

            exported_count = export_leads(database, output_path)

            self.assertEqual(exported_count, 0)
            with output_path.open(encoding="utf-8-sig", newline="") as csv_file:
                rows = list(csv.reader(csv_file))
            self.assertEqual(rows, [EXPORT_COLUMNS])


class TelegramBotFormattingTests(unittest.TestCase):
    def test_escapes_lead_content_for_html(self) -> None:
        formatted = format_lead(
            {
                "lead_score": 90,
                "category": "website",
                "source_username": "public_chat",
                "budget": "1000",
                "currency": "USD",
                "contact_usernames": ("@client",),
                "sender_username": None,
                "task_summary": "Нужен сайт <срочно>",
                "message_link": "https://t.me/public_chat/1",
            }
        )

        self.assertIn("Нужен сайт &lt;срочно&gt;", formatted)
        self.assertIn("1000 USD", formatted)


if __name__ == "__main__":
    unittest.main()
