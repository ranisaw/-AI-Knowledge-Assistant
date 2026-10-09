"""
Retrieval-Augmented Generation (RAG) Orchestrator.
Coordinates:
1. Query preprocessing & PII scrubbing
2. Vector similarity search & context retrieval
3. Grounded prompt assembly with citation anchors
4. LLM response generation & citation mapping
5. Structured audit logging (latency, tokens, chunk IDs)
"""
import uuid
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.config import settings
from core.security import redact_pii
from core.vector_store import vector_store
from core.prompt_builder import build_rag_prompt
from core.llm_client import llm_client


class RAGPipeline:
    """Core RAG pipeline coordinating retrieval, LLM reasoning, and citation synthesis."""

    def __init__(self):
        self.audit_log_file = settings.logs_dir / "audit.jsonl"
        self.audit_log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log_audit_event(self, event: Dict[str, Any]):
        """Append query audit event to JSONL log."""
        try:
            with open(self.audit_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Warning: Audit logging failed: {e}")

    def query(
        self,
        question: str,
        top_k: int = 4,
        filter_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute end-to-end RAG query flow.
        """
        start_time = time.time()
        query_id = f"qry_{uuid.uuid4().hex[:10]}"

        # Step 1: PII Sanitization
        sanitized_question, pii_counts = redact_pii(question)

        # Step 2: Vector Retrieval
        retrieved_chunks = vector_store.similarity_search(
            query=sanitized_question,
            top_k=top_k,
            filter_meta=filter_meta
        )

        # Step 3: Prompt Construction
        prompt = build_rag_prompt(sanitized_question, retrieved_chunks)

        # Step 4: LLM Generation
        llm_response = llm_client.generate(prompt, context_chunks=retrieved_chunks)
        answer = llm_response.get("text", "")
        model_name = llm_response.get("model", "unknown")

        total_latency = round((time.time() - start_time) * 1000, 2)

        # Step 5: Format Citations
        citations = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            meta = chunk.get("metadata", {})
            citations.append({
                "doc_number": i,
                "chunk_id": chunk.get("id"),
                "source": meta.get("source", "unknown"),
                "title": meta.get("title", "Untitled Document"),
                "score": chunk.get("score", 0.0),
                "doc_type": meta.get("doc_type", "document"),
                "excerpt": chunk.get("text", "")[:240].strip() + "..."
            })

        # Step 6: Audit Record
        audit_entry = {
            "query_id": query_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "question": sanitized_question,
            "pii_redacted": pii_counts,
            "retrieved_chunk_ids": [c["chunk_id"] for c in citations],
            "top_similarity": citations[0]["score"] if citations else 0.0,
            "latency_ms": total_latency,
            "model": model_name,
            "citations_count": len(citations)
        }
        self._log_audit_event(audit_entry)

        return {
            "query_id": query_id,
            "question": sanitized_question,
            "answer": answer,
            "citations": citations,
            "latency_ms": total_latency,
            "model": model_name,
            "retrieved_count": len(retrieved_chunks)
        }


rag_pipeline = RAGPipeline()


if __name__ == "__main__":
    result = rag_pipeline.query("What is FloCard?")
    print(f"\nQuestion: {result['question']}")
    print(f"Answer: {result['answer']}")
    print(f"Latency: {result['latency_ms']} ms | Model: {result['model']}")
    print("\nCitations:")
    for c in result["citations"]:
        print(f"- [Doc {c['doc_number']}] {c['title']} ({c['source']}) [Score: {c['score']}]")
