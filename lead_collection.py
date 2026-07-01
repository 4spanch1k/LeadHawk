from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config import Settings
from db import Database


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    links_found: int
    sources_saved: int


@dataclass(frozen=True, slots=True)
class ParseResult:
    messages_checked: int
    leads_saved: int


@dataclass(frozen=True, slots=True)
class ExportResult:
    leads_exported: int
    output_path: Path


class LeadCollection:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def discover(self) -> DiscoveryResult:
        from google_finder import GoogleFinder

        links_found, sources_saved = GoogleFinder(
            self.settings, self.database
        ).discover()
        return DiscoveryResult(links_found, sources_saved)

    async def parse(self) -> ParseResult:
        from telegram_parser import TelegramParser

        messages_checked, leads_saved = await TelegramParser(
            self.settings, self.database
        ).parse()
        return ParseResult(messages_checked, leads_saved)

    def export(self) -> ExportResult:
        from exporter import export_leads

        output_path = self.settings.data_dir / "leads.csv"
        leads_exported = export_leads(self.database, output_path)
        return ExportResult(leads_exported, output_path)
