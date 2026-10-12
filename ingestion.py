from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from legal_parser import flatten_law, parse_law


def _pdf_pages(path: Path) -> list[dict[str, Any]]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        method = "text_layer" if text.strip() else "empty"
        if not text.strip():
            try:
                import fitz
                import pytesseract
                from PIL import Image
                import io
                pdf = fitz.open(str(path))
                pix = pdf[number - 1].get_pixmap(matrix=fitz.Matrix(2, 2))
                text = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))), lang="ara+eng")
                pdf.close()
                method = "ocr" if text.strip() else "empty"
            except Exception:
                pass
        pages.append({"page_number": number, "text": text, "extraction_method": method})
    return pages


def _docx_pages(path: Path) -> list[dict[str, Any]]:
    import docx
    doc = docx.Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"page_number": 1, "text": text, "extraction_method": "docx"}]


def _doc_pages(path: Path) -> list[dict[str, Any]]:
    """Convert legacy .doc to a temporary .docx, then use the normal parser."""
    with tempfile.TemporaryDirectory(prefix="lexgo_doc_") as temp_dir:
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "docx", "--outdir", temp_dir, str(path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        converted = Path(temp_dir) / f"{path.stem}.docx"
        if result.returncode != 0 or not converted.exists():
            raise RuntimeError("تعذر تحويل ملف DOC القديم. تأكد من تثبيت LibreOffice.")
        return _docx_pages(converted)


def extract_pages(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return _pdf_pages(path)
    if path.suffix.lower() == ".docx":
        return _docx_pages(path)
    if path.suffix.lower() == ".doc":
        return _doc_pages(path)
    raise ValueError("الامتدادات المدعومة هي PDF وDOC وDOCX فقط")


def ingest_file(path: str | Path, parsed_dir: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = Path(path)
    pages = extract_pages(path)
    raw = path.read_bytes()
    document_id = "doc_" + hashlib.sha256(raw).hexdigest()[:16]
    law = parse_law(pages, path.name)
    law.update({"document_id": document_id, "source_path": path.name, "pages": pages})
    law["extraction"]["ocr_available"] = any(p["extraction_method"] == "empty" for p in pages)
    rows = flatten_law(law, document_id)
    out = Path(parsed_dir) / f"{document_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(law, ensure_ascii=False, indent=2), encoding="utf-8")
    return law, rows


def load_all(data_dir: str | Path, parsed_dir: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    laws, rows = [], []
    data_dir = Path(data_dir)
    for path in sorted(data_dir.iterdir() if data_dir.exists() else []):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        try:
            law, law_rows = ingest_file(path, parsed_dir)
            laws.append(law)
            rows.extend(law_rows)
        except Exception as exc:
            laws.append({"file_name": path.name, "error": str(exc), "extraction": {"needs_review": True}})
    return laws, rows
