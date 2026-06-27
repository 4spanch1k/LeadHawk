from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


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


def configure_logging(logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "lead_parser.log", encoding="utf-8"),
        ],
        force=True,
    )

