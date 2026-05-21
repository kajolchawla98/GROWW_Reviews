'use client';

import { useState, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [expandedRec, setExpandedRec] = useState(null);

  useEffect(() => {
    fetchDashboard();
  }, []);

  async function fetchDashboard() {
    try {
      const res = await fetch(`${API_BASE}/dashboard?t=${Date.now()}`, { cache: 'no-store' });
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-state" style={{ height: '100vh' }}>
        <div className="spinner" />
        <p style={{ color: 'var(--text-secondary)' }}>Loading intelligence data...</p>
      </div>
    );
  }

  if (!data || !data.summary) {
    return (
      <div className="loading-state" style={{ height: '100vh' }}>
        <p style={{ fontSize: '2rem' }}>📊</p>
        <p style={{ color: 'var(--text-secondary)' }}>No data yet — run the pipeline first</p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          POST http://localhost:8000/api/v1/pipeline/run
        </p>
      </div>
    );
  }

  const { summary, themes, recommendations, review_replay, pulse } = data;

  const navItems = [
    { id: 'overview', icon: '📊', label: 'Overview' },
    { id: 'themes', icon: '🏷️', label: 'Theme Intelligence' },
    { id: 'recommendations', icon: '🎯', label: 'Recommendations' },
    { id: 'reviews', icon: '💬', label: 'Review Replay' },
    { id: 'pulse', icon: '📋', label: 'Weekly Pulse' },
  ];

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">G</div>
          <div>
            <h2>GROWW AI</h2>
            <span>Product Intelligence</span>
          </div>
        </div>

        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-link ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </button>
        ))}

        <div style={{ marginTop: 'auto', padding: '12px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {summary.total_reviews} reviews analyzed
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {activeTab === 'overview' && (
          <OverviewTab summary={summary} themes={themes} recommendations={recommendations} />
        )}
        {activeTab === 'themes' && (
          <ThemesTab themes={themes} />
        )}
        {activeTab === 'recommendations' && (
          <RecommendationsTab
            recommendations={recommendations}
            expandedRec={expandedRec}
            setExpandedRec={setExpandedRec}
          />
        )}
        {activeTab === 'reviews' && (
          <ReviewReplayTab reviews={review_replay} />
        )}
        {activeTab === 'pulse' && (
          <PulseTab pulse={pulse} onDataRefresh={fetchDashboard} />
        )}
      </main>
    </div>
  );
}

/* ── Overview Tab ──────────────────────────────────────────── */

function OverviewTab({ summary, themes, recommendations }) {
  const sentimentEmoji = summary.average_sentiment > 0.2 ? '🟢' : summary.average_sentiment < -0.2 ? '🔴' : '🟡';

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Executive Overview</h1>
          <p className="subtitle">Real-time product intelligence from user reviews</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="summary-grid">
        <SummaryCard label="Total Reviews" value={summary.total_reviews} icon="📝" />
        <SummaryCard
          label="Avg Rating"
          value={`${summary.average_rating}★`}
          icon="⭐"
          color={summary.average_rating >= 4 ? 'var(--positive)' : summary.average_rating >= 3 ? 'var(--neutral)' : 'var(--negative)'}
        />
        <SummaryCard
          label="Sentiment"
          value={`${sentimentEmoji} ${summary.average_sentiment.toFixed(2)}`}
          icon="💬"
        />
        <SummaryCard
          label="Critical Issues"
          value={summary.critical_issues}
          icon="🚨"
          color={summary.critical_issues > 0 ? 'var(--negative)' : 'var(--positive)'}
        />
      </div>

      {/* Sentiment Distribution */}
      <div className="section animate-in">
        <div className="section-header">
          <h2>📈 Sentiment Distribution</h2>
        </div>
        <div className="card" style={{ display: 'flex', gap: '32px', flexWrap: 'wrap' }}>
          {Object.entries(summary.sentiment_distribution || {}).map(([key, count]) => (
            <div key={key} style={{ textAlign: 'center' }}>
              <div style={{
                fontSize: '1.8rem', fontWeight: '700', fontFamily: 'var(--font-heading)',
                color: key === 'positive' ? 'var(--positive)' : key === 'negative' ? 'var(--negative)' : key === 'mixed' ? 'var(--mixed)' : 'var(--neutral)'
              }}>
                {count}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>{key}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Themes Quick View */}
      <div className="section animate-in">
        <div className="section-header">
          <h2>🏷️ Top Themes</h2>
          <span className="badge">{themes?.length || 0} themes</span>
        </div>
        <div className="theme-grid">
          {(themes || []).slice(0, 3).map((theme, i) => (
            <ThemeCard key={i} theme={theme} />
          ))}
        </div>
      </div>

      {/* Top Recommendations */}
      <div className="section animate-in">
        <div className="section-header">
          <h2>🎯 Top Recommendations</h2>
        </div>
        <div className="rec-list">
          {(recommendations || []).slice(0, 3).map((rec, i) => (
            <RecCard key={i} rec={rec} />
          ))}
        </div>
      </div>
    </>
  );
}

/* ── Themes Tab ────────────────────────────────────────────── */

function ThemesTab({ themes }) {
  return (
    <>
      <div className="page-header">
        <div>
          <h1>Theme Intelligence</h1>
          <p className="subtitle">Product themes discovered from user reviews</p>
        </div>
        <span className="badge">{themes?.length || 0} themes</span>
      </div>
      <div className="theme-grid">
        {(themes || []).map((theme, i) => (
          <ThemeCard key={i} theme={theme} />
        ))}
      </div>
    </>
  );
}

/* ── Recommendations Tab ───────────────────────────────────── */

function RecommendationsTab({ recommendations, expandedRec, setExpandedRec }) {
  return (
    <>
      <div className="page-header">
        <div>
          <h1>PM Recommendations</h1>
          <p className="subtitle">AI-generated actionable insights with evidence</p>
        </div>
      </div>
      <div className="rec-list">
        {(recommendations || []).map((rec, i) => (
          <div key={i} className="rec-card" onClick={() => setExpandedRec(expandedRec === i ? null : i)}>
            <div className="rec-header">
              <span className="rec-title">{rec.title}</span>
              <span className={`priority-badge ${rec.priority}`}>{rec.priority}</span>
            </div>
            <div className="rec-theme">Theme: {rec.theme} · Impact: {rec.score?.toFixed(1)}</div>
            <div className="rec-desc">{rec.description}</div>
            {expandedRec === i && rec.evidence && rec.evidence.length > 0 && (
              <div className="evidence-drawer">
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8 }}>
                  📎 Evidence Quotes
                </div>
                {rec.evidence.map((q, j) => (
                  <div key={j} className="quote">"{q}"</div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

/* ── Review Replay Tab ─────────────────────────────────────── */

function ReviewReplayTab({ reviews }) {
  return (
    <>
      <div className="page-header">
        <div>
          <h1>Review Replay</h1>
          <p className="subtitle">Live feed of recent user reviews with AI tags</p>
        </div>
      </div>
      <div className="review-stream">
        {(reviews || []).map((r, i) => (
          <div key={i} className="review-card animate-in" style={{ animationDelay: `${i * 0.05}s` }}>
            <div className="review-header">
              <span className="stars">{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {r.version || ''} · {new Date(r.date).toLocaleDateString()}
              </span>
            </div>
            <div className="review-text">{r.text}</div>
            <div className="review-tags">
              {r.theme && <span className="tag tag-theme">{r.theme}</span>}
              {r.sentiment && <span className={`tag tag-sentiment ${r.sentiment}`}>{r.sentiment}</span>}
              {r.emotion && r.emotion !== 'neutral' && <span className="tag tag-emotion">{r.emotion}</span>}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function PulseTab({ pulse, onDataRefresh }) {
  const [publishing, setPublishing] = useState(false);
  const [publishStatus, setPublishStatus] = useState(null);
  const [running, setRunning] = useState(false);
  const [runStatus, setRunStatus] = useState(null);
  const [pollProgress, setPollProgress] = useState(null);

  const handleRunPipeline = async () => {
    setRunning(true);
    setRunStatus(null);
    setPollProgress('Starting pipeline...');
    try {
      const res = await fetch(`${API_BASE}/pipeline/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_id: 'com.nextbillion.groww', weeks: 4 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start pipeline');

      const runId = data.pipeline_run_id;
      setPollProgress('Pipeline running... (this takes 2–5 min due to rate limits)');

      // Poll status every 10 seconds for up to 10 minutes
      let attempts = 0;
      const maxAttempts = 60;
      const poll = setInterval(async () => {
        attempts++;
        const elapsed = Math.round(attempts * 10 / 60);
        try {
          const statusRes = await fetch(`${API_BASE}/pipeline/status/${runId}`);
          if (!statusRes.ok) {
            setPollProgress(`Pipeline running... ${elapsed}m elapsed (checking...)`);
            return;
          }
          const statusData = await statusRes.json();
          const status = statusData.status;

          if (status === 'completed') {
            clearInterval(poll);
            setPollProgress(null);
            setRunStatus({ type: 'success', msg: 'Pipeline complete! Refreshing data...' });
            setRunning(false);
            setTimeout(() => {
              onDataRefresh();
              setRunStatus({ type: 'success', msg: 'Data updated successfully.' });
            }, 1000);
          } else if (status === 'failed') {
            clearInterval(poll);
            setPollProgress(null);
            setRunStatus({ type: 'error', msg: `Pipeline failed: ${statusData.error_log || 'Unknown error'}` });
            setRunning(false);
          } else if (attempts >= maxAttempts) {
            clearInterval(poll);
            setPollProgress(null);
            setRunStatus({ type: 'error', msg: 'Pipeline timed out after 10 minutes. Check backend logs.' });
            setRunning(false);
          } else {
            setPollProgress(`Pipeline running... ${elapsed}m elapsed (status: ${status || 'running'})`);
          }
        } catch {
          // Network hiccup — keep polling silently
          setPollProgress(`Pipeline running... ${elapsed}m elapsed (checking...)`);
        }
      }, 10000);

    } catch (err) {
      setRunStatus({ type: 'error', msg: err.message });
      setPollProgress(null);
      setRunning(false);
    }
  };

  if (!pulse || !pulse.markdown) {
    return (
      <div className="empty-state">
        <p>📋 No pulse report generated yet.</p>
        <p style={{ marginTop: 8 }}>Run the pipeline to generate a weekly pulse.</p>
        <button className="action-btn" style={{ marginTop: 16 }} onClick={handleRunPipeline} disabled={running}>
          {running ? '⏳ Running...' : '▶ Run Pipeline Now'}
        </button>
        {pollProgress && (
          <p style={{ marginTop: 12, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            ⏳ {pollProgress}
          </p>
        )}
        {runStatus && (
          <p style={{ marginTop: 12, fontSize: '0.85rem', color: runStatus.type === 'error' ? 'var(--negative)' : 'var(--positive)' }}>
            {runStatus.msg}
          </p>
        )}
      </div>
    );
  }

  const handlePublish = async (target) => {
    setPublishing(true);
    setPublishStatus(null);
    try {
      // Always use "latest" so it works even after a redeploy resets the DB
      const res = await fetch(`${API_BASE}/pulses/latest/publish?target=${target}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Publish failed');
      setPublishStatus({ type: 'success', msg: `Successfully published to ${target.replace('_', ' ')}!` });
    } catch (err) {
      setPublishStatus({ type: 'error', msg: err.message });
    } finally {
      setPublishing(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Weekly Pulse</h1>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginTop: '8px' }}>
            <span className="badge">{pulse.week_label}</span>
            <span style={{ 
              fontSize: '0.85rem', 
              color: 'var(--text-muted)', 
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              🕒 Last updated: {pulse.generated_at ? new Date(pulse.generated_at).toLocaleString() : 'N/A'}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {pollProgress && (
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              ⏳ {pollProgress}
            </span>
          )}
          {runStatus && !pollProgress && (
            <span style={{ fontSize: '0.8rem', color: runStatus.type === 'error' ? 'var(--negative)' : 'var(--positive)' }}>
              {runStatus.type === 'error' ? '❌ ' : '✅ '}{runStatus.msg}
            </span>
          )}
          {publishStatus && (
            <span style={{ fontSize: '0.8rem', color: publishStatus.type === 'error' ? 'var(--negative)' : 'var(--positive)' }}>
              {publishStatus.type === 'error' ? '❌ ' : '✅ '}{publishStatus.msg}
            </span>
          )}
          <button
            className="action-btn outline"
            onClick={handleRunPipeline}
            disabled={running}
            title="Fetch latest reviews and regenerate pulse"
          >
            {running ? '⏳ Running...' : '🔄 Refresh Now'}
          </button>
          <button 
            className="action-btn" 
            onClick={() => handlePublish('google_docs')}
            disabled={publishing}
          >
            {publishing ? 'Publishing...' : '📄 Publish to Docs'}
          </button>
          <button 
            className="action-btn outline" 
            onClick={() => handlePublish('gmail')}
            disabled={publishing}
          >
            {publishing ? 'Drafting...' : '📧 Draft in Gmail'}
          </button>
        </div>
      </div>
      <div className="pulse-preview" dangerouslySetInnerHTML={{ __html: markdownToHtml(pulse.markdown) }} />
    </>
  );
}

/* ── Shared Components ─────────────────────────────────────── */

function SummaryCard({ label, value, icon, color }) {
  return (
    <div className="summary-card animate-in">
      <div className="card-label">{icon} {label}</div>
      <div className="card-value" style={color ? { color } : {}}>{value}</div>
    </div>
  );
}

function ThemeCard({ theme }) {
  const total = (theme.sentiment_breakdown?.positive || 0) +
    (theme.sentiment_breakdown?.negative || 0) +
    (theme.sentiment_breakdown?.neutral || 0) +
    (theme.sentiment_breakdown?.mixed || 0) || 1;

  const trendIcon = theme.trend_direction === 'rising' ? '↑' :
    theme.trend_direction === 'falling' ? '↓' :
    theme.trend_direction === 'spike' ? '⚠️' : '→';

  const trendClass = theme.trend_direction === 'rising' || theme.trend_direction === 'spike' ? 'trend-up' :
    theme.trend_direction === 'falling' ? 'trend-down' : 'trend-stable';

  return (
    <div className="theme-card animate-in">
      <div className="theme-header">
        <span className="theme-name">{theme.name || theme.theme_name}</span>
        <span className={`priority-badge ${theme.priority || 'P3'}`}>{theme.priority || 'P3'}</span>
      </div>
      <div className="theme-summary">{theme.summary || theme.ai_summary || 'No summary available'}</div>

      {/* Sentiment Bar */}
      <div className="sentiment-bar">
        <div className="seg-positive" style={{ flex: theme.sentiment_breakdown?.positive || 0 }} />
        <div className="seg-negative" style={{ flex: theme.sentiment_breakdown?.negative || 0 }} />
        <div className="seg-neutral" style={{ flex: theme.sentiment_breakdown?.neutral || 0 }} />
        <div className="seg-mixed" style={{ flex: theme.sentiment_breakdown?.mixed || 0 }} />
      </div>

      <div className="theme-meta">
        <span className="meta-item">📝 {theme.review_count} reviews</span>
        <span className="meta-item">⚡ Score: {(theme.impact_score || 0).toFixed(1)}</span>
        <span className={`meta-item ${trendClass}`}>
          {trendIcon} {(theme.volume_change || 0).toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

function RecCard({ rec }) {
  return (
    <div className="rec-card">
      <div className="rec-header">
        <span className="rec-title">{rec.title}</span>
        <span className={`priority-badge ${rec.priority}`}>{rec.priority}</span>
      </div>
      <div className="rec-theme">Theme: {rec.theme} · Impact: {rec.score?.toFixed(1)}</div>
      <div className="rec-desc">{rec.description}</div>
    </div>
  );
}

/* ── Markdown → HTML (simple converter) ────────────────────── */

function markdownToHtml(md) {
  if (!md) return '';
  let html = md
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\> (.*$)/gm, '<blockquote>$1</blockquote>')
    .replace(/^---$/gm, '<hr/>')
    .replace(/^\- (.*$)/gm, '<p>• $1</p>')
    .replace(/\|(.*)\|/g, (match) => {
      const cells = match.split('|').filter(c => c.trim());
      if (cells.length === 0 || cells.some(c => /^[\-\s:]+$/.test(c.trim()))) return '';
      const isHeader = match.includes('Theme') || match.includes('Metric');
      const tag = isHeader ? 'th' : 'td';
      return '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>';
    });

  // Wrap consecutive <tr> elements with a <table> tag
  html = html.replace(/(<tr>(?:.|\n)*?<\/tr>\s*)+/g, (match) => {
    return `<div class="table-container"><table><tbody>${match}</tbody></table></div>`;
  });

  return html.replace(/\n\n/g, '<br/>').replace(/\n/g, ' ');
}

