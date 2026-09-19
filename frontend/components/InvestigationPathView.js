"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { apiClient } from "../lib/apiClient";

const ENTITY_CONFIG = {
  PERSON: { color: "#1d4ed8", bg: "#eff6ff", border: "#bfdbfe", label: "Person" },
  PHONE: { color: "#047857", bg: "#ecfdf5", border: "#a7f3d0", label: "Phone" },
  BANK_ACCOUNT: { color: "#b45309", bg: "#fffbeb", border: "#fde68a", label: "Bank Account" },
  VEHICLE: { color: "#6d28d9", bg: "#f5f3ff", border: "#ddd6fe", label: "Vehicle" },
  ORGANIZATION: { color: "#334155", bg: "#f1f5f9", border: "#cbd5e1", label: "Organization" },
  LOCATION: { color: "#c2410c", bg: "#fff7ed", border: "#fed7aa", label: "Location" },
  EVENT: { color: "#0e7490", bg: "#ecfeff", border: "#a5f3fc", label: "Event" },
};

const RELATIONSHIP_COLORS = {
  CONFIRMED: { stroke: "#2563eb", label: "CONFIRMED", dot: "#2563eb" },
  INFERRED: { stroke: "#d97706", label: "INFERRED", dot: "#d97706" },
  PREDICTED: { stroke: "#7c3aed", label: "PREDICTED", dot: "#7c3aed" },
};

const DARK_ENTITY_COLORS = {
  PERSON: "#1d4ed8",
  PHONE: "#047857",
  BANK_ACCOUNT: "#b45309",
  VEHICLE: "#6d28d9",
  ORGANIZATION: "#1e293b",
  LOCATION: "#c2410c",
  EVENT: "#0e7490",
};

function EntityTypeTag({ type }) {
  const cfg = ENTITY_CONFIG[type] || ENTITY_CONFIG.PERSON;
  return (
    <span
      style={{
        display: "inline-block",
        background: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.border || "transparent"}`,
        fontSize: "0.62rem",
        fontWeight: 700,
        letterSpacing: "0.05em",
        textTransform: "uppercase",
        borderRadius: "4px",
        padding: "0.15rem 0.45rem",
        fontFamily: "ui-monospace, monospace",
        marginBottom: "0.35rem",
      }}
    >
      {cfg.label}
    </span>
  );
}

function PathNodeCard({ node, isSource, isTarget, stepIndex }) {
  const badgeColor = isSource ? "#2563eb" : isTarget ? "#d97706" : "#475569";
  const badgeBg = isSource ? "#eff6ff" : isTarget ? "#fffbeb" : "#f1f5f9";
  const badgeBorder = isSource ? "#93c5fd" : isTarget ? "#fcd34d" : "#cbd5e1";

  return (
    <div
      className="path-node-card"
      style={{
        border: "2px solid #0f172a",
        background: "#ffffff",
        boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)",
      }}
    >
      <div className="path-node-top">
        <EntityTypeTag type={node.type} />
        <span
          className="path-node-badge"
          style={{
            color: badgeColor,
            background: badgeBg,
            borderColor: badgeBorder,
          }}
        >
          {isSource ? "SOURCE" : isTarget ? "TARGET" : `STEP ${stepIndex}`}
        </span>
      </div>
      <div className="path-node-name" title={node.name} style={{ color: "#0f172a", fontWeight: 700 }}>
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

function PathVerticalArrow({ rel, onClick, isSelected }) {
  const cfg = RELATIONSHIP_COLORS[rel.status] || RELATIONSHIP_COLORS.CONFIRMED;
  const confidence = rel.confidence != null ? Math.round(rel.confidence * 100) : null;

  return (
    <div className="path-vert-connector-wrap">
      <button
        className={`path-vert-arrow-btn${isSelected ? " path-vert-arrow-active" : ""}`}
        onClick={() => onClick(rel)}
        style={{ "--rel-color": cfg.stroke }}
        title="Click to view evidence details"
      >
        <div className="vert-arrow-stem-top" />
        <div className="path-rel-pill vert-rel-pill">
          <span className="path-rel-type">{rel.relationship}</span>
          {confidence != null && (
            <span className="path-rel-confidence" style={{ color: cfg.stroke }}>
              {confidence}%
            </span>
          )}
        </div>
        <div className="vert-arrow-stem-bottom">
          <div className="vert-arrow-bar" />
          <svg width="18" height="15" viewBox="0 0 14 11" className="vert-arrowhead">
            <polygon points="1,1 13,1 7,10" fill={cfg.stroke} />
          </svg>
        </div>
      </button>
    </div>
  );
}

function CustomEntitySelect({ value, onChange, entities, placeholder = "Select entity...", disabled = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const [openUpwards, setOpenUpwards] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);

  const selectedEntity = entities.find((e) => e.id === value);

  const handleToggle = () => {
    if (disabled) return;
    if (!isOpen && dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      if (spaceBelow < 280 && rect.top > 280) {
        setOpenUpwards(true);
      } else {
        setOpenUpwards(false);
      }
    }
    setIsOpen((prev) => !prev);
  };

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event) {
      if (event.key === "Escape") setIsOpen(false);
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filteredEntities = entities.filter((e) => {
    if (!search.trim()) return true;
    const term = search.toLowerCase();
    const typeLabel = (ENTITY_CONFIG[e.type]?.label || e.type).toLowerCase();
    return e.name.toLowerCase().includes(term) || typeLabel.includes(term);
  });

  return (
    <div className="custom-entity-select-root" ref={dropdownRef}>
      <button
        type="button"
        className={`custom-select-trigger ${isOpen ? "custom-select-trigger-active" : ""}`}
        onClick={handleToggle}
        disabled={disabled}
      >
        <div className="custom-select-content">
          {selectedEntity ? (
            <div className="custom-select-selected-row">
              <span
                className="custom-select-type-bracket"
                style={{ color: DARK_ENTITY_COLORS[selectedEntity.type] || "#1e40af" }}
              >
                [{ENTITY_CONFIG[selectedEntity.type]?.label || selectedEntity.type}]
              </span>
              <span className="custom-select-selected-name" title={selectedEntity.name}>
                {selectedEntity.name}
              </span>
            </div>
          ) : (
            <span className="custom-select-placeholder">{placeholder}</span>
          )}
        </div>
        <svg
          className={`custom-select-chevron ${isOpen ? "custom-select-chevron-open" : ""}`}
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {isOpen && (
        <div className={`custom-select-dropdown ${openUpwards ? "custom-select-dropdown-up" : ""}`}>
          <div className="custom-select-search-box">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2.4">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              ref={searchInputRef}
              type="text"
              className="custom-select-search-input"
              placeholder="Search by name or category..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
            {search && (
              <button
                type="button"
                className="custom-select-clear-search"
                onClick={() => setSearch("")}
                title="Clear"
              >
                ×
              </button>
            )}
          </div>

          <div className="custom-select-list">
            {filteredEntities.length === 0 ? (
              <div className="custom-select-empty">No entities match your search</div>
            ) : (
              filteredEntities.map((e) => {
                const isSelected = e.id === value;
                const cfg = ENTITY_CONFIG[e.type] || ENTITY_CONFIG.PERSON;
                return (
                  <button
                    key={e.id}
                    type="button"
                    className={`custom-select-item ${isSelected ? "custom-select-item-selected" : ""}`}
                    onClick={() => {
                      onChange(e.id);
                      setIsOpen(false);
                      setSearch("");
                    }}
                  >
                    <div className="custom-select-item-info">
                      <span
                        className="custom-select-item-bracket"
                        style={{ color: DARK_ENTITY_COLORS[e.type] || "#1e293b" }}
                      >
                        [{cfg.label || e.type}]
                      </span>
                      <span className="custom-select-item-name">{e.name}</span>
                    </div>
                    {isSelected && (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
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
  const [flowLayout, setFlowLayout] = useState("vertical");

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
        .path-view-root { display: flex; gap: 1.5rem; min-height: auto; overflow: visible; }
        .path-form-panel {
          width: 300px;
          flex-shrink: 0;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 14px;
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
          height: fit-content;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
          overflow: visible;
          position: relative;
        }
        .path-form-title {
          font-size: 0.85rem;
          font-weight: 700;
          color: #2563eb;
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
          font-weight: 700;
          color: #475569;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }
        .custom-entity-select-root {
          position: relative;
          width: 100%;
        }
        .custom-select-trigger {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.55rem 0.75rem;
          background: #f8fafc;
          border: 1.5px solid #cbd5e1;
          border-radius: 8px;
          cursor: pointer;
          text-align: left;
          transition: all 0.15s ease;
          min-height: 44px;
        }
        .custom-select-trigger:hover:not(:disabled) {
          border-color: #94a3b8;
          background: #ffffff;
        }
        .custom-select-trigger-active {
          border-color: #0f172a !important;
          background: #ffffff !important;
          box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.08);
        }
        .custom-select-content {
          flex: 1;
          min-width: 0;
          margin-right: 0.5rem;
        }
        .custom-select-selected-row {
          display: flex;
          align-items: center;
          gap: 0.45rem;
          overflow: hidden;
        }
        .custom-select-type-bracket,
        .custom-select-type-chip {
          display: inline-flex;
          align-items: center;
          font-size: 0.72rem;
          font-weight: 750;
          letter-spacing: 0.03em;
          text-transform: uppercase;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          background: transparent;
          border: none;
          padding: 0;
          margin: 0;
          flex-shrink: 0;
        }
        .custom-select-selected-name {
          font-size: 0.84rem;
          font-weight: 700;
          color: #0f172a;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .custom-select-placeholder {
          font-size: 0.84rem;
          color: #64748b;
          font-weight: 500;
        }
        .custom-select-chevron {
          color: #64748b;
          transition: transform 0.2s ease;
          flex-shrink: 0;
        }
        .custom-select-chevron-open {
          transform: rotate(180deg);
          color: #0f172a;
        }
        .custom-select-dropdown {
          position: absolute;
          top: calc(100% + 5px);
          left: 0;
          right: 0;
          z-index: 1000;
          background: #ffffff;
          border: 1.5px solid #0f172a;
          border-radius: 10px;
          box-shadow: 0 10px 25px -4px rgba(0, 0, 0, 0.16), 0 4px 6px -2px rgba(0, 0, 0, 0.06);
          overflow: hidden;
          animation: selectDropdownFade 0.15s ease;
        }
        .custom-select-dropdown-up {
          top: auto !important;
          bottom: calc(100% + 5px) !important;
          box-shadow: 0 -10px 25px -4px rgba(0, 0, 0, 0.16), 0 -4px 6px -2px rgba(0, 0, 0, 0.06) !important;
        }
        @keyframes selectDropdownFade {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .custom-select-search-box {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.55rem 0.75rem;
          border-bottom: 1px solid #e2e8f0;
          background: #f8fafc;
        }
        .custom-select-search-input {
          flex: 1;
          border: none;
          background: transparent;
          font-size: 0.82rem;
          color: #0f172a;
          outline: none;
          font-weight: 500;
        }
        .custom-select-clear-search {
          background: none;
          border: none;
          color: #94a3b8;
          font-size: 1.1rem;
          line-height: 1;
          cursor: pointer;
          padding: 0 0.25rem;
          border-radius: 4px;
        }
        .custom-select-clear-search:hover {
          color: #0f172a;
        }
        .custom-select-list {
          max-height: 230px;
          overflow-y: auto;
          padding: 0.35rem;
          display: flex;
          flex-direction: column;
          gap: 2px;
          scrollbar-width: thin;
          scrollbar-color: #cbd5e1 transparent;
        }
        .custom-select-list::-webkit-scrollbar {
          width: 4px;
        }
        .custom-select-list::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 4px;
        }
        .custom-select-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.5rem;
          padding: 0.5rem 0.65rem;
          border: none;
          background: transparent;
          border-radius: 6px;
          cursor: pointer;
          text-align: left;
          transition: background 0.12s;
          width: 100%;
        }
        .custom-select-item:hover {
          background: #f1f5f9;
        }
        .custom-select-item-selected {
          background: #eff6ff !important;
        }
        .custom-select-item-info {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          overflow: hidden;
          flex: 1;
        }
        .custom-select-item-bracket,
        .custom-select-item-chip {
          display: inline-flex;
          align-items: center;
          font-size: 0.72rem;
          font-weight: 750;
          letter-spacing: 0.03em;
          text-transform: uppercase;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          background: transparent;
          border: none;
          padding: 0;
          margin: 0;
          flex-shrink: 0;
        }
        .custom-select-item-name {
          font-size: 0.82rem;
          font-weight: 600;
          color: #0f172a;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .custom-select-empty {
          padding: 1rem;
          text-align: center;
          font-size: 0.8rem;
          color: #64748b;
          font-weight: 500;
        }
        .path-query-btn {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          background: #2563eb;
          border: 1px solid #1d4ed8;
          border-radius: 8px;
          color: #ffffff;
          font-size: 0.85rem;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s;
          letter-spacing: 0.02em;
          margin-top: 0.5rem;
          box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
        }
        .path-query-btn:hover:not(:disabled) {
          background: #1d4ed8;
          box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
        }
        .path-query-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .path-same-warn { font-size: 0.72rem; color: #d97706; display: flex; align-items: center; gap: 0.35rem; }
        .path-result-panel {
          flex: 1;
          min-width: 0;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 14px;
          padding: 1.75rem;
          position: relative;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }
        .path-idle-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 280px;
          text-align: center;
          gap: 1rem;
        }
        .path-idle-icon { opacity: 0.6; }
        .path-idle-title { font-size: 0.95rem; font-weight: 600; color: #0f172a; margin: 0; }
        .path-idle-sub { font-size: 0.82rem; color: #64748b; max-width: 320px; line-height: 1.5; margin: 0; }
        .path-querying-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 280px;
          gap: 1rem;
        }
        .path-querying-spinner {
          width: 36px;
          height: 36px;
          border: 2.5px solid rgba(37, 99, 235, 0.2);
          border-top-color: #2563eb;
          border-radius: 50%;
          animation: path-spin 0.7s linear infinite;
        }
        @keyframes path-spin { to { transform: rotate(360deg); } }
        .path-querying-text { font-size: 0.85rem; color: #64748b; }
        .path-error-card {
          background: #fffbeb;
          border: 1px solid #fde68a;
          border-radius: 10px;
          padding: 1.25rem 1.5rem;
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          margin-bottom: 1.5rem;
        }
        .path-error-icon { color: #d97706; flex-shrink: 0; margin-top: 1px; }
        .path-error-text { font-size: 0.84rem; color: #b45309; line-height: 1.5; }
        .path-not-found {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 260px;
          gap: 0.75rem;
          text-align: center;
        }
        .path-not-found-icon { color: #64748b; opacity: 0.7; }
        .path-not-found-title { font-size: 1rem; font-weight: 700; color: #0f172a; margin: 0; }
        .path-not-found-sub { font-size: 0.82rem; color: #64748b; max-width: 360px; line-height: 1.5; margin: 0; }
        .path-result-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.25rem;
          padding-bottom: 0.85rem;
          border-bottom: 1px solid #e2e8f0;
          flex-wrap: wrap;
          gap: 0.75rem;
        }
        .path-result-title {
          font-size: 0.88rem;
          font-weight: 700;
          color: #2563eb;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        .path-hop-badge {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 5px;
          padding: 0.15rem 0.5rem;
          font-size: 0.72rem;
          font-weight: 700;
          color: #2563eb;
          font-family: ui-monospace, monospace;
        }
        .path-chain-container {
          overflow-x: auto;
          padding: 1.25rem 1.15rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          margin-bottom: 0;
        }
        .path-chain {
          display: flex;
          align-items: center;
          padding: 0.75rem 0.5rem;
          gap: 0.5rem;
        }
        .path-chain-horizontal {
          flex-wrap: nowrap;
          overflow-x: auto;
          scrollbar-width: thin;
        }
        .path-chain-vertical {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0;
          padding: 1.5rem 0.5rem;
          width: 100%;
          max-width: 460px;
          margin: 0 auto;
        }
        .path-chain-vertical .path-node-card {
          width: 100%;
          max-width: 320px;
          min-width: 280px;
          text-align: center;
        }
        .path-vert-step-group {
          display: flex;
          flex-direction: column;
          align-items: center;
          width: 100%;
        }
        .path-vert-connector-wrap {
          display: flex;
          justify-content: center;
          width: 100%;
          margin: 2px 0;
        }
        .path-vert-arrow-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          background: #ffffff;
          border: 1.5px solid #cbd5e1;
          border-radius: 10px;
          cursor: pointer;
          padding: 0.35rem 0.75rem;
          transition: all 0.15s ease;
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
        }
        .path-vert-arrow-btn:hover {
          border-color: #2563eb;
          box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
          transform: translateY(-1px);
        }
        .path-vert-arrow-active {
          border-color: #2563eb;
          background: #eff6ff;
          box-shadow: 0 0 0 2px #bfdbfe;
        }
        .vert-arrow-stem-top {
          width: 3px;
          height: 16px;
          background: var(--rel-color, #2563eb);
          border-radius: 2px;
        }
        .vert-rel-pill {
          margin: 4px 0;
        }
        .vert-arrow-stem-bottom {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .vert-arrow-bar {
          width: 3px;
          height: 16px;
          background: var(--rel-color, #2563eb);
          border-radius: 2px;
        }
        .vert-arrowhead {
          margin-top: -1px;
        }
        .path-layout-toggle {
          display: inline-flex;
          align-items: center;
          background: #ffffff;
          padding: 3px;
          border-radius: 8px;
          border: 1.5px solid #cbd5e1;
          gap: 4px;
        }
        .layout-toggle-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 5px 12px;
          border-radius: 6px;
          border: 1px solid transparent;
          background: #ffffff;
          font-size: 0.76rem;
          font-weight: 700;
          color: #475569;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .layout-toggle-btn:hover {
          color: #0f172a;
          background: #f1f5f9;
        }
        .layout-toggle-btn.active {
          background: #0f172a;
          color: #ffffff;
          border-color: #0f172a;
          box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
        }
        .path-result-title-group {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .path-step-item {
          display: inline-flex;
          align-items: center;
          flex-shrink: 0;
        }
        .path-step-group {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          flex-shrink: 0;
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
          border-radius: 4px;
          padding: 0.1rem 0.4rem;
          font-family: ui-monospace, monospace;
        }
        .path-node-name {
          font-size: 0.9rem;
          font-weight: 700;
          color: #0f172a;
          word-break: break-word;
          line-height: 1.35;
        }
        .path-rel-arrow {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.35rem;
          padding: 0.4rem 0.6rem;
          background: transparent;
          border: 1px solid transparent;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.15s;
          flex-shrink: 0;
          min-width: 110px;
          max-width: 160px;
        }
        .path-rel-arrow:hover {
          background: rgba(37, 99, 235, 0.06);
          border-color: rgba(37, 99, 235, 0.2);
        }
        .path-rel-arrow-active {
          background: rgba(37, 99, 235, 0.1);
          border-color: #2563eb;
          box-shadow: 0 0 10px rgba(37, 99, 235, 0.15);
        }
        .path-rel-pill {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          background: #ffffff;
          border: 1.5px solid #0f172a;
          border-radius: 6px;
          padding: 0.2rem 0.55rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        .path-rel-type {
          font-size: 0.68rem;
          font-weight: 700;
          color: #1e293b;
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
          background: var(--rel-color, #2563eb);
          opacity: 0.85;
          border-radius: 2px;
        }
        .path-rel-arrowhead {
          flex-shrink: 0;
          margin-left: -2px;
          opacity: 0.9;
        }
        .path-evidence-panel {
          margin-top: 1.25rem;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
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
          background: #eff6ff;
          border-bottom: 1px solid #dbeafe;
        }
        .path-evidence-title {
          font-size: 0.78rem;
          font-weight: 700;
          color: #1d4ed8;
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
        .path-evidence-close:hover { color: #0f172a; }
        .path-evidence-body { padding: 1.1rem; display: flex; flex-direction: column; gap: 0.75rem; }
        .path-ev-loading { display: flex; align-items: center; gap: 0.65rem; color: #64748b; font-size: 0.82rem; }
        .path-ev-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(37, 99, 235, 0.2);
          border-top-color: #2563eb;
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
          color: #0f172a;
          line-height: 1.5;
          word-break: break-word;
          font-family: ui-monospace, monospace;
        }
        .path-ev-snippet {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-left: 3px solid #2563eb;
          padding: 0.75rem 1rem;
          border-radius: 0 6px 6px 0;
          font-size: 0.82rem;
          color: #1e293b;
          line-height: 1.6;
          font-style: italic;
          word-break: break-word;
          white-space: pre-wrap;
          margin: 0;
        }
        .path-ev-error { font-size: 0.8rem; color: #dc2626; }
        .path-entity-loading { display: flex; align-items: center; gap: 0.5rem; color: #64748b; font-size: 0.8rem; }
        .path-mini-spinner {
          width: 14px;
          height: 14px;
          border: 2px solid rgba(37, 99, 235, 0.2);
          border-top-color: #2563eb;
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
            <CustomEntitySelect
              value={sourceId}
              onChange={(val) => setSourceId(val)}
              entities={entities}
              placeholder="Select first entity..."
              disabled={querying || loadingEntities}
            />
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
            <CustomEntitySelect
              value={targetId}
              onChange={(val) => setTargetId(val)}
              entities={entities}
              placeholder="Select second entity..."
              disabled={querying || loadingEntities}
            />
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
            <svg className="path-idle-icon" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="1.2">
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
              <div className="path-result-title-group">
                <h3 className="path-result-title">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                  Connection Flow
                </h3>
                <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                  Click any arrow to view evidence document snippet
                </span>
              </div>

              <div className="path-layout-toggle">
                <button
                  type="button"
                  className={`layout-toggle-btn ${flowLayout === "vertical" ? "active" : ""}`}
                  onClick={() => setFlowLayout("vertical")}
                  title="Vertical step flow with downward arrows"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6">
                    <line x1="12" y1="3" x2="12" y2="21" />
                    <polyline points="19 14 12 21 5 14" />
                  </svg>
                  <span>Vertical Flow (↓)</span>
                </button>
                <button
                  type="button"
                  className={`layout-toggle-btn ${flowLayout === "horizontal" ? "active" : ""}`}
                  onClick={() => setFlowLayout("horizontal")}
                  title="Horizontal step flow"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6">
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <polyline points="14 5 21 12 14 19" />
                  </svg>
                  <span>Horizontal Flow (➔)</span>
                </button>
              </div>
            </div>

            {/* BOX FLOW CONTAINER */}
            <div className="path-chain-container">
              {flowLayout === "vertical" ? (
                <div className="path-chain-vertical">
                  {pathResult.nodes && pathResult.nodes.length > 0 && (
                    <div className="path-vert-node-step">
                      <PathNodeCard
                        node={pathResult.nodes[0]}
                        isSource={true}
                        isTarget={pathResult.nodes[0].entity_id === pathResult.target_entity_id}
                        stepIndex={1}
                      />
                    </div>
                  )}

                  {(pathResult.relationships || []).map((rel, idx) => {
                    const nextNode = (pathResult.nodes || [])[idx + 1];
                    const stepNum = idx + 2;
                    const isTarget = nextNode && nextNode.entity_id === pathResult.target_entity_id;

                    return (
                      <div key={`v-step-${rel.relationship_id || idx}`} className="path-vert-step-group">
                        <PathVerticalArrow
                          rel={rel}
                          onClick={handleRelClick}
                          isSelected={selectedRel?.relationship_id === rel.relationship_id}
                        />
                        {nextNode && (
                          <PathNodeCard
                            node={nextNode}
                            isSource={false}
                            isTarget={isTarget}
                            stepIndex={stepNum}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="path-chain path-chain-horizontal">
                  {pathResult.nodes && pathResult.nodes.length > 0 && (
                    <div className="path-step-item">
                      <PathNodeCard
                        node={pathResult.nodes[0]}
                        isSource={true}
                        isTarget={pathResult.nodes[0].entity_id === pathResult.target_entity_id}
                        stepIndex={1}
                      />
                    </div>
                  )}

                  {(pathResult.relationships || []).map((rel, idx) => {
                    const nextNode = (pathResult.nodes || [])[idx + 1];
                    const stepNum = idx + 2;
                    const isTarget = nextNode && nextNode.entity_id === pathResult.target_entity_id;

                    return (
                      <div key={`h-step-${rel.relationship_id || idx}`} className="path-step-group">
                        <PathRelationshipArrow
                          rel={rel}
                          onClick={handleRelClick}
                          isSelected={selectedRel?.relationship_id === rel.relationship_id}
                        />
                        {nextNode && (
                          <PathNodeCard
                            node={nextNode}
                            isSource={false}
                            isTarget={isTarget}
                            stepIndex={stepNum}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
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
