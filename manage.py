"""
CLI Management & Orchestration Tool for AI Knowledge Assistant.
Provides one-command operations for:
- Synthetic data generation (synth)
- Document ingestion & chunking (ingest)
- Vector indexing (index)
- RAG question answering (ask)
- Evaluation & benchmarking (eval)
- Serving the FastAPI server & web UI (serve)
- Complete end-to-end demo runner (all)
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import settings
from core.synth_data import generate_synthetic_documents
from core.ingest import ingest_documents
from core.vector_store import vector_store
from core.rag_pipeline import rag_pipeline
from eval.eval_suite import run_eval_suite


def cmd_synth():
    print("Generating synthetic enterprise documentation...")
    generate_synthetic_documents()


def cmd_ingest():
    print("Ingesting raw documentation into normalized chunks...")
    ingest_documents()


def cmd_index():
    print("Loading chunks and building vector store index...")
    import json
    if not settings.chunks_file.exists():
        print(f"Chunks file not found at {settings.chunks_file}. Ingesting documents first...")
        ingest_documents()
    chunks = json.loads(settings.chunks_file.read_text(encoding="utf-8"))
    vector_store.add_chunks(chunks)
    print(f"Vector store ready with {vector_store.count()} indexed chunks.")


def cmd_ask(query: str, top_k: int = 4):
    print(f"\nInquiring Knowledge Assistant: '{query}'\n")
    res = rag_pipeline.query(query, top_k=top_k)
    print("==================================================")
    print("GROUNDED RESPONSE:")
    print("==================================================")
    print(res["answer"])
    print("\n--------------------------------------------------")
    print(f"CITATIONS ({len(res['citations'])} sources cited):")
    print("--------------------------------------------------")
    for c in res["citations"]:
        print(f"- [Doc {c['doc_number']}] {c['title']} ({c['source']}) [Sim: {c['score']:.4f}]")
        print(f"  Excerpt: {c['excerpt']}\n")
    print(f"Telemetry: Latency={res['latency_ms']} ms | Model={res['model']} | QueryID={res['query_id']}")


def cmd_eval():
    print("Running system evaluation benchmark suite...")
    run_eval_suite()


def cmd_serve():
    print(f"Starting AI Knowledge Assistant API & Web Interface on http://{settings.host}:{settings.port}...")
    import uvicorn
    uvicorn.run("api.main:app", host=settings.host, port=settings.port, reload=True)


def cmd_all():
    print("================================================================")
    print("🚀 Running Complete End-to-End AI Knowledge Assistant Pipeline")
    print("================================================================\n")
    
    print("\n[Phase 1] Synthetic Data Generation...")
    generate_synthetic_documents()

    print("\n[Phase 2] Document Ingestion & Chunking...")
    chunks = ingest_documents()

    print("\n[Phase 3] Vector Indexing & Embedding...")
    vector_store.add_chunks(chunks)

    print("\n[Phase 4] Testing RAG Query ('What is FloCard?')...")
    cmd_ask("What is FloCard?", top_k=3)

    print("\n[Phase 5] Running Automated Evaluation Benchmark...")
    run_eval_suite(top_k=3)

    print("\n✅ End-to-End Pipeline Verification Complete!")


def main():
    parser = argparse.ArgumentParser(description="AI Knowledge Assistant Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    subparsers.add_parser("synth", help="Generate mock enterprise docs")
    subparsers.add_parser("ingest", help="Ingest and chunk raw documents")
    subparsers.add_parser("index", help="Index chunks into vector store")

    ask_parser = subparsers.add_parser("ask", help="Query the RAG assistant")
    ask_parser.add_argument("--query", "-q", type=str, default="What is FloCard?", help="Question text")
    ask_parser.add_argument("--top_k", "-k", type=int, default=4, help="Top K context chunks")

    subparsers.add_parser("eval", help="Run benchmark evaluation")
    subparsers.add_parser("serve", help="Launch FastAPI server & UI")
    subparsers.add_parser("all", help="Run full pipeline end-to-end")

    args = parser.parse_args()

    if args.command == "synth":
        cmd_synth()
    elif args.command == "ingest":
        cmd_ingest()
    elif args.command == "index":
        cmd_index()
    elif args.command == "ask":
        cmd_ask(args.query, args.top_k)
    elif args.command == "eval":
        cmd_eval()
    elif args.command == "serve":
        cmd_serve()
    elif args.command == "all":
        cmd_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
