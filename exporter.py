from __future__ import annotations

from pathlib import Path

import pandas as pd

from db import Database

EXPORT_COLUMNS = [
    "published_at",
    "source_username",
    "category",
    "lead_score",
    "task_summary",
    "budget",
    "currency",
    "contact_usernames",
    "sender_username",
    "message_link",
    "raw_text",
]


def export_leads(database: Database, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = database.export_rows()
    frame = pd.DataFrame(rows, columns=EXPORT_COLUMNS)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return len(frame)
