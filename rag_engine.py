from __future__ import annotations

import re
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from legal_parser import normalize_digits

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

ARABIC_ORDINALS = {
    "الأولى": "1", "الاولي": "1", "الاولى": "1", "أولى": "1", "اولى": "1",
    "الثانية": "2", "الثانيه": "2", "ثانية": "2", "الثالثة": "3", "الثالثه": "3",
    "الرابعة": "4", "الرابعه": "4", "الخامسة": "5", "الخامسه": "5",
    "السادسة": "6", "السادسه": "6", "السابعة": "7", "السابعه": "7",
    "الثامنة": "8", "الثامنه": "8", "التاسعة": "9", "التاسعه": "9",
    "العاشرة": "10", "العاشره": "10",
}


def tokens(text: str) -> list[str]:
    text = normalize_digits(text or "") or ""
    return re.findall(r"[\w]+", text.lower(), flags=re.UNICODE)


def query_filters(query: str) -> dict[str, str | int]:
    result: dict[str, str | int] = {}
    law = re.search(r"(?:القانون|قانون|مرسوم\s+بقانون|قرار)[^\n٠-٩0-9]{0,60}(?:رقم\s*)?([٠-٩0-9]+)\s*(?:لسنة|لعام|سنة)\s*([٠-٩0-9]{4})", query)
    article = re.search(r"(?:المادة|مادة)\s*(?:رقم\s*)?([٠-٩0-9]+)", query)
    paragraph = re.search(r"(?:الفقرة|فقرة)\s*(?:رقم\s*)?([٠-٩0-9]+)", query)
    clause = re.search(r"(?:البند|بند|clause)\s*(?:رقم\s*)?([٠-٩0-9]+|[أ-ي])", query, flags=re.IGNORECASE)
    if not article:
        ordinal = re.search(r"(?:المادة|مادة)\s+(الأولى|الاولي|الاولى|أولى|اولى|الثانية|الثانيه|ثانية|الثالثة|الثالثه|الرابعة|الرابعه|الخامسة|الخامسه|السادسة|السادسه|السابعة|السابعه|الثامنة|الثامنه|التاسعة|التاسعه|العاشرة|العاشره)", query)
        if ordinal:
            result["article_number"] = ARABIC_ORDINALS[ordinal.group(1)]
    if law:
        result["law_number"] = normalize_digits(law.group(1)) or ""
        result["law_year"] = int(normalize_digits(law.group(2)) or 0)
    if article:
        result["article_number"] = normalize_digits(article.group(1)) or ""
    if paragraph:
        result["paragraph_number"] = int(normalize_digits(paragraph.group(1)) or 0)
    if clause:
        clause_value = normalize_digits(clause.group(1)) or ""
        result["clause_number"] = int(clause_value) if clause_value.isdigit() else clause_value
    normalized_query = query.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    if "مدني" in normalized_query:
        result["law_title_contains"] = "مدني"
    elif "ادارات قانونية" in normalized_query or "إدارات قانونية" in query:
        result["law_title_contains"] = "ادارات قانونية"
    return result


class LegalIndex:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.documents = [r.get("text", "") for r in rows]
        self.bm25 = BM25Okapi([tokens(x) for x in self.documents]) if rows else None
        self.model = SentenceTransformer(MODEL_NAME) if rows else None
        self.embeddings = self.model.encode(self.documents, normalize_embeddings=True, convert_to_numpy=True) if rows else np.empty((0, 384))

    def search(self, query: str, k: int = 6, threshold: float = 70.0) -> list[dict[str, Any]]:
        if not self.rows:
            return []
        filters = query_filters(query)
        candidates = list(range(len(self.rows)))
        for key, value in filters.items():
            if key == "law_title_contains":
                candidates = [i for i in candidates if str(value) in str(self.rows[i].get("title", "")).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا") or str(value).replace("ادارات", "الادارات") in str(self.rows[i].get("title", ""))]
            else:
                candidates = [i for i in candidates if str(self.rows[i].get(key, "")) == str(value)]
        if not candidates:
            # Explicit article/law/paragraph requests must never fall back to
            # semantically similar text from another article.
            return []
        bm = self.bm25.get_scores(tokens(query))
        q_emb = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        dense = self.embeddings @ q_emb
        bm_values = np.array([bm[i] for i in candidates], dtype=float)
        de_values = np.array([dense[i] for i in candidates], dtype=float)
        def norm(a):
            if len(a) == 0 or float(a.max()) == float(a.min()):
                return np.ones_like(a) if len(a) else a
            return (a - a.min()) / (a.max() - a.min())
        query_tokens = set(tokens(query))
        filters = query_filters(query)
        confidences = []
        for idx, candidate in enumerate(candidates):
            row_tokens = set(tokens(self.rows[candidate].get("text", "")))
            lexical = (len(query_tokens & row_tokens) / max(1, len(query_tokens))) * 100
            semantic = float(np.clip((de_values[idx] + 1.0) * 50.0, 0.0, 100.0))
            metadata_bonus = 0.0
            if filters.get("article_number") and str(self.rows[candidate].get("article_number")) == str(filters["article_number"]):
                metadata_bonus += 15.0
            if filters.get("law_number") and str(self.rows[candidate].get("law_number")) == str(filters["law_number"]):
                metadata_bonus += 10.0
            if filters.get("law_title_contains") and str(filters["law_title_contains"]) in str(self.rows[candidate].get("title", "")):
                metadata_bonus += 15.0
            confidences.append(min(100.0, .65 * semantic + .25 * lexical + metadata_bonus))
        confidences = np.array(confidences, dtype=float)
        # A direct request such as "ما نص المادة 1" already contains an
        # authoritative database key. Do not reject the exact article merely
        # because its legal wording has few lexical words in common with the
        # short question. The 70% threshold remains active for semantic-only
        # searches without an explicit article/law/paragraph filter.
        explicit_lookup = any(filters.get(key) for key in ("article_number", "law_number", "law_year", "paragraph_number", "clause_number"))
        qualified = np.arange(len(candidates)) if explicit_lookup else np.where(confidences >= threshold)[0]
        if len(qualified) == 0:
            return []
        order = qualified[np.argsort(confidences[qualified])[::-1][:k]]
        output = []
        for pos in order:
            row = dict(self.rows[candidates[int(pos)]])
            row["score"] = round(float(confidences[pos]), 2)
            row["semantic_score"] = round(float(np.clip((de_values[pos] + 1.0) * 50.0, 0.0, 100.0)), 2)
            output.append(row)
        return output
