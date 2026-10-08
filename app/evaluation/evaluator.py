"""
Evaluation Module — runs a synthetic question set against the RAG pipeline
and computes simple, honest metrics.

All results are clearly labelled as synthetic evaluation.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any

from app.rag.pipeline  import ask
from app.rag.vector_store import VectorStore
from config.settings   import EVAL_RESULTS_DIR


# ── Synthetic evaluation dataset ───────────────────────────────────────────────
# Ground truth is SYNTHETIC and based on the demo HLD document.
# Clearly labelled to avoid confusion with real validation.

SYNTHETIC_QA: List[Dict[str, str]] = [
    {
        "id": "Q01",
        "question": "What are the main software components described in the HLD?",
        "ground_truth": "DiagnosticManager, CANDriver, FlashManager, NvMManager, ECUStateManager, CommunicationManager",
    },
    {
        "id": "Q02",
        "question": "What is the role of the DiagnosticManager component?",
        "ground_truth": "Manages UDS diagnostic sessions, processes diagnostic requests, and communicates with the CAN interface",
    },
    {
        "id": "Q03",
        "question": "Which interfaces does the CANDriver expose?",
        "ground_truth": "Can_Init, Can_Write, Can_Read, Can_MainFunction_Write, Can_MainFunction_Read",
    },
    {
        "id": "Q04",
        "question": "What signals are used between DiagnosticManager and CANDriver?",
        "ground_truth": "Diag_Request_Signal, Diag_Response_Signal, CAN_TX_PDU, CAN_RX_PDU",
    },
    {
        "id": "Q05",
        "question": "What is the dependency between FlashManager and NvMManager?",
        "ground_truth": "FlashManager depends on NvMManager for persistent data storage of flash job results",
    },
    {
        "id": "Q06",
        "question": "What ports does the ECUStateManager provide?",
        "ground_truth": "EcuM_GetState port, EcuM_RequestRUN port, EcuM_ReleaseRUN port",
    },
    {
        "id": "Q07",
        "question": "Describe the functional flow for a diagnostic request.",
        "ground_truth": "External tester sends UDS request → CAN bus → CANDriver → PduR → DiagnosticManager processes → response via CANDriver → CAN bus → tester",
    },
    {
        "id": "Q08",
        "question": "What AUTOSAR layer does the CANDriver belong to?",
        "ground_truth": "Microcontroller Abstraction Layer (MCAL)",
    },
    {
        "id": "Q09",
        "question": "What communication stack is used for diagnostic messaging?",
        "ground_truth": "CAN stack with PduR routing and Dcm/Dem integration",
    },
    {
        "id": "Q10",
        "question": "What is the purpose of the FlashManager component?",
        "ground_truth": "Manages bootloader flash programming sequences and interfaces with memory drivers for ECU reprogramming",
    },
    {
        "id": "Q11",
        "question": "What are the main interfaces in the architecture?",
        "ground_truth": "Diagnostic interface, CAN interface, NvM interface, Flash interface, OS interface",
    },
    {
        "id": "Q12",
        "question": "Which components communicate with the NvMManager?",
        "ground_truth": "FlashManager, DiagnosticManager, ECUStateManager",
    },
    {
        "id": "Q13",
        "question": "What is the document version mentioned in the HLD?",
        "ground_truth": "Version 1.0 (Synthetic Demo Document)",
    },
    {
        "id": "Q14",
        "question": "What operating system abstraction is used?",
        "ground_truth": "AUTOSAR OS with Task-based scheduling",
    },
    {
        "id": "Q15",
        "question": "Summarize the overall architecture in one paragraph.",
        "ground_truth": "The architecture follows AUTOSAR Classic Platform layers with MCAL drivers, BSW modules, and application SW-Cs. DiagnosticManager handles UDS sessions via CAN stack, FlashManager manages reprogramming, NvMManager handles persistent storage, and ECUStateManager controls lifecycle.",
    },
]


def _check_groundedness(answer: str, chunks: List[Dict]) -> bool:
    """
    Naive check: answer is grounded if it mentions terms from retrieved chunks
    (or is a mock/insufficient response).
    """
    if "Insufficient evidence" in answer or "MOCK MODE" in answer:
        return True   # correctly refusing / mock is expected
    chunk_text = " ".join(c["text"].lower() for c in chunks)
    answer_words = set(answer.lower().split())
    chunk_words  = set(chunk_text.split())
    overlap = answer_words & chunk_words
    return len(overlap) > 5   # at least some shared vocabulary


def _check_citation_coverage(citations: List[str]) -> bool:
    return len(citations) > 0


def _check_retrieval_success(chunks: List[Dict]) -> bool:
    return len(chunks) > 0


def _check_answer_correctness(answer: str, ground_truth: str) -> str:
    """
    Simple keyword overlap metric (not semantic).
    Returns: "Pass" | "Partial" | "Fail" | "Unverifiable"
    """
    if "MOCK MODE" in answer or "Insufficient evidence" in answer:
        return "Unverifiable"
    gt_keywords = set(ground_truth.lower().split())
    ans_keywords = set(answer.lower().split())
    overlap = len(gt_keywords & ans_keywords)
    ratio   = overlap / max(len(gt_keywords), 1)
    if ratio >= 0.35:
        return "Pass"
    if ratio >= 0.15:
        return "Partial"
    return "Fail"


def run_evaluation(store: VectorStore) -> Dict[str, Any]:
    """
    Run all synthetic QA pairs through the pipeline and return structured results.
    """
    results = []
    for qa in SYNTHETIC_QA:
        resp = ask(qa["question"], store)
        result = {
            "id":                 qa["id"],
            "question":           qa["question"],
            "ground_truth":       qa["ground_truth"],
            "generated_answer":   resp["answer"],
            "citations":          resp["citations"],
            "confidence":         resp["confidence"],
            "retrieval_success":  _check_retrieval_success(resp["chunks"]),
            "citation_coverage":  _check_citation_coverage(resp["citations"]),
            "groundedness":       _check_groundedness(resp["answer"], resp["chunks"]),
            "answer_correctness": _check_answer_correctness(
                resp["answer"], qa["ground_truth"]
            ),
            "mock_mode":          resp["mock_mode"],
        }
        results.append(result)

    # ── Aggregate metrics ──────────────────────────────────────────────────────
    n = len(results)
    metrics = {
        "total_questions":     n,
        "retrieval_success":   sum(r["retrieval_success"] for r in results) / n,
        "citation_coverage":   sum(r["citation_coverage"] for r in results) / n,
        "groundedness_rate":   sum(r["groundedness"] for r in results) / n,
        "answer_pass_rate":    sum(r["answer_correctness"] == "Pass" for r in results) / n,
        "answer_partial_rate": sum(r["answer_correctness"] == "Partial" for r in results) / n,
        "answer_fail_rate":    sum(r["answer_correctness"] == "Fail" for r in results) / n,
        "unverifiable_rate":   sum(r["answer_correctness"] == "Unverifiable" for r in results) / n,
        "is_synthetic":        True,
    }

    # Persist results
    out_file = EVAL_RESULTS_DIR / "evaluation_results.json"
    payload  = {"metrics": metrics, "results": results}
    out_file.write_text(json.dumps(payload, indent=2))

    return payload
