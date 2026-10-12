import os
from importlib import import_module
from typing import Tuple, List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI


# ==============================================================================
# Imports
# ==============================================================================
build_context = import_module(
    "06_retrieve_context"
).build_context


# ==============================================================================
# Configuration
# ==============================================================================
load_dotenv()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "meta-llama/llama-3.3-70b-instruct:free",
)


# ==============================================================================
# System Prompt
# ==============================================================================
SYSTEM_PROMPT = """
You are a professional legal policy assistant.

Rules:

- Answer ONLY using the provided context.
- Never use external knowledge.
- If the answer is not available in the retrieved documents, reply:

"I could not find relevant information in the provided policy documents."

- Prefer CURRENT documents over OUTDATED documents.
- Mention if a source is outdated.
- Always cite sources using [Source X].
- Do not make assumptions.
- Keep responses concise, professional, and factual.
"""


# ==============================================================================
# Prompt Builder
# ==============================================================================
def build_prompt(
    question: str,
    context: str
) -> str:

    return f"""
Question:

{question}


Retrieved Policy Context:

{context}
"""


# ==============================================================================
# OpenRouter Request
# ==============================================================================
def ask_openrouter(
    prompt: str
) -> str:


    if not OPENROUTER_API_KEY:

        return (
            "Error: Missing OPENROUTER_API_KEY environment variable."
        )


    client = OpenAI(

        base_url="https://openrouter.ai/api/v1",

        api_key=OPENROUTER_API_KEY,

        timeout=60,

        default_headers={

            "HTTP-Referer":
                "https://localhost",

            "X-Title":
                "LexGO Legal RAG Assistant",
        },
    )


    try:

        response = client.chat.completions.create(

            model=OPENROUTER_MODEL,


            messages=[

                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },


                {
                    "role": "user",
                    "content": prompt,
                }

            ],


            temperature=0,


            max_tokens=700,

        )


        if (
            response
            and response.choices
            and len(response.choices) > 0
        ):

            return (
                response
                .choices[0]
                .message
                .content
                or "Empty response from model."
            )


        return "OpenRouter returned an empty response."


    except Exception as error:

        status_code = getattr(
            error,
            "status_code",
            "unknown"
        )

        message = getattr(
            error,
            "message",
            str(error)
        )


        return (
            f"OpenRouter Error ({status_code}): {message}"
        )



# ==============================================================================
# Main RAG Pipeline
# ==============================================================================
def answer_question(
    question: str,
) -> Tuple[str, List[Dict[str, Any]]]:


    if not question.strip():

        return (
            "Please enter a valid question.",
            []
        )


    # Retrieve context
    context, sources = build_context(
        question
    )


    # No retrieval result
    if not sources:

        return (

            "I could not find relevant information in the provided policy documents.",

            []

        )


    # Build prompt
    prompt = build_prompt(

        question,

        context

    )


    # Generate answer
    answer = ask_openrouter(
        prompt
    )


    # ==========================================================================
    # Add Retrieval Analytics For Dashboard
    # ==========================================================================

    for source in sources:


        source["retrieval_metrics"] = {

            "semantic_similarity":
                source.get(
                    "similarity_score",
                    0
                ),


            "hybrid_score":
                source.get(
                    "hybrid_score",
                    0
                ),


            "bm25_score":
                source.get(
                    "bm25_score",
                    0
                )

        }


    return answer, sources
