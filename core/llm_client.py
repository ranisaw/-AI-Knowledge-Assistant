"""
LLM Client Interface & Resilient Inference Engine.
Connects to Ollama (local daemon) with streaming/batch completions, and provides
an intelligent local extractive/synthesis fallback when Ollama is offline.
"""
import json
import time
import re
from typing import Generator, Dict, Any, List, Optional
import requests
from core.config import settings


class LLMClient:
    """Unified LLM client with Ollama integration and local offline fallback."""

    def __init__(
        self,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = provider or settings.llm_provider
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    def is_ollama_available(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            return res.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, context_chunks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate grounded completion for given prompt.
        Returns:
            { "text": str, "model": str, "latency_ms": float, "fallback_used": bool }
        """
        start_time = time.time()

        if self.provider.lower() == "ollama" and self.is_ollama_available():
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                }
                res = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    answer = data.get("response", "").strip()
                    latency = round((time.time() - start_time) * 1000, 2)
                    return {
                        "text": answer,
                        "model": f"ollama:{self.model}",
                        "latency_ms": latency,
                        "fallback_used": False
                    }
            except Exception as e:
                print(f"Ollama inference failed ({e}). Shifting to resilient local synthesizer.")

        # Resilient Local Synthesizer Fallback
        answer = self._synthesize_local_answer(prompt, context_chunks or [])
        latency = round((time.time() - start_time) * 1000, 2)
        return {
            "text": answer,
            "model": "local-rule-synthesizer",
            "latency_ms": latency,
            "fallback_used": True
        }

    def generate_stream(
        self,
        prompt: str,
        context_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> Generator[str, None, None]:
        """
        Stream response tokens via generator.
        """
        if self.provider.lower() == "ollama" and self.is_ollama_available():
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": 0.1}
                }
                with requests.post(f"{self.base_url}/api/generate", json=payload, stream=True, timeout=60) as r:
                    for line in r.iter_lines():
                        if line:
                            data = json.loads(line.decode("utf-8"))
                            token = data.get("response", "")
                            if token:
                                yield token
                            if data.get("done", False):
                                return
                return
            except Exception:
                pass

        # Streaming simulation for local synthesizer
        full_answer = self._synthesize_local_answer(prompt, context_chunks or [])
        words = full_answer.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.015)

    def _synthesize_local_answer(self, prompt: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        Intelligent local synthesis using lexical extraction and grounded summarization.
        Extracts salient sentences from retrieved chunks and links citations.
        """
        if not context_chunks:
            return "I cannot find sufficient information in the provided internal documentation to answer this question."

        # Extract question from prompt
        q_match = re.search(r"Engineer's Question:\s*(.*)", prompt)
        question = q_match.group(1).strip() if q_match else prompt
        q_terms = set(re.findall(r'\w{3,}', question.lower()))

        findings = []
        for i, chunk in enumerate(context_chunks, 1):
            text = chunk.get("text", "")
            meta = chunk.get("metadata", {})
            title = meta.get("title", f"Doc {i}")
            
            # Score sentences in chunk against query terms
            sentences = re.split(r'(?<=[.!?])\s+', text)
            scored = []
            for s in sentences:
                s_clean = s.strip()
                if len(s_clean) < 15:
                    continue
                s_words = set(re.findall(r'\w{3,}', s_clean.lower()))
                overlap = len(s_words.intersection(q_terms))
                if overlap > 0:
                    scored.append((overlap, s_clean))

            if scored:
                scored.sort(key=lambda x: x[0], reverse=True)
                top_s = scored[0][1]
                findings.append(f"{top_s} [Doc {i}]")
            elif len(text.strip()) > 30:
                # Fallback to leading summary sentence
                first_s = sentences[0].strip() if sentences else text[:120]
                findings.append(f"{first_s} [Doc {i}]")

        if not findings:
            return "Based on internal documentation, no direct matches were found for the query parameters."

        combined = " ".join(findings[:3])
        return f"Based on internal documentation:\n\n{combined}\n\nFor additional details, refer to the cited references."


llm_client = LLMClient()
