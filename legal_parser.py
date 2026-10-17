from __future__ import annotations

import re
from typing import Any

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4,
    "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8, "اغسطس": 8,
    "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}

LAW_RE = re.compile(r"(?im)(?:القانون|قانون|مرسوم\s+بقانون|قرار)\s*(?:رقم)?\s*([٠-٩0-9]+)\s*(?:لسنة|لعام|سنة)\s*([٠-٩0-9]{4})")
ARTICLE_RE = re.compile(r"(?im)^\s*(?:المادة|مادة)\s*[\(（]?\s*([٠-٩0-9]+(?:\s*[-/.]\s*[٠-٩0-9]+)?)\s*[\)）]?\s*(?:[-–—:]\s*(.*))?$")
PARAGRAPH_RE = re.compile(r"^\s*(?:الفقرة\s*)?[\(（]?([٠-٩0-9]+)[\)）)،.\-:]\s*(.*)$")
CLAUSE_RE = re.compile(r"^\s*(?:\(([أ-ي])\)|([أ-ي])\s*[-–—.):])\s*(.*)$")
DATE_RE = re.compile(r"(?P<day>[٠-٩0-9]{1,2})\s+(?P<month>[ء-ياأإآ]+)\s+(?P<year>[٠-٩0-9]{4})")


def normalize_digits(value: str | None) -> str | None:
    return value.translate(ARABIC_DIGITS) if value is not None else None


def clean_line(line: str) -> str:
    line = line.replace("\u200f", "").replace("\u200e", "")
    return re.sub(r"[ \t]+", " ", line).strip()


def parse_date(text: str | None) -> str | None:
    if not text:
        return None
    m = DATE_RE.search(text)
    if not m:
        numeric = re.search(r"([٠-٩0-9]{1,2})\s*[/.-]\s*([٠-٩0-9]{1,2})\s*[/.-]\s*([٠-٩0-9]{2,4})", text)
        if numeric:
            d, mo, y = [normalize_digits(x) for x in numeric.groups()]
            y = ("20" + y) if len(y) == 2 else y
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        return None
    day = int(normalize_digits(m.group("day")))
    month = MONTHS.get(m.group("month"))
    year = int(normalize_digits(m.group("year")))
    return f"{year:04d}-{month:02d}-{day:02d}" if month else None


def _find_date_near(lines: list[str], keywords: tuple[str, ...]) -> str | None:
    for line in lines:
        if any(k in line for k in keywords):
            value = parse_date(line)
            if value:
                return value
    return None


def _split_paragraphs(lines: list[str]) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue
        pm = PARAGRAPH_RE.match(line)
        cm = CLAUSE_RE.match(line)
        if pm:
            if current:
                paragraphs.append(current)
            current = {"paragraph_number": int(normalize_digits(pm.group(1))), "text": pm.group(2).strip(), "clauses": []}
        elif cm and current is not None:
            current["clauses"].append({"clause_number": cm.group(1) or cm.group(2), "text": cm.group(3).strip()})
        elif current is not None:
            current["text"] += (" " if current["text"] else "") + line
        else:
            paragraphs.append({"paragraph_number": None, "text": line, "clauses": []})
    if current:
        paragraphs.append(current)
    if not paragraphs and lines:
        paragraphs = [{"paragraph_number": None, "text": " ".join(clean_line(x) for x in lines if clean_line(x)), "clauses": []}]
    return paragraphs


def parse_law(pages: list[dict[str, Any]], file_name: str) -> dict[str, Any]:
    all_lines: list[str] = []
    for page in pages:
        all_lines.extend(page.get("text", "").splitlines())
    lines = [clean_line(x) for x in all_lines if clean_line(x)]
    joined = "\n".join(lines)
    law_match = LAW_RE.search(joined)
    law_number = normalize_digits(law_match.group(1)) if law_match else None
    law_year = int(normalize_digits(law_match.group(2))) if law_match else None

    articles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    page_index = 1
    for page in pages:
        page_text = page.get("text", "")
        page_lines = page_text.splitlines()
        for raw in page_lines:
            line = clean_line(raw)
            if not line:
                continue
            match = ARTICLE_RE.match(line)
            if match:
                if current:
                    articles.append(current)
                current = {
                    "article_number": normalize_digits(match.group(1)),
                    "title": (match.group(2) or "").strip(),
                    "page_start": page.get("page_number", page_index),
                    "page_end": page.get("page_number", page_index),
                    # Text after the article number is legal text, not a display-only title.
                    "lines": [match.group(2).strip()] if (match.group(2) or "").strip() else [],
                    "paragraphs": [],
                }
            elif current is not None:
                current["lines"].append(line)
                current["page_end"] = page.get("page_number", page_index)
        page_index += 1
    if current:
        articles.append(current)

    for article in articles:
        article["paragraphs"] = _split_paragraphs(article.pop("lines"))
        article["text"] = "\n".join(p["text"] for p in article["paragraphs"])

    title = next((x for x in lines[:20] if "القانون" in x or "مرسوم" in x), file_name.rsplit(".", 1)[0])
    effective_from = _find_date_near(lines, ("يعمل به", "يسري", "السريان", "نفاذ", "ينفذ"))
    effective_to = _find_date_near(lines, ("ينتهي العمل", "انتهاء السريان", "يلغى في", "إلغاء"))
    publication_date = _find_date_near(lines, ("نشر", "الجريدة الرسمية", "صدر في"))

    return {
        "file_name": file_name,
        "title": title,
        "law_number": law_number,
        "law_year": law_year,
        "publication_date": publication_date,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "status": "active" if not effective_to else "unknown",
        "articles": articles,
        "article_count": len(articles),
        "extraction": {"method": "rules", "confidence": 0.0 if not articles else 0.85, "needs_review": not bool(law_number and law_year and articles)},
    }


def flatten_law(law: dict[str, Any], document_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for article in law.get("articles", []):
        paragraphs = article.get("paragraphs") or [{"paragraph_number": None, "text": article.get("text", ""), "clauses": []}]
        for p_idx, paragraph in enumerate(paragraphs, 1):
            p_num = paragraph.get("paragraph_number")
            clauses = paragraph.get("clauses") or [{"clause_number": None, "text": paragraph.get("text", "")}]
            for c_idx, clause in enumerate(clauses, 1):
                c_num = clause.get("clause_number")
                text = clause.get("text", "")
                if not text.strip():
                    continue
                rows.append({
                    # OCR and loosely formatted laws can repeat paragraph/clause
                    # labels. The primary key must remain unique for every chunk.
                    "chunk_id": f"{document_id}_chunk_{len(rows) + 1}",
                    "document_id": document_id,
                    "title": law.get("title"),
                    "law_number": law.get("law_number"),
                    "law_year": law.get("law_year"),
                    "status": law.get("status"),
                    "effective_from": law.get("effective_from") or "",
                    "effective_to": law.get("effective_to") or "",
                    "article_number": article.get("article_number"),
                    "paragraph_number": p_num if p_num is not None else p_idx,
                    "clause_number": c_num if c_num is not None else c_idx,
                    "page_start": article.get("page_start", 0),
                    "page_end": article.get("page_end", 0),
                    "text": text,
                })
    return rows
