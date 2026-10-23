"""
Architecture Extractor — pulls components, interfaces, ports, signals,
dependencies, and functional flows from retrieved chunks using the LLM.

All claims are grounded in retrieved evidence only.
"""

from __future__ import annotations
import json
import re
from typing import List, Dict, Any

from app.rag.vector_store import VectorStore
from app.rag.llm_client   import llm_answer, is_mock_mode


# ── Extraction prompts ─────────────────────────────────────────────────────────
_EXTRACT_PROMPT = """
From the AUTOSAR HLD document context provided, extract the following information.
Return ONLY a valid JSON object with these exact keys:
  "components":    list of strings (SW component names)
  "interfaces":    list of strings (interface names)
  "ports":         list of strings (port names/identifiers)
  "signals":       list of strings (signal names)
  "dependencies":  list of strings (e.g. "ComponentA → ComponentB via InterfaceX")
  "functional_flows": list of strings (brief description of functional flows)

Rules:
- Only include items explicitly mentioned in the context.
- If no information is found for a field, use an empty list [].
- Do NOT invent names. Do NOT hallucinate.
- Keep each string concise (< 120 chars).
- Return ONLY the JSON, no other text.
"""

_INCONSISTENCY_PROMPT = """
Analyze the following AUTOSAR HLD context for potential inconsistencies.
Look for:
- Same component associated with conflicting interfaces
- Contradictory descriptions of the same component
- Missing or ambiguous dependency definitions
- Inconsistent terminology (same concept, different names)
- Components referenced but never defined

Return ONLY a valid JSON array of objects with keys:
  "finding":  short description of the potential inconsistency
  "evidence": list of citation strings (page/section references from the context)
  "severity": "High" | "Medium" | "Low"

If no inconsistencies are detected, return an empty array [].
Do NOT fabricate issues. Only report what is genuinely ambiguous or contradictory.
Prefix every finding with "Potential inconsistency detected:".
"""


def _safe_json_parse(text: str, fallback):
    """Try to extract and parse JSON from LLM output."""
    text = text.strip()
    # strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # try extracting first {...} or [...]
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return fallback


def extract_architecture(store: VectorStore) -> Dict[str, Any]:
    """
    Retrieve broad context and ask the LLM to extract structured architecture info.
    Returns a dict with keys: components, interfaces, ports, signals,
    dependencies, functional_flows, citations.
    """
    empty = {
        "components": [], "interfaces": [], "ports": [],
        "signals": [], "dependencies": [], "functional_flows": [],
        "citations": [], "error": None,
    }

    if not store.is_ready:
        empty["error"] = "No documents processed yet."
        return empty

    # Broad retrieval for architecture overview
    queries = [
        "software components interfaces ports",
        "signals dependencies functional flow",
        "component description AUTOSAR architecture",
    ]

    all_chunks: List[Dict] = []
    seen_ids: set = set()
    for q in queries:
        for c in store.search(q, top_k=6):
            if c["chunk_id"] not in seen_ids:
                all_chunks.append(c)
                seen_ids.add(c["chunk_id"])

    if not all_chunks:
        empty["error"] = "No relevant chunks found."
        return empty

    # Build citations
    citations = []
    for c in all_chunks:
        h = c.get("heading") or ""
        s = f", Section: {h}" if h else ""
        citations.append(f"{c['doc_name']} — Page {c['page']}{s}")

    # Ask LLM
    if is_mock_mode():
        empty["citations"] = list(dict.fromkeys(citations))
        empty["error"] = ("Architecture extraction needs a real LLM (demo/mock mode is active). "
                          "Set LLM_PROVIDER=ollama or openai in .env.")
        return empty

    raw = llm_answer(_EXTRACT_PROMPT, all_chunks, extra_instruction="")
    parsed = _safe_json_parse(raw, {})
    if not isinstance(parsed, dict):
        parsed = {}

    def _as_list(v):
        if not isinstance(v, list):
            return []
        return [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in v]

    return {
        "components":       _as_list(parsed.get("components")),
        "interfaces":       _as_list(parsed.get("interfaces")),
        "ports":            _as_list(parsed.get("ports")),
        "signals":          _as_list(parsed.get("signals")),
        "dependencies":     _as_list(parsed.get("dependencies")),
        "functional_flows": _as_list(parsed.get("functional_flows")),
        "citations":        list(dict.fromkeys(citations)),
        "error":            None,
    }


def detect_inconsistencies(store: VectorStore) -> List[Dict[str, Any]]:
    """
    Detect potential inconsistencies in the architecture document.
    Returns a list of finding dicts: {finding, evidence, severity}.
    """
    if not store.is_ready:
        return []

    queries = [
        "component interface dependency",
        "port signal definition",
        "architecture description",
    ]

    all_chunks: List[Dict] = []
    seen_ids: set = set()
    for q in queries:
        for c in store.search(q, top_k=6):
            if c["chunk_id"] not in seen_ids:
                all_chunks.append(c)
                seen_ids.add(c["chunk_id"])

    if not all_chunks or is_mock_mode():
        return []

    raw = llm_answer(_INCONSISTENCY_PROMPT, all_chunks)
    parsed = _safe_json_parse(raw, [])

    if not isinstance(parsed, list):
        return []
    findings = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        ev = item.get("evidence", [])
        item["evidence"] = [ev] if isinstance(ev, str) else [str(e) for e in ev] if isinstance(ev, list) else []
        item["finding"] = str(item.get("finding", "")) or "Finding"
        if item.get("severity") not in ("High", "Medium", "Low"):
            item["severity"] = "Low"
        findings.append(item)
    return findings


def generate_summary(store: VectorStore, arch: Dict[str, Any]) -> str:
    """
    Generate a structured architecture summary report.
    """
    if not store.is_ready:
        return "No documents processed yet."
    if is_mock_mode():
        return ("_Summary generation needs a real LLM (demo/mock mode is active). "
                "Set `LLM_PROVIDER=ollama` or `openai` in `.env`._")

    # Pull high-level chunks
    chunks = store.search("architecture overview summary components interfaces", top_k=8)

    summary_prompt = f"""
Generate a structured AUTOSAR Architecture Summary Report based on the retrieved HLD evidence.
The report must follow this structure:

# Architecture Summary Report

## 1. Document Overview
## 2. Software Components
## 3. Interfaces
## 4. Ports
## 5. Signals
## 6. Dependencies & Interactions
## 7. Functional Flow
## 8. Key Observations

Previously extracted data for reference:
- Components: {arch.get('components', [])}
- Interfaces: {arch.get('interfaces', [])}
- Ports:      {arch.get('ports', [])}
- Signals:    {arch.get('signals', [])}
- Dependencies: {arch.get('dependencies', [])}

Rules:
- Base everything on the retrieved context.
- Include citations (Page X, Section Y) for each section.
- If a section has no evidence, write "Not found in document."
- Do NOT fabricate information.
""".strip()

    return llm_answer(summary_prompt, chunks)
