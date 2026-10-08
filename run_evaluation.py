"""
Standalone Evaluation CLI
=========================
Runs the full synthetic evaluation set against the RAG pipeline.
Can be run independently without the Streamlit UI.

Usage:
    python run_evaluation.py

    # With a specific PDF:
    python run_evaluation.py --pdf path/to/your_hld.pdf

    # Save results to a custom file:
    python run_evaluation.py --output results/my_eval.json
"""

from __future__ import annotations
import sys
import os
import json
import argparse
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Windows encoding fix for console output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(
        description="AUTOSAR HLD AI Assistant - RAG Pipeline Evaluation"
    )
    parser.add_argument(
        "--pdf", type=str, default=None,
        help="Path to PDF to evaluate against. Defaults to synthetic demo HLD."
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Path to save evaluation JSON. Defaults to evaluation_results/evaluation_results.json"
    )
    parser.add_argument(
        "--top-k", type=int, default=5,
        help="Number of chunks to retrieve per question (default: 5)"
    )
    args = parser.parse_args()

    print("=" * 65)
    print("AUTOSAR HLD AI Assistant - RAG Evaluation")
    print("Tata TechPulse Applied AI/ML Capstone")
    print("=" * 65)
    print()
    print("[INFO] NOTE: Ground truth is SYNTHETIC (based on demo HLD).")
    print("[INFO] This evaluation is indicative, not production-validated.")
    print()

    # ── Step 1: Load / create document ────────────────────────────────────────
    from config.settings import DATA_INPUT_DIR
    from app.utils.synthetic_hld import create_synthetic_hld
    from app.ingestion.pdf_extractor import extract_pages
    from app.ingestion.chunker import chunk_pages
    from app.rag.vector_store import VectorStore
    from app.utils.helpers import project_id_for_files
    from app.evaluation.evaluator import run_evaluation, SYNTHETIC_QA

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"[ERROR] PDF not found: {pdf_path}")
            sys.exit(1)
    else:
        print("[INFO] No PDF provided. Generating synthetic demo HLD...")
        pdf_path = create_synthetic_hld(DATA_INPUT_DIR)

    print(f"[INFO] Document: {pdf_path.name} ({pdf_path.stat().st_size:,} bytes)")

    # ── Step 2: Extract pages ──────────────────────────────────────────────────
    print("[INFO] Extracting pages...")
    if pdf_path.suffix == ".pdf":
        pages = extract_pages(pdf_path)
    else:
        text = pdf_path.read_text(encoding="utf-8")
        pages = [{"page": 1, "text": text, "heading": "Overview",
                  "char_count": len(text), "is_scanned": False}]
    print(f"[INFO] Pages extracted: {len(pages)}")

    # ── Step 3: Chunk ──────────────────────────────────────────────────────────
    print("[INFO] Chunking text...")
    chunks = chunk_pages(pages, doc_name=pdf_path.name)
    print(f"[INFO] Chunks created: {len(chunks)}")

    # ── Step 4: Embed and index ────────────────────────────────────────────────
    project_id = project_id_for_files([pdf_path])
    store = VectorStore(project_id=project_id)
    if store.is_ready:
        print(f"[INFO] Loaded existing index ({store.chunk_count} chunks).")
    else:
        print("[INFO] Embedding chunks (this takes ~30-60s on first run)...")
        store.add_chunks(chunks, show_progress=True)
        print(f"[INFO] Index ready: {store.chunk_count} chunks.")

    # ── Step 5: Run evaluation ─────────────────────────────────────────────────
    print()
    print(f"[INFO] Running {len(SYNTHETIC_QA)} evaluation questions...")
    print()

    from app.rag.pipeline import ask
    from app.evaluation.evaluator import (
        _check_retrieval_success, _check_citation_coverage,
        _check_groundedness, _check_answer_correctness,
        EVAL_RESULTS_DIR
    )

    results = []
    for i, qa in enumerate(SYNTHETIC_QA, 1):
        resp = ask(qa["question"], store, top_k=args.top_k)
        correctness = _check_answer_correctness(resp["answer"], qa["ground_truth"])
        result = {
            "id": qa["id"],
            "question": qa["question"],
            "ground_truth": qa["ground_truth"],
            "generated_answer": resp["answer"],
            "citations": resp["citations"],
            "confidence": resp["confidence"],
            "retrieval_success": _check_retrieval_success(resp["chunks"]),
            "citation_coverage": _check_citation_coverage(resp["citations"]),
            "groundedness": _check_groundedness(resp["answer"], resp["chunks"]),
            "answer_correctness": correctness,
            "mock_mode": resp["mock_mode"],
        }
        results.append(result)

        ret_icon = "[OK]" if result["retrieval_success"] else "[--]"
        cit_icon = "[OK]" if result["citation_coverage"] else "[--]"
        print(f"  {qa['id']} | Retrieval:{ret_icon} Citation:{cit_icon} "
              f"Correctness:{correctness:12s} | {qa['question'][:55]}...")

    # ── Step 6: Compute metrics ────────────────────────────────────────────────
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
        "is_synthetic": True,
        "note": "Ground truth is synthetic. Results are indicative only.",
    }

    print()
    print("=" * 65)
    print("EVALUATION RESULTS")
    print("=" * 65)
    print(f"  Total Questions:     {metrics['total_questions']}")
    print(f"  Retrieval Success:   {metrics['retrieval_success']:.1%}")
    print(f"  Citation Coverage:   {metrics['citation_coverage']:.1%}")
    print(f"  Groundedness:        {metrics['groundedness_rate']:.1%}")
    print(f"  Answer Pass:         {metrics['answer_pass_rate']:.1%}")
    print(f"  Answer Partial:      {metrics['answer_partial_rate']:.1%}")
    print(f"  Answer Fail:         {metrics['answer_fail_rate']:.1%}")
    print(f"  Unverifiable:        {metrics['unverifiable_rate']:.1%}")
    print()
    if any(r["mock_mode"] for r in results):
        print("[WARN] Running in Demo/Mock mode. Connect an LLM for real answer scores.")
        print("       Set LLM_PROVIDER=ollama in .env and run: ollama pull llama3.1")

    # ── Step 7: Save results ───────────────────────────────────────────────────
    payload = {"metrics": metrics, "results": results}
    if args.output:
        out_file = Path(args.output)
        out_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_file = EVAL_RESULTS_DIR / "evaluation_results.json"

    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[INFO] Results saved to: {out_file}")
    print("=" * 65)


if __name__ == "__main__":
    main()
