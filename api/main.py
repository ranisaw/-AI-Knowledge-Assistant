"""
FastAPI Server for AI Knowledge Assistant.
Exposes endpoints for RAG queries, streaming inference, document re-indexing,
metrics telemetry, Word/Excel exports, and benchmark evaluations.
"""
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Depends, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.security import verify_token, ETHICAL_AI_DISCLAIMER
from core.synth_data import generate_synthetic_documents
from core.ingest import ingest_documents
from core.vector_store import vector_store
from core.rag_pipeline import rag_pipeline
from core.llm_client import llm_client
from api.schemas import (
    AskRequest, AskResponse, CitationModel, ReindexResponse,
    ExportRequest, MetricSummary
)
from api.exporter import export_to_docx, export_to_xlsx

app = FastAPI(
    title="AI Knowledge Assistant API",
    description="Enterprise RAG Service for Engineering Onboarding",
    version="1.0.0"
)

# Enable CORS for Next.js and frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def auth_guard(authorization: Optional[str] = Header(None)):
    """Enforce token validation if enabled in settings."""
    if settings.require_auth and not verify_token(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API token")
    return True


@app.get("/health")
def health_check():
    """Health and readiness check."""
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "vector_count": vector_store.count(),
        "llm_provider": settings.llm_provider,
        "ollama_online": llm_client.is_ollama_available(),
        "disclaimer": ETHICAL_AI_DISCLAIMER
    }


@app.post("/api/ask", response_model=AskResponse, dependencies=[Depends(auth_guard)])
def ask_question(payload: AskRequest):
    """
    Primary RAG query endpoint.
    Retrieves grounded context, generates answer, and returns structured citations.
    """
    filter_meta = {"doc_type": payload.filter_type} if payload.filter_type else None
    result = rag_pipeline.query(
        question=payload.question,
        top_k=payload.top_k,
        filter_meta=filter_meta
    )
    return AskResponse(
        query_id=result["query_id"],
        question=result["question"],
        answer=result["answer"],
        citations=[CitationModel(**c) for c in result["citations"]],
        latency_ms=result["latency_ms"],
        model=result["model"],
        retrieved_count=result["retrieved_count"]
    )


@app.get("/api/ask/stream", dependencies=[Depends(auth_guard)])
def stream_ask_question(
    q: str = Query(..., min_length=2, description="Question"),
    top_k: int = Query(default=4, ge=1, le=10)
):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time word-by-word token generation.
    """
    from core.prompt_builder import build_rag_prompt
    from core.security import redact_pii

    sanitized_q, _ = redact_pii(q)
    chunks = vector_store.similarity_search(sanitized_q, top_k=top_k)
    prompt = build_rag_prompt(sanitized_q, chunks)

    def event_stream():
        # First send citation metadata header
        cites = [
            {
                "doc_number": i,
                "title": c.get("metadata", {}).get("title"),
                "source": c.get("metadata", {}).get("source"),
                "score": c.get("score"),
                "chunk_id": c.get("id"),
                "doc_type": c.get("metadata", {}).get("doc_type")
            }
            for i, c in enumerate(chunks, 1)
        ]
        yield f"event: metadata\ndata: {json.dumps({'citations': cites})}\n\n"

        for token in llm_client.generate_stream(prompt, context_chunks=chunks):
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/reindex", response_model=ReindexResponse, dependencies=[Depends(auth_guard)])
def trigger_reindex(generate_mock_data: bool = True):
    """
    Trigger full re-indexing:
    Optionally generate synthetic docs -> ingest documents -> chunk -> embed -> index in vector store.
    """
    start_time = time.time()
    if generate_mock_data:
        generate_synthetic_documents(settings.raw_data_dir)

    chunks = ingest_documents()
    vector_store.add_chunks(chunks)
    duration = round(time.time() - start_time, 2)

    return ReindexResponse(
        status="success",
        files_processed=len(set(c["source"] for c in chunks)),
        chunks_created=len(chunks),
        vector_count=vector_store.count(),
        message=f"Re-indexing complete in {duration}s. {len(chunks)} chunks indexed."
    )


@app.get("/api/documents", dependencies=[Depends(auth_guard)])
def list_documents():
    """List all ingested documents and their chunk counts."""
    if not settings.chunks_file.exists():
        return {"documents": [], "total_chunks": 0}

    try:
        chunks = json.loads(settings.chunks_file.read_text(encoding="utf-8"))
        docs_map = {}
        for c in chunks:
            src = c.get("source", "unknown")
            if src not in docs_map:
                docs_map[src] = {
                    "source": src,
                    "title": c.get("title", src),
                    "doc_type": c.get("doc_type", "document"),
                    "tags": c.get("tags", []),
                    "author": c.get("author", "Unknown"),
                    "chunk_count": 0
                }
            docs_map[src]["chunk_count"] += 1

        return {
            "documents": list(docs_map.values()),
            "total_chunks": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed loading document manifest: {str(e)}")


@app.post("/api/export/docx", dependencies=[Depends(auth_guard)])
def export_docx_report(payload: ExportRequest):
    """Download Word document (.docx) containing question, answer, and citations."""
    docx_bytes = export_to_docx(
        question=payload.question,
        answer=payload.answer,
        citations=[c.dict() for c in payload.citations]
    )
    filename = f"knowledge_report_{payload.query_id or 'doc'}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/api/export/xlsx", dependencies=[Depends(auth_guard)])
def export_xlsx_report(payload: ExportRequest):
    """Download Excel spreadsheet (.xlsx) containing question, answer, and citations breakdown."""
    xlsx_bytes = export_to_xlsx(
        question=payload.question,
        answer=payload.answer,
        citations=[c.dict() for c in payload.citations]
    )
    filename = f"knowledge_report_{payload.query_id or 'data'}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/metrics", response_model=MetricSummary, dependencies=[Depends(auth_guard)])
def get_metrics():
    """Retrieve usage telemetry, latency statistics, and audit traces."""
    audit_file = settings.logs_dir / "audit.jsonl"
    if not audit_file.exists():
        return MetricSummary(
            total_queries=0,
            average_latency_ms=0.0,
            p95_latency_ms=0.0,
            recent_queries=[]
        )

    records = []
    latencies = []
    with open(audit_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    item = json.loads(line)
                    records.append(item)
                    if "latency_ms" in item:
                        latencies.append(item["latency_ms"])
                except Exception:
                    pass

    total = len(records)
    avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    latencies.sort()
    p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    return MetricSummary(
        total_queries=total,
        average_latency_ms=avg_lat,
        p95_latency_ms=round(p95_lat, 2),
        recent_queries=records[-10:][::-1]
    )


@app.post("/api/evaluate", dependencies=[Depends(auth_guard)])
def run_evaluation_benchmark():
    """Execute evaluation benchmark suite."""
    from eval.eval_suite import run_eval_suite
    results = run_eval_suite()
    return results


# Built-in Modern Web Interface
WEB_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Knowledge Assistant — Engineering Onboarding</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(18, 24, 38, 0.7);
      --border: rgba(255, 255, 255, 0.08);
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.15);
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --brand-grad: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }
    header {
      border-bottom: 1px solid var(--border);
      padding: 1rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      backdrop-filter: blur(12px);
      background: rgba(9, 13, 22, 0.8);
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .badge-logo {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: var(--brand-grad);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      color: #fff;
    }
    .brand h1 { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; }
    .header-actions { display: flex; gap: 0.75rem; align-items: center; }
    .btn {
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.05);
      color: var(--text);
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }
    .btn:hover { background: rgba(255, 255, 255, 0.1); border-color: var(--accent); }
    .btn-primary {
      background: var(--brand-grad);
      color: #0b0f19;
      border: none;
      font-weight: 700;
    }
    .btn-primary:hover { opacity: 0.9; }
    .container {
      max-width: 1100px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem 1.5rem;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }
    .stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem;
      backdrop-filter: blur(10px);
    }
    .stat-label { font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }
    .stat-val { font-size: 1.4rem; font-weight: 700; margin-top: 0.25rem; color: #38bdf8; }
    
    .chat-box {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      backdrop-filter: blur(16px);
      display: flex;
      flex-direction: column;
      min-height: 480px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    .chat-history {
      flex: 1;
      padding: 1.5rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      max-height: 520px;
    }
    .msg {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      max-width: 85%;
      animation: fadeIn 0.3s ease;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    .msg.user { align-self: flex-end; }
    .msg.assistant { align-self: flex-start; max-width: 95%; }
    .bubble {
      padding: 1rem 1.25rem;
      border-radius: 14px;
      font-size: 0.95rem;
      line-height: 1.6;
    }
    .msg.user .bubble {
      background: linear-gradient(135deg, #2563eb, #3b82f6);
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    .msg.assistant .bubble {
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid var(--border);
      border-bottom-left-radius: 4px;
    }
    .citations-container {
      margin-top: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }
    .citation-card {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(56, 189, 248, 0.25);
      border-radius: 10px;
      padding: 0.75rem 1rem;
      font-size: 0.85rem;
    }
    .citation-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.4rem;
    }
    .citation-badge {
      font-size: 0.75rem;
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      font-weight: 600;
    }
    .citation-score {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      color: #10b981;
    }
    .citation-excerpt {
      color: var(--text-muted);
      font-size: 0.8rem;
      line-height: 1.4;
      font-style: italic;
    }
    .export-bar {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.75rem;
    }
    .input-bar {
      border-top: 1px solid var(--border);
      padding: 1rem 1.25rem;
      display: flex;
      gap: 0.75rem;
      background: rgba(15, 23, 42, 0.4);
      border-bottom-left-radius: 16px;
      border-bottom-right-radius: 16px;
    }
    .input-bar input {
      flex: 1;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.85rem 1.25rem;
      color: #fff;
      font-size: 0.95rem;
      outline: none;
      transition: border 0.2s;
    }
    .input-bar input:focus { border-color: var(--accent); }
    .quick-queries {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }
    .chip {
      font-size: 0.78rem;
      padding: 0.35rem 0.75rem;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s;
    }
    .chip:hover {
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border-color: #38bdf8;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="badge-logo">KA</div>
      <div>
        <h1>AI Knowledge Assistant</h1>
        <p style="font-size: 0.75rem; color: var(--text-muted);">Engineering Onboarding & Knowledge Retrieval</p>
      </div>
    </div>
    <div class="header-actions">
      <button class="btn" onclick="triggerReindex()">🔄 Re-Index Docs</button>
      <button class="btn" onclick="runEvaluation()">📊 Run Benchmark</button>
    </div>
  </header>

  <div class="container">
    <div class="stats-bar">
      <div class="stat-card">
        <div class="stat-label">Vector Store Status</div>
        <div class="stat-val" id="stat-vectors">-</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Average Latency</div>
        <div class="stat-val" id="stat-latency">-</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">LLM Engine</div>
        <div class="stat-val" style="font-size: 1rem; color: #a78bfa;" id="stat-model">Initializing...</div>
      </div>
    </div>

    <div>
      <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.5rem;">Sample Onboarding Inquiries:</p>
      <div class="quick-queries">
        <div class="chip" onclick="askPreset('What is FloCard?')">What is FloCard?</div>
        <div class="chip" onclick="askPreset('What is our code review SLA and PR policy?')">Code Review SLA & PR Policy</div>
        <div class="chip" onclick="askPreset('How do we handle SEV-1 production incidents?')">SEV-1 Incident Runbook</div>
        <div class="chip" onclick="askPreset('What employee stipends and IT perks do we receive?')">IT Perks & Stipends</div>
        <div class="chip" onclick="askPreset('How does zero-downtime database migration work?')">Zero-Downtime DB Migrations</div>
      </div>
    </div>

    <div class="chat-box">
      <div class="chat-history" id="chat-history">
        <div class="msg assistant">
          <div class="bubble">
            👋 Hello! I am your <strong>AI Knowledge Assistant</strong>. I have indexed our internal engineering documentation (architecture guides, FAQs, SOPs, and employee perks). Ask me anything, and I'll provide answers with verified source citations!
          </div>
        </div>
      </div>

      <div class="input-bar">
        <input type="text" id="query-input" placeholder="Ask a question about internal architecture, policies, or procedures..." onkeydown="if(event.key==='Enter') submitQuery()">
        <button class="btn btn-primary" onclick="submitQuery()" id="send-btn">Ask</button>
      </div>
    </div>
  </div>

  <script>
    let lastResponse = null;

    async function loadStats() {
      try {
        const health = await fetch('/health').then(r => r.json());
        document.getElementById('stat-vectors').textContent = health.vector_count + ' Chunks';
        document.getElementById('stat-model').textContent = health.ollama_online ? 'Ollama (' + health.llm_provider + ')' : 'Local Synthesizer';
        
        const metrics = await fetch('/api/metrics').then(r => r.json());
        document.getElementById('stat-latency').textContent = metrics.average_latency_ms ? metrics.average_latency_ms + ' ms' : '0 ms';
      } catch (e) {
        console.error(e);
      }
    }

    function askPreset(q) {
      document.getElementById('query-input').value = q;
      submitQuery();
    }

    async function submitQuery() {
      const input = document.getElementById('query-input');
      const question = input.value.trim();
      if (!question) return;

      input.value = '';
      appendUserMsg(question);

      const history = document.getElementById('chat-history');
      const loadingMsg = document.createElement('div');
      loadingMsg.className = 'msg assistant';
      loadingMsg.innerHTML = '<div class="bubble" style="color: #94a3b8;">🔍 Searching vector store and synthesizing grounded answer...</div>';
      history.appendChild(loadingMsg);
      history.scrollTop = history.scrollHeight;

      try {
        const res = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, top_k: 4 })
        });
        const data = await res.json();
        lastResponse = data;
        history.removeChild(loadingMsg);
        appendAssistantMsg(data);
        loadStats();
      } catch (err) {
        history.removeChild(loadingMsg);
        alert('Query error: ' + err);
      }
    }

    function appendUserMsg(text) {
      const history = document.getElementById('chat-history');
      const div = document.createElement('div');
      div.className = 'msg user';
      div.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
      history.appendChild(div);
      history.scrollTop = history.scrollHeight;
    }

    function appendAssistantMsg(data) {
      const history = document.getElementById('chat-history');
      const div = document.createElement('div');
      div.className = 'msg assistant';

      let citationsHtml = '';
      if (data.citations && data.citations.length > 0) {
        citationsHtml = '<div class="citations-container"><p style="font-size:0.8rem; font-weight:700; color:#38bdf8;">Verified Source Citations:</p>';
        data.citations.forEach(c => {
          citationsHtml += `
            <div class="citation-card">
              <div class="citation-header">
                <span class="citation-badge">[Doc ${c.doc_number}] ${escapeHtml(c.title)}</span>
                <span class="citation-score">Sim: ${(c.score * 100).toFixed(1)}%</span>
              </div>
              <p class="citation-excerpt">"${escapeHtml(c.excerpt)}"</p>
              <div style="font-size:0.75rem; color:#64748b; margin-top:0.25rem;">Source: ${escapeHtml(c.source)} | Chunk ID: ${escapeHtml(c.chunk_id)}</div>
            </div>
          `;
        });
        citationsHtml += '</div>';
      }

      div.innerHTML = `
        <div class="bubble">
          <div>${escapeHtml(data.answer).replace(/\\n/g, '<br>')}</div>
          ${citationsHtml}
          <div class="export-bar">
            <button class="btn" style="font-size: 0.75rem; padding: 0.35rem 0.7rem;" onclick="exportDocx('${data.query_id}')">📄 Export to Word (.docx)</button>
            <button class="btn" style="font-size: 0.75rem; padding: 0.35rem 0.7rem;" onclick="exportXlsx('${data.query_id}')">📊 Export to Excel (.xlsx)</button>
            <span style="font-size: 0.75rem; color: #64748b; margin-left: auto; align-self: center;">⚡ ${data.latency_ms} ms (${escapeHtml(data.model)})</span>
          </div>
        </div>
      `;
      history.appendChild(div);
      history.scrollTop = history.scrollHeight;
    }

    async function exportDocx(queryId) {
      if (!lastResponse) return;
      const res = await fetch('/api/export/docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lastResponse)
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${queryId}.docx`;
      a.click();
    }

    async function exportXlsx(queryId) {
      if (!lastResponse) return;
      const res = await fetch('/api/export/xlsx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lastResponse)
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${queryId}.xlsx`;
      a.click();
    }

    async function triggerReindex() {
      if (!confirm('Re-generate synthetic docs and re-index vector store?')) return;
      const res = await fetch('/api/reindex', { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      loadStats();
    }

    async function runEvaluation() {
      const res = await fetch('/api/evaluate', { method: 'POST' });
      const data = await res.json();
      alert(`Benchmark Completed!\nRecall@k: ${(data.overall_recall * 100).toFixed(1)}%\nAvg Citation Coverage: ${(data.avg_citation_coverage * 100).toFixed(1)}%\nAvg Latency: ${data.avg_latency_ms} ms`);
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    loadStats();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def root_dashboard():
    """Serves the built-in modern web dashboard."""
    return WEB_UI_HTML


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=settings.host, port=settings.port, reload=True)
