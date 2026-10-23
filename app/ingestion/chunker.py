"""
Text Chunker — splits pages into overlapping chunks while preserving metadata.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
import uuid

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


def _split_text(text: str, size: int, overlap: int) -> List[Tuple[int, str]]:
    """
    Sliding-window splitter. Returns (start_offset, chunk_text) pairs.
    Prefers to break on a newline/space near the window end so words are not cut.
    """
    if size <= 0:
        raise ValueError("chunk size must be positive")
    overlap = max(0, min(overlap, size - 1))   # overlap >= size would never advance
    chunks: List[Tuple[int, str]] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            window_floor = start + size // 2
            cut = max(text.rfind("\n", window_floor, end), text.rfind(" ", window_floor, end))
            if cut > start:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append((start, piece))
        if end >= n:
            break
        nxt = max(end - overlap, start + 1)
        # snap forward to the next word boundary so a chunk never starts mid-word
        while 0 < nxt < n and not text[nxt - 1].isspace() and nxt < end:
            nxt += 1
        start = nxt
    return chunks


def _heading_for_offset(page: Dict[str, Any], offset: int):
    """Heading in effect at *offset* inside the page text."""
    heading = page.get("heading")
    for off, h in page.get("sections", []) or []:
        if off <= offset:
            heading = h
        else:
            break
    return heading


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
        for start_off, chunk_text in _split_text(text, chunk_size, chunk_overlap):
            all_chunks.append(
                {
                    "chunk_id":   str(uuid.uuid4()),
                    "doc_name":   doc_name,
                    "page":       page["page"],
                    "heading":    _heading_for_offset(page, start_off),
                    "text":       chunk_text,
                    "char_count": len(chunk_text),
                }
            )

    return all_chunks
