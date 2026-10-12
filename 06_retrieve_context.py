from importlib import import_module
from typing import Tuple, List, Dict, Any


hybrid_search = import_module(
    "04_vector_representation"
).hybrid_search



def build_context(
    question: str,
    k: int = 10,
    max_sources: int = 3,
) -> Tuple[str, List[Dict[str, Any]]]:

    """
    Build an LLM context using hybrid retrieval.

    Steps:
    1. Retrieve Top-K candidate chunks.
    2. Prioritize CURRENT documents.
    3. Remove duplicate documents.
    4. Return top unique sources with similarity metrics.
    """

    # ==========================================================
    # Retrieve candidates
    # ==========================================================

    rows = hybrid_search(
        question,
        k=k
    )


    if not rows:
        return "", []



    # ==========================================================
    # Sort Results
    # Current documents first
    # Higher similarity score first
    # ==========================================================

    def sort_key(row):

        is_current = row.get(
            "is_current",
            True
        )

        if isinstance(is_current, str):
            is_current = (
                is_current.lower()
                ==
                "true"
            )


        return (
            bool(is_current),

            row.get(
                "similarity_score",
                0.0
            )
        )



    rows = sorted(
        rows,
        key=sort_key,
        reverse=True
    )



    # ==========================================================
    # Remove Duplicate Documents
    # ==========================================================

    selected = []

    seen_documents = set()


    for row in rows:


        doc_id = row.get(
            "document_id",
            row.get(
                "doc_id",
                "unknown"
            )
        )


        if doc_id in seen_documents:
            continue



        selected.append(row)

        seen_documents.add(doc_id)



        if len(selected) >= max_sources:
            break



    if not selected:
        return "", []



    # ==========================================================
    # Build Context For LLM
    # ==========================================================

    context_blocks = []


    for source_number, row in enumerate(
        selected,
        start=1
    ):

        is_current = row.get(
            "is_current",
            True
        )


        if isinstance(is_current, str):
            is_current = (
                is_current.lower()
                ==
                "true"
            )


        status = (
            "CURRENT"
            if is_current
            else
            "OUTDATED"
        )


        context_blocks.append(
            f"""
[Source {source_number}]
Document:
{row.get('title','Unknown')}

Status:
{status}

Similarity Score:
{row.get('similarity_score',0)}%

Hybrid Score:
{row.get('hybrid_score',0)}%

Content:
{row.get('chunk_text','')}
"""
        )



    context = "\n\n".join(
        context_blocks
    )


    return context.strip(), selected
