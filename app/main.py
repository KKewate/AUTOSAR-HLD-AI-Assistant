"""
AUTOSAR HLD Document Analysis Assistant
Tata TechPulse Applied AI/ML Capstone Project

Main Streamlit application — professional automotive engineering dashboard.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# ── Path fix: run from project root ───────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tempfile
import json
import pandas as pd
import streamlit as st

from config.settings import DATA_INPUT_DIR
from app.ingestion.pdf_extractor import extract_pages, get_document_stats
from app.ingestion.chunker import chunk_pages
from app.rag.vector_store import VectorStore
from app.rag.pipeline import ask
from app.rag.llm_client import is_mock_mode, get_llm_label, get_llm_setup_message
from app.extraction.arch_extractor import (
    extract_architecture, detect_inconsistencies, generate_summary,
)
from app.evaluation.evaluator import run_evaluation, SYNTHETIC_QA
from app.utils.helpers import project_id_for_files, format_chunk_as_evidence
from app.utils.synthetic_hld import create_synthetic_hld

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AUTOSAR HLD AI Assistant | TechPulse",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — Professional Automotive Theme
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root tokens ─────────────────────────────────────────────────────────── */
:root {
  --bg-primary:    #0d1117;
  --bg-secondary:  #161b22;
  --bg-tertiary:   #21262d;
  --accent-blue:   #1a73e8;
  --accent-teal:   #00b4d8;
  --accent-green:  #3fb950;
  --accent-orange: #f7850f;
  --accent-red:    #e74c3c;
  --text-primary:  #e6edf3;
  --text-secondary:#8b949e;
  --border:        #30363d;
  --glass-bg:      rgba(22,27,34,0.85);
  --shadow:        0 4px 24px rgba(0,0,0,0.4);
}

/* ── Base ────────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
}
.stApp { background: linear-gradient(135deg, #0d1117 0%, #0f1923 50%, #0d1117 100%); }

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0f1923 0%, #161b22 100%);
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stMarkdown h3 {
  color: var(--accent-teal);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
}

/* ── Metric cards ────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  transition: transform 0.2s, box-shadow 0.2s;
}
[data-testid="metric-container"]:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}
[data-testid="stMetricValue"] { color: var(--accent-teal) !important; font-weight: 700; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button {
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-teal));
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.85rem;
  letter-spacing: 0.03em;
  padding: 10px 20px;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(26,115,232,0.3);
}
.stButton > button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(26,115,232,0.5);
}

/* ── Chat messages ───────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
  border-radius: 12px;
  margin-bottom: 8px;
  border: 1px solid var(--border);
  background: var(--bg-secondary);
}

/* ── Cards / containers ──────────────────────────────────────────────────── */
.card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: var(--shadow);
}
.card-header {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent-teal);
  margin-bottom: 10px;
}

/* ── Badges ──────────────────────────────────────────────────────────────── */
.badge { display: inline-block; border-radius: 6px; padding: 2px 10px; font-size: 0.75rem; font-weight: 600; }
.badge-high    { background: rgba(63,185,80,0.15);  color: var(--accent-green);  border: 1px solid var(--accent-green); }
.badge-medium  { background: rgba(247,133,15,0.15); color: var(--accent-orange); border: 1px solid var(--accent-orange); }
.badge-low     { background: rgba(231,76,60,0.15);  color: var(--accent-red);    border: 1px solid var(--accent-red); }
.badge-mock    { background: rgba(139,148,158,0.15);color: var(--text-secondary);border: 1px solid var(--border); }
.badge-na      { background: rgba(139,148,158,0.15);color: var(--text-secondary);border: 1px solid var(--border); }

/* ── Evidence block ──────────────────────────────────────────────────────── */
.evidence-block {
  background: var(--bg-tertiary);
  border-left: 3px solid var(--accent-blue);
  border-radius: 0 8px 8px 0;
  padding: 12px 16px;
  margin: 8px 0;
  font-size: 0.8rem;
  font-family: 'JetBrains Mono', monospace;
}

/* ── Warning banner ──────────────────────────────────────────────────────── */
.mock-banner {
  background: linear-gradient(90deg, rgba(247,133,15,0.1), rgba(247,133,15,0.05));
  border: 1px solid var(--accent-orange);
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 0.82rem;
  color: var(--accent-orange);
  margin-bottom: 12px;
}

/* ── Tab styling ─────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg-secondary);
  border-radius: 10px 10px 0 0;
  border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
  font-weight: 600;
  font-size: 0.82rem;
  color: var(--text-secondary);
  padding: 10px 20px;
}
.stTabs [aria-selected="true"] {
  background: transparent;
  color: var(--accent-teal) !important;
  border-bottom: 2px solid var(--accent-teal) !important;
}

/* ── Expander ─────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 8px;
}

/* ── Progress bar ─────────────────────────────────────────────────────────── */
.stProgress > div > div { background: linear-gradient(90deg, var(--accent-blue), var(--accent-teal)); }

/* ── Divider ──────────────────────────────────────────────────────────────── */
hr { border-color: var(--border); }

/* ── Headers ─────────────────────────────────────────────────────────────── */
h1 { background: linear-gradient(135deg, var(--accent-teal), var(--accent-blue));
     -webkit-background-clip: text; -webkit-text-fill-color: transparent;
     font-weight: 700; }
h2, h3 { color: var(--text-primary); }

/* ── Table ────────────────────────────────────────────────────────────────── */
[data-testid="stTable"] { background: var(--bg-secondary); border-radius: 8px; }
thead tr th { background: var(--bg-tertiary) !important; color: var(--accent-teal) !important; }
tbody tr:hover { background: rgba(26,115,232,0.05) !important; }

/* ── Scrollbar ────────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-blue); }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "store": None,
        "doc_stats": {},
        "chunk_count": 0,
        "doc_names": [],
        "chat_history": [],
        "arch_result": None,
        "inconsistencies": None,
        "summary_text": "",
        "eval_result": None,
        "project_id": None,
        "processed": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding:12px 0;">
            <div style="font-size:2.5rem;">🚗</div>
            <div style="font-size:1rem; font-weight:700; color:#00b4d8;">AUTOSAR HLD</div>
            <div style="font-size:0.72rem; color:#8b949e; letter-spacing:0.08em;">AI ANALYSIS ASSISTANT</div>
            <div style="font-size:0.65rem; color:#8b949e; margin-top:4px;">Tata TechPulse Capstone</div>
        </div>
        <hr/>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📄 Document Upload")

    uploaded_files = st.file_uploader(
        "Upload AUTOSAR HLD PDF(s)",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more AUTOSAR HLD PDFs. Text-based PDFs work best.",
        key="uploader",
    )

    use_demo = st.checkbox(
        "Use Synthetic Demo HLD",
        value=not bool(uploaded_files),
        help="Creates a realistic-but-synthetic AUTOSAR HLD document for demo/evaluation.",
    )

    st.markdown("### ⚙️ Processing")
    col_a, col_b = st.columns(2)
    with col_a:
        chunk_size = st.number_input("Chunk Size", value=600, min_value=200, max_value=2000, step=100)
    with col_b:
        top_k = st.number_input("Top-K Retrieval", value=5, min_value=1, max_value=15, step=1)

    process_btn = st.button("⚡ Process Document", use_container_width=True, type="primary")

    st.markdown("### 📊 Status")

    if st.session_state.processed:
        store: VectorStore = st.session_state.store
        stats = store.get_stats()
        st.markdown(
            f"""
<div class="card" style="padding:12px;">
  <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
    <span style="color:#8b949e;font-size:0.75rem;">Status</span>
    <span style="color:#3fb950;font-size:0.75rem;font-weight:700;">✅ Ready</span>
  </div>
  <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
    <span style="color:#8b949e;font-size:0.75rem;">Chunks</span>
    <span style="color:#e6edf3;font-size:0.75rem;font-weight:600;">{stats['n_chunks']}</span>
  </div>
  <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
    <span style="color:#8b949e;font-size:0.75rem;">Documents</span>
    <span style="color:#e6edf3;font-size:0.75rem;font-weight:600;">{len(stats['documents'])}</span>
  </div>
  <div style="display:flex;justify-content:space-between;">
    <span style="color:#8b949e;font-size:0.75rem;">Vector DB</span>
    <span style="color:#00b4d8;font-size:0.75rem;font-weight:600;">FAISS Local</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.session_state.doc_names:
            st.markdown("**Loaded Documents:**")
            for dn in st.session_state.doc_names:
                st.markdown(f"- 📄 `{dn}`")
    else:
        st.markdown(
            '<div style="color:#8b949e;font-size:0.8rem;">No documents processed yet.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    llm_label = get_llm_label()
    setup_msg = get_llm_setup_message()

    if is_mock_mode():
        st.markdown(
            '<div class="mock-banner">'
            '<b>Demo Mode (No LLM)</b><br/>'
            'Retrieval and citations work fully.<br/>'
            'For real AI answers, set LLM_PROVIDER in .env:<br/>'
            '<b>Option A (Free/Local):</b> LLM_PROVIDER=ollama<br/>'
            'then: <code>ollama pull llama3.1 &amp;&amp; ollama serve</code><br/>'
            '<b>Option B (OpenAI):</b> LLM_PROVIDER=openai + OPENAI_API_KEY'
            '</div>',
            unsafe_allow_html=True,
        )
        if setup_msg:
            with st.expander("Setup details"):
                st.code(setup_msg)
    else:
        st.markdown(
            f'<div style="color:#3fb950;font-size:0.78rem;">'
            f'LLM: {llm_label}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div style="color:#8b949e;font-size:0.7rem;margin-top:8px;">'
        'Embeddings: BGE-small-en-v1.5 (local)<br/>'
        'Vector DB: FAISS (local, project-isolated)'
        '</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT PROCESSING
# ─────────────────────────────────────────────────────────────────────────────
if process_btn:
    pdf_paths: list[Path] = []

    if use_demo or not uploaded_files:
        with st.spinner("Creating synthetic demo HLD..."):
            p = create_synthetic_hld(DATA_INPUT_DIR)
            pdf_paths = [p]
            st.sidebar.success(f"Demo HLD created: {p.name}")

    if uploaded_files and not use_demo:
        for uf in uploaded_files:
            save_path = DATA_INPUT_DIR / Path(uf.name).name   # strip any path components
            save_path.write_bytes(uf.getvalue())
            pdf_paths.append(save_path)

    if not pdf_paths:
        st.sidebar.error("No PDFs to process.")
    else:
        project_id = project_id_for_files(pdf_paths)
        store = VectorStore(project_id=project_id)

        if store.is_ready:
            store.reset()   # Re-process to pick up new files

        all_chunks = []
        doc_stats_list = []

        progress = st.sidebar.progress(0, text="Extracting text...")

        for i, pdf_path in enumerate(pdf_paths):
            # Handle .txt fallback (when reportlab absent)
            if pdf_path.suffix == ".txt":
                text = pdf_path.read_text(encoding="utf-8")
                pages = [{"page": 1, "text": text, "heading": "Overview", "char_count": len(text), "is_scanned": False}]
            else:
                pages = extract_pages(pdf_path)

            stats = get_document_stats(pages)
            stats["doc_name"] = pdf_path.name
            doc_stats_list.append(stats)

            chunks = chunk_pages(pages, doc_name=pdf_path.name, chunk_size=int(chunk_size),
                                 chunk_overlap=min(100, int(chunk_size) // 4))
            all_chunks.extend(chunks)
            progress.progress((i + 1) / len(pdf_paths), text=f"Chunked: {pdf_path.name}")

        if all_chunks:
            progress.progress(0.8, text="Embedding & indexing...")
            store.add_chunks(all_chunks, show_progress=False)
            progress.progress(1.0, text="Done!")

            st.session_state.store         = store
            st.session_state.doc_stats     = doc_stats_list
            st.session_state.chunk_count   = store.chunk_count
            st.session_state.doc_names     = store.document_names
            st.session_state.project_id    = project_id
            st.session_state.processed     = True
            st.session_state.arch_result   = None
            st.session_state.inconsistencies = None
            st.session_state.summary_text  = ""
            st.session_state.eval_result   = None

            st.sidebar.success(f"✅ Processed {store.chunk_count} chunks from {len(pdf_paths)} document(s).")
        else:
            st.sidebar.error("No text could be extracted. Check if the PDF is text-based (not scanned-only).")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div style="display:flex;align-items:center;gap:16px;margin-bottom:4px;">
  <span style="font-size:2.5rem;">🚗</span>
  <div>
    <h1 style="margin:0;font-size:1.8rem;">AUTOSAR HLD Analysis Assistant</h1>
    <p style="margin:0;color:#8b949e;font-size:0.85rem;">
      AI-powered Retrieval-Augmented Generation for grounded automotive architecture understanding
      · <span style="color:#00b4d8;">Tata TechPulse Capstone</span>
    </p>
  </div>
</div>
<hr/>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW (document statistics)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.processed:
    store: VectorStore = st.session_state.store
    ds_list = st.session_state.doc_stats

    total_pages = sum(ds.get("total_pages", 0) for ds in ds_list)
    total_chars = sum(ds.get("total_chars", 0) for ds in ds_list)
    total_headings = sum(len(ds.get("headings_found", [])) for ds in ds_list)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📄 Documents", len(st.session_state.doc_names))
    k2.metric("📑 Pages",     total_pages)
    k3.metric("🔢 Chunks",    st.session_state.chunk_count)
    k4.metric("📌 Headings",  total_headings)
    k5.metric("🔤 Characters", f"{total_chars:,}")
    st.markdown("<br/>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_chat, tab_arch, tab_incon, tab_summary, tab_eval = st.tabs([
    "💬 Chat with HLD",
    "🔍 Architecture Analysis",
    "⚠️ Inconsistency Detection",
    "📋 Architecture Summary",
    "📊 Evaluation",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    if not st.session_state.processed:
        st.info("👆 Upload and process an HLD document using the sidebar to start chatting.", icon="ℹ️")
    else:
        store: VectorStore = st.session_state.store

        st.markdown("#### 💬 Chat with your AUTOSAR HLD Document")
        st.caption(
            "Ask architecture questions. Every answer is grounded in the uploaded document "
            "with page citations. No hallucination — if evidence is insufficient, the system will say so."
        )

        # Example questions
        with st.expander("💡 Example Questions"):
            example_qs = [
                "What are the main software components?",
                "What interfaces are present in the architecture?",
                "What is the dependency between DiagnosticManager and CANDriver?",
                "Summarize the overall architecture.",
                "Which component communicates with the diagnostic interface?",
                "What signals are used for diagnostic communication?",
                "Describe the flash reprogramming functional flow.",
                "What ports does the ECUStateManager provide?",
            ]
            cols = st.columns(2)
            for i, q in enumerate(example_qs):
                with cols[i % 2]:
                    if st.button(q, key=f"eg_{i}", use_container_width=True):
                        st.session_state["prefill_question"] = q

        # Chat history display
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and "meta" in msg:
                        meta = msg["meta"]
                        conf = meta.get("confidence", "N/A")
                        badge_cls = f"badge-{conf.lower()}" if conf in ("High","Medium","Low") else "badge-na"
                        cols = st.columns([1, 3])
                        with cols[0]:
                            st.markdown(
                                f'<span class="badge {badge_cls}">Confidence: {conf}</span>',
                                unsafe_allow_html=True,
                            )
                        if meta.get("mock_mode"):
                            st.markdown(
                                '<span class="badge badge-mock">⚙️ Mock LLM</span>',
                                unsafe_allow_html=True,
                            )

                        if meta.get("citations"):
                            with st.expander(f"📌 Citations ({len(meta['citations'])})"):
                                for c in meta["citations"]:
                                    st.markdown(f"- {c}")

                        if meta.get("chunks"):
                            with st.expander(f"🔍 Retrieved Evidence ({len(meta['chunks'])} chunks)"):
                                for i, chunk in enumerate(meta["chunks"], 1):
                                    st.markdown(
                                        format_chunk_as_evidence(chunk, i),
                                        unsafe_allow_html=False,
                                    )
                                    if i < len(meta["chunks"]):
                                        st.divider()

        # Input
        prefill = st.session_state.pop("prefill_question", "")
        user_input = st.chat_input(
            "Ask an architecture question about your HLD...",
            key="chat_input",
        )
        question = user_input or prefill

        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})

            with st.spinner("Retrieving and reasoning..."):
                result = ask(question, store, top_k=int(top_k))

            answer = result["answer"]
            st.session_state.chat_history.append(
                {
                    "role":    "assistant",
                    "content": answer,
                    "meta":    result,
                }
            )
            st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ARCHITECTURE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_arch:
    if not st.session_state.processed:
        st.info("Process a document first to run Architecture Analysis.", icon="ℹ️")
    else:
        store: VectorStore = st.session_state.store
        st.markdown("#### 🔍 Architecture Extraction")
        st.caption("Extracts structured architecture elements from the HLD. All items are grounded in document evidence.")

        if st.button("🔍 Run Architecture Analysis", type="primary", key="run_arch"):
            with st.spinner("Extracting architecture elements..."):
                st.session_state.arch_result = extract_architecture(store)

        arch = st.session_state.arch_result
        if arch:
            if arch.get("error"):
                st.error(arch["error"])
            else:
                # Display in table form
                def show_table(title: str, items: list, col_name: str = "Value"):
                    st.markdown(f"**{title}**")
                    if items:
                        df = pd.DataFrame({col_name: items})
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.markdown(
                            '<div style="color:#8b949e;font-size:0.82rem;">Not found in document.</div>',
                            unsafe_allow_html=True,
                        )

                c1, c2 = st.columns(2)
                with c1:
                    show_table("🧩 Software Components",  arch["components"],       "Component")
                    show_table("🔌 Interfaces",            arch["interfaces"],       "Interface")
                    show_table("🚪 Ports",                 arch["ports"],            "Port")
                with c2:
                    show_table("📡 Signals",               arch["signals"],          "Signal")
                    show_table("🔗 Dependencies",          arch["dependencies"],     "Dependency")
                    show_table("🔄 Functional Flows",      arch["functional_flows"], "Flow")

                if arch.get("citations"):
                    with st.expander("📌 Source Citations"):
                        for c in arch["citations"]:
                            st.markdown(f"- {c}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — INCONSISTENCY DETECTION
# ══════════════════════════════════════════════════════════════════════════════
with tab_incon:
    if not st.session_state.processed:
        st.info("Process a document first.", icon="ℹ️")
    else:
        store: VectorStore = st.session_state.store
        st.markdown("#### ⚠️ Potential Inconsistency Detection")
        st.caption(
            "Detects potential conflicts in the architecture. "
            "Every finding includes document citations. **Does NOT claim definitive errors.**"
        )

        if st.button("⚠️ Run Inconsistency Check", type="primary", key="run_incon"):
            with st.spinner("Analysing document for potential inconsistencies..."):
                st.session_state.inconsistencies = detect_inconsistencies(store)

        incons = st.session_state.inconsistencies
        if incons is not None:
            if not incons:
                st.success("✅ No potential inconsistencies detected in the retrieved evidence.")
            else:
                st.warning(f"⚠️ {len(incons)} potential inconsistency/inconsistencies detected.")
                for i, item in enumerate(incons, 1):
                    sev = item.get("severity", "Low")
                    color_map = {"High": "#e74c3c", "Medium": "#f7850f", "Low": "#f1c40f"}
                    color = color_map.get(sev, "#f1c40f")

                    with st.expander(f"#{i} — {item.get('finding', 'Finding')[:80]}"):
                        st.markdown(f"**Severity:** <span style='color:{color}'>{sev}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Finding:** {item.get('finding', '—')}")
                        evid = item.get("evidence", [])
                        if evid:
                            st.markdown("**Evidence:**")
                            for e in evid:
                                st.markdown(f"- {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ARCHITECTURE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
with tab_summary:
    if not st.session_state.processed:
        st.info("Process a document first.", icon="ℹ️")
    else:
        store: VectorStore = st.session_state.store
        st.markdown("#### 📋 Architecture Summary Report")
        st.caption("Generates a structured summary of the entire AUTOSAR architecture. Grounded in document evidence with citations.")

        if st.button("📋 Generate Architecture Summary", type="primary", key="run_summary"):
            arch = st.session_state.arch_result
            if arch is None:
                with st.spinner("Running architecture extraction first..."):
                    arch = extract_architecture(store)
                    st.session_state.arch_result = arch
            with st.spinner("Generating summary..."):
                st.session_state.summary_text = generate_summary(store, arch)

        if st.session_state.summary_text:
            st.markdown(st.session_state.summary_text)
            st.download_button(
                "⬇️ Download Summary",
                data=st.session_state.summary_text,
                file_name="architecture_summary.md",
                mime="text/markdown",
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — EVALUATION
# ══════════════════════════════════════════════════════════════════════════════
with tab_eval:
    st.markdown("#### 📊 RAG Pipeline Evaluation")
    st.caption(
        "⚠️ **Synthetic Evaluation Set** — The ground truth answers are synthetic, "
        "based on the demo HLD document. Results are indicative, not production-validated."
    )

    st.markdown(f"**{len(SYNTHETIC_QA)} test questions** covering components, interfaces, signals, dependencies, and functional flows.")

    if not st.session_state.processed:
        st.info("Process a document first to run evaluation.", icon="ℹ️")
    else:
        store: VectorStore = st.session_state.store

        if st.button("▶️ Run Evaluation", type="primary", key="run_eval"):
            with st.spinner(f"Running {len(SYNTHETIC_QA)} evaluation questions..."):
                st.session_state.eval_result = run_evaluation(store)

        ev = st.session_state.eval_result
        if ev:
            metrics = ev["metrics"]
            results = ev["results"]

            st.markdown("##### 📈 Metrics")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Retrieval Success",  f"{metrics['retrieval_success']:.0%}")
            m2.metric("Citation Coverage",  f"{metrics['citation_coverage']:.0%}")
            m3.metric("Groundedness",       f"{metrics['groundedness_rate']:.0%}")
            m4.metric("Answer Pass Rate",   f"{metrics['answer_pass_rate']:.0%}")

            # Correctness breakdown bar
            st.markdown("##### 🎯 Answer Correctness Breakdown")
            pass_c    = round(metrics["answer_pass_rate"]    * len(results))
            partial_c = round(metrics["answer_partial_rate"] * len(results))
            fail_c    = round(metrics["answer_fail_rate"]    * len(results))
            unv_c     = round(metrics["unverifiable_rate"]   * len(results))

            col_p, col_pa, col_f, col_u = st.columns(4)
            col_p.metric( "✅ Pass",          pass_c)
            col_pa.metric("🟡 Partial",       partial_c)
            col_f.metric( "❌ Fail",          fail_c)
            col_u.metric( "🔘 Unverifiable",  unv_c)

            st.divider()
            st.markdown("##### 📋 Per-Question Results")

            # Build display dataframe
            rows = []
            for r in results:
                rows.append({
                    "ID":          r["id"],
                    "Question":    r["question"][:60] + ("..." if len(r["question"]) > 60 else ""),
                    "Confidence":  r["confidence"],
                    "Retrieval":   "✅" if r["retrieval_success"] else "❌",
                    "Citation":    "✅" if r["citation_coverage"] else "❌",
                    "Grounded":    "✅" if r["groundedness"] else "❌",
                    "Correctness": r["answer_correctness"],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Full detail expander
            with st.expander("🔎 Full Question-by-Question Detail"):
                for r in results:
                    st.markdown(f"**{r['id']}: {r['question']}**")
                    st.markdown(f"*Ground Truth:* {r['ground_truth']}")
                    st.markdown(f"*Generated:* {r['generated_answer'][:300]}...")
                    st.markdown(f"*Citations:* {', '.join(r['citations']) if r['citations'] else 'None'}")
                    st.divider()

            st.download_button(
                "⬇️ Download Evaluation Results (JSON)",
                data=json.dumps(ev, indent=2),
                file_name="evaluation_results.json",
                mime="application/json",
            )

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<hr/>
<div style="text-align:center;color:#8b949e;font-size:0.72rem;padding:8px 0;">
  AUTOSAR HLD AI Assistant · Tata TechPulse Applied AI/ML Capstone ·
  Built with Streamlit · FAISS · BGE Embeddings · PyMuPDF<br/>
  All document data is processed locally. No documents are sent to external servers unless explicitly configured.
</div>
""",
    unsafe_allow_html=True,
)
