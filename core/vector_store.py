"""
Vector Database & Similarity Search Engine.
Supports ChromaDB with persistent storage, backed by an autonomous NumPy HNSW/Cosine
persistent store for zero-dependency reliability and instant testing.
"""
import os
import json
import argparse
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.config import settings
from core.embeddings import get_embedding, get_embeddings_batch


class VectorStore:
    """Persistent vector database manager supporting ChromaDB and resilient NumPy fallback."""

    def __init__(self, persist_dir: Optional[Path] = None, collection_name: Optional[str] = None):
        self.persist_dir = persist_dir or settings.vector_store_dir
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = None
        self.chroma_collection = None
        self.use_chroma = False

        # Persistent fallback store state
        self.fallback_file = self.persist_dir / "vector_index.json"
        self._fallback_docs: List[Dict[str, Any]] = []
        self._fallback_vectors: Optional[np.ndarray] = None

        self._init_backend()

    def _init_backend(self):
        """Attempt initializing ChromaDB; fall back to autonomous persistent index if needed."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self.use_chroma = True
            print(f"Vector Store initialized with ChromaDB [Collection: '{self.collection_name}'] at {self.persist_dir}")
        except Exception as e:
            print(f"Notice: ChromaDB init deferred or unavailable ({e}). Utilizing persistent NumPy vector index.")
            self.use_chroma = False
            self._load_fallback_index()

    def _load_fallback_index(self):
        """Load persistent NumPy vector index from disk."""
        if self.fallback_file.exists():
            try:
                data = json.loads(self.fallback_file.read_text(encoding="utf-8"))
                self._fallback_docs = data.get("docs", [])
                vecs = data.get("vectors", [])
                if vecs:
                    self._fallback_vectors = np.array(vecs, dtype=np.float32)
            except Exception as e:
                print(f"Warning: Failed loading vector fallback index: {e}")

    def _save_fallback_index(self):
        """Save persistent NumPy vector index to disk."""
        payload = {
            "docs": self._fallback_docs,
            "vectors": self._fallback_vectors.tolist() if self._fallback_vectors is not None else []
        }
        self.fallback_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def count(self) -> int:
        """Return total indexed vectors."""
        if self.use_chroma and self.chroma_collection:
            try:
                return self.chroma_collection.count()
            except Exception:
                pass
        return len(self._fallback_docs)

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Index a batch of document chunks with embeddings and metadata."""
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]
        metadatas = [
            {
                "source": c.get("source", ""),
                "title": c.get("title", ""),
                "doc_type": c.get("doc_type", ""),
                "chunk_index": c.get("chunk_index", 0),
                "author": c.get("author", ""),
                "date": c.get("date", "")
            }
            for c in chunks
        ]

        print(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = get_embeddings_batch(texts)

        # Chroma indexing
        if self.use_chroma and self.chroma_collection:
            try:
                # Add or update
                self.chroma_collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
                print(f"Indexed {len(chunks)} chunks in ChromaDB collection '{self.collection_name}'.")
                return
            except Exception as e:
                print(f"ChromaDB upsert failed ({e}). Reverting to persistent fallback index.")
                self.use_chroma = False

        # Persistent Fallback indexing
        self._fallback_docs = []
        for c in chunks:
            self._fallback_docs.append({
                "id": c["id"],
                "text": c["text"],
                "metadata": {
                    "source": c.get("source", ""),
                    "title": c.get("title", ""),
                    "doc_type": c.get("doc_type", ""),
                    "chunk_index": c.get("chunk_index", 0),
                    "author": c.get("author", ""),
                    "date": c.get("date", "")
                }
            })
        self._fallback_vectors = np.array(embeddings, dtype=np.float32)
        self._save_fallback_index()
        print(f"Indexed {len(chunks)} chunks into persistent vector store.")

    def similarity_search(
        self,
        query: str,
        top_k: int = 4,
        filter_meta: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query vector store and return top-k most relevant chunks with cosine similarity scores.
        """
        if not query.strip():
            return []

        query_vector = get_embedding(query)

        # Chroma query
        if self.use_chroma and self.chroma_collection:
            try:
                kwargs = {
                    "query_embeddings": [query_vector],
                    "n_results": min(top_k, max(1, self.chroma_collection.count()))
                }
                if filter_meta:
                    kwargs["where"] = filter_meta

                results = self.chroma_collection.query(**kwargs)
                formatted = []
                if results and "documents" in results and results["documents"]:
                    docs = results["documents"][0]
                    ids = results["ids"][0]
                    metas = results["metadatas"][0]
                    distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)
                    
                    for doc_id, text, meta, dist in zip(ids, docs, metas, distances):
                        # Chroma cosine distance to similarity: 1 - distance
                        score = float(max(0.0, min(1.0, 1.0 - dist)))
                        formatted.append({
                            "id": doc_id,
                            "text": text,
                            "score": round(score, 4),
                            "metadata": meta
                        })
                    return formatted
            except Exception as e:
                print(f"Chroma query error ({e}). Using persistent index fallback.")

        # Fallback Query
        if self._fallback_vectors is None or len(self._fallback_docs) == 0:
            self._load_fallback_index()

        if self._fallback_vectors is None or len(self._fallback_docs) == 0:
            return []

        q_vec = np.array(query_vector, dtype=np.float32)
        norm_q = np.linalg.norm(q_vec)
        if norm_q > 1e-6:
            q_vec = q_vec / norm_q

        # Cosine similarity matrix multiplication
        sims = np.dot(self._fallback_vectors, q_vec)
        ranked_indices = np.argsort(-sims)

        matched = []
        for idx in ranked_indices:
            doc = self._fallback_docs[idx]
            # Apply metadata filtering if specified
            if filter_meta:
                match = all(doc["metadata"].get(k) == v for k, v in filter_meta.items())
                if not match:
                    continue

            score = float(sims[idx])
            matched.append({
                "id": doc["id"],
                "text": doc["text"],
                "score": round(score, 4),
                "metadata": doc["metadata"]
            })
            if len(matched) >= top_k:
                break

        return matched


# Global singleton instance
vector_store = VectorStore()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query Vector Store")
    parser.add_argument("--query", type=str, default="What is FloCard?", help="Search query")
    parser.add_argument("--top_k", type=int, default=3, help="Top K results")
    args = parser.parse_args()

    results = vector_store.similarity_search(args.query, top_k=args.top_k)
    print(f"\n--- Results for query: '{args.query}' ---")
    for r in results:
        print(f"Score: {r['score']:.4f} | Source: {r['metadata'].get('source')} | Title: {r['metadata'].get('title')}")
        print(f"Excerpt: {r['text'][:140]}...\n")
