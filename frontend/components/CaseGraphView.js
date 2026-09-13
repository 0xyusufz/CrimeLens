"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import { apiClient } from "../lib/apiClient";

// Entity type color tokens (investigator palette, non-risk based)
const ENTITY_CONFIG = {
  PERSON: {
    color: "#38bdf8",
    bg: "rgba(14, 165, 233, 0.12)",
    border: "rgba(56, 189, 248, 0.4)",
    label: "Person",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  PHONE: {
    color: "#34d399",
    bg: "rgba(16, 185, 129, 0.12)",
    border: "rgba(52, 211, 153, 0.4)",
    label: "Phone",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
      </svg>
    ),
  },
  BANK_ACCOUNT: {
    color: "#fbbf24",
    bg: "rgba(245, 158, 11, 0.12)",
    border: "rgba(251, 191, 36, 0.4)",
    label: "Bank Account",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="2" y="5" width="20" height="14" rx="2" />
        <line x1="2" y1="10" x2="22" y2="10" />
      </svg>
    ),
  },
  VEHICLE: {
    color: "#818cf8",
    bg: "rgba(99, 102, 241, 0.12)",
    border: "rgba(129, 140, 248, 0.4)",
    label: "Vehicle",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="1" y="3" width="15" height="13" />
        <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
        <circle cx="5.5" cy="18.5" r="2.5" />
        <circle cx="18.5" cy="18.5" r="2.5" />
      </svg>
    ),
  },
  ORGANIZATION: {
    color: "#2dd4bf",
    bg: "rgba(20, 184, 166, 0.12)",
    border: "rgba(45, 212, 191, 0.4)",
    label: "Organization",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
  LOCATION: {
    color: "#fb923c",
    bg: "rgba(249, 115, 22, 0.12)",
    border: "rgba(251, 146, 60, 0.4)",
    label: "Location",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
        <circle cx="12" cy="10" r="3" />
      </svg>
    ),
  },
  EVENT: {
    color: "#f472b6",
    bg: "rgba(236, 72, 153, 0.12)",
    border: "rgba(244, 114, 182, 0.4)",
    label: "Event",
    icon: (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    ),
  },
};

// Custom React Flow Node for Investigation Entities
function InvestigationNode({ data, selected }) {
  const config = ENTITY_CONFIG[data.type] || ENTITY_CONFIG.PERSON;

  return (
    <div
      className={`investigation-node ${selected ? "node-selected" : ""}`}
      style={{
        borderColor: selected ? "#38bdf8" : config.border,
        boxShadow: selected ? `0 0 16px rgba(56, 189, 248, 0.45)` : undefined,
      }}
    >
      <Handle type="target" position={Position.Top} className="node-handle" />
      <Handle type="source" position={Position.Bottom} className="node-handle" />

      <div className="node-badge" style={{ color: config.color, background: config.bg }}>
        <span className="node-icon">{config.icon}</span>
        <span className="node-type-label">{config.label}</span>
      </div>

      <div className="node-name" title={data.name}>
        {data.name}
      </div>

      <style>{`
        .investigation-node {
          padding: 0.65rem 0.85rem;
          background: rgba(15, 23, 42, 0.94);
          border: 1.5px solid rgba(56, 189, 248, 0.25);
          border-radius: 10px;
          min-width: 150px;
          max-width: 220px;
          cursor: pointer;
          transition: all 0.2s ease;
          backdrop-filter: blur(8px);
        }
        .node-selected {
          background: rgba(22, 33, 58, 0.98);
        }
        .node-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.15rem 0.45rem;
          border-radius: 4px;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          margin-bottom: 0.4rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }
        .node-icon {
          display: flex;
          align-items: center;
        }
        .node-name {
          font-size: 0.84rem;
          font-weight: 600;
          color: #f1f5f9;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          line-height: 1.3;
        }
        :global(.node-handle) {
          width: 6px;
          height: 6px;
          background: #38bdf8;
          border: none;
          opacity: 0.4;
        }
      `}</style>
    </div>
  );
}

// Inner Graph Canvas Component
function GraphCanvas({ caseId }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [graphError, setGraphError] = useState(null);
  const [isTruncated, setIsTruncated] = useState(false);

  // Selected item states (Node or Edge)
  const [selectedNodeData, setSelectedNodeData] = useState(null);
  const [loadingNodeDetails, setLoadingNodeDetails] = useState(false);
  const [expanding, setExpanding] = useState(false);
  const [expandFeedback, setExpandFeedback] = useState(null);

  const [selectedEdgeData, setSelectedEdgeData] = useState(null);
  const [loadingEdgeEvidence, setLoadingEdgeEvidence] = useState(false);

  const reactFlowInstance = useReactFlow();

  const nodeTypes = useMemo(
    () => ({
      investigationNode: InvestigationNode,
    }),
    []
  );

  // Format edges with CrimeLens status aesthetics
  const formatEdge = useCallback((rel) => {
    let strokeColor = "#38bdf8";
    let strokeDash = undefined;
    let labelBadge = rel.relationship;

    if (rel.status === "CONFIRMED") {
      strokeColor = "#38bdf8"; // Solid cyan
    } else if (rel.status === "INFERRED") {
      strokeColor = "#818cf8"; // Dashed indigo
      strokeDash = "5 5";
    } else if (rel.status === "PREDICTED") {
      strokeColor = "#f59e0b"; // Dotted amber
      strokeDash = "3 4";
    }

    return {
      id: rel.relationship_id,
      source: rel.source_entity_id,
      target: rel.target_entity_id,
      label: `${rel.relationship} (${Math.round((rel.confidence || 1) * 100)}%)`,
      type: "smoothstep",
      animated: rel.status === "PREDICTED",
      style: {
        stroke: strokeColor,
        strokeWidth: 2,
        strokeDasharray: strokeDash,
      },
      labelStyle: {
        fill: "#cbd5e1",
        fontSize: 10,
        fontWeight: 600,
        fontFamily: "ui-monospace, monospace",
      },
      labelBgStyle: {
        fill: "#0b101b",
        fillOpacity: 0.85,
        stroke: strokeColor,
        strokeWidth: 1,
        rx: 4,
        ry: 4,
      },
      labelBgPadding: [6, 4],
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: strokeColor,
        width: 14,
        height: 14,
      },
      data: {
        relationshipId: rel.relationship_id,
        relationship: rel.relationship,
        status: rel.status,
        confidence: rel.confidence,
        sourceDocumentId: rel.source_document_id,
        evidenceSnippet: rel.evidence_snippet,
        sourceEntityId: rel.source_entity_id,
        targetEntityId: rel.target_entity_id,
      },
    };
  }, []);

  // Fetch initial case graph
  const loadGraph = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setGraphError(null);
    setSelectedNodeData(null);
    setSelectedEdgeData(null);
    setExpandFeedback(null);

    try {
      const data = await apiClient(`/api/cases/${caseId}/graph`);
      setIsTruncated(!!data?.truncated);

      const rawNodes = data?.nodes || [];
      const rawRels = data?.relationships || [];

      // Circular/Radial layout for initial nodes
      const count = rawNodes.length;
      const centerX = 380;
      const centerY = 260;
      const radius = Math.max(160, count * 35);

      const rfNodes = rawNodes.map((n, idx) => {
        const angle = count > 1 ? (2 * Math.PI * idx) / count : 0;
        const x = count === 1 ? centerX : centerX + radius * Math.cos(angle);
        const y = count === 1 ? centerY : centerY + radius * Math.sin(angle);

        return {
          id: n.entity_id,
          type: "investigationNode",
          position: { x, y },
          data: {
            name: n.name,
            type: n.type,
            entityId: n.entity_id,
          },
        };
      });

      const rfEdges = rawRels.map(formatEdge);

      setNodes(rfNodes);
      setEdges(rfEdges);

      // Fit view after a slight tick
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
      }, 100);
    } catch (err) {
      if (err?.status === 404) {
        setGraphError("Case record not found in repository.");
      } else if (err?.status === 403) {
        setGraphError("Clearance Restriction: You lack authorization to query this case graph.");
      } else {
        setGraphError("Failed to retrieve graph data from intelligence service.");
      }
    } finally {
      setLoading(false);
    }
  }, [caseId, formatEdge, reactFlowInstance, setNodes, setEdges]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Handle Node Selection & Fetch Entity Details
  const onNodeClick = async (_event, node) => {
    setSelectedEdgeData(null);
    setExpandFeedback(null);
    setSelectedNodeData({
      id: node.id,
      name: node.data.name,
      type: node.data.type,
      cases: [],
    });
    setLoadingNodeDetails(true);

    try {
      const entityDetails = await apiClient(`/api/entities/${node.id}`);
      setSelectedNodeData((prev) => ({
        ...prev,
        canonical_name: entityDetails.canonical_name || prev.name,
        cases: entityDetails.cases || [],
      }));
    } catch {
      // Keep basic node data if details fail
    } finally {
      setLoadingNodeDetails(false);
    }
  };

  // Handle Edge Selection & Fetch Evidence
  const onEdgeClick = async (_event, edge) => {
    setSelectedNodeData(null);
    setExpandFeedback(null);
    setSelectedEdgeData({
      relationship_id: edge.id,
      relationship: edge.data?.relationship,
      status: edge.data?.status,
      confidence: edge.data?.confidence,
      source_document_id: edge.data?.sourceDocumentId,
      evidence_snippet: edge.data?.evidenceSnippet,
      source_entity_id: edge.data?.sourceEntityId,
      target_entity_id: edge.data?.targetEntityId,
    });
    setLoadingEdgeEvidence(true);

    try {
      const evidence = await apiClient(`/api/relationships/${edge.id}/evidence`);
      setSelectedEdgeData(evidence);
    } catch {
      // Retain fallback data from edge.data
    } finally {
      setLoadingEdgeEvidence(false);
    }
  };

  // Expand Connections for Selected Entity (1-hop expansion)
  const handleExpandConnections = async () => {
    if (!selectedNodeData || expanding || !caseId) return;

    setExpanding(true);
    setExpandFeedback(null);

    try {
      const result = await apiClient(
        `/api/entities/${selectedNodeData.id}/connections?case_id=${caseId}`
      );

      const connections = result?.connections || [];
      if (connections.length === 0) {
        setExpandFeedback({ type: "info", text: "No additional 1-hop connections found in this case." });
        return;
      }

      // Existing sets
      const existingNodeIds = new Set(nodes.map((n) => n.id));
      const existingEdgeIds = new Set(edges.map((e) => e.id));

      const currentNode = nodes.find((n) => n.id === selectedNodeData.id);
      const baseX = currentNode?.position?.x || 300;
      const baseY = currentNode?.position?.y || 250;

      const newNodes = [];
      const newEdges = [];
      let addedNodesCount = 0;
      let addedEdgesCount = 0;

      connections.forEach((conn, i) => {
        // Node
        if (!existingNodeIds.has(conn.entity_id)) {
          existingNodeIds.add(conn.entity_id);
          addedNodesCount++;

          const angle = (2 * Math.PI * i) / connections.length;
          const dist = 180;
          newNodes.push({
            id: conn.entity_id,
            type: "investigationNode",
            position: {
              x: baseX + dist * Math.cos(angle),
              y: baseY + dist * Math.sin(angle),
            },
            data: {
              name: conn.name,
              type: conn.type,
              entityId: conn.entity_id,
            },
          });
        }

        // Edge
        if (!existingEdgeIds.has(conn.relationship_id)) {
          existingEdgeIds.add(conn.relationship_id);
          addedEdgesCount++;
          newEdges.push(
            formatEdge({
              relationship_id: conn.relationship_id,
              source_entity_id: selectedNodeData.id,
              target_entity_id: conn.entity_id,
              relationship: conn.relationship,
              confidence: conn.confidence,
              status: conn.status,
              source_document_id: conn.source_document_id,
              evidence_snippet: conn.evidence_snippet,
            })
          );
        }
      });

      if (newNodes.length > 0) {
        setNodes((prev) => [...prev, ...newNodes]);
      }
      if (newEdges.length > 0) {
        setEdges((prev) => [...prev, ...newEdges]);
      }

      setExpandFeedback({
        type: "success",
        text: `Expanded ${addedNodesCount} new entities and ${addedEdgesCount} relationships.`,
      });

      // Recenter lightly
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
      }, 150);
    } catch {
      setExpandFeedback({
        type: "error",
        text: "Failed to expand entity connections. Please try again.",
      });
    } finally {
      setExpanding(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "CONFIRMED":
        return { label: "CONFIRMED", className: "badge-confirmed" };
      case "INFERRED":
        return { label: "INFERRED", className: "badge-inferred" };
      case "PREDICTED":
        return { label: "PREDICTED", className: "badge-predicted" };
      default:
        return { label: status || "UNKNOWN", className: "badge-default" };
    }
  };

  return (
    <div className="graph-workspace-layout">
      {/* 1. TOP GRAPH TOOLBAR */}
      <div className="graph-toolbar">
        <div className="toolbar-left">
          <div className="toolbar-stat">
            <span className="stat-label">Entities:</span>
            <span className="stat-value font-mono">{nodes.length}</span>
          </div>
          <div className="toolbar-stat">
            <span className="stat-label">Relationships:</span>
            <span className="stat-value font-mono">{edges.length}</span>
          </div>
          {isTruncated && (
            <span className="truncated-badge" title="Query limit reached. Use entity expansion to view more.">
              Limit Reached (Truncated)
            </span>
          )}
        </div>

        <div className="toolbar-actions">
          <button
            onClick={() => reactFlowInstance.fitView({ padding: 0.2, duration: 300 })}
            className="tool-btn"
            title="Fit and center graph"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
            </svg>
            <span>Center View</span>
          </button>

          <button
            onClick={loadGraph}
            className="tool-btn"
            disabled={loading}
            title="Reload initial graph"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={loading ? "spinning" : ""}
            >
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
            </svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* 2. MAIN GRAPH CANVAS & SIDEBAR */}
      <div className="graph-main-split">
        {/* GRAPH VIEWPORT */}
        <div className="graph-viewport-area">
          {loading && (
            <div className="graph-overlay-loading">
              <div className="mini-radar-pulse" />
              <span>Projecting investigation graph...</span>
            </div>
          )}

          {graphError && (
            <div className="graph-overlay-error">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{graphError}</span>
              <button onClick={loadGraph} className="retry-btn">
                Retry
              </button>
            </div>
          )}

          {!loading && !graphError && nodes.length === 0 && (
            <div className="graph-overlay-empty">
              <div className="empty-radar-icon">
                <svg width="40" height="40" viewBox="0 0 32 32" fill="none">
                  <circle cx="16" cy="16" r="14" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.4" />
                  <circle cx="16" cy="16" r="8" stroke="#0ea5e9" strokeWidth="1.5" opacity="0.7" />
                  <circle cx="16" cy="16" r="3" fill="#38bdf8" />
                </svg>
              </div>
              <h4>No Network Entities in Case Graph</h4>
              <p>
                No entities or relationships have been linked to this case file yet. Upload and process documents or ingest evidentiary records to populate the intelligence graph.
              </p>
              <button onClick={loadGraph} className="retry-btn">
                Check Again
              </button>
            </div>
          )}

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={() => {
              setSelectedNodeData(null);
              setSelectedEdgeData(null);
              setExpandFeedback(null);
            }}
            fitView
            minZoom={0.2}
            maxZoom={2.5}
            attributionPosition="bottom-left"
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls className="rf-controls-custom" showInteractive={false} />
            <MiniMap
              className="rf-minimap-custom"
              nodeColor={(n) => {
                const cfg = ENTITY_CONFIG[n.data?.type];
                return cfg ? cfg.color : "#38bdf8";
              }}
              maskColor="rgba(11, 16, 27, 0.75)"
            />
          </ReactFlow>
        </div>

        {/* 3. DETAILS SIDE PANEL */}
        <aside className="graph-details-sidebar">
          {/* A. NODE DETAILS */}
          {selectedNodeData && (
            <div className="panel-card">
              <div className="panel-header">
                <div className="panel-title-group">
                  <span className="panel-type-label">Entity Details</span>
                  <h3 className="panel-entity-name">{selectedNodeData.canonical_name || selectedNodeData.name}</h3>
                </div>
                <button
                  onClick={() => setSelectedNodeData(null)}
                  className="close-panel-btn"
                  title="Close details panel"
                >
                  ✕
                </button>
              </div>

              <div className="panel-body">
                {/* Type & ID */}
                <div className="detail-row">
                  <span className="detail-key">Entity Type:</span>
                  <span
                    className="entity-badge-pill"
                    style={{
                      color: ENTITY_CONFIG[selectedNodeData.type]?.color || "#38bdf8",
                      background: ENTITY_CONFIG[selectedNodeData.type]?.bg || "rgba(14, 165, 233, 0.12)",
                    }}
                  >
                    {selectedNodeData.type}
                  </span>
                </div>

                <div className="detail-row">
                  <span className="detail-key">UUID:</span>
                  <span className="detail-val font-mono">{selectedNodeData.id}</span>
                </div>

                {/* Associated Cases */}
                <div className="associated-cases-block">
                  <span className="detail-key">Associated Cases ({selectedNodeData.cases?.length || 0}):</span>
                  {loadingNodeDetails ? (
                    <div className="details-loading-spinner">Loading case associations...</div>
                  ) : selectedNodeData.cases?.length > 0 ? (
                    <div className="case-chips-wrap">
                      {selectedNodeData.cases.map((c) => (
                        <span key={c.case_id} className="case-chip font-mono">
                          {c.case_number}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="no-data-text">Current case record</span>
                  )}
                </div>

                {/* EXPAND CONNECTIONS ACTION */}
                <div className="expansion-action-box">
                  <button
                    onClick={handleExpandConnections}
                    className="expand-connections-btn"
                    disabled={expanding}
                  >
                    {expanding ? (
                      <>
                        <span className="mini-spin" />
                        <span>Querying 1-Hop Network...</span>
                      </>
                    ) : (
                      <>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="3" />
                          <path d="M12 3v3m0 12v3m9-9h-3m-12 0H3" />
                        </svg>
                        <span>Expand Connections</span>
                      </>
                    )}
                  </button>

                  {expandFeedback && (
                    <div className={`feedback-banner banner-${expandFeedback.type}`}>
                      {expandFeedback.text}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* B. RELATIONSHIP EVIDENCE PANEL */}
          {selectedEdgeData && !selectedNodeData && (
            <div className="panel-card">
              <div className="panel-header">
                <div className="panel-title-group">
                  <span className="panel-type-label">Relationship Evidence</span>
                  <h3 className="panel-entity-name">{selectedEdgeData.relationship}</h3>
                </div>
                <button
                  onClick={() => setSelectedEdgeData(null)}
                  className="close-panel-btn"
                  title="Close panel"
                >
                  ✕
                </button>
              </div>

              <div className="panel-body">
                {/* Status & Confidence */}
                <div className="detail-row">
                  <span className="detail-key">Status:</span>
                  <span className={`status-pill-small ${getStatusBadge(selectedEdgeData.status).className}`}>
                    {selectedEdgeData.status}
                  </span>
                </div>

                <div className="detail-row">
                  <span className="detail-key">Confidence:</span>
                  <span className="detail-val font-mono">
                    {Math.round((selectedEdgeData.confidence || 1) * 100)}%
                  </span>
                </div>

                {/* Provenance details */}
                {selectedEdgeData.source_document_id && (
                  <div className="detail-row">
                    <span className="detail-key">Source Doc ID:</span>
                    <span className="detail-val font-mono">
                      {selectedEdgeData.source_document_id.slice(0, 14)}...
                    </span>
                  </div>
                )}

                {selectedEdgeData.extracted_at && (
                  <div className="detail-row">
                    <span className="detail-key">Extracted:</span>
                    <span className="detail-val">
                      {new Date(selectedEdgeData.extracted_at).toLocaleDateString()}
                    </span>
                  </div>
                )}

                {/* Evidence snippet: WHY the relationship exists */}
                <div className="evidence-snippet-section">
                  <span className="snippet-heading">Evidentiary Snippet & Provenance:</span>
                  {loadingEdgeEvidence ? (
                    <div className="details-loading-spinner">Verifying relationship ledger...</div>
                  ) : selectedEdgeData.evidence_snippet ? (
                    <blockquote className="evidence-quote">
                      &ldquo;{selectedEdgeData.evidence_snippet}&rdquo;
                    </blockquote>
                  ) : (
                    <p className="no-snippet-text">
                      Relationship inferred from co-occurrence in analyzed case filings.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* C. DEFAULT / IDLE PANEL (NO SELECTION) */}
          {!selectedNodeData && !selectedEdgeData && (
            <div className="panel-idle-card">
              <div className="idle-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 16v-4m0-4h.01" />
                </svg>
              </div>
              <h4 className="idle-title">Graph Inspection</h4>
              <p className="idle-desc">
                Select any entity node to view intelligence records and expand 1-hop connections. Click any edge to review evidentiary provenance and extraction snippets.
              </p>
            </div>
          )}
        </aside>
      </div>

      {/* 4. GRAPH LEGEND */}
      <footer className="graph-legend-bar">
        <div className="legend-section">
          <span className="legend-title">Relationship Statuses:</span>
          <div className="legend-item">
            <span className="legend-line line-confirmed" />
            <span className="legend-text">
              <strong>CONFIRMED:</strong> Direct evidentiary record
            </span>
          </div>
          <div className="legend-item">
            <span className="legend-line line-inferred" />
            <span className="legend-text">
              <strong>INFERRED:</strong> Multi-source coreference
            </span>
          </div>
          <div className="legend-item">
            <span className="legend-line line-predicted" />
            <span className="legend-text">
              <strong>PREDICTED:</strong> Algorithmic hypothesis
            </span>
          </div>
        </div>
      </footer>

      <style>{`
        .graph-workspace-layout {
          background: rgba(11, 16, 27, 0.7);
          border: 1px solid rgba(56, 189, 248, 0.15);
          border-radius: 14px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
        }

        /* 1. TOOLBAR */
        .graph-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem 1.25rem;
          background: rgba(15, 23, 42, 0.85);
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          font-size: 0.82rem;
        }

        .toolbar-left {
          display: flex;
          align-items: center;
          gap: 1.25rem;
        }

        .toolbar-stat {
          display: flex;
          align-items: center;
          gap: 0.4rem;
        }

        .stat-label {
          color: #94a3b8;
        }

        .stat-value {
          color: #38bdf8;
          font-weight: 700;
        }

        .truncated-badge {
          background: rgba(245, 158, 11, 0.12);
          border: 1px solid rgba(245, 158, 11, 0.3);
          color: #fbbf24;
          font-size: 0.7rem;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          font-weight: 600;
        }

        .toolbar-actions {
          display: flex;
          align-items: center;
          gap: 0.65rem;
        }

        .tool-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.4rem 0.75rem;
          background: rgba(15, 23, 42, 0.7);
          border: 1px solid rgba(56, 189, 248, 0.2);
          border-radius: 6px;
          color: #e2e8f0;
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .tool-btn:hover:not(:disabled) {
          background: rgba(30, 41, 59, 0.9);
          border-color: rgba(56, 189, 248, 0.4);
          color: #38bdf8;
        }

        .tool-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .spinning {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        /* 2. MAIN SPLIT */
        .graph-main-split {
          display: flex;
          height: 600px;
          position: relative;
        }

        .graph-viewport-area {
          flex: 1;
          position: relative;
          background: #06080d;
        }

        .graph-overlay-loading,
        .graph-overlay-error,
        .graph-overlay-empty {
          position: absolute;
          inset: 0;
          z-index: 10;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: rgba(6, 8, 13, 0.85);
          backdrop-filter: blur(4px);
          gap: 0.85rem;
          padding: 2rem;
          text-align: center;
          color: #cbd5e1;
        }

        .mini-radar-pulse {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(14, 165, 233, 0.2);
          border: 2px solid #38bdf8;
          animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
        }

        @keyframes ping {
          75%, 100% {
            transform: scale(1.8);
            opacity: 0;
          }
        }

        .retry-btn {
          margin-top: 0.5rem;
          padding: 0.45rem 1rem;
          background: rgba(14, 165, 233, 0.15);
          border: 1px solid rgba(56, 189, 248, 0.35);
          border-radius: 6px;
          color: #38bdf8;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
        }

        .empty-radar-icon {
          margin-bottom: 0.5rem;
        }

        .graph-overlay-empty h4 {
          font-size: 1.1rem;
          font-weight: 700;
          color: #f1f5f9;
        }

        .graph-overlay-empty p {
          font-size: 0.82rem;
          color: #94a3b8;
          max-width: 440px;
          line-height: 1.5;
        }

        /* 3. SIDEBAR */
        .graph-details-sidebar {
          width: 360px;
          background: rgba(11, 16, 27, 0.95);
          border-left: 1px solid rgba(255, 255, 255, 0.08);
          overflow-y: auto;
          display: flex;
          flex-direction: column;
        }

        .panel-card {
          padding: 1.25rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 0.75rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
          padding-bottom: 0.85rem;
        }

        .panel-title-group {
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }

        .panel-type-label {
          font-size: 0.68rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: #38bdf8;
          font-family: ui-monospace, monospace;
        }

        .panel-entity-name {
          font-size: 1.1rem;
          font-weight: 700;
          color: #f8fafc;
          line-height: 1.3;
        }

        .close-panel-btn {
          background: transparent;
          border: none;
          color: #64748b;
          font-size: 1rem;
          cursor: pointer;
          padding: 0.2rem;
        }

        .close-panel-btn:hover {
          color: #f1f5f9;
        }

        .panel-body {
          display: flex;
          flex-direction: column;
          gap: 0.85rem;
        }

        .detail-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.78rem;
        }

        .detail-key {
          color: #94a3b8;
          font-weight: 500;
        }

        .detail-val {
          color: #f1f5f9;
        }

        .entity-badge-pill {
          font-size: 0.68rem;
          font-weight: 700;
          padding: 0.2rem 0.55rem;
          border-radius: 4px;
          letter-spacing: 0.04em;
          font-family: ui-monospace, monospace;
        }

        .associated-cases-block {
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
          font-size: 0.78rem;
        }

        .case-chips-wrap {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
        }

        .case-chip {
          font-size: 0.7rem;
          padding: 0.15rem 0.45rem;
          background: rgba(14, 165, 233, 0.08);
          border: 1px solid rgba(56, 189, 248, 0.2);
          border-radius: 4px;
          color: #38bdf8;
        }

        .details-loading-spinner,
        .no-data-text {
          font-size: 0.75rem;
          color: #64748b;
        }

        /* EXPANSION BOX */
        .expansion-action-box {
          margin-top: 0.5rem;
          display: flex;
          flex-direction: column;
          gap: 0.6rem;
        }

        .expand-connections-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          padding: 0.55rem 1rem;
          background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
          border: 1px solid rgba(56, 189, 248, 0.35);
          border-radius: 8px;
          color: #ffffff;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .expand-connections-btn:hover:not(:disabled) {
          background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
        }

        .expand-connections-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .mini-spin {
          width: 12px;
          height: 12px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: #ffffff;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        .feedback-banner {
          font-size: 0.74rem;
          padding: 0.45rem 0.65rem;
          border-radius: 6px;
          line-height: 1.4;
        }

        .banner-success {
          background: rgba(16, 185, 129, 0.12);
          border: 1px solid rgba(16, 185, 129, 0.3);
          color: #34d399;
        }

        .banner-info {
          background: rgba(14, 165, 233, 0.12);
          border: 1px solid rgba(56, 189, 248, 0.3);
          color: #38bdf8;
        }

        .banner-error {
          background: rgba(239, 68, 68, 0.12);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #f87171;
        }

        /* RELATIONSHIP EVIDENCE STYLING */
        .status-pill-small {
          font-size: 0.68rem;
          font-weight: 700;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          font-family: ui-monospace, monospace;
        }

        .badge-confirmed {
          background: rgba(14, 165, 233, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.3);
        }

        .badge-inferred {
          background: rgba(129, 140, 248, 0.15);
          color: #a5b4fc;
          border: 1px solid rgba(129, 140, 248, 0.3);
        }

        .badge-predicted {
          background: rgba(245, 158, 11, 0.15);
          color: #fbbf24;
          border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .evidence-snippet-section {
          margin-top: 0.5rem;
          padding-top: 0.75rem;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
        }

        .snippet-heading {
          display: block;
          font-size: 0.75rem;
          font-weight: 600;
          color: #94a3b8;
          margin-bottom: 0.5rem;
        }

        .evidence-quote {
          background: rgba(15, 23, 42, 0.8);
          border-left: 3px solid #38bdf8;
          border-radius: 0 6px 6px 0;
          padding: 0.75rem;
          font-size: 0.8rem;
          font-style: italic;
          color: #cbd5e1;
          line-height: 1.5;
          margin: 0;
        }

        .no-snippet-text {
          font-size: 0.75rem;
          color: #64748b;
          line-height: 1.4;
        }

        /* IDLE CARD */
        .panel-idle-card {
          padding: 3rem 1.5rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          color: #94a3b8;
          margin: auto 0;
        }

        .idle-icon {
          color: #475569;
          margin-bottom: 0.85rem;
        }

        .idle-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: #cbd5e1;
          margin-bottom: 0.35rem;
        }

        .idle-desc {
          font-size: 0.78rem;
          color: #64748b;
          line-height: 1.5;
        }

        /* 4. LEGEND */
        .graph-legend-bar {
          background: rgba(15, 23, 42, 0.9);
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          padding: 0.65rem 1.25rem;
        }

        .legend-section {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 1.25rem;
          font-size: 0.74rem;
        }

        .legend-title {
          font-weight: 700;
          color: #94a3b8;
        }

        .legend-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .legend-line {
          width: 24px;
          height: 2px;
          display: inline-block;
        }

        .line-confirmed {
          background: #38bdf8;
        }

        .line-inferred {
          background: #818cf8;
          border-top: 2px dashed #818cf8;
          height: 0;
        }

        .line-predicted {
          background: #f59e0b;
          border-top: 2px dotted #f59e0b;
          height: 0;
        }

        .legend-text {
          color: #cbd5e1;
        }

        .legend-text strong {
          color: #f8fafc;
        }

        .font-mono {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        @media (max-width: 900px) {
          .graph-main-split {
            flex-direction: column;
            height: auto;
          }
          .graph-viewport-area {
            height: 480px;
          }
          .graph-details-sidebar {
            width: 100%;
            border-left: none;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
          }
        }
      `}</style>
    </div>
  );
}

// Wrapper providing ReactFlow context
export default function CaseGraphView({ caseId }) {
  return (
    <ReactFlowProvider>
      <GraphCanvas caseId={caseId} />
    </ReactFlowProvider>
  );
}
