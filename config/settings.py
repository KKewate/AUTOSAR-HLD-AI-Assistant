"""
AUTOSAR HLD AI Assistant — Central Configuration
All tunable parameters in one place. Secrets via .env only.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")   # independent of the current working directory

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent.parent
DATA_INPUT_DIR  = BASE_DIR / "data" / "input"
DATA_PROC_DIR   = BASE_DIR / "data" / "processed"
VECTOR_STORE_DIR= BASE_DIR / "vector_store"
EVAL_RESULTS_DIR= BASE_DIR / "evaluation_results"
PROMPTS_DIR     = BASE_DIR / "prompts"

for _d in [DATA_INPUT_DIR, DATA_PROC_DIR, VECTOR_STORE_DIR, EVAL_RESULTS_DIR, PROMPTS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── LLM ───────────────────────────────────────────────────────────────────────
# Supported providers: "openai" | "ollama" | "mock"
# - openai:  requires OPENAI_API_KEY
# - ollama:  requires Ollama running locally (no API key needed)
# - mock:    no external service needed (demo/offline mode)
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "mock")   # default mock so app runs without setup
LLM_PROVIDER   = LLM_PROVIDER.strip().lower()
# Provider-aware default: "llama3.1" is not a valid OpenAI model name.
LLM_MODEL       = os.getenv("LLM_MODEL") or ("gpt-4o-mini" if LLM_PROVIDER == "openai" else "llama3.1")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TEMPERATURE     = float(os.getenv("TEMPERATURE") or "0.1")
MAX_TOKENS      = int(os.getenv("MAX_TOKENS") or "1500")

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "BAAI/bge-small-en-v1.5"          # fast local model; swap for bge-large if needed
)

# ── Vector DB ─────────────────────────────────────────────────────────────────
VECTOR_DB       = os.getenv("VECTOR_DB", "faiss")              # faiss | chroma
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE      = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP   = int(os.getenv("CHUNK_OVERLAP", "100"))

# ── System prompt (override via prompts/system.txt if present) ────────────────
DEFAULT_SYSTEM_PROMPT = """
You are an expert AUTOSAR automotive architecture analyst.
Answer ONLY using the provided retrieved evidence from the HLD document.
Do NOT invent or assume any AUTOSAR architecture facts not present in the evidence.
If the retrieved context does not contain enough information to answer, respond exactly:
"Insufficient evidence in the uploaded HLD."
Always include citations (document name, page, section) for every factual claim.
Clearly distinguish between what is directly stated (Evidence) and what you infer (Inference).
Keep answers precise and professional.
""".strip()

def get_system_prompt() -> str:
    p = PROMPTS_DIR / "system.txt"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return DEFAULT_SYSTEM_PROMPT
