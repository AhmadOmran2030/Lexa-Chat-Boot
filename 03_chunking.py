import os
import re
from typing import Dict, List, Any
from importlib import import_module

# ==============================================================================
# 1. SAFE IMPORTS (استدعاء آمن للموديولات)
# ==============================================================================
try:
    doc_module = import_module("01_documents")
    base_documents = getattr(doc_module, "documents", [])
except Exception:
    base_documents = []

try:
    prep_module = import_module("02_preprocessing")
    preprocess_text = getattr(prep_module, "preprocess_text", lambda x: x.lower())
except Exception:
    def preprocess_text(text: str) -> str:
        return text.lower()

DATA_DIR = "./data"

# ==============================================================================
# 2. HELPER TO LOAD USER UPLOADED FILES FROM ./data
# ==============================================================================
def load_uploaded_documents() -> List[Dict[str, Any]]:
    """قراءة كل الملفات المرفوعة ديناميكياً من المجلد الدائم ./data"""
    uploaded_docs = []
    if not os.path.exists(DATA_DIR):
        return uploaded_docs

    for file_name in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, file_name)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_name)[1].lower()
            text = ""
            try:
                if ext == ".pdf":
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                elif ext in [".docx", ".doc"]:
                    import docx
                    doc = docx.Document(file_path)
                    text = "\n".join([p.text for p in doc.paragraphs if p.text])
            except Exception as e:
                print(f"Error reading uploaded file {file_name}: {e}")
                continue

            if text.strip():
                clean_name = os.path.splitext(file_name)[0]
                doc_id = f"doc_{clean_name.lower().replace(' ', '_')}"
                uploaded_docs.append({
                    "id": doc_id,
                    "title": clean_name.replace("_", " ").title(),
                    "is_current": True,
                    "text": text
                })
    return uploaded_docs

# ==============================================================================
# 3. PARAGRAPH CHUNKING LOGIC
# ==============================================================================
def chunk_by_paragraphs(text: str, max_words: int = 300, overlap_paragraphs: int = 1) -> List[str]:
    """
    Splits text by natural paragraphs while maintaining context integrity.
    If a paragraph is too large, it gracefully splits without breaking legal meaning.
    """
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current_chunk = []
    current_word_count = 0

    for para in paragraphs:
        para_words = len(para.split())
        
        if para_words > max_words:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                sent_words = len(sent.split())
                if current_word_count + sent_words > max_words and current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = current_chunk[-overlap_paragraphs:] if len(current_chunk) >= overlap_paragraphs else []
                    current_word_count = sum(len(p.split()) for p in current_chunk)
                
                current_chunk.append(sent)
                current_word_count += sent_words
        else:
            if current_word_count + para_words > max_words and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = current_chunk[-overlap_paragraphs:] if len(current_chunk) >= overlap_paragraphs else []
                current_word_count = sum(len(p.split()) for p in current_chunk)

            current_chunk.append(para)
            current_word_count += para_words

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks

# ==============================================================================
# 4. BUILD CHUNKS FUNCTION
# ==============================================================================
def build_chunks() -> List[Dict[str, Any]]:
    """Builds preprocessed search chunk dicts from base & user-uploaded documents."""
    rows = []

    # دمج المستندات الأساسية من 01_documents مع الملفات المرفوعة حديثاً
    all_documents = base_documents + load_uploaded_documents()

    for document in all_documents:
        doc_id = document.get("id", "doc_unknown")
        doc_title = document.get("title", "Untitled Document")
        is_current = document.get("is_current", True)
        doc_text = document.get("text", "")

        if not doc_text:
            continue

        text_chunks = chunk_by_paragraphs(doc_text, max_words=300, overlap_paragraphs=1)
        
        for chunk_number, chunk in enumerate(text_chunks):
            search_input = f"{doc_title} {chunk}"
            
            rows.append(
                {
                    "chunk_id": f"{doc_id}_{chunk_number}",
                    "document_id": doc_id,
                    "doc_id": doc_id,
                    "title": doc_title,
                    "is_current": is_current,
                    "chunk_text": chunk,
                    "search_text": preprocess_text(search_input),
                }
            )

    return rows


if __name__ == "__main__":
    generated_chunks = build_chunks()
    print(f"Total Chunks Generated: {len(generated_chunks)}")
