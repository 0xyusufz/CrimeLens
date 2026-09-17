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
    <span style={{
      display: "inline-block",
      background: cfg.bg,
      color: cfg.color,
      fontSize: "0.6rem",
      fontWeight: 700,
      letterSpacing: "0.05em",
      textTransform: "uppercase",
      borderRadius: "3px",
      padding: "0.1rem 0.35rem",
      fontFamily: "ui-monospace, monospace",
      marginBottom: "0.3rem",
    }}>
      {cfg.label}
    </span>
  );
}

function PathNodeCard({ node, isSource, isTarget }) {
  const borderColor = isSource ? "#38bdf8" : isTarget ? "#f472b6" : "rgba(56,189,248,0.2)";
  const glowColor = isSource ? "rgba(56,189,248,0.25)" : isTarget ? "rgba(244,114,182,0.25)" : "transparent";
  return (
    <div className="path-node-card" style={{ borderColor, boxShadow: `0 0 14px ${glowColor}` }}>
      <EntityTypeTag type={node.type} />
      <div className="path-node-name" title={node.name}>{node.name}</div>
      {(isSource || isTarget) && (
        <div className="path-node-role" style={{ color: isSource ? "#38bdf8" : "#f472b6" }}>
          {isSource ? "SOURCE" : "TARGET"}
        </div>
      )}
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
      title="Click to view evidence"
    >
      <div className="path-rel-line">
        <div className="path-rel-line-bar" />
        <svg width="10" height="10" viewBox="0 0 10 10" className="path-rel-arrowhead">
          <polygon points="0,0 10,5 0,10" fill={cfg.stroke} />
        </svg>
      </div>
      <div className="path-rel-label">
        <span className="path-rel-type">{rel.relationship}</span>
        {confidence != null && <span className="path-rel-confidence" style={{ color: cfg.stroke }}>{confidence}%</span>}
        <span className="path-rel-status" style={{ color: cfg.dot }}>{cfg.label}</span>
      </div>
    </button>
  );
}

function PathNetworkVisualizer({ chain, pathResult }) {
  if (!chain || chain.length < 2) return null;
  const nodes = chain.filter((c) => c.kind === "node").map((c) => c.data);
  if (nodes.length < 2) return null;

  const width = Math.min(800, Math.max(480, nodes.length * 150));
  const height = 180;
  const padding = 70;

  const points = nodes.map((n, idx) => {
    const x = padding + (idx / (nodes.length - 1)) * (width - padding * 2);
    const isEnd = idx === 0 || idx === nodes.length - 1;
    const y = isEnd ? height / 2 : height / 2 + (idx % 2 === 1 ? -24 : 24);
    return {
      x,
      y,
      node: n,
      isSource: n.entity_id === pathResult.source_entity_id,
      isTarget: n.entity_id === pathResult.target_entity_id,
    };
  });

  return (
    <div className="path-network-visualizer">
      <div className="visualizer-header">
        <span className="visualizer-badge">3D Network Topology</span>
        <span className="visualizer-hint">Source (Red) ➔ Intermediate Network ➔ Target (Green)</span>
      </div>
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="path-network-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id="pathRedSphere" cx="35%" cy="28%" r="65%">
            <stop offset="0%" stopColor="#ffe4e6" />
            <stop offset="22%" stopColor="#fca5a5" />
            <stop offset="60%" stopColor="#ef4444" />
            <stop offset="90%" stopColor="#b91c1c" />
            <stop offset="100%" stopColor="#7f1d1d" />
          </radialGradient>

          <radialGradient id="pathGreenSphere" cx="35%" cy="28%" r="65%">
            <stop offset="0%" stopColor="#dcfce7" />
            <stop offset="22%" stopColor="#86efac" />
            <stop offset="60%" stopColor="#22c55e" />
            <stop offset="90%" stopColor="#15803d" />
            <stop offset="100%" stopColor="#14532d" />
          </radialGradient>

          <radialGradient id="pathBlueSphere" cx="35%" cy="28%" r="65%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="24%" stopColor="#d5e0eb" />
            <stop offset="65%" stopColor="#839ab4" />
            <stop offset="92%" stopColor="#3e546d" />
            <stop offset="100%" stopColor="#223243" />
          </radialGradient>

          <radialGradient id="pathSphereShadow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(15, 23, 42, 0.48)" />
            <stop offset="50%" stopColor="rgba(15, 23, 42, 0.18)" />
            <stop offset="85%" stopColor="transparent" />
          </radialGradient>
        </defs>

        {/* Straight Edges */}
        {points.map((p, idx) => {
          if (idx === points.length - 1) return null;
          const next = points[idx + 1];
          const isSourceEdge = idx === 0;
          const isTargetEdge = idx === points.length - 2;
          let strokeColor = "#1e293b";
          if (isSourceEdge) strokeColor = "#ef4444";
          else if (isTargetEdge) strokeColor = "#22c55e";

          return (
            <line
              key={`line-${idx}`}
              x1={p.x}
              y1={p.y}
              x2={next.x}
              y2={next.y}
              stroke={strokeColor}
              strokeWidth={isSourceEdge || isTargetEdge ? 3 : 2.4}
              strokeLinecap="round"
            />
          );
        })}

        {/* 3D Spheres */}
        {points.map((p, idx) => {
          const gradId = p.isSource ? "url(#pathRedSphere)" : p.isTarget ? "url(#pathGreenSphere)" : "url(#pathBlueSphere)";
          const borderColor = p.isSource ? "rgba(127, 29, 29, 0.75)" : p.isTarget ? "rgba(20, 83, 45, 0.75)" : "rgba(34, 50, 67, 0.7)";

          return (
            <g key={`sphere-${idx}`} className="path-svg-node-group">
              {/* Ground Shadow */}
              <ellipse
                cx={p.x - 3}
                cy={p.y + 23}
                rx={19}
                ry={6.5}
                fill="url(#pathSphereShadow)"
              />

              {/* 3D Sphere */}
              <circle
                cx={p.x}
                cy={p.y}
                r={21}
                fill={gradId}
                stroke={borderColor}
                strokeWidth={1.5}
              />

              {/* Specular Highlight Glint */}
              <ellipse
                cx={p.x - 6}
                cy={p.y - 7}
                rx={4.5}
                ry={2.8}
                fill="rgba(255, 255, 255, 0.88)"
                transform={`rotate(-25 ${p.x - 6} ${p.y - 7})`}
              />

              {/* Text Label Below */}
              <text
                x={p.x}
                y={p.y + 37}
                textAnchor="middle"
                fontSize={11}
                fontWeight={650}
                fill="#1e293b"
              >
                {p.node.name?.length > 15 ? p.node.name.slice(0, 13) + "…" : p.node.name}
              </text>
              <text
                x={p.x}
                y={p.y + 49}
                textAnchor="middle"
                fontSize={9}
                fontWeight={700}
                fill={p.isSource ? "#ef4444" : p.isTarget ? "#22c55e" : "#64748b"}
              >
                {p.isSource ? "SOURCE" : p.isTarget ? "TARGET" : (p.node.type || "INTERMEDIATE")}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function InvestigationPathView({ caseId }) {
  const [entities, setEntities] = useState([]);
  const [loadingEntities, setLoadingEntities] = useState(true);
  const [entityError, setEntityError] = useState(null);

  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [maxHops, setMaxHops] = useState(3);

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
    e.preventDefault();
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
        max_hops: maxHops,
      });
      const result = await apiClient(`/api/investigation/path?${params.toString()}`);
      setPathResult(result);
    } catch (err) {
      if (err?.status === 404) setPathError("One or both entities were not found in this case.");
      else if (err?.status === 403) setPathError("Access denied. You are not authorized to investigate this case.");
      else if (err?.status === 422) setPathError("Invalid hop limit. Must be between 1 and 5.");
      else setPathError("Failed to retrieve investigation path. Please verify backend connectivity.");
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
        .path-view-root { display:flex; gap:1.5rem; min-height:520px; }
        .path-form-panel { width:280px; flex-shrink:0; background:rgba(15,23,42,0.75); border:1px solid rgba(56,189,248,0.15); border-radius:12px; padding:1.5rem; display:flex; flex-direction:column; gap:1.25rem; height:fit-content; }
        .path-form-title { font-size:0.82rem; font-weight:700; color:#38bdf8; letter-spacing:0.06em; text-transform:uppercase; margin:0; display:flex; align-items:center; gap:0.5rem; }
        .path-form-group { display:flex; flex-direction:column; gap:0.4rem; }
        .path-form-label { font-size:0.72rem; font-weight:600; color:#94a3b8; letter-spacing:0.04em; text-transform:uppercase; }
        .path-form-select { width:100%; background:rgba(10,15,30,0.85); border:1px solid rgba(56,189,248,0.2); border-radius:7px; color:#f1f5f9; font-size:0.84rem; padding:0.55rem 2rem 0.55rem 0.75rem; outline:none; cursor:pointer; transition:border-color 0.15s; appearance:none; background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2338bdf8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E"); background-repeat:no-repeat; background-position:right 0.6rem center; }
        .path-form-select:focus { border-color:rgba(56,189,248,0.5); box-shadow:0 0 0 2px rgba(56,189,248,0.1); }
        .path-form-select option { background:#0f172a; color:#f1f5f9; }
        .path-hops-row { display:flex; gap:0.4rem; }
        .path-hop-btn { flex:1; padding:0.45rem 0; border-radius:6px; font-size:0.78rem; font-weight:700; border:1px solid rgba(56,189,248,0.15); background:rgba(10,15,30,0.6); color:#64748b; cursor:pointer; transition:all 0.15s; }
        .path-hop-btn:hover { border-color:rgba(56,189,248,0.3); color:#94a3b8; }
        .path-hop-btn-active { background:rgba(14,165,233,0.18); border-color:rgba(56,189,248,0.5); color:#38bdf8; box-shadow:0 0 8px rgba(56,189,248,0.15); }
        .path-query-btn { width:100%; display:flex; align-items:center; justify-content:center; gap:0.5rem; padding:0.7rem 1rem; background:rgba(14,165,233,0.2); border:1px solid rgba(56,189,248,0.4); border-radius:8px; color:#38bdf8; font-size:0.84rem; font-weight:700; cursor:pointer; transition:all 0.2s; letter-spacing:0.02em; margin-top:0.25rem; }
        .path-query-btn:hover:not(:disabled) { background:rgba(14,165,233,0.32); box-shadow:0 0 16px rgba(56,189,248,0.25); }
        .path-query-btn:disabled { opacity:0.45; cursor:not-allowed; }
        .path-same-warn { font-size:0.72rem; color:#f59e0b; display:flex; align-items:center; gap:0.35rem; }
        .path-result-panel { flex:1; min-width:0; background:rgba(15,23,42,0.75); border:1px solid rgba(56,189,248,0.12); border-radius:12px; padding:1.75rem; position:relative; }
        .path-idle-state { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; min-height:400px; text-align:center; gap:1rem; }
        .path-idle-icon { opacity:0.4; }
        .path-idle-title { font-size:0.95rem; font-weight:600; color:#64748b; margin:0; }
        .path-idle-sub { font-size:0.8rem; color:#475569; max-width:320px; line-height:1.5; margin:0; }
        .path-querying-state { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; min-height:400px; gap:1rem; }
        .path-querying-spinner { width:36px; height:36px; border:2.5px solid rgba(56,189,248,0.2); border-top-color:#38bdf8; border-radius:50%; animation:path-spin 0.7s linear infinite; }
        @keyframes path-spin { to { transform:rotate(360deg); } }
        .path-querying-text { font-size:0.85rem; color:#94a3b8; }
        .path-error-card { background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:1.25rem 1.5rem; display:flex; align-items:flex-start; gap:0.75rem; margin-bottom:1.5rem; }
        .path-error-icon { color:#ef4444; flex-shrink:0; margin-top:1px; }
        .path-error-text { font-size:0.84rem; color:#fca5a5; line-height:1.5; }
        .path-not-found { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:300px; gap:0.75rem; text-align:center; }
        .path-not-found-icon { color:#475569; opacity:0.6; }
        .path-not-found-title { font-size:1rem; font-weight:700; color:#64748b; margin:0; }
        .path-not-found-sub { font-size:0.82rem; color:#475569; max-width:340px; line-height:1.5; margin:0; }
        .path-result-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:1.75rem; flex-wrap:wrap; gap:0.75rem; }
        .path-result-title { font-size:0.82rem; font-weight:700; color:#38bdf8; letter-spacing:0.06em; text-transform:uppercase; margin:0; display:flex; align-items:center; gap:0.5rem; }
        .path-hop-badge { background:rgba(14,165,233,0.15); border:1px solid rgba(56,189,248,0.35); border-radius:5px; padding:0.15rem 0.5rem; font-size:0.72rem; font-weight:700; color:#38bdf8; font-family:ui-monospace,monospace; }
        .path-network-visualizer {
          background: #fbfdff;
          border: 1px solid #dce7f1;
          border-radius: 12px;
          padding: 1rem 1.25rem 0.5rem;
          margin-bottom: 1.5rem;
          box-shadow: 0 4px 14px rgba(35, 72, 103, 0.04);
        }
        .visualizer-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }
        .visualizer-badge {
          font-size: 0.7rem;
          font-weight: 700;
          color: #0787d1;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          background: #e7f5ff;
          border: 1px solid #bfe8ff;
          border-radius: 4px;
          padding: 0.15rem 0.45rem;
        }
        .visualizer-hint {
          font-size: 0.72rem;
          color: #71829b;
          font-weight: 500;
        }
        .path-network-svg {
          display: block;
          margin: 0 auto;
        }
        .path-chain-container { overflow-x:auto; padding-bottom:1rem; }
        .path-chain { display:flex; align-items:center; min-width:max-content; padding:0.5rem 0; }
        .path-node-card { background:rgba(10,15,30,0.9); border:1.5px solid rgba(56,189,248,0.2); border-radius:10px; padding:0.7rem 0.9rem; min-width:130px; max-width:180px; text-align:center; flex-shrink:0; }
        .path-node-name { font-size:0.83rem; font-weight:600; color:#f1f5f9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .path-node-role { font-size:0.6rem; font-weight:800; letter-spacing:0.08em; margin-top:0.2rem; font-family:ui-monospace,monospace; }
        .path-rel-arrow { display:flex; flex-direction:column; align-items:center; gap:0.3rem; padding:0.4rem 0.5rem; background:transparent; border:1px solid transparent; border-radius:8px; cursor:pointer; transition:all 0.15s; flex-shrink:0; min-width:110px; }
        .path-rel-arrow:hover { background:rgba(56,189,248,0.06); border-color:rgba(56,189,248,0.15); }
        .path-rel-arrow-active { background:rgba(56,189,248,0.1); border-color:rgba(56,189,248,0.35); box-shadow:0 0 10px rgba(56,189,248,0.15); }
        .path-rel-line { display:flex; align-items:center; width:100%; padding:0 4px; }
        .path-rel-line-bar { flex:1; height:2px; background:var(--rel-color,#38bdf8); opacity:0.7; }
        .path-rel-arrowhead { flex-shrink:0; margin-left:-1px; opacity:0.8; }
        .path-rel-label { display:flex; flex-direction:column; align-items:center; gap:0.1rem; }
        .path-rel-type { font-size:0.65rem; font-weight:700; color:#cbd5e1; font-family:ui-monospace,monospace; letter-spacing:0.03em; text-transform:uppercase; white-space:nowrap; }
        .path-rel-confidence { font-size:0.62rem; font-weight:600; font-family:ui-monospace,monospace; }
        .path-rel-status { font-size:0.58rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; font-family:ui-monospace,monospace; }
        .path-legend { display:flex; gap:1.25rem; margin-top:1.75rem; padding-top:1.25rem; border-top:1px solid rgba(255,255,255,0.06); flex-wrap:wrap; }
        .path-legend-item { display:flex; align-items:center; gap:0.4rem; font-size:0.71rem; color:#64748b; }
        .path-legend-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
        .path-evidence-panel { margin-top:1.5rem; background:rgba(10,15,30,0.85); border:1px solid rgba(56,189,248,0.22); border-radius:10px; overflow:hidden; animation:fadeInUp 0.2s ease; }
        @keyframes fadeInUp { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        .path-evidence-header { display:flex; justify-content:space-between; align-items:center; padding:0.85rem 1.1rem; background:rgba(14,165,233,0.08); border-bottom:1px solid rgba(56,189,248,0.15); }
        .path-evidence-title { font-size:0.78rem; font-weight:700; color:#38bdf8; letter-spacing:0.05em; text-transform:uppercase; margin:0; display:flex; align-items:center; gap:0.5rem; }
        .path-evidence-close { background:none; border:none; color:#64748b; cursor:pointer; padding:0.2rem; display:flex; align-items:center; border-radius:4px; transition:color 0.15s; }
        .path-evidence-close:hover { color:#f1f5f9; }
        .path-evidence-body { padding:1.1rem; display:flex; flex-direction:column; gap:0.75rem; }
        .path-ev-loading { display:flex; align-items:center; gap:0.65rem; color:#64748b; font-size:0.82rem; }
        .path-ev-spinner { width:16px; height:16px; border:2px solid rgba(56,189,248,0.2); border-top-color:#38bdf8; border-radius:50%; animation:path-spin 0.7s linear infinite; flex-shrink:0; }
        .path-ev-row { display:flex; gap:0.5rem; align-items:flex-start; }
        .path-ev-key { font-size:0.72rem; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.04em; min-width:110px; flex-shrink:0; padding-top:1px; }
        .path-ev-val { font-size:0.82rem; color:#cbd5e1; line-height:1.5; word-break:break-word; font-family:ui-monospace,monospace; }
        .path-ev-snippet { background:rgba(56,189,248,0.06); border-left:3px solid rgba(56,189,248,0.35); padding:0.6rem 0.85rem; border-radius:0 6px 6px 0; font-size:0.82rem; color:#94a3b8; line-height:1.6; font-style:italic; word-break:break-word; white-space:pre-wrap; margin:0; }
        .path-ev-error { font-size:0.8rem; color:#fca5a5; }
        .path-entity-loading { display:flex; align-items:center; gap:0.5rem; color:#64748b; font-size:0.8rem; }
        .path-mini-spinner { width:14px; height:14px; border:2px solid rgba(56,189,248,0.2); border-top-color:#38bdf8; border-radius:50%; animation:path-spin 0.7s linear infinite; flex-shrink:0; }
      `}</style>

      {/* LEFT: FORM PANEL */}
      <form className="path-form-panel" onSubmit={handleQuery}>
        <h2 className="path-form-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          Path Analysis
        </h2>

        <div className="path-form-group">
          <label className="path-form-label">Source Entity</label>
          {loadingEntities ? (
            <div className="path-entity-loading">
              <div className="path-mini-spinner" />
              <span>Loading entities...</span>
            </div>
          ) : entityError ? (
            <div style={{ fontSize: "0.75rem", color: "#fca5a5" }}>{entityError}</div>
          ) : (
            <select className="path-form-select" value={sourceId} onChange={(e) => setSourceId(e.target.value)} required>
              <option value="">Select source...</option>
              {entities.map((e) => (
                <option key={e.id} value={e.id}>[{ENTITY_CONFIG[e.type]?.label || e.type}] {e.name}</option>
              ))}
            </select>
          )}
        </div>

        <div className="path-form-group">
          <label className="path-form-label">Target Entity</label>
          {loadingEntities ? (
            <div className="path-entity-loading">
              <div className="path-mini-spinner" />
              <span>Loading entities...</span>
            </div>
          ) : entityError ? null : (
            <select className="path-form-select" value={targetId} onChange={(e) => setTargetId(e.target.value)} required>
              <option value="">Select target...</option>
              {entities.map((e) => (
                <option key={e.id} value={e.id}>[{ENTITY_CONFIG[e.type]?.label || e.type}] {e.name}</option>
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
              Source and target must differ
            </div>
          )}
        </div>

        <div className="path-form-group">
          <label className="path-form-label">Max Hops (1–5)</label>
          <div className="path-hops-row">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" className={`path-hop-btn${maxHops === n ? " path-hop-btn-active" : ""}`} onClick={() => setMaxHops(n)}>{n}</button>
            ))}
          </div>
        </div>

        <button type="submit" className="path-query-btn" disabled={!isFormReady || querying || loadingEntities}>
          {querying ? (
            <><div className="path-mini-spinner" /><span>Analyzing...</span></>
          ) : (
            <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="9 18 15 12 9 6" /></svg><span>Investigate Path</span></>
          )}
        </button>
      </form>

      {/* RIGHT: RESULT PANEL */}
      <div className="path-result-panel">
        {!hasQueried && !querying && (
          <div className="path-idle-state">
            <svg className="path-idle-icon" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="1.2">
              <circle cx="5" cy="12" r="2" /><circle cx="19" cy="12" r="2" /><circle cx="12" cy="5" r="2" /><circle cx="12" cy="19" r="2" />
              <line x1="7" y1="12" x2="10" y2="12" /><line x1="14" y1="12" x2="17" y2="12" /><line x1="12" y1="7" x2="12" y2="10" /><line x1="12" y1="14" x2="12" y2="17" />
            </svg>
            <h3 className="path-idle-title">Investigation Path Ready</h3>
            <p className="path-idle-sub">Select a source and target entity, set the maximum hop depth, and run a path investigation.</p>
          </div>
        )}

        {querying && (
          <div className="path-querying-state">
            <div className="path-querying-spinner" />
            <p className="path-querying-text">Tracing investigation path through entity network...</p>
          </div>
        )}

        {!querying && pathError && (
          <div className="path-error-card">
            <div className="path-error-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <div className="path-error-text">{pathError}</div>
          </div>
        )}

        {!querying && pathResult && !pathResult.found && (
          <div className="path-not-found">
            <div className="path-not-found-icon">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
                <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><line x1="8" y1="11" x2="14" y2="11" />
              </svg>
            </div>
            <h3 className="path-not-found-title">No Path Found</h3>
            <p className="path-not-found-sub">No connection was discovered within {maxHops} hop{maxHops !== 1 ? "s" : ""}. Try increasing max hops or selecting different entities.</p>
          </div>
        )}

        {!querying && pathResult && pathResult.found && chain && (
          <>
            <div className="path-result-header">
              <h3 className="path-result-title">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
                Connection Path Found
                <span className="path-hop-badge">{pathResult.hop_count} hop{pathResult.hop_count !== 1 ? "s" : ""}</span>
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Click a relationship to view evidence</span>
            </div>

            {/* 3D NETWORK TOPOLOGY VISUALIZER */}
            <PathNetworkVisualizer chain={chain} pathResult={pathResult} />

            <div className="path-chain-container">
              <div className="path-chain">
                {chain.map((item, idx) =>
                  item.kind === "node" ? (
                    <PathNodeCard
                      key={`node-${idx}`}
                      node={item.data}
                      isSource={item.data.entity_id === pathResult.source_entity_id}
                      isTarget={item.data.entity_id === pathResult.target_entity_id}
                    />
                  ) : (
                    <PathRelationshipArrow
                      key={`rel-${idx}`}
                      rel={item.data}
                      onClick={handleRelClick}
                      isSelected={selectedRel?.relationship_id === item.data.relationship_id}
                    />
                  )
                )}
              </div>
            </div>

            <div className="path-legend">
              {Object.entries(RELATIONSHIP_COLORS).map(([status, cfg]) => (
                <div key={status} className="path-legend-item">
                  <div className="path-legend-dot" style={{ background: cfg.dot }} />
                  <span>{cfg.label}</span>
                </div>
              ))}
            </div>

            {selectedRel && (
              <div className="path-evidence-panel">
                <div className="path-evidence-header">
                  <h4 className="path-evidence-title">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
                    </svg>
                    Relationship Evidence
                  </h4>
                  <button className="path-evidence-close" onClick={closeEvidence} title="Close">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
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
                        <span className="path-ev-key">Status</span>
                        <span className="path-ev-val" style={{ color: RELATIONSHIP_COLORS[evidenceData.status || selectedRel.status]?.dot || "#38bdf8" }}>
                          {evidenceData.status || selectedRel.status}
                        </span>
                      </div>
                      <div className="path-ev-row">
                        <span className="path-ev-key">Confidence</span>
                        <span className="path-ev-val">
                          {evidenceData.confidence != null ? `${Math.round(evidenceData.confidence * 100)}%`
                            : selectedRel.confidence != null ? `${Math.round(selectedRel.confidence * 100)}%` : "—"}
                        </span>
                      </div>
                      {evidenceData.relationship_id && (
                        <div className="path-ev-row">
                          <span className="path-ev-key">Relationship ID</span>
                          <span className="path-ev-val" style={{ fontSize: "0.72rem" }}>{String(evidenceData.relationship_id)}</span>
                        </div>
                      )}
                      {evidenceData.source_document_id && (
                        <div className="path-ev-row">
                          <span className="path-ev-key">Source Document</span>
                          <span className="path-ev-val" style={{ fontSize: "0.72rem" }}>{String(evidenceData.source_document_id)}</span>
                        </div>
                      )}
                      {evidenceData.evidence_snippet ? (
                        <>
                          <div className="path-ev-row"><span className="path-ev-key">Evidence Snippet</span></div>
                          <blockquote className="path-ev-snippet">{evidenceData.evidence_snippet}</blockquote>
                        </>
                      ) : !evidenceData.source_document_id ? (
                        <div style={{ fontSize: "0.8rem", color: "#475569" }}>No additional evidence detail available for this relationship.</div>
                      ) : null}
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
