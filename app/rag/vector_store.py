"""
Vector Store — wraps FAISS for local embedding storage and retrieval.
Each project gets its own index saved to vector_store/<project_id>/.
"""

from __future__ import annotations
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from config.settings import EMBEDDING_MODEL, RETRIEVAL_TOP_K, VECTOR_STORE_DIR


class VectorStore:
    """
    Lightweight FAISS-backed vector store.

    Files on disk (inside *store_path*):
        index.faiss   — FAISS IndexFlatIP index
        metadata.pkl  — list of chunk metadata dicts
        config.json   — store configuration
    """

    INDEX_FILE    = "index.faiss"
    META_FILE     = "metadata.pkl"
    CONFIG_FILE   = "config.json"

    def __init__(self, project_id: str, model_name: str = EMBEDDING_MODEL):
        self.project_id  = project_id
        self.model_name  = model_name
        self.store_path  = VECTOR_STORE_DIR / project_id
        self.store_path.mkdir(parents=True, exist_ok=True)

        self._model: SentenceTransformer | None = None
        self._index: faiss.Index | None         = None
        self._metadata: List[Dict[str, Any]]    = []

        self._load_if_exists()

    # ── Embedding model (lazy) ─────────────────────────────────────────────────
    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    # ── Persistence ────────────────────────────────────────────────────────────
    def _load_if_exists(self):
        idx_path  = self.store_path / self.INDEX_FILE
        meta_path = self.store_path / self.META_FILE
        if idx_path.exists() and meta_path.exists():
            cfg_path = self.store_path / self.CONFIG_FILE
            if cfg_path.exists():
                try:
                    saved = json.loads(cfg_path.read_text()).get("model_name")
                except Exception:
                    saved = None
                if saved and saved != self.model_name:
                    # Index was built with a different embedding model: dimensions/space
                    # would not match, so discard it and force a rebuild.
                    self.reset()
                    return
            self._index    = faiss.read_index(str(idx_path))
            with open(meta_path, "rb") as f:
                self._metadata = pickle.load(f)

    def _save(self):
        faiss.write_index(self._index, str(self.store_path / self.INDEX_FILE))
        with open(self.store_path / self.META_FILE, "wb") as f:
            pickle.dump(self._metadata, f)
        cfg = {"model_name": self.model_name, "n_vectors": len(self._metadata)}
        (self.store_path / self.CONFIG_FILE).write_text(json.dumps(cfg, indent=2))

    # ── Build / Add ────────────────────────────────────────────────────────────
    def add_chunks(self, chunks: List[Dict[str, Any]], show_progress: bool = True):
        """Embed *chunks* and add to the FAISS index."""
        if not chunks:
            return
        texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=show_progress,
            normalize_embeddings=True,   # cosine via inner-product
        )
        embeddings = np.array(embeddings, dtype="float32")

        if self._index is None:
            dim = embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dim)

        self._index.add(embeddings)
        self._metadata.extend(chunks)
        self._save()

    def reset(self):
        """Clear the index (e.g. re-process the same project)."""
        self._index    = None
        self._metadata = []
        for f in [self.INDEX_FILE, self.META_FILE, self.CONFIG_FILE]:
            p = self.store_path / f
            if p.exists():
                p.unlink()

    # ── Search ─────────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = RETRIEVAL_TOP_K,
    ) -> List[Dict[str, Any]]:
        """
        Returns top-k chunks most similar to *query*.
        Each result has an extra "score" key (cosine similarity, 0-1).
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        q_emb = self.model.encode(
            [query], normalize_embeddings=True
        ).astype("float32")

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(q_emb, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = dict(self._metadata[idx])
            chunk["score"] = float(score)
            results.append(chunk)

        return results

    # ── Info ───────────────────────────────────────────────────────────────────
    @property
    def is_ready(self) -> bool:
        return self._index is not None and self._index.ntotal > 0

    @property
    def chunk_count(self) -> int:
        return len(self._metadata)

    @property
    def document_names(self) -> List[str]:
        return list({c["doc_name"] for c in self._metadata})

    def get_stats(self) -> Dict[str, Any]:
        return {
            "project_id":   self.project_id,
            "model":        self.model_name,
            "n_chunks":     self.chunk_count,
            "documents":    self.document_names,
            "is_ready":     self.is_ready,
        }
