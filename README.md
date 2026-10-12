# LexGo RAG v2

Clean, independent, document-first RAG scaffold. No old English sample corpus is included.

## Windows setup
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

This is a scaffold, not yet a complete working RAG system. The TODO services must be implemented and tested before using it for real answers. Never commit `.env`, uploaded documents, or local vector database files.

## Intended flow
Upload → text extraction/OCR → document classification and metadata extraction → structure-aware chunking → embeddings/indexing → hybrid retrieval → answer with source citations.
