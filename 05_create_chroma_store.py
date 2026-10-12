from importlib import import_module
from pathlib import Path

import chromadb
from chromadb.config import Settings

vectors = import_module("04_vector_representation")

# ==============================================================================
# Configuration
# ==============================================================================
MODEL_NAME = "all-MiniLM-L6-v2"

try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path.cwd()

DB_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "legal_docs"


def create_vector_store():

    if len(vectors.chunks) != len(vectors.chunk_embeddings):
        raise ValueError(
            "Number of chunks and embeddings must match."
        )

    client = chromadb.PersistentClient(
        path=str(DB_PATH),
        settings=Settings(anonymized_telemetry=False),
    )

    collection = client.get_or_create_collection(COLLECTION_NAME)

    try:

        collection.upsert(

            ids=[
                chunk["chunk_id"]
                for chunk in vectors.chunks
            ],

            documents=[
                chunk["chunk_text"]
                for chunk in vectors.chunks
            ],

            metadatas=[
                {
                    "document_id": chunk["document_id"],
                    "title": chunk["title"],
                    "is_current": str(chunk["is_current"]),
                    "chunk_number": index,
                    "embedding_model": MODEL_NAME,
                }
                for index, chunk in enumerate(vectors.chunks)
            ],

            embeddings=vectors.chunk_embeddings.tolist(),
        )

    except Exception as e:
        raise RuntimeError(
            f"Failed to create vector store: {e}"
        )

    return collection


if __name__ == "__main__":
    create_vector_store()
    print(f"Chroma vector store created at: {DB_PATH}")
