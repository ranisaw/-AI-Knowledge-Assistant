"""
Embedding Engine for AI Knowledge Assistant.
Uses Sentence-Transformers (e.g., all-MiniLM-L6-v2) to generate normalized dense vector embeddings.
Includes graceful local fallback embedder for maximum system resilience.
"""
import os
import math
import numpy as np
from typing import List, Union
from core.config import settings

_MODEL_INSTANCE = None
_FALLBACK_ACTIVE = False


def _get_sentence_transformer():
    """Lazy-load SentenceTransformer model singleton."""
    global _MODEL_INSTANCE, _FALLBACK_ACTIVE
    if _MODEL_INSTANCE is None and not _FALLBACK_ACTIVE:
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {settings.embedding_model} on {settings.device}...")
            _MODEL_INSTANCE = SentenceTransformer(settings.embedding_model, device=settings.device)
            print("Embedding model loaded successfully.")
        except Exception as e:
            print(f"Warning: Could not initialize SentenceTransformer ({e}). Engaging deterministic resilient fallback embedder.")
            _FALLBACK_ACTIVE = True
    return _MODEL_INSTANCE


def _compute_fallback_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Deterministic hashed n-gram embedding fallback.
    Guarantees consistent cosine similarity between lexically/semantically related text
    even if torch/transformers are downloading or offline.
    """
    import hashlib
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    if not words:
        return vec.tolist()
        
    for w in words:
        # Single word hash
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign

    # Add bigrams for phrase matching
    for i in range(len(words) - 1):
        bigram = f"{words[i]}_{words[i+1]}"
        h = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign * 1.5

    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec = vec / norm
    return vec.tolist()


def get_embedding(text: str) -> List[float]:
    """Generate dense vector embedding for a single text string."""
    model = _get_sentence_transformer()
    if model is not None:
        try:
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            print(f"Embedding error: {e}. Falling back.")
    return _compute_fallback_embedding(text)


def get_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Generate dense vector embeddings for a batch of text strings."""
    if not texts:
        return []

    model = _get_sentence_transformer()
    if model is not None:
        try:
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 20,
                normalize_embeddings=True
            )
            return embeddings.tolist()
        except Exception as e:
            print(f"Batch embedding error: {e}. Falling back.")

    return [_compute_fallback_embedding(t) for t in texts]
