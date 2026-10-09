"""Semantic similarity. Uses Sentence-Transformers when installed, otherwise a lexical fallback."""
from __future__ import annotations

import logging
import math
import re
from collections import Counter

log = logging.getLogger(__name__)

_STOP = set("a an the and or but if of to in on for with at by from as is are was were be been it this that these those i you we they he she my our your their me do does did have has had not so can could would should will just about into than then there what which who how why when where also very".split())


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9\+#\.]+", (text or "").lower()) if t not in _STOP and len(t) > 1]


class EmbeddingService:
    def __init__(self, enabled: bool = True, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.enabled, self.model_name = enabled, model_name
        self._model = None
        self._tried = False

    @property
    def backend(self) -> str:
        return f"sentence-transformers ({self.model_name.split('/')[-1]})" if self._load() else "lexical-cosine (fallback)"

    def _load(self):
        if self._model is not None:
            return self._model
        if not self.enabled or self._tried:
            return None
        self._tried = True
        try:  # heavy optional dependency
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            log.info("embedding_model_loaded")
        except Exception as e:  # noqa: BLE001
            log.warning("embedding_model_unavailable: %s", type(e).__name__)
            self._model = None
        return self._model

    # ------------------------------------------------------------------ API
    def similarity(self, a: str, b: str) -> float:
        """Cosine similarity in [0, 1]."""
        if not a or not b:
            return 0.0
        model = self._load()
        if model is not None:
            try:
                import numpy as np
                va, vb = model.encode([a, b], normalize_embeddings=True)
                return float(max(0.0, min(1.0, float(np.dot(va, vb)))))
            except Exception:  # noqa: BLE001
                log.warning("embedding_encode_failed")
        return self._lexical(a, b)

    def top_k(self, query: str, docs: list[str], k: int = 3) -> list[tuple[str, float]]:
        scored = [(d, self.similarity(query, d)) for d in docs if d]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    @staticmethod
    def _lexical(a: str, b: str) -> float:
        ca, cb = Counter(_tokens(a)), Counter(_tokens(b))
        if not ca or not cb:
            return 0.0
        dot = sum(ca[t] * cb[t] for t in ca)
        na, nb = math.sqrt(sum(v * v for v in ca.values())), math.sqrt(sum(v * v for v in cb.values()))
        return dot / (na * nb) if na and nb else 0.0

    def is_semantic(self) -> bool:
        return self._load() is not None
