"""
Setup and Smoke Test
====================
Verifies the installation and tests the complete pipeline end-to-end.
Run this once after installation to confirm everything works.

Usage:
    python setup_and_test.py
"""

from __future__ import annotations
import sys
import os
from pathlib import Path

# Windows encoding fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def check_imports() -> list:
    """Check all required package imports."""
    print("Checking required packages...")
    errors = []
    packages = [
        ("fitz",               "PyMuPDF"),
        ("sentence_transformers", "sentence-transformers"),
        ("faiss",              "faiss-cpu"),
        ("streamlit",          "streamlit"),
        ("dotenv",             "python-dotenv"),
        ("pandas",             "pandas"),
        ("numpy",              "numpy"),
        ("reportlab",          "reportlab"),
        ("requests",           "requests"),
    ]
    for mod, pkg in packages:
        try:
            __import__(mod)
            print(f"  [OK] {pkg}")
        except ImportError:
            print(f"  [MISSING] {pkg}  -> pip install {pkg}")
            errors.append(pkg)
    return errors


def check_optional_imports() -> None:
    """Check optional LLM packages."""
    print("\nChecking optional packages (for LLM)...")
    try:
        import openai
        print(f"  [OK] openai (version {openai.__version__})")
    except ImportError:
        print("  [OPTIONAL] openai not installed (needed for OpenAI provider)")

    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            print("  [OK] Ollama is running at http://localhost:11434")
        else:
            print("  [INFO] Ollama server returned unexpected status")
    except Exception:
        print("  [INFO] Ollama not running (needed for local LLM - optional)")


def test_config() -> bool:
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from config.settings import BASE_DIR, EMBEDDING_MODEL, CHUNK_SIZE, LLM_PROVIDER
        print(f"  [OK] BASE_DIR: {BASE_DIR}")
        print(f"  [OK] EMBEDDING_MODEL: {EMBEDDING_MODEL}")
        print(f"  [OK] CHUNK_SIZE: {CHUNK_SIZE}")
        print(f"  [OK] LLM_PROVIDER: {LLM_PROVIDER}")
        return True
    except Exception as e:
        print(f"  [ERROR] Config failed: {e}")
        return False


def test_synthetic_hld() -> Path | None:
    """Test synthetic HLD generation."""
    print("\nTesting synthetic HLD generation...")
    try:
        from app.utils.synthetic_hld import create_synthetic_hld
        from config.settings import DATA_INPUT_DIR
        p = create_synthetic_hld(DATA_INPUT_DIR)
        size = p.stat().st_size
        print(f"  [OK] Created: {p.name} ({size:,} bytes)")
        return p
    except Exception as e:
        print(f"  [ERROR] Synthetic HLD creation failed: {e}")
        return None


def test_pdf_extraction(pdf_path: Path) -> list | None:
    """Test PDF text extraction."""
    print("\nTesting PDF extraction...")
    try:
        if pdf_path.suffix == ".pdf":
            from app.ingestion.pdf_extractor import extract_pages, get_document_stats
            pages = extract_pages(pdf_path)
            stats = get_document_stats(pages)
            print(f"  [OK] Pages: {stats['total_pages']}")
            print(f"  [OK] Characters: {stats['total_chars']:,}")
            print(f"  [OK] Headings found: {len(stats['headings_found'])}")
            print(f"  [OK] Scanned pages: {stats['scanned_pages']}")
            return pages
        else:
            text = pdf_path.read_text(encoding="utf-8")
            pages = [{"page": 1, "text": text, "heading": "Overview",
                      "char_count": len(text), "is_scanned": False}]
            print(f"  [OK] Text fallback: {len(text):,} chars (PDF generation unavailable)")
            return pages
    except Exception as e:
        print(f"  [ERROR] Extraction failed: {e}")
        return None


def test_chunking(pages: list, doc_name: str) -> list | None:
    """Test text chunking."""
    print("\nTesting chunking...")
    try:
        from app.ingestion.chunker import chunk_pages
        chunks = chunk_pages(pages, doc_name=doc_name)
        print(f"  [OK] Chunks created: {len(chunks)}")
        if chunks:
            sample = chunks[0]
            print(f"  [OK] Sample chunk keys: {list(sample.keys())}")
            print(f"  [OK] Sample page number: {sample['page']}")
        return chunks
    except Exception as e:
        print(f"  [ERROR] Chunking failed: {e}")
        return None


def test_vector_store(chunks: list) -> bool:
    """Test FAISS embedding and retrieval (uses first 20 chunks for speed)."""
    print("\nTesting vector store (embedding ~30 chunks)...")
    print("  [INFO] First run downloads BGE model (~130 MB). Please wait...")
    try:
        from app.rag.vector_store import VectorStore
        store = VectorStore("setup_test")
        store.reset()
        test_chunks = chunks[:20]
        store.add_chunks(test_chunks, show_progress=False)
        print(f"  [OK] Index ready: {store.chunk_count} chunks")

        results = store.search("diagnostic manager component interface", top_k=3)
        print(f"  [OK] Search returned {len(results)} results")
        if results:
            r = results[0]
            print(f"  [OK] Top result: Page {r['page']}, Score {r['score']:.3f}")

        store.reset()
        return True
    except Exception as e:
        print(f"  [ERROR] Vector store test failed: {e}")
        return False


def test_llm_client() -> bool:
    """Test LLM client factory."""
    print("\nTesting LLM client...")
    try:
        from app.rag.llm_client import get_llm, is_mock_mode, get_llm_label, reset_llm
        reset_llm()
        llm = get_llm()
        print(f"  [OK] LLM initialized: {get_llm_label()}")
        print(f"  [OK] Mock mode: {is_mock_mode()}")
        return True
    except Exception as e:
        print(f"  [ERROR] LLM client failed: {e}")
        return False


def main():
    print("=" * 60)
    print("AUTOSAR HLD AI Assistant - Setup Verification")
    print("Tata TechPulse Applied AI/ML Capstone")
    print("=" * 60)

    # Check packages
    missing = check_imports()
    if missing:
        print(f"\n[FAIL] Missing packages: {missing}")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)

    check_optional_imports()

    # Run pipeline tests
    passed = 0
    failed = 0

    if test_config():
        passed += 1
    else:
        failed += 1

    pdf_path = test_synthetic_hld()
    if pdf_path:
        passed += 1
        pages = test_pdf_extraction(pdf_path)
        if pages:
            passed += 1
            chunks = test_chunking(pages, pdf_path.name)
            if chunks:
                passed += 1
                if test_vector_store(chunks):
                    passed += 1
                else:
                    failed += 1
            else:
                failed += 1
        else:
            failed += 1
    else:
        failed += 3

    if test_llm_client():
        passed += 1
    else:
        failed += 1

    # Summary
    total = passed + failed
    print()
    print("=" * 60)
    print(f"RESULTS: {passed}/{total} checks passed")
    if failed == 0:
        print("[SUCCESS] All checks passed! Ready to launch.")
        print()
        print("To start the application:")
        print("  streamlit run app/main.py")
        print()
        print("To run evaluation:")
        print("  python run_evaluation.py")
        print()
        print("To run tests:")
        print("  python -m pytest tests/ -v")
    else:
        print(f"[WARNING] {failed} check(s) failed. See errors above.")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
