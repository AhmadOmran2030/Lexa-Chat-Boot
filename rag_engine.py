from __future__ import annotations

import re
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from legal_parser import normalize_digits

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def tokens(text: str) -> list[str]:
    text = normalize_digits(text or "") or ""
    return re.findall(r"[\w]+", text.lower(), flags=re.UNICODE)


def query_filters(query: str) -> dict[str, str | int]:
    result: dict[str, str | int] = {}
    law = re.search(r"(?:القانون|مرسوم\s+بقانون|قرار)\s*(?:رقم)?\s*([٠-٩0-9]+)\s*(?:لسنة|لعام|سنة)\s*([٠-٩0-9]{4})", query)
    article = re.search(r"(?:المادة|مادة)\s*([٠-٩0-9]+)", query)
    paragraph = re.search(r"(?:الفقرة|فقرة)\s*([٠-٩0-9]+)", query)
    if law:
        result["law_number"] = normalize_digits(law.group(1)) or ""
        result["law_year"] = int(normalize_digits(law.group(2)) or 0)
    if article:
        result["article_number"] = normalize_digits(article.group(1)) or ""
    if paragraph:
        result["paragraph_number"] = int(normalize_digits(paragraph.group(1)) or 0)
    return result


class LegalIndex:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.documents = [r.get("text", "") for r in rows]
        self.bm25 = BM25Okapi([tokens(x) for x in self.documents]) if rows else None
        self.model = SentenceTransformer(MODEL_NAME) if rows else None
        self.embeddings = self.model.encode(self.documents, normalize_embeddings=True, convert_to_numpy=True) if rows else np.empty((0, 384))

    def search(self, query: str, k: int = 6) -> list[dict[str, Any]]:
        if not self.rows:
            return []
        filters = query_filters(query)
        candidates = list(range(len(self.rows)))
        for key, value in filters.items():
            candidates = [i for i in candidates if str(self.rows[i].get(key, "")) == str(value)]
        if not candidates:
            candidates = list(range(len(self.rows)))
        bm = self.bm25.get_scores(tokens(query))
        q_emb = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        dense = self.embeddings @ q_emb
        bm_values = np.array([bm[i] for i in candidates], dtype=float)
        de_values = np.array([dense[i] for i in candidates], dtype=float)
        def norm(a):
            if len(a) == 0 or float(a.max()) == float(a.min()):
                return np.ones_like(a) if len(a) else a
            return (a - a.min()) / (a.max() - a.min())
        scores = .4 * norm(bm_values) + .6 * norm(de_values)
        order = np.argsort(scores)[::-1][:k]
        output = []
        for pos in order:
            row = dict(self.rows[candidates[int(pos)]])
            row["score"] = round(float(scores[pos]) * 100, 2)
            row["semantic_score"] = round(float(de_values[pos]) * 100, 2)
            output.append(row)
        return output
