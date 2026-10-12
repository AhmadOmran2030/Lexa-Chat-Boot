from importlib import import_module

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


# ==============================================================================
# Imports
# ==============================================================================

preprocessing = import_module("02_preprocessing")
chunks = import_module("03_chunking").build_chunks()


# ==============================================================================
# Configuration
# ==============================================================================

ALPHA = 0.6

MODEL_NAME = "all-MiniLM-L6-v2"

# Minimum semantic similarity
SIMILARITY_THRESHOLD = 0.55

# Minimum hybrid relevance
HYBRID_THRESHOLD = 0.35



# ==============================================================================
# BM25 Index
# ==============================================================================

tokenized_chunks = [
    chunk["search_text"].split()
    for chunk in chunks
]


bm25 = BM25Okapi(
    tokenized_chunks
)



# ==============================================================================
# Embedding Model
# ==============================================================================

model = SentenceTransformer(
    MODEL_NAME
)


chunk_embeddings = model.encode(
    [
        chunk["search_text"]
        for chunk in chunks
    ],
    convert_to_numpy=True,
    normalize_embeddings=True,
)



# ==============================================================================
# Helpers
# ==============================================================================

def min_max_normalize(scores: np.ndarray) -> np.ndarray:
    """
    Normalize values between 0 and 1
    """

    scores = np.asarray(
        scores,
        dtype=float
    )


    if len(scores) == 0:
        return scores


    score_min = scores.min()
    score_max = scores.max()


    if score_max == score_min:
        return np.zeros_like(scores)


    return (
        scores - score_min
    ) / (
        score_max - score_min
    )



def similarity_label(score: float) -> str:
    """
    Convert similarity score into confidence level
    """

    if score >= 80:
        return "High"

    elif score >= 60:
        return "Medium"

    else:
        return "Low"




# ==============================================================================
# Hybrid Search
# ==============================================================================

def hybrid_search(
        query: str,
        k: int = 4
) -> list[dict]:


    if not query.strip():
        return []


    if len(chunks) == 0:
        return []



    # ==========================================================
    # BM25 Sparse Retrieval
    # ==========================================================

    clean_query = preprocessing.preprocess_text(
        query
    )


    bm25_scores = bm25.get_scores(
        clean_query.split()
    )



    # ==========================================================
    # Dense Semantic Retrieval
    # ==========================================================

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )


    # cosine similarity
    embedding_scores = np.dot(
        chunk_embeddings,
        query_embedding.T
    ).flatten()



    # ==========================================================
    # Hybrid Score Calculation
    # ==========================================================

    normalized_bm25 = min_max_normalize(
        bm25_scores
    )


    normalized_embedding = min_max_normalize(
        embedding_scores
    )


    hybrid_scores = (
        (1 - ALPHA)
        *
        normalized_bm25

        +

        ALPHA
        *
        normalized_embedding
    )



    ranking = np.argsort(
        hybrid_scores
    )[::-1]



    results = []



    # ==========================================================
    # Filtering & Ranking
    # ==========================================================

    for index in ranking:


        semantic_score = float(
            embedding_scores[index]
        )


        hybrid_score = float(
            hybrid_scores[index]
        )


        bm25_score = float(
            bm25_scores[index]
        )


        similarity_percentage = round(
            semantic_score * 100,
            2
        )



        # Remove weak matches

        if (
            semantic_score < SIMILARITY_THRESHOLD
            or
            hybrid_score < HYBRID_THRESHOLD
        ):
            continue



        results.append(
            {

                **chunks[index],


                # ============================
                # Metrics For Dashboard
                # ============================

                "similarity_score":
                    similarity_percentage,


                "hybrid_score":
                    round(
                        hybrid_score * 100,
                        2
                    ),


                "bm25_score":
                    round(
                        bm25_score,
                        4
                    ),


                "confidence":
                    similarity_label(
                        similarity_percentage
                    )
            }
        )



        if len(results) >= k:
            break



    return results
