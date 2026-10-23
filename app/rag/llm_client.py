"""
LLM Client — supports three providers:

  1. ollama   — Llama 3.1 8B (or any model) via local Ollama server (no API key)
  2. openai   — GPT-4o-mini via OpenAI API (requires OPENAI_API_KEY)
  3. mock     — deterministic canned responses for offline demo (default)

Provider selection via LLM_PROVIDER env variable.
Never hard-codes secrets.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any

from config.settings import (
    LLM_PROVIDER, LLM_MODEL, OPENAI_API_KEY,
    OLLAMA_BASE_URL, TEMPERATURE, MAX_TOKENS, get_system_prompt,
)


# ─────────────────────────────────────────────────────────────────────────────
# MOCK LLM  (offline / demo mode — clearly labelled)
# ─────────────────────────────────────────────────────────────────────────────
class _MockLLM:
    """
    Returns structured responses referencing retrieved evidence.
    Clearly flagged as DEMO MODE so viewers understand no real LLM is running.
    
    Why mock?  Allows the full RAG pipeline — retrieval, chunking, citations —
    to be demonstrated without any external API dependency.
    """
    provider_label = "Mock (Demo Mode)"

    def chat(self, messages: List[Dict[str, str]]) -> str:
        ctx_block = next(
            (m["content"] for m in messages
             if m["role"] == "system" and "CONTEXT" in m["content"]),
            ""
        )
        user_q = next(
            (m["content"] for m in messages if m["role"] == "user"), "")

        # Extract first page citation from retrieved context
        page_hint = "the document"
        match = re.search(r"Page (\d+)", ctx_block)
        if match:
            page_hint = f"Page {match.group(1)}"

        # Count how many evidence chunks were retrieved
        chunk_count = len(re.findall(r"^\[\d+\] Source:", ctx_block, re.MULTILINE))

        return (
            f"**[DEMO MODE — No LLM configured]**\n\n"
            f"The RAG pipeline retrieved **{chunk_count} evidence chunks** from the "
            f"uploaded HLD (first citation: {page_hint}). In a live deployment this "
            f"context would be sent to an LLM (Ollama/Llama 3.1 or OpenAI GPT-4o-mini) "
            f"to generate a grounded answer.\n\n"
            f"**Your question:** _{user_q}_\n\n"
            f"**To enable real AI answers**, configure one of:\n"
            f"- **Ollama (local, free):** `LLM_PROVIDER=ollama` in `.env` then run "
            f"`ollama pull llama3.1` and `ollama serve`\n"
            f"- **OpenAI:** Set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY` in `.env`"
        )


# ─────────────────────────────────────────────────────────────────────────────
# OLLAMA LLM  (local, free, no API key)
# ─────────────────────────────────────────────────────────────────────────────
class _OllamaLLM:
    """
    Uses the Ollama REST API (http://localhost:11434).
    Requires: ollama installed + model pulled (e.g. ollama pull llama3.1)
    
    Why Ollama?  Free, local, privacy-preserving — documents never leave the machine.
    """
    provider_label = f"Ollama ({LLM_MODEL})"

    def __init__(self):
        try:
            import requests
            self._requests = requests
            # Quick connectivity check
            resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if resp.status_code != 200:
                raise ConnectionError(f"Ollama returned status {resp.status_code}")
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {OLLAMA_BASE_URL}.\n"
                f"Original error: {e}\n\n"
                f"To fix:\n"
                f"  1. Install Ollama: https://ollama.ai\n"
                f"  2. Run: ollama pull {LLM_MODEL}\n"
                f"  3. Ensure ollama serve is running"
            )

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send messages to Ollama /api/chat endpoint."""
        import json
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
            },
            "stream": False,
        }
        resp = self._requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()


# ─────────────────────────────────────────────────────────────────────────────
# OPENAI LLM
# ─────────────────────────────────────────────────────────────────────────────
class _OpenAILLM:
    """OpenAI GPT-4o-mini via official Python SDK."""
    provider_label = f"OpenAI ({LLM_MODEL})"

    def __init__(self):
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        kwargs = dict(model=LLM_MODEL, messages=messages, temperature=TEMPERATURE)
        try:
            resp = self._client.chat.completions.create(max_tokens=MAX_TOKENS, **kwargs)
        except Exception as e:
            # Newer OpenAI models reject max_tokens and/or custom temperature.
            msg = str(e)
            if "max_completion_tokens" in msg or "temperature" in msg:
                kwargs.pop("temperature", None)
                resp = self._client.chat.completions.create(
                    max_completion_tokens=MAX_TOKENS, **kwargs)
            else:
                raise
        return (resp.choices[0].message.content or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# FACTORY
# ─────────────────────────────────────────────────────────────────────────────
def _build_llm():
    """
    Build the LLM based on LLM_PROVIDER environment variable.
    Falls back to Mock on any error so the app never crashes.
    """
    provider = LLM_PROVIDER

    if provider == "ollama":
        try:
            return _OllamaLLM()
        except ConnectionError as e:
            # Return mock but store the error for display in the UI
            m = _MockLLM()
            m._ollama_error = str(e)
            return m

    if provider == "openai":
        if not OPENAI_API_KEY:
            m = _MockLLM()
            m._setup_msg = "OPENAI_API_KEY is not set in .env. Running in demo mode."
            return m
        try:
            return _OpenAILLM()
        except Exception as e:
            m = _MockLLM()
            m._setup_msg = f"OpenAI init failed: {e}"
            return m

    # provider == "mock" or anything else
    return _MockLLM()


_LLM_INSTANCE = None


def get_llm():
    global _LLM_INSTANCE
    if _LLM_INSTANCE is None:
        _LLM_INSTANCE = _build_llm()
    return _LLM_INSTANCE


def reset_llm():
    """Force LLM to be re-built (e.g. after .env changes)."""
    global _LLM_INSTANCE
    _LLM_INSTANCE = None


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def is_mock_mode() -> bool:
    return isinstance(get_llm(), _MockLLM)


def get_llm_label() -> str:
    """Return a human-readable label for the current LLM."""
    llm = get_llm()
    return getattr(llm, "provider_label", "Unknown")


def get_llm_setup_message() -> str:
    """Return any setup/error message from the LLM initialisation."""
    llm = get_llm()
    if hasattr(llm, "_ollama_error"):
        return llm._ollama_error
    if hasattr(llm, "_setup_msg"):
        return llm._setup_msg
    return ""


def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Format retrieved chunks into a clearly labelled context block for the prompt.
    Each chunk is numbered and tagged with its source (document, page, section).
    """
    lines = []
    for i, c in enumerate(chunks, 1):
        heading = c.get("heading") or "General"
        lines.append(
            f"[{i}] Source: {c['doc_name']} | Page {c['page']} | Section: {heading}\n"
            f"{c['text']}\n"
        )
    return "\n".join(lines)


def llm_answer(
    question: str,
    chunks: List[Dict[str, Any]],
    extra_instruction: str = "",
) -> str:
    """
    Full RAG prompt: system_prompt + retrieved_context + user_question -> answer.
    
    The system prompt instructs the LLM to:
    - Use ONLY retrieved context as knowledge source
    - Cite page/section for every factual claim
    - Respond with "Insufficient evidence" if context is inadequate
    - Distinguish evidence from inference
    """
    system_prompt = get_system_prompt()
    if extra_instruction:
        system_prompt += f"\n\nAdditional instruction: {extra_instruction}"

    context = build_context_block(chunks)

    system_with_ctx = (
        f"{system_prompt}\n\n"
        f"CONTEXT (retrieved from HLD document — use ONLY this as your knowledge source):\n"
        f"{'=' * 60}\n"
        f"{context}\n"
        f"{'=' * 60}"
    )

    messages = [
        {"role": "system", "content": system_with_ctx},
        {"role": "user",   "content": question},
    ]

    try:
        return get_llm().chat(messages)
    except Exception as e:   # network/timeout/auth errors must not crash the app
        return f"**LLM request failed** ({type(e).__name__}): {e}"
