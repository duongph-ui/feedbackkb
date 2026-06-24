"""Search adapter — dedupe + knowledge ranking.

Step 3 ships the contract + `keyword` impl (accent-folded substring rank, no
embeddings, no external service). `pgvector` and `sepo` impls land in Step 37.
"""

from __future__ import annotations

import abc
import unicodedata


def fold(text: str) -> str:
    """Lowercase + strip accents — Vietnamese-friendly match key."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class SearchAdapter(abc.ABC):
    @abc.abstractmethod
    def search(self, query: str, candidates: list[dict], system: str | None = None) -> list[dict]:
        """Rank candidates against query. Each result gets a `score` in [0,1]."""


class KeywordSearch(SearchAdapter):
    def search(self, query: str, candidates: list[dict], system: str | None = None) -> list[dict]:
        q = fold(query)
        q_terms = set(q.split())
        scored = []
        for c in candidates:
            if system is not None and c.get("system") != system:
                continue
            text = fold(c.get("text", ""))
            terms = set(text.split())
            if not q_terms:
                score = 0.0
            elif q in text:
                score = 1.0
            else:
                score = len(q_terms & terms) / len(q_terms)
            if score > 0:
                scored.append({**c, "score": round(score, 4)})
        return sorted(scored, key=lambda r: r["score"], reverse=True)


class PgVectorSearch(SearchAdapter):
    """Semantic search via pgvector (Step 37, P4). Embedding model chosen by env
    (self-host MiniLM-384 or OpenAI 1536). SDK imported lazily; until configured
    it raises so the deploy doesn't silently fall back to keyword."""

    def __init__(self, model: str | None = None) -> None:
        import os

        self._model = model or os.environ.get("FEEDBACKKB_EMBED_MODEL", "")
        if not self._model:
            raise RuntimeError(
                "FEEDBACKKB_EMBED_MODEL not set (e.g. all-MiniLM-L6-v2 or text-embedding-3-small)"
            )

    def search(self, query: str, candidates: list[dict], system: str | None = None) -> list[dict]:
        # Real impl: embed query + candidates, cosine rank via pgvector.
        raise NotImplementedError("pgvector ranking wired at P4 with the chosen embed model")
