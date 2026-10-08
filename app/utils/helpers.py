"""
Utility helpers used across the application.
"""

from __future__ import annotations
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List


def file_hash(path: Path, length: int = 8) -> str:
    """Short SHA-256 hash of a file — used as project_id."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:length]


def project_id_for_files(paths: List[Path]) -> str:
    """Stable project ID for a set of PDFs (based on sorted filenames)."""
    names = sorted(p.name for p in paths)
    combined = "|".join(names)
    return hashlib.sha256(combined.encode()).hexdigest()[:12]


def format_chunk_as_evidence(chunk: Dict[str, Any], index: int) -> str:
    h = chunk.get("heading") or "—"
    score = chunk.get("score", 0)
    return (
        f"**[{index}]** `{chunk['doc_name']}` — "
        f"Page **{chunk['page']}**, Section: _{h}_ "
        f"(similarity: {score:.2f})\n\n"
        f"> {chunk['text'][:500]}{'...' if len(chunk['text']) > 500 else ''}"
    )


def clean_text(text: str) -> str:
    """Basic text cleaning for display."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()
