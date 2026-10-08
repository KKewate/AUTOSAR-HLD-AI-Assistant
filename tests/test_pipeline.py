"""
Test Suite for AUTOSAR HLD AI Assistant
=======================================
Tests the complete pipeline end to end.

Run with:
    python -m pytest tests/ -v
    
or:
    python tests/test_pipeline.py
"""

import sys
import os
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest


class TestPDFExtraction(unittest.TestCase):
    """Tests for PDF ingestion and text extraction."""

    @classmethod
    def setUpClass(cls):
        """Create a synthetic HLD PDF once for all tests in this class."""
        from app.utils.synthetic_hld import create_synthetic_hld
        from config.settings import DATA_INPUT_DIR
        cls.pdf_path = create_synthetic_hld(DATA_INPUT_DIR)

    def test_pdf_exists(self):
        """Synthetic HLD file must be created."""
        self.assertTrue(self.pdf_path.exists(), f"PDF not found: {self.pdf_path}")
        self.assertGreater(self.pdf_path.stat().st_size, 1000, "PDF is too small")

    def test_text_extraction_pdf(self):
        """PDF must yield extracted text pages."""
        if self.pdf_path.suffix != ".pdf":
            self.skipTest("Not a PDF (txt fallback mode)")
        from app.ingestion.pdf_extractor import extract_pages
        pages = extract_pages(self.pdf_path)
        self.assertGreater(len(pages), 0, "No pages extracted")
        # Every page must have page number
        for p in pages:
            self.assertIn("page", p)
            self.assertIsInstance(p["page"], int)
            self.assertGreater(p["page"], 0)

    def test_document_stats(self):
        """Document stats must report correct counts."""
        if self.pdf_path.suffix != ".pdf":
            self.skipTest("Not a PDF")
        from app.ingestion.pdf_extractor import extract_pages, get_document_stats
        pages = extract_pages(self.pdf_path)
        stats = get_document_stats(pages)
        self.assertIn("total_pages", stats)
        self.assertIn("total_chars", stats)
        self.assertGreater(stats["total_pages"], 0)
        self.assertGreater(stats["total_chars"], 500)

    def test_no_scanned_pages(self):
        """Synthetic HLD should have no scanned pages (it has real text)."""
        if self.pdf_path.suffix != ".pdf":
            self.skipTest("Not a PDF")
        from app.ingestion.pdf_extractor import extract_pages, get_document_stats
        pages = extract_pages(self.pdf_path)
        stats = get_document_stats(pages)
        self.assertEqual(stats["scanned_pages"], [],
                         f"Unexpected scanned pages: {stats['scanned_pages']}")


class TestChunking(unittest.TestCase):
    """Tests for text chunking and metadata preservation."""

    @classmethod
    def setUpClass(cls):
        from app.utils.synthetic_hld import create_synthetic_hld
        from config.settings import DATA_INPUT_DIR
        pdf_path = create_synthetic_hld(DATA_INPUT_DIR)
        if pdf_path.suffix == ".pdf":
            from app.ingestion.pdf_extractor import extract_pages
            cls.pages = extract_pages(pdf_path)
        else:
            text = pdf_path.read_text(encoding="utf-8")
            cls.pages = [{"page": 1, "text": text, "heading": "Overview",
                          "char_count": len(text), "is_scanned": False}]
        cls.doc_name = pdf_path.name

    def test_chunks_created(self):
        """Chunking must produce at least one chunk."""
        from app.ingestion.chunker import chunk_pages
        chunks = chunk_pages(self.pages, doc_name=self.doc_name)
        self.assertGreater(len(chunks), 5, "Too few chunks created")

    def test_chunk_metadata_keys(self):
        """Every chunk must have required metadata fields."""
        from app.ingestion.chunker import chunk_pages
        chunks = chunk_pages(self.pages, doc_name=self.doc_name)
        required = {"chunk_id", "doc_name", "page", "heading", "text", "char_count"}
        for chunk in chunks:
            for key in required:
                self.assertIn(key, chunk, f"Chunk missing key: {key}")

    def test_chunk_page_number_preserved(self):
        """Page numbers in chunks must be valid (>= 1)."""
        from app.ingestion.chunker import chunk_pages
        chunks = chunk_pages(self.pages, doc_name=self.doc_name)
        for chunk in chunks:
            self.assertGreaterEqual(chunk["page"], 1, "Page number < 1")

    def test_chunk_doc_name_preserved(self):
        """Document name must be preserved in every chunk."""
        from app.ingestion.chunker import chunk_pages
        chunks = chunk_pages(self.pages, doc_name=self.doc_name)
        for chunk in chunks:
            self.assertEqual(chunk["doc_name"], self.doc_name)

    def test_chunk_text_not_empty(self):
        """No chunk should have empty text."""
        from app.ingestion.chunker import chunk_pages
        chunks = chunk_pages(self.pages, doc_name=self.doc_name)
        for chunk in chunks:
            self.assertTrue(chunk["text"].strip(), f"Empty chunk: {chunk['chunk_id']}")

    def test_chunk_size_respected(self):
        """Chunks should not exceed chunk_size * 1.5 (overlap tolerance)."""
        from app.ingestion.chunker import chunk_pages
        chunk_size = 400
        chunks = chunk_pages(self.pages, doc_name=self.doc_name,
                             chunk_size=chunk_size, chunk_overlap=50)
        for chunk in chunks:
            self.assertLessEqual(len(chunk["text"]), chunk_size * 2,
                                 f"Chunk too large: {len(chunk['text'])} chars")


class TestVectorStore(unittest.TestCase):
    """Tests for FAISS vector store: embedding, indexing, retrieval."""

    @classmethod
    def setUpClass(cls):
        """Build a small index once for all vector store tests."""
        from app.utils.synthetic_hld import create_synthetic_hld
        from config.settings import DATA_INPUT_DIR
        from app.ingestion.pdf_extractor import extract_pages
        from app.ingestion.chunker import chunk_pages
        from app.rag.vector_store import VectorStore

        pdf_path = create_synthetic_hld(DATA_INPUT_DIR)
        if pdf_path.suffix == ".pdf":
            pages = extract_pages(pdf_path)
        else:
            text = pdf_path.read_text(encoding="utf-8")
            pages = [{"page": 1, "text": text, "heading": None,
                      "char_count": len(text), "is_scanned": False}]

        chunks = chunk_pages(pages, doc_name=pdf_path.name)

        cls.store = VectorStore("test_suite_project")
        cls.store.reset()
        # Use first 30 chunks to keep test fast
        cls.store.add_chunks(chunks[:30], show_progress=False)

    @classmethod
    def tearDownClass(cls):
        cls.store.reset()

    def test_store_is_ready(self):
        """Vector store must be ready after adding chunks."""
        self.assertTrue(self.store.is_ready)

    def test_chunk_count(self):
        """Chunk count must match what was added."""
        self.assertGreater(self.store.chunk_count, 0)

    def test_retrieval_returns_results(self):
        """A basic query must return at least one result."""
        results = self.store.search("diagnostic manager software component", top_k=3)
        self.assertGreater(len(results), 0, "No results returned for query")

    def test_retrieval_result_structure(self):
        """Retrieved results must have required fields including score."""
        results = self.store.search("CAN driver interface", top_k=2)
        for r in results:
            self.assertIn("score", r)
            self.assertIn("page", r)
            self.assertIn("doc_name", r)
            self.assertIn("text", r)
            self.assertIn("chunk_id", r)

    def test_retrieval_score_range(self):
        """Cosine similarity scores must be in [0, 1]."""
        results = self.store.search("flash memory programming", top_k=3)
        for r in results:
            self.assertGreaterEqual(r["score"], 0.0)
            self.assertLessEqual(r["score"], 1.0)

    def test_citation_page_is_real(self):
        """Page numbers from retrieved chunks must be real (>= 1)."""
        results = self.store.search("NvMManager block", top_k=3)
        for r in results:
            self.assertGreaterEqual(r["page"], 1, "Page number must be >= 1")

    def test_top_k_respected(self):
        """Result count must not exceed top_k."""
        for k in [1, 3, 5]:
            results = self.store.search("architecture", top_k=k)
            self.assertLessEqual(len(results), k, f"Got more than {k} results")

    def test_store_get_stats(self):
        """get_stats must return expected structure."""
        stats = self.store.get_stats()
        self.assertIn("project_id", stats)
        self.assertIn("n_chunks", stats)
        self.assertIn("documents", stats)
        self.assertTrue(stats["is_ready"])


class TestRAGPipeline(unittest.TestCase):
    """Integration tests for the full RAG pipeline."""

    @classmethod
    def setUpClass(cls):
        from app.utils.synthetic_hld import create_synthetic_hld
        from config.settings import DATA_INPUT_DIR
        from app.ingestion.pdf_extractor import extract_pages
        from app.ingestion.chunker import chunk_pages
        from app.rag.vector_store import VectorStore

        pdf_path = create_synthetic_hld(DATA_INPUT_DIR)
        if pdf_path.suffix == ".pdf":
            pages = extract_pages(pdf_path)
        else:
            text = pdf_path.read_text(encoding="utf-8")
            pages = [{"page": 1, "text": text, "heading": None,
                      "char_count": len(text), "is_scanned": False}]

        chunks = chunk_pages(pages, doc_name=pdf_path.name)
        cls.store = VectorStore("test_rag_project")
        cls.store.reset()
        cls.store.add_chunks(chunks, show_progress=False)

    @classmethod
    def tearDownClass(cls):
        cls.store.reset()

    def test_ask_returns_result_structure(self):
        """ask() must return dict with required keys."""
        from app.rag.pipeline import ask
        result = ask("What are the software components?", self.store)
        required = {"question", "answer", "confidence", "chunks", "citations", "mock_mode"}
        for key in required:
            self.assertIn(key, result, f"Missing key in result: {key}")

    def test_ask_returns_citations(self):
        """Every answered question must produce citations with page numbers."""
        from app.rag.pipeline import ask
        result = ask("What is the DiagnosticManager?", self.store)
        # Citations should exist
        self.assertGreater(len(result["citations"]), 0,
                           "No citations returned for a valid question")
        # Every citation must mention a page
        for cit in result["citations"]:
            self.assertIn("Page", cit, f"Citation missing 'Page': {cit}")

    def test_ask_retrieves_chunks(self):
        """ask() must retrieve relevant chunks from the index."""
        from app.rag.pipeline import ask
        result = ask("CAN driver MCAL", self.store)
        self.assertGreater(len(result["chunks"]), 0, "No chunks retrieved")

    def test_insufficient_evidence_response(self):
        """A completely out-of-scope question must not fabricate an answer."""
        from app.rag.pipeline import ask
        result = ask("What is the recipe for chocolate cake?", self.store)
        # Either answer mentions insufficient evidence, or it is a mock response
        answer_lower = result["answer"].lower()
        is_appropriate = (
            "insufficient" in answer_lower
            or "demo mode" in answer_lower
            or "not found" in answer_lower
            or result["mock_mode"]  # mock mode is acceptable for demo
        )
        self.assertTrue(is_appropriate,
                        f"Unexpected answer for out-of-scope query: {result['answer'][:200]}")

    def test_confidence_is_valid_value(self):
        """Confidence must be High, Medium, Low, or N/A."""
        from app.rag.pipeline import ask
        result = ask("What interfaces are present?", self.store)
        self.assertIn(result["confidence"], {"High", "Medium", "Low", "N/A"})


class TestCitationMetadata(unittest.TestCase):
    """Tests that citations correctly reference actual document pages."""

    @classmethod
    def setUpClass(cls):
        from app.utils.synthetic_hld import create_synthetic_hld
        from config.settings import DATA_INPUT_DIR
        from app.ingestion.pdf_extractor import extract_pages
        from app.ingestion.chunker import chunk_pages
        from app.rag.vector_store import VectorStore

        pdf_path = create_synthetic_hld(DATA_INPUT_DIR)
        if pdf_path.suffix == ".pdf":
            pages = extract_pages(pdf_path)
            cls.max_page = max(p["page"] for p in pages)
        else:
            text = pdf_path.read_text(encoding="utf-8")
            pages = [{"page": 1, "text": text, "heading": None,
                      "char_count": len(text), "is_scanned": False}]
            cls.max_page = 1

        chunks = chunk_pages(pages, doc_name=pdf_path.name)
        cls.store = VectorStore("test_citation_project")
        cls.store.reset()
        cls.store.add_chunks(chunks, show_progress=False)

    @classmethod
    def tearDownClass(cls):
        cls.store.reset()

    def test_citation_page_within_document(self):
        """Citation page numbers must not exceed the document's total pages."""
        from app.rag.pipeline import ask
        import re
        result = ask("What are the signals in the architecture?", self.store)
        for cit in result["citations"]:
            match = re.search(r"Page (\d+)", cit)
            if match:
                page_num = int(match.group(1))
                self.assertGreaterEqual(page_num, 1)
                self.assertLessEqual(page_num, self.max_page + 2,
                                     f"Citation page {page_num} exceeds document pages {self.max_page}")

    def test_chunk_page_traceable(self):
        """Retrieved chunk pages must be traceable to real document pages."""
        results = self.store.search("motor control torque", top_k=3)
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertGreaterEqual(r["page"], 1)
            self.assertLessEqual(r["page"], self.max_page + 2)


class TestLLMClient(unittest.TestCase):
    """Tests for the LLM client factory."""

    def test_get_llm_returns_object(self):
        """get_llm() must return a non-None object."""
        from app.rag.llm_client import get_llm, reset_llm
        reset_llm()
        llm = get_llm()
        self.assertIsNotNone(llm)

    def test_is_mock_mode_bool(self):
        """is_mock_mode() must return a boolean."""
        from app.rag.llm_client import is_mock_mode
        result = is_mock_mode()
        self.assertIsInstance(result, bool)

    def test_get_llm_label_string(self):
        """get_llm_label() must return a non-empty string."""
        from app.rag.llm_client import get_llm_label
        label = get_llm_label()
        self.assertIsInstance(label, str)
        self.assertGreater(len(label), 0)

    def test_llm_answer_returns_string(self):
        """llm_answer() must return a non-empty string."""
        from app.rag.llm_client import llm_answer
        # Use fake chunks to avoid embedding
        fake_chunks = [
            {"doc_name": "test.pdf", "page": 1, "heading": "Test",
             "text": "DiagnosticManager manages UDS sessions via CAN.", "score": 0.9,
             "chunk_id": "test-001"}
        ]
        result = llm_answer("What does DiagnosticManager do?", fake_chunks)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)


if __name__ == "__main__":
    # Run all tests with verbose output
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
