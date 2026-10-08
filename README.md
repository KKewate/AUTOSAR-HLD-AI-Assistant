# AUTOSAR HLD Document Analysis Assistant

**Tata Technologies TechPulse FY-26 — Applied AI/ML Capstone**
**Case Study CS1: AUTOSAR HLD Document Analysis Assistant**

> An AI-powered Retrieval-Augmented Generation (RAG) system that allows automotive engineers to upload AUTOSAR High-Level Design (HLD) PDFs and get **grounded, citation-backed answers** about the architecture — no hallucination.

---

## 1. Problem Statement

Automotive software architects spend significant time manually searching through lengthy AUTOSAR HLD documents to answer questions about component relationships, interface definitions, signal flows, and architecture decisions. This is time-consuming, error-prone, and difficult to scale across teams.

**This project automates that process** using RAG: the engineer uploads an HLD PDF, and the system answers questions about the architecture with direct citations to the source page and section.

---

## 2. Objectives

1. Enable engineers to upload real AUTOSAR HLD PDFs and ask architecture questions
2. Ground every answer in retrieved document evidence (no fabrication)
3. Provide page-level citations for every factual claim
4. Extract structured architecture elements (components, interfaces, ports, signals)
5. Detect potential inconsistencies in the architecture documentation
6. Generate structured architecture summary reports
7. Evaluate RAG system performance with transparent, honest metrics

---

## 3. Features

| Feature | Status |
|---------|--------|
| PDF Upload (multi-file) | Working |
| Page-aware text extraction (PyMuPDF) | Working |
| Sliding-window chunking with metadata | Working |
| Local embeddings (BGE-small-en-v1.5) | Working |
| FAISS vector store (project-isolated) | Working |
| Semantic retrieval with similarity scores | Working |
| RAG pipeline (retrieve → answer → cite) | Working |
| Grounded answers with page citations | Working |
| Mock mode (no API key needed) | Working |
| Ollama LLM support (local, free) | Working |
| OpenAI GPT-4o-mini support | Working |
| Architecture element extraction | Working |
| Inconsistency detection | Working |
| Architecture summary generation | Working |
| Evaluation with real metrics | Working |
| Streamlit professional dashboard | Working |
| Synthetic demo HLD (AUTOSAR PCU) | Working |
| Standalone evaluation CLI | Working |
| Full test suite (29 tests) | Passing |

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI (app/main.py)              │
│   Chat │ Architecture │ Inconsistency │ Summary │ Evaluation │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │    RAG PIPELINE     │
    │    (pipeline.py)    │
    └──────┬──────────────┘
           │                    ┌─────────────────────────┐
    ┌──────▼──────┐             │  LLM Client             │
    │  RETRIEVAL  │             │  - Ollama (local, free) │
    │  FAISS      │────────────►│  - OpenAI GPT-4o-mini  │
    │  vector_    │             │  - Mock (demo mode)     │
    │  store.py   │             └─────────────────────────┘
    └──────▲──────┘
           │
    ┌──────┴──────────────┐
    │   INGESTION         │
    │   pdf_extractor.py  │
    │   chunker.py        │
    │   (PyMuPDF)         │
    └──────▲──────────────┘
           │
    ┌──────┴──────────────┐
    │   SOURCE            │
    │   AUTOSAR HLD PDF   │
    │   (uploaded or demo)│
    └─────────────────────┘
```

---

## 5. RAG Workflow

```
AUTOSAR HLD PDF
      │
      ▼ PyMuPDF extraction
Page-aware text (page number, heading preserved)
      │
      ▼ Sliding-window chunker (600 chars, 100 overlap)
Chunks with metadata {chunk_id, doc_name, page, heading, text}
      │
      ▼ BAAI/bge-small-en-v1.5 embedding (local)
Dense vectors (384-dim, cosine similarity)
      │
      ▼ FAISS IndexFlatIP (inner product = cosine on normalized)
Persistent index in vector_store/<project_id>/
      │
      ▼ Semantic search (top-K = 5 by default)
Retrieved chunks + similarity scores
      │
      ▼ Context block with citations
"[1] Source: doc.pdf | Page 4 | Section: Software Components\n..."
      │
      ▼ LLM (Ollama/OpenAI/Mock)
Grounded answer with citations
      │
      ▼ Response to user
Answer + Confidence + Citations + Retrieved Evidence
```

---

## 6. Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| UI | Streamlit | Professional dark theme |
| PDF Extraction | PyMuPDF (fitz/pymupdf) | Page-aware, heading detection |
| Embeddings | sentence-transformers | BAAI/bge-small-en-v1.5 (local) |
| Vector DB | FAISS | Local, project-isolated |
| LLM (local) | Ollama (Llama 3.1 8B) | Free, private, no API key |
| LLM (cloud) | OpenAI GPT-4o-mini | Optional, requires API key |
| Data processing | pandas, numpy | Evaluation tables |
| Synthetic PDF | reportlab | Demo document generation |
| Testing | pytest | 29 tests |
| Configuration | python-dotenv | Secrets via .env |

---

## 7. Project Structure

```
AUTOSAR_HLD_AI_Assistant/
│
├── app/
│   ├── main.py                    # Streamlit dashboard
│   ├── ingestion/
│   │   ├── pdf_extractor.py       # PyMuPDF page extraction
│   │   └── chunker.py             # Sliding-window chunker
│   ├── rag/
│   │   ├── pipeline.py            # RAG orchestration
│   │   ├── vector_store.py        # FAISS store
│   │   └── llm_client.py          # Ollama / OpenAI / Mock
│   ├── extraction/
│   │   └── arch_extractor.py      # Component/interface extraction
│   ├── evaluation/
│   │   └── evaluator.py           # Metrics + synthetic QA
│   └── utils/
│       ├── helpers.py             # Utility functions
│       └── synthetic_hld.py       # Demo PDF generator
│
├── config/
│   └── settings.py                # Centralised configuration
│
├── prompts/
│   └── system.txt                 # (optional override)
│
├── data/
│   └── input/                     # PDF storage
│
├── vector_store/                  # FAISS indices (git-ignored)
│
├── evaluation_results/            # JSON evaluation output
│
├── docs/
│   └── PROJECT_IMPLEMENTATION.md  # Technical documentation
│
├── tests/
│   └── test_pipeline.py           # 29 pytest tests
│
├── .env                           # Local secrets (git-ignored)
├── .env.example                   # Template (committed)
├── .gitignore
├── requirements.txt
├── setup_and_test.py              # Verification script
├── run_evaluation.py              # Standalone evaluation CLI
└── README.md
```

---

## 8. Installation

### Prerequisites

- Python 3.10+ (Python 3.10.x recommended)
- pip
- (Optional) Ollama for real AI answers — see below

### Install Dependencies

```bash
git clone <your-repo-url>
cd AUTOSAR_HLD_AI_Assistant
pip install -r requirements.txt
```

### Verify Installation

```bash
python setup_and_test.py
```

Expected output: `6/6 checks passed`

---

## 9. Ollama Setup (Recommended — Free, Local, Private)

Ollama runs a local LLM on your machine. No API key. Documents never leave your machine.

```bash
# 1. Install Ollama (Windows)
# Download from https://ollama.ai and run the installer

# 2. Pull the model (downloads ~4.7 GB once)
ollama pull llama3.1

# 3. Start the Ollama server (keep this running)
ollama serve

# 4. Configure the app
# Edit .env and set:
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
```

**Alternative smaller model** (faster, less accurate):
```bash
ollama pull llama3.2:3b
# Then set LLM_MODEL=llama3.2:3b in .env
```

---

## 10. OpenAI Setup (Optional — Cloud)

```bash
# Edit .env and set:
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-key-here
```

---

## 11. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `mock` | `mock` / `ollama` / `openai` |
| `LLM_MODEL` | `llama3.1` | Ollama model name or OpenAI model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENAI_API_KEY` | `""` | OpenAI API key (openai provider only) |
| `TEMPERATURE` | `0.1` | LLM temperature (0=factual, 1=creative) |
| `MAX_TOKENS` | `1500` | Max tokens per LLM response |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Local embedding model |
| `RETRIEVAL_TOP_K` | `5` | Chunks retrieved per query |
| `CHUNK_SIZE` | `600` | Characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |

---

## 12. Running the Application

```bash
# From the project root:
streamlit run app/main.py
```

Open your browser at: **http://localhost:8501**

### Demo Workflow

1. In the sidebar, check **"Use Synthetic Demo HLD"**
2. Click **"⚡ Process Document"**
3. Wait ~15s for embedding (first run downloads the model ~130MB)
4. Go to **"💬 Chat with HLD"** tab
5. Click an example question or type your own
6. View the grounded answer, citations, and retrieved evidence

---

## 13. Running Evaluation

```bash
# Evaluate using synthetic demo HLD:
python run_evaluation.py

# Evaluate with your own PDF:
python run_evaluation.py --pdf path/to/your_hld.pdf

# Save to custom output:
python run_evaluation.py --output results/my_eval.json
```

### Evaluation Metrics (Mock Mode — Demo Only)

| Metric | Result | Notes |
|--------|--------|-------|
| Retrieval Success | 100% | Documents retrieved for all 15 questions |
| Citation Coverage | 100% | All responses include page citations |
| Groundedness | 93.3% | Answers reference retrieved context |
| Answer Pass Rate | ~27% | Partial in mock (no real LLM answers) |

> **Note:** Answer correctness metrics require a real LLM (Ollama/OpenAI). With mock mode, the system correctly retrieves and cites evidence but does not produce semantic answers.

---

## 14. Running Tests

```bash
# Run full test suite:
python -m pytest tests/ -v

# Run specific test class:
python -m pytest tests/test_pipeline.py::TestVectorStore -v
```

**Test Results:** 29/29 tests passing

```
TestPDFExtraction       4 tests - PDF load, extraction, stats, scanned detection
TestChunking            6 tests - metadata preservation, page numbers, size
TestVectorStore         8 tests - embed, index, search, citations
TestRAGPipeline         5 tests - full pipeline, citations, grounding
TestCitationMetadata    2 tests - page numbers within doc range
TestLLMClient           4 tests - factory, labels, mock response
```

---

## 15. Example Questions

For the synthetic EV Powertrain Control Unit demo document:

```
What are the main software components described in the HLD?
What is the role of the DiagnosticManager?
Which interfaces does the CANDriver expose?
What signals are used between DiagnosticManager and CANDriver?
What is the dependency between FlashManager and NvMManager?
What ports does the ECUStateManager provide?
Describe the functional flow for a diagnostic request.
What AUTOSAR layer does the CANDriver belong to?
What communication stack is used for diagnostic messaging?
What is the initialization sequence for the ECU?
What signals does the MotorControlSWC use?
What are the NvM blocks defined in this architecture?
```

---

## 16. Expected Outputs

### Chat Response (with Ollama connected)
```
The main software components are:
- DiagnosticManager (DCM_SWC): Manages UDS diagnostic sessions (Page 4)
- CANDriver (CAN_MCAL): MCAL CAN hardware driver (Page 5)
- FlashManager (Flash_SWC): ECU reprogramming (Page 6)
- NvMManager (NvM_BSW): Persistent data storage (Page 7)
- ECUStateManager (EcuM_BSW): ECU lifecycle management (Page 8)
- CommunicationManager (ComM_BSW): CAN channel management (Page 9)
- MotorControlSWC (MotCtrl_SWC): Motor torque control (Page 10)

Citations:
- AUTOSAR_HLD_Demo.pdf — Page 4, Section: 4. SOFTWARE COMPONENTS
```

### Chat Response (Mock Mode)
```
[DEMO MODE — No LLM configured]

The RAG pipeline retrieved 5 evidence chunks from the uploaded HLD
(first citation: Page 4)...

To enable real AI answers, configure Ollama or OpenAI in .env.
```

---

## 17. Responsible AI

This project implements the following responsible AI practices:

- **No hallucination by design**: The system prompt explicitly forbids the LLM from answering without retrieved context
- **Transparent mock mode**: When no LLM is configured, the UI clearly states "Demo Mode — No LLM" with instructions to set one up
- **Synthetic data only**: The demo document is clearly labelled as synthetic — no confidential data
- **Local processing**: Documents are processed locally using FAISS and local embeddings
- **Citation grounding**: Every answer must cite specific pages from the uploaded document
- **Honest evaluation**: Evaluation metrics are clearly labelled as synthetic and not production-validated

---

## 18. Limitations

1. **OCR not supported**: Scanned PDFs with image-only content will not extract text. Use text-based PDFs.
2. **Mock mode answer quality**: Without a real LLM, answers are placeholder-only. Citation and retrieval still work.
3. **Single language**: Only English-language documents are supported.
4. **Chunking heuristic**: Uses character-level sliding window — may split mid-sentence in some cases.
5. **Heading detection**: Heuristic-based — may miss some section headings in unusual PDF layouts.
6. **Evaluation ground truth**: The 15 synthetic QA pairs are based on the demo document only.
7. **No history persistence**: Chat history is per-session only (cleared on restart).

---

## 19. Future Work

- [ ] Add OCR support (Tesseract) for scanned PDFs
- [ ] Multi-language support for HLD documents in German, Japanese
- [ ] Persistent chat history in SQLite
- [ ] Hierarchical chunk retrieval (page → section → paragraph)
- [ ] Fine-tuned embedding model on AUTOSAR terminology
- [ ] Export answers as PDF report
- [ ] Integration with AUTOSAR toolchain APIs
- [ ] User authentication and multi-project management

---

## 20. Demo Script (5–10 Minutes)

```
1. Open http://localhost:8501
2. Show the project title and Tata TechPulse branding
3. Check "Use Synthetic Demo HLD" and click "Process Document"
4. Show the KPI bar: 1 doc, 15 pages, 60 chunks, 28,130 chars
5. Go to Chat tab → ask "What are the main software components?"
6. Show: answer + Citations expander (real page numbers) + Evidence expander
7. Ask "What is the dependency between FlashManager and NvMManager?"
8. Show the grounded response with page citations
9. Go to Architecture Analysis → Run Analysis → show component table
10. Go to Inconsistency Detection → Run Check → show findings
11. Go to Architecture Summary → Generate → show structured report
12. Go to Evaluation → Run Evaluation → show 100% retrieval/citation
13. Point to sidebar: "Demo Mode (No LLM)" — show Ollama setup instructions
14. Optional: Switch .env to LLM_PROVIDER=ollama and show live LLM answers
```

---

## 21. GitHub Readiness

### Suggested Commit Structure

```
commit 1: "Initial project structure and configuration"
commit 2: "PDF ingestion with page-aware chunking"
commit 3: "FAISS vector store and RAG pipeline"
commit 4: "Ollama/OpenAI LLM client with fallback"
commit 5: "Architecture extraction and inconsistency detection"
commit 6: "Streamlit professional dashboard"
commit 7: "Synthetic AUTOSAR HLD demo document"
commit 8: "Evaluation module and CLI"
commit 9: "Test suite (29 tests)"
commit 10: "Documentation and README"
```

### .gitignore covers

```
.env                   # Secrets — never committed
__pycache__/           # Python bytecode
.pytest_cache/         # Test cache
vector_store/          # Generated FAISS indices
evaluation_results/    # Generated evaluation JSON
data/input/*.pdf       # Uploaded documents
*.pyc
.vscode/
.idea/
```

---

## 22. Project Credits

**Developed for:** Tata Technologies TechPulse FY-26 Applied AI/ML Capstone

**Case Study:** CS1 — AUTOSAR HLD Document Analysis Assistant

**Technology Foundation:**
- [AUTOSAR](https://www.autosar.org/) — Automotive Open System Architecture standard
- [sentence-transformers](https://sbert.net/) — BAAI/bge-small-en-v1.5 embeddings
- [FAISS](https://github.com/facebookresearch/faiss) — Facebook AI Similarity Search
- [Ollama](https://ollama.ai) — Local LLM serving
- [Streamlit](https://streamlit.io) — Web dashboard framework
- [PyMuPDF](https://pymupdf.readthedocs.io) — PDF text extraction

---

*All document data is processed locally. No customer or confidential data is included in this repository. The synthetic HLD document is for demonstration purposes only.*
