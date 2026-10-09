"""
Configuration management for the AI Knowledge Assistant.
Loads environment variables with robust defaults for local-first execution.
"""
from pathlib import Path
import os
from dataclasses import dataclass, field

# Base workspace path
BASE_DIR = Path(__file__).resolve().parent.parent

# Attempt loading .env file
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


@dataclass
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))

    # LLM Settings
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

    # Embeddings & Vector Store
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    device: str = os.getenv("DEVICE", "cpu")
    vector_store_dir: Path = BASE_DIR / os.getenv("VECTOR_STORE_DIR", "data/vector_store")
    chroma_collection_name: str = os.getenv("CHROMA_COLLECTION_NAME", "knowledge_assistant")

    # Ingestion & Data Paths
    raw_data_dir: Path = BASE_DIR / os.getenv("RAW_DATA_DIR", "data/raw")
    processed_data_dir: Path = BASE_DIR / os.getenv("PROCESSED_DATA_DIR", "data/processed")
    chunks_file: Path = processed_data_dir / "chunks.json"
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "600"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    # Security & Compliance
    api_secret_key: str = os.getenv("API_SECRET_KEY", "dev_secret_key_change_in_production")
    require_auth: bool = os.getenv("REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")
    enable_pii_redaction: bool = os.getenv("ENABLE_PII_REDACTION", "true").lower() in ("true", "1", "yes")

    # Logging & Evaluation
    logs_dir: Path = BASE_DIR / os.getenv("LOGS_DIR", "logs")
    eval_results_dir: Path = BASE_DIR / os.getenv("EVAL_RESULTS_DIR", "eval/reports")

    def __post_init__(self):
        # Ensure directories exist
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.eval_results_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
