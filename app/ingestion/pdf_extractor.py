"""
PDF Ingestion — text extraction with page/section metadata preservation.
Uses PyMuPDF (fitz). Falls back gracefully on scanned PDFs.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF


# ── Section heading detection ──────────────────────────────────────────────────
_HEADING_RE = re.compile(
    r"^(\d+(?:\.\d+){0,3})\s+([A-Z][^\n]{3,80})$",
    re.MULTILINE,
)


def _detect_heading(text: str, font_size: float, flags: int) -> str | None:
    """
    Heuristic: large font, bold flags, or numbered heading pattern → section.
    Returns heading string or None.
    """
    is_bold = bool(flags & 2**4)
    is_large = font_size >= 13
    stripped = text.strip()
    if (is_bold or is_large) and 4 <= len(stripped) <= 100:
        return stripped
    m = _HEADING_RE.match(stripped)
    if m:
        return stripped
    return None


def extract_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extract text from every page of *pdf_path*.

    Returns a list of dicts:
        {
          "page":    int (1-indexed),
          "text":    str,
          "heading": str | None   (best candidate heading for the page),
          "char_count": int,
          "is_scanned": bool,
        }
    """
    doc = fitz.open(str(pdf_path))
    pages: List[Dict[str, Any]] = []

    current_heading: str | None = None

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        page_text_parts: List[str] = []
        page_heading_candidate: str | None = None

        for block in blocks:
            if block.get("type") != 0:          # skip image blocks
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    txt = span.get("text", "").strip()
                    if not txt:
                        continue
                    font_size = span.get("size", 11)
                    flags     = span.get("flags", 0)
                    h = _detect_heading(txt, font_size, flags)
                    if h and page_heading_candidate is None:
                        page_heading_candidate = h
                        current_heading = h
                    page_text_parts.append(txt)

        raw_text = "\n".join(page_text_parts).strip()
        is_scanned = len(raw_text) < 50 and len(blocks) > 0

        pages.append(
            {
                "page":       page_num,
                "text":       raw_text,
                "heading":    page_heading_candidate or current_heading,
                "char_count": len(raw_text),
                "is_scanned": is_scanned,
            }
        )

    doc.close()
    return pages


def get_document_stats(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_chars  = sum(p["char_count"] for p in pages)
    scanned_pgs  = [p["page"] for p in pages if p["is_scanned"]]
    headings     = list({p["heading"] for p in pages if p["heading"]})
    return {
        "total_pages":   len(pages),
        "total_chars":   total_chars,
        "scanned_pages": scanned_pgs,
        "headings_found": headings,
        "ocr_required":  len(scanned_pgs) > 0,
    }
