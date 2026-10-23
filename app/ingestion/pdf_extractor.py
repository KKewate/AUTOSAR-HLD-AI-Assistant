"""
PDF Ingestion — text extraction with page/section metadata preservation.
Uses PyMuPDF (fitz). Falls back gracefully on scanned PDFs.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import List, Dict, Any

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24.3 (no deprecation warning)
except ImportError:  # pragma: no cover
    import fitz  # type: ignore


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
    if (is_bold or is_large) and 4 <= len(stripped) <= 100 \
            and not stripped.endswith((":", ",", ";")):
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
          "page":     int (1-indexed),
          "text":     str,
          "heading":  str | None   (heading in effect at the start of the page,
                                    else the first heading on it),
          "sections": list[(char_offset, heading)]  (headings inside the page text),
          "char_count": int,
          "is_scanned": bool,
        }
    """
    pages: List[Dict[str, Any]] = []
    current_heading: str | None = None

    with fitz.open(str(pdf_path)) as doc:
        for page_num, page in enumerate(doc, start=1):
            blocks = page.get_text("dict")["blocks"]
            lines_out: List[str] = []
            sections: List[tuple] = []
            offset = 0
            heading_at_start = current_heading

            for block in blocks:
                if block.get("type") != 0:          # skip image blocks
                    continue
                for line in block.get("lines", []):
                    spans = [sp for sp in line.get("spans", []) if sp.get("text", "").strip()]
                    if not spans:
                        continue
                    # Join the spans of one visual line with spaces (not newlines)
                    line_text = " ".join(sp["text"].strip() for sp in spans)
                    # Heading decision is made on the whole line, using its first span
                    h = _detect_heading(line_text, spans[0].get("size", 11), spans[0].get("flags", 0))
                    if h:
                        current_heading = h
                        sections.append((offset, h))
                    lines_out.append(line_text)
                    offset += len(line_text) + 1

            raw_text = "\n".join(lines_out).strip()
            is_scanned = len(raw_text) < 50 and len(blocks) > 0

            pages.append(
                {
                    "page":       page_num,
                    "text":       raw_text,
                    "heading":    heading_at_start or (sections[0][1] if sections else None),
                    "sections":   sections,
                    "char_count": len(raw_text),
                    "is_scanned": is_scanned,
                }
            )

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
