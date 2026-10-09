"""
Pydantic data models and API schemas for the AI Knowledge Assistant.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CitationModel(BaseModel):
    doc_number: int
    chunk_id: str
    source: str
    title: str
    score: float
    doc_type: str
    excerpt: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Natural language question")
    top_k: int = Field(default=4, ge=1, le=10, description="Number of top chunks to retrieve")
    filter_type: Optional[str] = Field(default=None, description="Optional document type filter")


class AskResponse(BaseModel):
    query_id: str
    question: str
    answer: str
    citations: List[CitationModel]
    latency_ms: float
    model: str
    retrieved_count: int


class ReindexResponse(BaseModel):
    status: str
    files_processed: int
    chunks_created: int
    vector_count: int
    message: str


class ExportRequest(BaseModel):
    question: str
    answer: str
    citations: List[CitationModel]
    query_id: Optional[str] = "export"


class MetricSummary(BaseModel):
    total_queries: int
    average_latency_ms: float
    p95_latency_ms: float
    recent_queries: List[Dict[str, Any]]
