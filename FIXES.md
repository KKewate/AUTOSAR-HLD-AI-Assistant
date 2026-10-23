# Bug fixes applied

1. **Evaluator scored mock/demo runs as Fail** – it looked for "MOCK MODE" but the mock LLM prints "DEMO MODE"; now such runs are "Unverifiable".
2. **Mock LLM chunk count wrong** – counted every `[` in the context; now counts only `[n] Source:` headers.
3. **PDF extraction** – spans of one line were joined with newlines (broke words/lines); headings now detected per line, bold labels ending in ":" are no longer headings, and a heading is tracked per position, so each chunk cites the correct section instead of the first heading on the page.
4. **Chunker** – `overlap >= size` caused an infinite loop; chunks no longer start/end mid-word.
5. **Architecture / inconsistency / summary** – crashed or silently returned empty when the LLM returned a list/dict of the wrong shape; output is now validated. In mock mode they show a clear "needs a real LLM" message.
6. **LLM errors** – a network/timeout/auth failure at chat time crashed the Streamlit app; now returned as a message. OpenAI newer models (`max_completion_tokens`, fixed temperature) handled.
7. **Config** – `LLM_MODEL` defaulted to `llama3.1` even for OpenAI; now `gpt-4o-mini`. `.env` loaded relative to project, not cwd. Empty env values no longer crash.
8. **Vector store** – stale index built with a different embedding model is discarded; empty `add_chunks` guarded.
9. **UI** – uploaded filename sanitised (path traversal), `uf.getvalue()` instead of `read()`, correctness counts use `round()` instead of `int()`, chunk overlap scales with chunk size, PyMuPDF `import pymupdf` (no deprecation warning).
