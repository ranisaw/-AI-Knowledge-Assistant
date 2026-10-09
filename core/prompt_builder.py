"""
Prompt Engineering and Context Formatting for RAG.
Constructs grounded, system-guided prompts with explicit citation anchors.
"""
from typing import List, Dict, Any

SYSTEM_PROMPT = """You are the AI Knowledge Assistant for internal engineering onboarding.
Your mission is to provide accurate, concise, and verifiable answers to questions based SOLELY on the internal documentation provided below.

Strict Guardrails:
1. Grounding: Every factual statement must be directly supported by the provided Context.
2. Citations: Cite your sources using bracketed references matching the document numbers, e.g. [Doc 1], [Doc 2].
3. Unanswered Queries: If the provided context does not contain enough information to answer the question, state clearly: "I cannot find sufficient information in the provided internal documentation to answer this question." Do NOT hallucinate, guess, or extrapolate.
4. Professional Demeanor: Be direct, structured, and helpful to new engineers.
"""


def build_rag_prompt(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """
    Construct the complete augmented prompt with formatted context and citations instructions.
    """
    if not context_chunks:
        context_block = "No relevant internal documentation was found."
    else:
        doc_entries = []
        for i, chunk in enumerate(context_chunks, 1):
            meta = chunk.get("metadata", {})
            title = meta.get("title", "Document")
            source = meta.get("source", "Unknown Source")
            chunk_id = chunk.get("id", f"chk_{i}")
            text = chunk.get("text", "").strip()

            entry = (
                f"--- [Doc {i}] Source: {source} | Title: {title} | Chunk ID: {chunk_id} ---\n"
                f"{text}"
            )
            doc_entries.append(entry)
        context_block = "\n\n".join(doc_entries)

    prompt = f"""{SYSTEM_PROMPT}

=== INTERNAL CONTEXT BEGIN ===
{context_block}
=== INTERNAL CONTEXT END ===

Engineer's Question: {question}

Grounded Answer (including [Doc X] citations):"""
    return prompt
