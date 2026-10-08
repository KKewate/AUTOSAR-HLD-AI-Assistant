"""
RAG Pipeline — orchestrates retrieval + LLM answering.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple

from app.rag.vector_store import VectorStore
from app.rag.llm_client   import llm_answer, build_context_block, is_mock_mode
from config.settings       import RETRIEVAL_TOP_K


def _score_to_confidence(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.50:
        return "Medium"
    return "Low"


def ask(
    question: str,
    store: VectorStore,
    top_k: int = RETRIEVAL_TOP_K,
    extra_instruction: str = "",
) -> Dict[str, Any]:
    """
    Full RAG pass.

    Returns:
        {
          "question":   str,
          "answer":     str,
          "confidence": str,
          "chunks":     List[dict],  ← retrieved evidence chunks
          "citations":  List[str],   ← human-readable citation strings
          "mock_mode":  bool,
        }
    """
    if not store.is_ready:
        return {
            "question":   question,
            "answer":     "No documents have been processed yet. Please upload and process an HLD PDF first.",
            "confidence": "N/A",
            "chunks":     [],
            "citations":  [],
            "mock_mode":  is_mock_mode(),
        }

    chunks = store.search(question, top_k=top_k)

    if not chunks:
        return {
            "question":   question,
            "answer":     "Insufficient evidence in the uploaded HLD.",
            "confidence": "Low",
            "chunks":     [],
            "citations":  [],
            "mock_mode":  is_mock_mode(),
        }

    answer    = llm_answer(question, chunks, extra_instruction)
    avg_score = sum(c["score"] for c in chunks) / len(chunks)
    confidence = _score_to_confidence(avg_score)

    citations = []
    for c in chunks:
        heading = c.get("heading") or ""
        sec = f", Section: {heading}" if heading else ""
        citations.append(f"{c['doc_name']} — Page {c['page']}{sec}")

    return {
        "question":   question,
        "answer":     answer,
        "confidence": confidence,
        "chunks":     chunks,
        "citations":  list(dict.fromkeys(citations)),   # deduplicate, preserve order
        "mock_mode":  is_mock_mode(),
    }
