"""
Text Chunker — splits pages into overlapping chunks while preserving metadata.
"""

from __future__ import annotations
from typing import List, Dict, Any
import uuid

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


def _split_text(text: str, size: int, overlap: int) -> List[str]:
    """Simple character-level sliding-window splitter."""
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start += size - overlap
    return [c for c in chunks if c]


def chunk_pages(
    pages: List[Dict[str, Any]],
    doc_name: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """
    Given extracted pages, produce a flat list of chunk dicts:
        {
          "chunk_id":   str (UUID),
          "doc_name":   str,
          "page":       int,
          "heading":    str | None,
          "text":       str,
          "char_count": int,
        }
    """
    all_chunks: List[Dict[str, Any]] = []

    for page in pages:
        text = page["text"]
        if not text:
            continue
        sub_chunks = _split_text(text, chunk_size, chunk_overlap)
        for chunk_text in sub_chunks:
            all_chunks.append(
                {
                    "chunk_id":   str(uuid.uuid4()),
                    "doc_name":   doc_name,
                    "page":       page["page"],
                    "heading":    page.get("heading"),
                    "text":       chunk_text,
                    "char_count": len(chunk_text),
                }
            )

    return all_chunks
