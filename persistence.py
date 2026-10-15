from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from typing import Any

TABLE = "legal_chunks"
USERS_TABLE = "app_users"
FIELDS = (
    "chunk_id,document_id,file_name,title,law_number,law_year,status,effective_from,effective_to,"
    "article_number,paragraph_number,clause_number,page_start,page_end,text"
)


def _setting(name: str, default: str = "") -> str:
    names = [name]
    if name == "SUPABASE_SERVICE_ROLE_KEY":
        names.append("SUPABASE_SECRET_KEY")
    for candidate in names:
        value = os.getenv(candidate)
        if value:
            return value
    try:
        import streamlit as st
        for candidate in names:
            value = st.secrets.get(candidate)
            if value:
                return str(value)
        return default
    except Exception:
        return default


def configured() -> bool:
    return bool(_setting("SUPABASE_URL") and _setting("SUPABASE_SERVICE_ROLE_KEY"))


def _request(method: str, path: str, payload: Any = None, table: str = TABLE) -> Any:
    base = _setting("SUPABASE_URL").rstrip("/")
    key = _setting("SUPABASE_SERVICE_ROLE_KEY")
    url = f"{base}/rest/v1/{table}{path}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase {exc.code}: {detail}") from exc


def save_document(law: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    if not configured() or not rows:
        return
    document_id = str(rows[0]["document_id"])
    encoded_id = urllib.parse.quote(document_id, safe="")
    _request("DELETE", f"?document_id=eq.{encoded_id}")
    file_name = law.get("file_name", law.get("source_path", ""))
    prepared = []
    for row in rows:
        item = {key: row.get(key) for key in FIELDS.split(",")}
        item["file_name"] = file_name
        prepared.append(item)
    for start in range(0, len(prepared), 100):
        batch = prepared[start:start + 100]
        _request("POST", "", batch)


def load_rows() -> list[dict[str, Any]]:
    if not configured():
        return []
    all_rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        query = "?select=" + urllib.parse.quote(FIELDS, safe=",")
        query += f"&order=chunk_id.asc&offset={offset}&limit=1000"
        batch = _request("GET", query) or []
        all_rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += len(batch)
    return all_rows


def load_users() -> list[dict[str, Any]]:
    if not configured():
        return []
    query = "?select=username,password_hash,role&order=username.asc"
    return _request("GET", query, table=USERS_TABLE) or []


def create_user(username: str, password_hash: str, role: str = "user") -> bool:
    if not configured():
        return False
    payload = {"username": username, "password_hash": password_hash, "role": role}
    try:
        _request("POST", "", [payload], table=USERS_TABLE)
        return True
    except RuntimeError:
        return False


def summarize_laws(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        grouped.setdefault(str(row.get("document_id", "")), []).append(row)
    laws = []
    for document_id, items in grouped.items():
        first = items[0]
        laws.append({
            "file_name": first.get("file_name", ""),
            "title": first.get("title", ""),
            "law_number": first.get("law_number"),
            "law_year": first.get("law_year"),
            "status": first.get("status"),
            "effective_from": first.get("effective_from", ""),
            "effective_to": first.get("effective_to", ""),
            "article_count": len({str(x.get("article_number")) for x in items}),
            "document_id": document_id,
            "extraction": {"method": "supabase", "needs_review": False},
        })
    return laws
