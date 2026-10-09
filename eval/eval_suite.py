"""
Evaluation and Benchmarking Suite for AI Knowledge Assistant.
Measures:
1. Recall@k (retrieval precision for known ground-truth documents)
2. Citation Coverage (ratio of retrieved chunks cited in final response)
3. Answer Grounding (lexical/semantic overlap between answer and retrieved context)
4. System Latency (ms)

Generates visual evaluation charts via Matplotlib and saves reports to eval/reports/.
"""
import time
import json
import re
from pathlib import Path
from typing import List, Dict, Any
from core.config import settings
from core.rag_pipeline import rag_pipeline

BENCHMARK_DATASET = [
    {
        "id": "bench_01",
        "question": "What is FloCard and what are its core capabilities?",
        "expected_source": "flocard_system_overview.md",
        "expected_keywords": ["flocard", "nfc", "identity", "telemetry"]
    },
    {
        "id": "bench_02",
        "question": "What is the code review SLA for standard and hotfix PRs?",
        "expected_source": "engineering_handbook.md",
        "expected_keywords": ["sla", "24 hours", "hotfix", "review"]
    },
    {
        "id": "bench_03",
        "question": "How do I issue an access token from the central auth service?",
        "expected_source": "auth_service_api_tutorial.md",
        "expected_keywords": ["oauth", "token", "client_credentials", "post"]
    },
    {
        "id": "bench_04",
        "question": "What is the progressive canary rollout schedule for microservice deployments?",
        "expected_source": "microservice_deployment_sop.docx",
        "expected_keywords": ["canary", "5%", "traffic", "argocd", "rollback"]
    },
    {
        "id": "bench_05",
        "question": "What is the severity definition and MTTR target for SEV-1 incidents?",
        "expected_source": "incident_response_runbook.docx",
        "expected_keywords": ["sev-1", "mttr", "incident", "commander"]
    },
    {
        "id": "bench_06",
        "question": "What hardware laptop and learning stipends are provided to engineers?",
        "expected_source": "it_setup_and_employee_perks.pdf",
        "expected_keywords": ["macbook", "stipend", "$1,500", "perks"]
    },
    {
        "id": "bench_07",
        "question": "What are the rules for zero-downtime database migrations?",
        "expected_source": "database_migration_protocol.pdf",
        "expected_keywords": ["expand", "contract", "migration", "zero-downtime"]
    },
    {
        "id": "bench_08",
        "question": "What port and protocol does flocard-auth-service run on?",
        "expected_source": "service_catalog_and_ports.csv",
        "expected_keywords": ["8081", "flocard-auth-service", "grpc"]
    }
]


def calculate_grounding_score(answer: str, context_text: str) -> float:
    """
    Compute lexical unigram overlap between answer tokens and retrieved context tokens.
    Indicates whether answer statements originate in the retrieved text.
    """
    ans_words = set(re.findall(r'\b\w{3,}\b', answer.lower()))
    ctx_words = set(re.findall(r'\b\w{3,}\b', context_text.lower()))
    
    if not ans_words:
        return 0.0
    overlap = ans_words.intersection(ctx_words)
    return round(len(overlap) / len(ans_words), 4)


def generate_eval_charts(results_summary: Dict[str, Any], output_path: Path):
    """Generate Matplotlib visualization of evaluation metrics."""
    try:
        import matplotlib.pyplot as plt

        metrics = ["Recall@k", "Citation Coverage", "Grounding Overlap"]
        scores = [
            results_summary["overall_recall"],
            results_summary["avg_citation_coverage"],
            results_summary["avg_grounding_score"]
        ]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
        fig.patch.set_facecolor('#0f172a')

        # Chart 1: Quality Metrics Bar Chart
        ax1.set_facecolor('#1e293b')
        bars = ax1.bar(metrics, [s * 100 for s in scores], color=['#38bdf8', '#818cf8', '#34d399'], width=0.55)
        ax1.set_ylim(0, 105)
        ax1.set_ylabel('Score (%)', color='#f1f5f9', fontsize=10)
        ax1.set_title('RAG Retrieval & Grounding Quality', color='#f1f5f9', fontsize=12, pad=10)
        ax1.tick_params(colors='#94a3b8')
        for spine in ax1.spines.values():
            spine.set_color('#334155')

        for bar in bars:
            height = bar.get_height()
            ax1.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 4), textcoords="offset points",
                        ha='center', va='bottom', color='#ffffff', fontweight='bold', fontsize=9)

        # Chart 2: Per-Query Latency
        ax2.set_facecolor('#1e293b')
        q_ids = [item["id"] for item in results_summary["benchmark_items"]]
        latencies = [item["latency_ms"] for item in results_summary["benchmark_items"]]
        ax2.plot(q_ids, latencies, marker='o', color='#f472b6', linewidth=2, markersize=6)
        ax2.set_ylabel('Latency (ms)', color='#f1f5f9', fontsize=10)
        ax2.set_title('Query Latency Distribution', color='#f1f5f9', fontsize=12, pad=10)
        ax2.tick_params(colors='#94a3b8', rotation=30)
        for spine in ax2.spines.values():
            spine.set_color('#334155')

        plt.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=180, facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close()
        print(f"Evaluation charts saved to: {output_path}")
    except Exception as e:
        print(f"Warning: Chart generation skipped ({e})")


def run_eval_suite(top_k: int = 4) -> Dict[str, Any]:
    """
    Run full benchmark suite against the RAG pipeline.
    """
    print(f"\n=======================================================")
    print(f"Running AI Knowledge Assistant Evaluation Benchmark...")
    print(f"=======================================================\n")

    items_result = []
    total_recall = 0
    total_citation_coverage = 0
    total_grounding = 0
    latencies = []

    for b in BENCHMARK_DATASET:
        t0 = time.time()
        res = rag_pipeline.query(b["question"], top_k=top_k)
        lat = res["latency_ms"]
        latencies.append(lat)

        retrieved_sources = [c["source"] for c in res["citations"]]
        is_recalled = b["expected_source"] in retrieved_sources
        if is_recalled:
            total_recall += 1

        # Check citation coverage (whether answer cites docs)
        cited_nums = set(re.findall(r'\[Doc\s*(\d+)\]', res["answer"]))
        coverage = min(1.0, len(cited_nums) / max(1, len(res["citations"])))
        total_citation_coverage += coverage

        # Grounding overlap
        all_context_text = " ".join([c["excerpt"] for c in res["citations"]])
        grounding = calculate_grounding_score(res["answer"], all_context_text)
        total_grounding += grounding

        item_entry = {
            "id": b["id"],
            "question": b["question"],
            "expected_source": b["expected_source"],
            "retrieved_sources": retrieved_sources,
            "recalled": is_recalled,
            "citations_count": len(res["citations"]),
            "coverage": round(coverage, 2),
            "grounding": round(grounding, 2),
            "latency_ms": lat
        }
        items_result.append(item_entry)
        status = "PASS" if is_recalled else "FAIL"
        print(f"[{status}] {b['id']}: Recall={is_recalled} | Grounding={grounding*100:.1f}% | Latency={lat:.1f}ms")

    n = len(BENCHMARK_DATASET)
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "total_test_cases": n,
        "overall_recall": round(total_recall / n, 4),
        "avg_citation_coverage": round(total_citation_coverage / n, 4),
        "avg_grounding_score": round(total_grounding / n, 4),
        "avg_latency_ms": round(sum(latencies) / n, 2),
        "benchmark_items": items_result
    }

    report_dir = settings.eval_results_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = report_dir / "eval_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    chart_path = report_dir / "eval_metrics_chart.png"
    generate_eval_charts(summary, chart_path)

    print(f"\nBenchmark Summary:")
    print(f"- Overall Recall@{top_k}: {summary['overall_recall'] * 100:.1f}%")
    print(f"- Avg Citation Coverage: {summary['avg_citation_coverage'] * 100:.1f}%")
    print(f"- Avg Grounding Overlap: {summary['avg_grounding_score'] * 100:.1f}%")
    print(f"- Average Latency: {summary['avg_latency_ms']} ms")
    print(f"Detailed report saved to: {summary_path}\n")

    return summary


if __name__ == "__main__":
    run_eval_suite()
