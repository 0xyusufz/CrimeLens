"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient } from "../lib/apiClient";

const ENTITY_CONFIG = {
  PERSON: { color: "#38bdf8", bg: "rgba(14,165,233,0.12)", label: "Person" },
  PHONE: { color: "#34d399", bg: "rgba(16,185,129,0.12)", label: "Phone" },
  BANK_ACCOUNT: { color: "#fbbf24", bg: "rgba(245,158,11,0.12)", label: "Bank Account" },
  VEHICLE: { color: "#818cf8", bg: "rgba(99,102,241,0.12)", label: "Vehicle" },
  ORGANIZATION: { color: "#2dd4bf", bg: "rgba(20,184,166,0.12)", label: "Organization" },
  LOCATION: { color: "#fb923c", bg: "rgba(249,115,22,0.12)", label: "Location" },
  EVENT: { color: "#f472b6", bg: "rgba(236,72,153,0.12)", label: "Event" },
};

const RELATIONSHIP_COLORS = {
  CONFIRMED: { stroke: "#38bdf8", label: "CONFIRMED", dot: "#38bdf8" },
  INFERRED: { stroke: "#818cf8", label: "INFERRED", dot: "#818cf8" },
  PREDICTED: { stroke: "#f59e0b", label: "PREDICTED", dot: "#f59e0b" },
};

function EntityTypeTag({ type }) {
  const cfg = ENTITY_CONFIG[type] || ENTITY_CONFIG.PERSON;
  return (
    <span
      style={{
        display: "inline-block",
        background: cfg.bg,
        color: cfg.color,
        fontSize: "0.62rem",
        fontWeight: 700,
        letterSpacing: "0.05em",
        textTransform: "uppercase",
        borderRadius: "4px",
        padding: "0.15rem 0.45rem",
        fontFamily: "ui-monospace, monospace",
        marginBottom: "0.4rem",
      }}
    >
      {cfg.label}
    </span>
  );
}

function PathNodeCard({ node, isSource, isTarget, stepIndex }) {
  const borderColor = isSource ? "#38bdf8" : isTarget ? "#22c55e" : "rgba(148, 163, 184, 0.25)";
  const bgGradient = isSource
    ? "linear-gradient(180deg, rgba(14,165,233,0.12) 0%, rgba(10,15,30,0.92) 100%)"
    : isTarget
    ? "linear-gradient(180deg, rgba(34,197,94,0.12) 0%, rgba(10,15,30,0.92) 100%)"
    : "linear-gradient(180deg, rgba(30,41,59,0.5) 0%, rgba(10,15,30,0.92) 100%)";
  const glowColor = isSource
    ? "rgba(56,189,248,0.2)"
    : isTarget
    ? "rgba(34,197,94,0.2)"
    : "transparent";

  return (
    <div
      className="path-node-card"
      style={{
        border: `1.5px solid ${borderColor}`,
        background: bgGradient,
        boxShadow: `0 4px 16px ${glowColor}`,
      }}
    >
      <div className="path-node-top">
        <EntityTypeTag type={node.type} />
        <span
          className="path-node-badge"
          style={{
            color: isSource ? "#38bdf8" : isTarget ? "#22c55e" : "#94a3b8",
            borderColor: isSource ? "rgba(56,189,248,0.3)" : isTarget ? "rgba(34,197,94,0.3)" : "rgba(148,163,184,0.2)",
          }}
        >
          {isSource ? "SOURCE" : isTarget ? "TARGET" : `STEP ${stepIndex}`}
        </span>
      </div>
      <div className="path-node-name" title={node.name}>
        {node.name}
      </div>
    </div>
  );
}

function PathRelationshipArrow({ rel, onClick, isSelected }) {
  const cfg = RELATIONSHIP_COLORS[rel.status] || RELATIONSHIP_COLORS.CONFIRMED;
  const confidence = rel.confidence != null ? Math.round(rel.confidence * 100) : null;

  return (
    <button
      className={`path-rel-arrow${isSelected ? " path-rel-arrow-active" : ""}`}
      onClick={() => onClick(rel)}
      style={{ "--rel-color": cfg.stroke }}
      title="Click to view evidence details"
    >
      <div className="path-rel-pill">
        <span className="path-rel-type">{rel.relationship}</span>
        {confidence != null && (
          <span className="path-rel-confidence" style={{ color: cfg.stroke }}>
            {confidence}%
          </span>
        )}
      </div>
      <div className="path-rel-line">
        <div className="path-rel-line-bar" />
        <svg width="12" height="12" viewBox="0 0 10 10" className="path-rel-arrowhead">
          <polygon points="0,1 9,5 0,9" fill={cfg.stroke} />
        </svg>
      </div>
    </button>
  );
}

export default function InvestigationPathView({ caseId }) {
  const [entities, setEntities] = useState([]);
  const [loadingEntities, setLoadingEntities] = useState(true);
  const [entityError, setEntityError] = useState(null);

  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");

  const [querying, setQuerying] = useState(false);
  const [pathResult, setPathResult] = useState(null);
  const [pathError, setPathError] = useState(null);
  const [hasQueried, setHasQueried] = useState(false);

  const [selectedRel, setSelectedRel] = useState(null);
  const [evidenceData, setEvidenceData] = useState(null);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState(null);

  const loadEntities = useCallback(async () => {
    if (!caseId) return;
    setLoadingEntities(true);
    setEntityError(null);
    try {
      const data = await apiClient(`/api/cases/${caseId}/graph`);
      const rawNodes = data?.nodes || [];
      setEntities(rawNodes.map((n) => ({ id: n.entity_id, name: n.name, type: n.type })));
    } catch {
      setEntityError("Unable to load case entities for path selection.");
    } finally {
      setLoadingEntities(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadEntities();
  }, [loadEntities]);

  const handleQuery = async (e) => {
    if (e) e.preventDefault();
    if (!sourceId || !targetId || sourceId === targetId || querying) return;
    setQuerying(true);
    setPathError(null);
    setPathResult(null);
    setSelectedRel(null);
    setEvidenceData(null);
    setHasQueried(true);
    try {
      const params = new URLSearchParams({
        case_id: caseId,
        source_entity_id: sourceId,
        target_entity_id: targetId,
        max_hops: 5,
      });
      const result = await apiClient(`/api/investigation/path?${params.toString()}`);
      setPathResult(result);
    } catch (err) {
      if (err?.status === 404) setPathError("One or both entities were not found in this case.");
      else if (err?.status === 403) setPathError("Access denied. You are not authorized to investigate this case.");
      else setPathError("Failed to retrieve connection path. Please check connectivity.");
    } finally {
      setQuerying(false);
    }
  };

  const handleRelClick = async (rel) => {
    if (selectedRel?.relationship_id === rel.relationship_id) {
      setSelectedRel(null);
      setEvidenceData(null);
      return;
    }
    setSelectedRel(rel);
    setEvidenceData(null);
    setEvidenceError(null);
    setLoadingEvidence(true);
    try {
      const evidence = await apiClient(`/api/relationships/${rel.relationship_id}/evidence`);
      setEvidenceData(evidence);
    } catch {
      setEvidenceError("Evidence data unavailable for this relationship.");
    } finally {
      setLoadingEvidence(false);
    }
  };

  const closeEvidence = () => {
    setSelectedRel(null);
    setEvidenceData(null);
    setEvidenceError(null);
  };

  const isFormReady = sourceId && targetId && sourceId !== targetId;

  const buildChain = () => {
    if (!pathResult || !pathResult.found) return null;
    const nodes = pathResult.nodes || [];
    const rels = pathResult.relationships || [];
    if (nodes.length === 0) return null;
    const chain = [{ kind: "node", data: nodes[0] }];
    rels.forEach((rel, idx) => {
      chain.push({ kind: "rel", data: rel });
      if (nodes[idx + 1]) chain.push({ kind: "node", data: nodes[idx + 1] });
    });
    return chain;
  };

  const chain = buildChain();

  return (
    <div className="path-view-root">
      <style>{`
        .path-view-root { display: flex; gap: 1.5rem; min-height: 480px; }
        .path-form-panel {
          width: 300px;
          flex-shrink: 0;
          background: rgba(15, 23, 42, 0.8);
          border: 1px solid rgba(56, 189, 248, 0.16);
          border-radius: 12px;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
          height: fit-content;
        }
        .path-form-title {
          font-size: 0.85rem;
          font-weight: 700;
          color: #38bdf8;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        .path-form-group { display: flex; flex-direction: column; gap: 0.4rem; }
        .path-form-label {
          font-size: 0.72rem;
          font-weight: 600;
          color: #94a3b8;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }
        .path-form-select {
          width: 100%;
          background: rgba(10, 15, 30, 0.85);
          border: 1px solid rgba(56, 189, 248, 0.2);
          border-radius: 8px;
          color: #f1f5f9;
          font-size: 0.85rem;
          padding: 0.6rem 2rem 0.6rem 0.75rem;
          outline: none;
          cursor: pointer;
          transition: border-color 0.15s;
          appearance: none;
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2338bdf8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-position: right 0.65rem center;
        }
        .path-form-select:focus {
          border-color: rgba(56, 189, 248, 0.5);
          box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.1);
        }
        .path-form-select option { background: #0f172a; color: #f1f5f9; }
        .path-query-btn {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          background: rgba(14, 165, 233, 0.2);
          border: 1px solid rgba(56, 189, 248, 0.45);
          border-radius: 8px;
          color: #38bdf8;
          font-size: 0.85rem;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s;
          letter-spacing: 0.02em;
          margin-top: 0.5rem;
        }
        .path-query-btn:hover:not(:disabled) {
          background: rgba(14, 165, 233, 0.32);
          box-shadow: 0 0 16px rgba(56, 189, 248, 0.25);
        }
        .path-query-btn:disabled { opacity: 0.45; cursor: not-allowed; }
        .path-same-warn { font-size: 0.72rem; color: #f59e0b; display: flex; align-items: center; gap: 0.35rem; }
        .path-result-panel {
          flex: 1;
          min-width: 0;
          background: rgba(15, 23, 42, 0.8);
          border: 1px solid rgba(56, 189, 248, 0.14);
          border-radius: 12px;
          padding: 1.75rem;
          position: relative;
        }
        .path-idle-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 380px;
          text-align: center;
          gap: 1rem;
        }
        .path-idle-icon { opacity: 0.4; }
        .path-idle-title { font-size: 0.95rem; font-weight: 600; color: #64748b; margin: 0; }
        .path-idle-sub { font-size: 0.82rem; color: #475569; max-width: 320px; line-height: 1.5; margin: 0; }
        .path-querying-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 380px;
          gap: 1rem;
        }
        .path-querying-spinner {
          width: 36px;
          height: 36px;
          border: 2.5px solid rgba(56, 189, 248, 0.2);
          border-top-color: #38bdf8;
          border-radius: 50%;
          animation: path-spin 0.7s linear infinite;
        }
        @keyframes path-spin { to { transform: rotate(360deg); } }
        .path-querying-text { font-size: 0.85rem; color: #94a3b8; }
        .path-error-card {
          background: rgba(239, 68, 68, 0.08);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 10px;
          padding: 1.25rem 1.5rem;
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          margin-bottom: 1.5rem;
        }
        .path-error-icon { color: #ef4444; flex-shrink: 0; margin-top: 1px; }
        .path-error-text { font-size: 0.84rem; color: #fca5a5; line-height: 1.5; }
        .path-not-found {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 300px;
          gap: 0.75rem;
          text-align: center;
        }
        .path-not-found-icon { color: #475569; opacity: 0.6; }
        .path-not-found-title { font-size: 1rem; font-weight: 700; color: #64748b; margin: 0; }
        .path-not-found-sub { font-size: 0.82rem; color: #475569; max-width: 360px; line-height: 1.5; margin: 0; }
        .path-result-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
          flex-wrap: wrap;
          gap: 0.75rem;
        }
        .path-result-title {
          font-size: 0.88rem;
          font-weight: 700;
          color: #38bdf8;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        .path-hop-badge {
          background: rgba(14, 165, 233, 0.15);
          border: 1px solid rgba(56, 189, 248, 0.35);
          border-radius: 5px;
          padding: 0.15rem 0.5rem;
          font-size: 0.72rem;
          font-weight: 700;
          color: #38bdf8;
          font-family: ui-monospace, monospace;
        }
        .path-chain-container {
          overflow-x: auto;
          padding: 1.5rem 0.5rem;
          background: rgba(10, 15, 30, 0.6);
          border: 1px solid rgba(56, 189, 248, 0.12);
          border-radius: 12px;
          margin-bottom: 1.5rem;
        }
        .path-chain {
          display: flex;
          align-items: center;
          min-width: max-content;
          padding: 0.5rem 1rem;
          gap: 0.25rem;
        }
        .path-node-card {
          border-radius: 10px;
          padding: 0.85rem 1.1rem;
          min-width: 150px;
          max-width: 220px;
          flex-shrink: 0;
          transition: transform 0.15s, box-shadow 0.15s;
        }
        .path-node-card:hover {
          transform: translateY(-2px);
        }
        .path-node-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.5rem;
        }
        .path-node-badge {
          font-size: 0.58rem;
          font-weight: 800;
          letter-spacing: 0.08em;
          border: 1px solid;
          border-radius: 3px;
          padding: 0.1rem 0.35rem;
          font-family: ui-monospace, monospace;
        }
        .path-node-name {
          font-size: 0.9rem;
          font-weight: 700;
          color: #f8fafc;
          word-break: break-word;
          line-height: 1.35;
        }
        .path-rel-arrow {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.35rem;
          padding: 0.5rem 0.75rem;
          background: transparent;
          border: 1px solid transparent;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.15s;
          flex-shrink: 0;
          min-width: 140px;
        }
        .path-rel-arrow:hover {
          background: rgba(56, 189, 248, 0.08);
          border-color: rgba(56, 189, 248, 0.25);
        }
        .path-rel-arrow-active {
          background: rgba(56, 189, 248, 0.14);
          border-color: rgba(56, 189, 248, 0.45);
          box-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
        }
        .path-rel-pill {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          background: rgba(15, 23, 42, 0.9);
          border: 1px solid rgba(56, 189, 248, 0.2);
          border-radius: 6px;
          padding: 0.2rem 0.55rem;
        }
        .path-rel-type {
          font-size: 0.68rem;
          font-weight: 700;
          color: #cbd5e1;
          font-family: ui-monospace, monospace;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }
        .path-rel-confidence {
          font-size: 0.62rem;
          font-weight: 700;
          font-family: ui-monospace, monospace;
        }
        .path-rel-line {
          display: flex;
          align-items: center;
          width: 100%;
          padding: 0 2px;
        }
        .path-rel-line-bar {
          flex: 1;
          height: 2.5px;
          background: var(--rel-color, #38bdf8);
          opacity: 0.85;
          border-radius: 2px;
        }
        .path-rel-arrowhead {
          flex-shrink: 0;
          margin-left: -2px;
          opacity: 0.9;
        }
        .path-evidence-panel {
          background: rgba(10, 15, 30, 0.85);
          border: 1px solid rgba(56, 189, 248, 0.25);
          border-radius: 10px;
          overflow: hidden;
          animation: fadeInUp 0.2s ease;
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .path-evidence-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.85rem 1.1rem;
          background: rgba(14, 165, 233, 0.08);
          border-bottom: 1px solid rgba(56, 189, 248, 0.15);
        }
        .path-evidence-title {
          font-size: 0.78rem;
          font-weight: 700;
          color: #38bdf8;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        .path-evidence-close {
          background: none;
          border: none;
          color: #64748b;
          cursor: pointer;
          padding: 0.2rem;
          display: flex;
          align-items: center;
          border-radius: 4px;
          transition: color 0.15s;
        }
        .path-evidence-close:hover { color: #f1f5f9; }
        .path-evidence-body { padding: 1.1rem; display: flex; flex-direction: column; gap: 0.75rem; }
        .path-ev-loading { display: flex; align-items: center; gap: 0.65rem; color: #64748b; font-size: 0.82rem; }
        .path-ev-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(56, 189, 248, 0.2);
          border-top-color: #38bdf8;
          border-radius: 50%;
          animation: path-spin 0.7s linear infinite;
          flex-shrink: 0;
        }
        .path-ev-row { display: flex; gap: 0.5rem; align-items: flex-start; }
        .path-ev-key {
          font-size: 0.72rem;
          font-weight: 600;
          color: #64748b;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          min-width: 110px;
          flex-shrink: 0;
          padding-top: 1px;
        }
        .path-ev-val {
          font-size: 0.82rem;
          color: #cbd5e1;
          line-height: 1.5;
          word-break: break-word;
          font-family: ui-monospace, monospace;
        }
        .path-ev-snippet {
          background: rgba(56, 189, 248, 0.06);
          border-left: 3px solid rgba(56, 189, 248, 0.35);
          padding: 0.6rem 0.85rem;
          border-radius: 0 6px 6px 0;
          font-size: 0.82rem;
          color: #94a3b8;
          line-height: 1.6;
          font-style: italic;
          word-break: break-word;
          white-space: pre-wrap;
          margin: 0;
        }
        .path-ev-error { font-size: 0.8rem; color: #fca5a5; }
        .path-entity-loading { display: flex; align-items: center; gap: 0.5rem; color: #64748b; font-size: 0.8rem; }
        .path-mini-spinner {
          width: 14px;
          height: 14px;
          border: 2px solid rgba(56, 189, 248, 0.2);
          border-top-color: #38bdf8;
          border-radius: 50%;
          animation: path-spin 0.7s linear infinite;
          flex-shrink: 0;
        }
      `}</style>

      {/* LEFT: SELECTION FORM */}
      <form className="path-form-panel" onSubmit={handleQuery}>
        <h2 className="path-form-title">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          Connection Finder
        </h2>

        <div className="path-form-group">
          <label className="path-form-label">First Person / Entity</label>
          {loadingEntities ? (
            <div className="path-entity-loading">
              <div className="path-mini-spinner" />
              <span>Loading entities...</span>
            </div>
          ) : entityError ? (
            <div style={{ fontSize: "0.75rem", color: "#fca5a5" }}>{entityError}</div>
          ) : (
            <select
              className="path-form-select"
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              required
            >
              <option value="">Select first entity...</option>
              {entities.map((e) => (
                <option key={e.id} value={e.id}>
                  [{ENTITY_CONFIG[e.type]?.label || e.type}] {e.name}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="path-form-group">
          <label className="path-form-label">Second Entity (Connect To)</label>
          {loadingEntities ? (
            <div className="path-entity-loading">
              <div className="path-mini-spinner" />
              <span>Loading entities...</span>
            </div>
          ) : entityError ? null : (
            <select
              className="path-form-select"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              required
            >
              <option value="">Select second entity...</option>
              {entities.map((e) => (
                <option key={e.id} value={e.id}>
                  [{ENTITY_CONFIG[e.type]?.label || e.type}] {e.name}
                </option>
              ))}
            </select>
          )}
          {sourceId && targetId && sourceId === targetId && (
            <div className="path-same-warn">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              Please choose two different entities
            </div>
          )}
        </div>

        <button
          type="submit"
          className="path-query-btn"
          disabled={!isFormReady || querying || loadingEntities}
        >
          {querying ? (
            <>
              <div className="path-mini-spinner" />
              <span>Tracing Connection...</span>
            </>
          ) : (
            <>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <span>Find Connection</span>
            </>
          )}
        </button>
      </form>

      {/* RIGHT: FLOW BOXES RESULT PANEL */}
      <div className="path-result-panel">
        {!hasQueried && !querying && (
          <div className="path-idle-state">
            <svg className="path-idle-icon" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="1.2">
              <rect x="2" y="7" width="6" height="10" rx="2" />
              <rect x="16" y="7" width="6" height="10" rx="2" />
              <line x1="8" y1="12" x2="16" y2="12" />
            </svg>
            <h3 className="path-idle-title">Select Entities to Trace Connection</h3>
            <p className="path-idle-sub">Choose a person or entity on the left and a target entity to see exactly how they are connected in this case.</p>
          </div>
        )}

        {querying && (
          <div className="path-querying-state">
            <div className="path-querying-spinner" />
            <p className="path-querying-text">Searching relationship paths across case documents...</p>
          </div>
        )}

        {!querying && pathError && (
          <div className="path-error-card">
            <div className="path-error-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <div className="path-error-text">{pathError}</div>
          </div>
        )}

        {!querying && pathResult && !pathResult.found && (
          <div className="path-not-found">
            <div className="path-not-found-icon">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                <line x1="8" y1="11" x2="14" y2="11" />
              </svg>
            </div>
            <h3 className="path-not-found-title">No Direct or Indirect Connection Found</h3>
            <p className="path-not-found-sub">These two entities do not have an evidence-supported connection chain in the current case records.</p>
          </div>
        )}

        {!querying && pathResult && pathResult.found && chain && (
          <>
            <div className="path-result-header">
              <h3 className="path-result-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                Connection Flow
                <span className="path-hop-badge">
                  {pathResult.hop_count} {pathResult.hop_count === 1 ? "step" : "steps"}
                </span>
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                Click any arrow to view evidence document snippet
              </span>
            </div>

            {/* BOX FLOW CONTAINER */}
            <div className="path-chain-container">
              <div className="path-chain">
                {chain.map((item, idx) => {
                  if (item.kind === "node") {
                    const nodeIndex = Math.floor(idx / 2) + 1;
                    return (
                      <PathNodeCard
                        key={`node-${idx}`}
                        node={item.data}
                        isSource={item.data.entity_id === pathResult.source_entity_id}
                        isTarget={item.data.entity_id === pathResult.target_entity_id}
                        stepIndex={nodeIndex}
                      />
                    );
                  }
                  return (
                    <PathRelationshipArrow
                      key={`rel-${idx}`}
                      rel={item.data}
                      onClick={handleRelClick}
                      isSelected={selectedRel?.relationship_id === item.data.relationship_id}
                    />
                  );
                })}
              </div>
            </div>

            {selectedRel && (
              <div className="path-evidence-panel">
                <div className="path-evidence-header">
                  <h4 className="path-evidence-title">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    Evidence Details
                  </h4>
                  <button className="path-evidence-close" onClick={closeEvidence} title="Close">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
                <div className="path-evidence-body">
                  {loadingEvidence ? (
                    <div className="path-ev-loading">
                      <div className="path-ev-spinner" />
                      <span>Loading evidence record...</span>
                    </div>
                  ) : evidenceError ? (
                    <div className="path-ev-error">{evidenceError}</div>
                  ) : evidenceData ? (
                    <>
                      <div className="path-ev-row">
                        <span className="path-ev-key">Relationship</span>
                        <span className="path-ev-val">{evidenceData.relationship || selectedRel.relationship}</span>
                      </div>
                      <div className="path-ev-row">
                        <span className="path-ev-key">Confidence</span>
                        <span className="path-ev-val">
                          {evidenceData.confidence != null
                            ? `${Math.round(evidenceData.confidence * 100)}%`
                            : selectedRel.confidence != null
                            ? `${Math.round(selectedRel.confidence * 100)}%`
                            : "N/A"}
                        </span>
                      </div>
                      {evidenceData.evidence_snippet && (
                        <>
                          <div className="path-ev-row">
                            <span className="path-ev-key">Evidence Snippet</span>
                          </div>
                          <blockquote className="path-ev-snippet">{evidenceData.evidence_snippet}</blockquote>
                        </>
                      )}
                    </>
                  ) : (
                    <div style={{ fontSize: "0.8rem", color: "#475569" }}>No evidence data loaded.</div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
