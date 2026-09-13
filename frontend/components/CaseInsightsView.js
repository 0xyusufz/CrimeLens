"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient } from "../lib/apiClient";

// ─── Enum display maps ─────────────────────────────────────────────────────────

const PATTERN_TYPE_LABELS = {
  CIRCULAR_TRANSACTION: "Circular Transaction",
  RAPID_TRANSFER_CHAIN: "Rapid Transfer Chain",
  LOCATION_TIME_OVERLAP: "Location / Time Overlap",
};

const LEAD_TYPE_LABELS = {
  FINANCIAL_NETWORK: "Financial Network",
  CIRCULAR_TRANSACTION: "Circular Transaction",
  RAPID_TRANSFER_CHAIN: "Rapid Transfer Chain",
  LOCATION_TIME_OVERLAP: "Location / Time Overlap",
  CROSS_CASE: "Cross-Case",
};

const SEVERITY_CONFIG = {
  HIGH:   { color: "#f87171", bg: "rgba(239,68,68,0.10)",   border: "rgba(239,68,68,0.30)",   label: "HIGH" },
  MEDIUM: { color: "#fbbf24", bg: "rgba(245,158,11,0.10)",  border: "rgba(245,158,11,0.30)",  label: "MEDIUM" },
  LOW:    { color: "#94a3b8", bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.25)", label: "LOW" },
};

const PRIORITY_CONFIG = {
  HIGH:   { color: "#f87171", bg: "rgba(239,68,68,0.10)",   border: "rgba(239,68,68,0.30)",   label: "HIGH" },
  MEDIUM: { color: "#fbbf24", bg: "rgba(245,158,11,0.10)",  border: "rgba(245,158,11,0.30)",  label: "MEDIUM" },
  LOW:    { color: "#94a3b8", bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.25)", label: "LOW" },
};

const STATUS_CONFIG = {
  CONFIRMED:       { color: "#38bdf8", label: "CONFIRMED" },
  INFERRED:        { color: "#818cf8", label: "INFERRED" },
  PREDICTED:       { color: "#f59e0b", label: "PREDICTED" },
  REVIEW_REQUIRED: { color: "#fb923c", label: "REVIEW REQUIRED" },
};

// ─── Small helpers ─────────────────────────────────────────────────────────────

function SeverityBadge({ value }) {
  const cfg = SEVERITY_CONFIG[value] || SEVERITY_CONFIG.LOW;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      background: cfg.bg, color: cfg.color,
      border: `1px solid ${cfg.border}`,
      borderRadius: "4px", padding: "0.12rem 0.5rem",
      fontSize: "0.65rem", fontWeight: 700,
      letterSpacing: "0.06em", textTransform: "uppercase",
      fontFamily: "ui-monospace, monospace",
    }}>
      {cfg.label}
    </span>
  );
}

function PriorityBadge({ value }) {
  const cfg = PRIORITY_CONFIG[value] || PRIORITY_CONFIG.LOW;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      background: cfg.bg, color: cfg.color,
      border: `1px solid ${cfg.border}`,
      borderRadius: "4px", padding: "0.12rem 0.5rem",
      fontSize: "0.65rem", fontWeight: 700,
      letterSpacing: "0.06em", textTransform: "uppercase",
      fontFamily: "ui-monospace, monospace",
    }}>
      {cfg.label}
    </span>
  );
}

function StatusBadge({ value }) {
  const cfg = STATUS_CONFIG[value] || { color: "#64748b", label: value };
  return (
    <span style={{
      color: cfg.color, fontSize: "0.67rem", fontWeight: 700,
      letterSpacing: "0.06em", textTransform: "uppercase",
      fontFamily: "ui-monospace, monospace",
    }}>
      {"\u25cf"} {cfg.label}
    </span>
  );
}

function EvidenceId({ id }) {
  return (
    <span style={{
      display: "inline-block",
      background: "rgba(56,189,248,0.07)",
      border: "1px solid rgba(56,189,248,0.18)",
      color: "#7dd3fc", borderRadius: "3px",
      padding: "0.08rem 0.4rem", fontSize: "0.67rem",
      fontFamily: "ui-monospace, monospace",
      marginRight: "0.35rem", marginBottom: "0.25rem",
      wordBreak: "break-all",
    }}>
      {id}
    </span>
  );
}

function EntityRefId({ id }) {
  return (
    <span style={{
      display: "inline-block",
      background: "rgba(129,140,248,0.07)",
      border: "1px solid rgba(129,140,248,0.18)",
      color: "#a5b4fc", borderRadius: "3px",
      padding: "0.08rem 0.4rem", fontSize: "0.67rem",
      fontFamily: "ui-monospace, monospace",
      marginRight: "0.35rem", marginBottom: "0.25rem",
      wordBreak: "break-all",
    }}>
      {id}
    </span>
  );
}

const NoticeIcon = () => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, marginTop: 2 }}>
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const ChevronIcon = ({ open }) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
    style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.18s" }}>
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

// ─── Pattern card ──────────────────────────────────────────────────────────────

function PatternCard({ pattern }) {
  const [expanded, setExpanded] = useState(false);
  const typeLabel = PATTERN_TYPE_LABELS[pattern.type] || pattern.type;
  return (
    <div className="intel-card">
      <div className="intel-card-header">
        <div className="intel-card-left">
          <span className="intel-kind-tag pattern-kind">PATTERN</span>
          <span className="intel-type-label">{typeLabel}</span>
        </div>
        <div className="intel-card-right">
          <StatusBadge value={pattern.status} />
          <SeverityBadge value={pattern.severity} />
          <button className="intel-expand-btn" onClick={() => setExpanded(v => !v)} title={expanded ? "Collapse" : "Expand"}>
            <ChevronIcon open={expanded} />
          </button>
        </div>
      </div>
      <p className="intel-explanation">{pattern.explanation}</p>
      {expanded && (
        <div className="intel-details">
          <div className="intel-detail-row">
            <span className="intel-detail-key">Pattern ID</span>
            <span className="intel-detail-val mono">{pattern.id}</span>
          </div>
          {pattern.entities && pattern.entities.length > 0 && (
            <div className="intel-detail-row" style={{ alignItems: "flex-start" }}>
              <span className="intel-detail-key">Entity References</span>
              <div className="intel-detail-val" style={{ display: "flex", flexWrap: "wrap" }}>
                {pattern.entities.map((eid, i) => <EntityRefId key={i} id={eid} />)}
              </div>
            </div>
          )}
          {pattern.evidence_ids && pattern.evidence_ids.length > 0 && (
            <div className="intel-detail-row" style={{ alignItems: "flex-start" }}>
              <span className="intel-detail-key">Evidence References</span>
              <div className="intel-detail-val" style={{ display: "flex", flexWrap: "wrap" }}>
                {pattern.evidence_ids.map((eid, i) => <EvidenceId key={i} id={eid} />)}
              </div>
            </div>
          )}
          <div className="intel-notice">
            <NoticeIcon />
            AI-derived pattern. Status: <strong>{pattern.status}</strong>. Investigator judgement required before any action.
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Lead card ────────────────────────────────────────────────────────────────

function LeadCard({ lead }) {
  const [expanded, setExpanded] = useState(false);
  const typeLabel = LEAD_TYPE_LABELS[lead.type] || lead.type;
  return (
    <div className="intel-card">
      <div className="intel-card-header">
        <div className="intel-card-left">
          <span className="intel-kind-tag lead-kind">LEAD</span>
          <span className="intel-type-label">{typeLabel}</span>
        </div>
        <div className="intel-card-right">
          <StatusBadge value={lead.status} />
          <PriorityBadge value={lead.priority} />
          <button className="intel-expand-btn" onClick={() => setExpanded(v => !v)} title={expanded ? "Collapse" : "Expand"}>
            <ChevronIcon open={expanded} />
          </button>
        </div>
      </div>
      {lead.title && <div className="intel-lead-title">{lead.title}</div>}
      <p className="intel-explanation">{lead.explanation}</p>
      {lead.priority_score != null && (
        <div className="intel-priority-score-bar" title={"Priority score: " + Math.round(lead.priority_score * 100) + "%"}>
          <div className="intel-priority-score-label">
            <span>Priority Score</span>
            <span className="mono">{Math.round(lead.priority_score * 100)}%</span>
          </div>
          <div className="intel-priority-track">
            <div className="intel-priority-fill" style={{ width: Math.round(lead.priority_score * 100) + "%" }} />
          </div>
        </div>
      )}
      {expanded && (
        <div className="intel-details">
          <div className="intel-detail-row">
            <span className="intel-detail-key">Lead ID</span>
            <span className="intel-detail-val mono">{lead.id}</span>
          </div>
          {lead.entity_ids && lead.entity_ids.length > 0 && (
            <div className="intel-detail-row" style={{ alignItems: "flex-start" }}>
              <span className="intel-detail-key">Entity References</span>
              <div className="intel-detail-val" style={{ display: "flex", flexWrap: "wrap" }}>
                {lead.entity_ids.map((eid, i) => <EntityRefId key={i} id={eid} />)}
              </div>
            </div>
          )}
          {lead.evidence_ids && lead.evidence_ids.length > 0 && (
            <div className="intel-detail-row" style={{ alignItems: "flex-start" }}>
              <span className="intel-detail-key">Evidence References</span>
              <div className="intel-detail-val" style={{ display: "flex", flexWrap: "wrap" }}>
                {lead.evidence_ids.map((eid, i) => <EvidenceId key={i} id={eid} />)}
              </div>
            </div>
          )}
          <div className="intel-notice">
            <NoticeIcon />
            Algorithmic lead. Status: <strong>{lead.status}</strong>. Verification and investigator review required.
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function CaseInsightsView({ caseId }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const fetchInsights = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient("/api/cases/" + caseId + "/insights");
      setData(result);
    } catch (err) {
      if (err && err.status === 403) {
        setError({ code: 403, message: "Access denied. You are not authorised to view intelligence for this case." });
      } else if (err && err.status === 401) {
        setError({ code: 401, message: "Authentication required. Please log in again." });
      } else {
        setError({ code: 0, message: "Unable to load case intelligence. Check backend connectivity." });
      }
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => { fetchInsights(); }, [fetchInsights]);

  const patterns = (data && data.patterns) || [];
  const leads    = (data && data.leads)    || [];
  const hasPatterns = patterns.length > 0;
  const hasLeads    = leads.length > 0;
  const isEmpty     = data && !hasPatterns && !hasLeads;

  return (
    <div className="insights-root">
      <style>{`
        .insights-root { display:flex; flex-direction:column; gap:0; }
        .insights-section-bar { display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; }
        .insights-title-group { display:flex; flex-direction:column; gap:0.25rem; }
        .insights-section-title { font-size:0.78rem; font-weight:700; color:#38bdf8; letter-spacing:0.06em; text-transform:uppercase; margin:0; display:flex; align-items:center; gap:0.5rem; }
        .insights-section-desc { font-size:0.78rem; color:#64748b; margin:0; }
        .insights-refresh-btn { display:flex; align-items:center; gap:0.4rem; background:rgba(14,165,233,0.08); border:1px solid rgba(56,189,248,0.22); color:#38bdf8; border-radius:7px; padding:0.45rem 0.85rem; font-size:0.78rem; font-weight:600; cursor:pointer; transition:all 0.15s; letter-spacing:0.02em; }
        .insights-refresh-btn:hover:not(:disabled) { background:rgba(14,165,233,0.18); box-shadow:0 0 10px rgba(56,189,248,0.15); }
        .insights-refresh-btn:disabled { opacity:0.45; cursor:not-allowed; }
        .insights-spin { animation:insights-spin 0.8s linear infinite; }
        @keyframes insights-spin { to { transform:rotate(360deg); } }
        .insights-loading { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:380px; gap:1rem; }
        .insights-loading-spinner { width:36px; height:36px; border:2.5px solid rgba(56,189,248,0.15); border-top-color:#38bdf8; border-radius:50%; animation:insights-spin 0.75s linear infinite; }
        .insights-loading-text { font-size:0.84rem; color:#64748b; }
        .insights-error-block { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:300px; gap:0.85rem; text-align:center; }
        .insights-error-icon { color:#ef4444; }
        .insights-error-title { font-size:0.95rem; font-weight:700; color:#f87171; margin:0; }
        .insights-error-msg { font-size:0.82rem; color:#94a3b8; max-width:380px; line-height:1.55; margin:0; }
        .insights-error-code { font-size:0.72rem; color:#475569; font-family:ui-monospace,monospace; }
        .insights-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:340px; gap:0.9rem; text-align:center; }
        .insights-empty-icon { opacity:0.35; }
        .insights-empty-title { font-size:0.95rem; font-weight:600; color:#64748b; margin:0; }
        .insights-empty-sub { font-size:0.8rem; color:#475569; max-width:400px; line-height:1.6; margin:0; }
        .insights-columns { display:grid; grid-template-columns:1fr 1fr; gap:2rem; align-items:start; }
        @media (max-width:900px) { .insights-columns { grid-template-columns:1fr; } }
        .insights-column-header { display:flex; align-items:center; gap:0.6rem; margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:1px solid rgba(255,255,255,0.06); }
        .insights-column-title { font-size:0.75rem; font-weight:700; letter-spacing:0.07em; text-transform:uppercase; margin:0; }
        .insights-column-count { margin-left:auto; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.25); color:#38bdf8; border-radius:10px; padding:0.1rem 0.5rem; font-size:0.67rem; font-weight:700; font-family:ui-monospace,monospace; }
        .intel-card { background:rgba(10,15,30,0.85); border:1px solid rgba(56,189,248,0.12); border-radius:10px; padding:1rem 1.1rem; margin-bottom:0.85rem; transition:border-color 0.15s; }
        .intel-card:hover { border-color:rgba(56,189,248,0.25); }
        .intel-card-header { display:flex; justify-content:space-between; align-items:center; gap:0.5rem; flex-wrap:wrap; margin-bottom:0.65rem; }
        .intel-card-left { display:flex; align-items:center; gap:0.6rem; min-width:0; }
        .intel-card-right { display:flex; align-items:center; gap:0.5rem; flex-shrink:0; }
        .intel-kind-tag { font-size:0.6rem; font-weight:800; letter-spacing:0.07em; text-transform:uppercase; border-radius:3px; padding:0.1rem 0.4rem; flex-shrink:0; font-family:ui-monospace,monospace; }
        .pattern-kind { background:rgba(14,165,233,0.14); color:#38bdf8; border:1px solid rgba(56,189,248,0.3); }
        .lead-kind { background:rgba(20,184,166,0.12); color:#2dd4bf; border:1px solid rgba(45,212,191,0.3); }
        .intel-type-label { font-size:0.82rem; font-weight:600; color:#e2e8f0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .intel-expand-btn { background:none; border:1px solid rgba(255,255,255,0.08); border-radius:5px; color:#64748b; cursor:pointer; padding:0.2rem; display:flex; align-items:center; transition:all 0.15s; }
        .intel-expand-btn:hover { border-color:rgba(56,189,248,0.25); color:#94a3b8; }
        .intel-lead-title { font-size:0.82rem; font-weight:600; color:#94a3b8; margin-bottom:0.4rem; font-style:italic; }
        .intel-explanation { font-size:0.82rem; color:#94a3b8; line-height:1.6; margin:0; }
        .intel-priority-score-bar { margin-top:0.75rem; }
        .intel-priority-score-label { display:flex; justify-content:space-between; font-size:0.7rem; color:#64748b; margin-bottom:0.3rem; }
        .intel-priority-track { height:4px; background:rgba(255,255,255,0.07); border-radius:2px; overflow:hidden; }
        .intel-priority-fill { height:100%; background:linear-gradient(90deg,#38bdf8,#818cf8); border-radius:2px; }
        .intel-details { margin-top:0.9rem; padding-top:0.85rem; border-top:1px solid rgba(255,255,255,0.05); display:flex; flex-direction:column; gap:0.6rem; }
        .intel-detail-row { display:flex; gap:0.75rem; align-items:center; }
        .intel-detail-key { font-size:0.69rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.04em; min-width:120px; flex-shrink:0; }
        .intel-detail-val { font-size:0.79rem; color:#cbd5e1; line-height:1.5; word-break:break-all; }
        .mono { font-family:ui-monospace,monospace; font-size:0.72rem !important; }
        .intel-notice { display:flex; align-items:flex-start; gap:0.45rem; font-size:0.72rem; color:#475569; line-height:1.5; background:rgba(255,255,255,0.025); border:1px solid rgba(255,255,255,0.06); border-radius:6px; padding:0.5rem 0.7rem; margin-top:0.25rem; }
        .intel-notice strong { color:#64748b; }
        .insights-positioning { margin-top:2rem; padding:0.85rem 1.1rem; background:rgba(14,165,233,0.04); border:1px solid rgba(56,189,248,0.1); border-radius:8px; font-size:0.76rem; color:#475569; line-height:1.6; display:flex; align-items:flex-start; gap:0.55rem; }
        .insights-positioning svg { flex-shrink:0; margin-top:2px; color:#38bdf8; opacity:0.6; }
      `}</style>

      {/* Header */}
      <div className="insights-section-bar">
        <div className="insights-title-group">
          <h2 className="insights-section-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            Intelligence
          </h2>
          <p className="insights-section-desc">AI-discovered patterns and investigative leads. Investigator review required.</p>
        </div>
        <button className="insights-refresh-btn" onClick={fetchInsights} disabled={loading} title="Refresh intelligence">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
            className={loading ? "insights-spin" : ""}>
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="insights-loading">
          <div className="insights-loading-spinner" />
          <p className="insights-loading-text">Loading case intelligence...</p>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="insights-error-block">
          <div className="insights-error-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h3 className="insights-error-title">
            {error.code === 403 ? "Access Restricted" : error.code === 401 ? "Authentication Required" : "Intelligence Unavailable"}
          </h3>
          <p className="insights-error-msg">{error.message}</p>
          {error.code > 0 && <span className="insights-error-code">HTTP {error.code}</span>}
        </div>
      )}

      {/* Empty */}
      {!loading && !error && isEmpty && (
        <div className="insights-empty">
          <div className="insights-empty-icon">
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="1.2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          </div>
          <h3 className="insights-empty-title">No Intelligence Generated</h3>
          <p className="insights-empty-sub">
            No intelligence patterns or leads have been generated for this case yet.
            Intelligence is derived from evidence processing — upload and process documents
            to enable pattern detection.
          </p>
        </div>
      )}

      {/* Results */}
      {!loading && !error && data && (hasPatterns || hasLeads) && (
        <>
          <div className="insights-columns">
            <div>
              <div className="insights-column-header">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2.5">
                  <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <h3 className="insights-column-title" style={{ color: "#38bdf8" }}>Patterns</h3>
                <span className="insights-column-count">{patterns.length}</span>
              </div>
              {!hasPatterns
                ? <div style={{ fontSize: "0.8rem", color: "#475569", padding: "1rem 0" }}>No patterns detected for this case.</div>
                : patterns.map(p => <PatternCard key={p.id} pattern={p} />)
              }
            </div>
            <div>
              <div className="insights-column-header">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" strokeWidth="2.5">
                  <line x1="12" y1="5" x2="12" y2="19" /><polyline points="19 12 12 19 5 12" />
                </svg>
                <h3 className="insights-column-title" style={{ color: "#2dd4bf" }}>Investigative Leads</h3>
                <span className="insights-column-count">{leads.length}</span>
              </div>
              {!hasLeads
                ? <div style={{ fontSize: "0.8rem", color: "#475569", padding: "1rem 0" }}>No investigative leads for this case.</div>
                : leads.map(l => <LeadCard key={l.id} lead={l} />)
              }
            </div>
          </div>

          <div className="insights-positioning">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>
              <strong style={{ color: "#64748b" }}>Investigator Responsibility: </strong>
              AI discovers. Graph connects. Evidence supports. Investigator decides.
              Patterns and leads are algorithmic hypotheses — not determinations of fact or culpability.
              All intelligence must be independently verified before any operational action.
            </span>
          </div>
        </>
      )}
    </div>
  );
}
