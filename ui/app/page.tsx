'use client';

import React, { useState, useEffect, useRef } from 'react';

interface Citation {
  doc_number: number;
  chunk_id: string;
  source: string;
  title: string;
  score: number;
  doc_type: string;
  excerpt: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  latency_ms?: number;
  model?: string;
  query_id?: string;
}

interface HealthStats {
  vector_count: number;
  ollama_online: boolean;
  llm_provider: string;
  avg_latency_ms: number;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        '👋 Welcome! I am your **AI Knowledge Assistant**. I have indexed internal engineering documentation (architecture guides, FAQs, SOPs, IT perks). Ask any question to retrieve grounded answers with verified citations!',
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<HealthStats>({
    vector_count: 31,
    ollama_online: false,
    llm_provider: 'ollama',
    avg_latency_ms: 0,
  });

  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const fetchStats = async () => {
    try {
      const healthRes = await fetch('http://127.0.0.1:8000/health');
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        const metricsRes = await fetch('http://127.0.0.1:8000/api/metrics');
        const metricsData = metricsRes.ok ? await metricsRes.json() : { average_latency_ms: 0 };

        setStats({
          vector_count: healthData.vector_count || 0,
          ollama_online: healthData.ollama_online || false,
          llm_provider: healthData.llm_provider || 'local',
          avg_latency_ms: metricsData.average_latency_ms || 0,
        });
      }
    } catch {
      // Backend may be starting
    }
  };

  const handleAsk = async (questionText?: string) => {
    const q = questionText || inputQuery;
    if (!q.trim() || loading) return;

    setInputQuery('');
    setMessages((prev) => [...prev, { role: 'user', content: q }]);
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, top_k: 4 }),
      });

      if (!res.ok) throw new Error(`Query failed with status ${res.status}`);
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          citations: data.citations,
          latency_ms: data.latency_ms,
          model: data.model,
          query_id: data.query_id,
        },
      ]);
      fetchStats();
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Failed to retrieve response: ${err.message}. Please verify the FastAPI backend is running on port 8000.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const exportDocx = async (msg: Message) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/export/docx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: 'Inquiry',
          answer: msg.content,
          citations: msg.citations || [],
          query_id: msg.query_id || 'export',
        }),
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${msg.query_id || 'qa'}.docx`;
      a.click();
    } catch (err) {
      alert('Export failed: ' + err);
    }
  };

  const exportXlsx = async (msg: Message) => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/export/xlsx', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: 'Inquiry',
          answer: msg.content,
          citations: msg.citations || [],
          query_id: msg.query_id || 'export',
        }),
      });
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${msg.query_id || 'qa'}.xlsx`;
      a.click();
    } catch (err) {
      alert('Export failed: ' + err);
    }
  };

  const triggerReindex = async () => {
    if (!confirm('Re-generate synthetic documentation and re-index vector database?')) return;
    try {
      const res = await fetch('http://127.0.0.1:8000/api/reindex', { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      fetchStats();
    } catch (err) {
      alert('Reindex error: ' + err);
    }
  };

  const runEvaluation = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/evaluate', { method: 'POST' });
      const data = await res.json();
      alert(
        `Benchmark Complete!\nRecall@k: ${(data.overall_recall * 100).toFixed(1)}%\nAvg Citation Coverage: ${(
          data.avg_citation_coverage * 100
        ).toFixed(1)}%\nAvg Latency: ${data.avg_latency_ms} ms`
      );
    } catch (err) {
      alert('Evaluation error: ' + err);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navbar */}
      <header
        style={{
          borderBottom: '1px solid var(--border)',
          padding: '1rem 2rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(9, 13, 22, 0.85)',
          backdropFilter: 'blur(12px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'var(--brand-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              color: '#090d16',
              fontSize: '1rem',
            }}
          >
            KA
          </div>
          <div>
            <h1 style={{ fontSize: '1.2rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              AI Knowledge Assistant
            </h1>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Engineering Onboarding & Grounded RAG System
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            onClick={triggerReindex}
            style={{
              padding: '0.55rem 1.1rem',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 600,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            🔄 Re-Index Docs
          </button>
          <button
            onClick={runEvaluation}
            style={{
              padding: '0.55rem 1.1rem',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 600,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            📊 Run Benchmark
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main
        style={{
          maxWidth: '1120px',
          width: '100%',
          margin: '0 auto',
          padding: '2rem 1.5rem',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '1.75rem',
        }}
      >
        {/* KPI Telemetry Bar */}
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1rem',
          }}
        >
          <div className="glass" style={{ padding: '1rem 1.25rem', borderRadius: '12px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              VECTOR DATABASE
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '0.3rem' }}>
              {stats.vector_count} Chunks
            </div>
          </div>

          <div className="glass" style={{ padding: '1rem 1.25rem', borderRadius: '12px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              AVERAGE LATENCY
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-emerald)', marginTop: '0.3rem' }}>
              {stats.avg_latency_ms.toFixed(1)} ms
            </div>
          </div>

          <div className="glass" style={{ padding: '1rem 1.25rem', borderRadius: '12px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
              ACTIVE LLM ENGINE
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-purple)', marginTop: '0.4rem' }}>
              {stats.ollama_online ? `Ollama (${stats.llm_provider})` : 'Local Resilient Synthesizer'}
            </div>
          </div>
        </section>

        {/* Quick Question Chips */}
        <div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
            Suggested Onboarding Questions:
          </p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {[
              'What is FloCard and what does it do?',
              'What is our code review SLA and PR policy?',
              'How do we handle SEV-1 production incidents?',
              'What employee stipends and IT perks do we receive?',
              'How does zero-downtime database migration work?',
            ].map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleAsk(q)}
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-secondary)',
                  padding: '0.4rem 0.8rem',
                  borderRadius: '20px',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Chat Console */}
        <section
          className="glass"
          style={{
            borderRadius: '16px',
            display: 'flex',
            flexDirection: 'column',
            minHeight: '520px',
            boxShadow: '0 12px 36px rgba(0, 0, 0, 0.4)',
          }}
        >
          {/* History */}
          <div
            style={{
              flex: 1,
              padding: '1.75rem',
              overflowY: 'auto',
              maxHeight: '540px',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.5rem',
            }}
          >
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: m.role === 'user' ? '80%' : '96%',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.5rem',
                }}
              >
                <div
                  style={{
                    padding: '1rem 1.3rem',
                    borderRadius: '14px',
                    fontSize: '0.95rem',
                    lineHeight: 1.6,
                    background:
                      m.role === 'user'
                        ? 'linear-gradient(135deg, #2563eb, #3b82f6)'
                        : 'rgba(30, 41, 59, 0.7)',
                    border: m.role === 'user' ? 'none' : '1px solid var(--border)',
                    borderBottomRightRadius: m.role === 'user' ? '4px' : '14px',
                    borderBottomLeftRadius: m.role === 'assistant' ? '4px' : '14px',
                    whiteSpace: 'pre-line',
                  }}
                >
                  {m.content}

                  {/* Expandable Citations */}
                  {m.citations && m.citations.length > 0 && (
                    <div style={{ marginTop: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      <p style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                        Document Citations & Evidence:
                      </p>
                      {m.citations.map((c, cIdx) => (
                        <div
                          key={cIdx}
                          style={{
                            background: 'rgba(15, 23, 42, 0.85)',
                            border: '1px solid rgba(56, 189, 248, 0.2)',
                            borderRadius: '10px',
                            padding: '0.8rem 1rem',
                          }}
                        >
                          <div
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              marginBottom: '0.35rem',
                            }}
                          >
                            <span
                              style={{
                                fontSize: '0.75rem',
                                background: 'rgba(56, 189, 248, 0.15)',
                                color: 'var(--accent-cyan)',
                                padding: '0.2rem 0.5rem',
                                borderRadius: '6px',
                                fontWeight: 700,
                              }}
                            >
                              [Doc {c.doc_number}] {c.title}
                            </span>
                            <span
                              style={{
                                fontFamily: 'JetBrains Mono, monospace',
                                fontSize: '0.75rem',
                                color: 'var(--accent-emerald)',
                              }}
                            >
                              Sim: {(c.score * 100).toFixed(1)}%
                            </span>
                          </div>
                          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                            "{c.excerpt}"
                          </p>
                          <div
                            style={{
                              fontSize: '0.75rem',
                              color: '#64748b',
                              marginTop: '0.35rem',
                            }}
                          >
                            Source: {c.source} | Chunk: {c.chunk_id}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Assistant Footer Actions (Word / Excel Export) */}
                  {m.role === 'assistant' && m.citations && (
                    <div
                      style={{
                        display: 'flex',
                        gap: '0.6rem',
                        marginTop: '1rem',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                      }}
                    >
                      <button
                        onClick={() => exportDocx(m)}
                        style={{
                          background: 'rgba(255, 255, 255, 0.06)',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          padding: '0.35rem 0.75rem',
                          color: 'var(--text-primary)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        📄 Export to Word (.docx)
                      </button>
                      <button
                        onClick={() => exportXlsx(m)}
                        style={{
                          background: 'rgba(255, 255, 255, 0.06)',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          padding: '0.35rem 0.75rem',
                          color: 'var(--text-primary)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        📊 Export to Excel (.xlsx)
                      </button>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          color: '#64748b',
                          marginLeft: 'auto',
                        }}
                      >
                        ⚡ {m.latency_ms} ms ({m.model})
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ alignSelf: 'flex-start', maxWidth: '85%' }}>
                <div
                  style={{
                    padding: '1rem 1.3rem',
                    borderRadius: '14px',
                    fontSize: '0.9rem',
                    color: 'var(--text-secondary)',
                    background: 'rgba(30, 41, 59, 0.6)',
                    border: '1px solid var(--border)',
                  }}
                >
                  🔍 Querying vector index and synthesizing grounded answer...
                </div>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Prompt Input */}
          <div
            style={{
              borderTop: '1px solid var(--border)',
              padding: '1rem 1.25rem',
              display: 'flex',
              gap: '0.75rem',
              background: 'rgba(15, 23, 42, 0.6)',
              borderBottomLeftRadius: '16px',
              borderBottomRightRadius: '16px',
            }}
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
              placeholder="Ask a question about internal architecture, policies, or procedures..."
              style={{
                flex: 1,
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border)',
                borderRadius: '10px',
                padding: '0.85rem 1.25rem',
                color: '#fff',
                fontSize: '0.95rem',
                outline: 'none',
              }}
            />
            <button
              onClick={() => handleAsk()}
              disabled={loading}
              style={{
                padding: '0.85rem 1.75rem',
                borderRadius: '10px',
                background: 'var(--brand-gradient)',
                color: '#090d16',
                border: 'none',
                fontWeight: 700,
                fontSize: '0.95rem',
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              Ask
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
