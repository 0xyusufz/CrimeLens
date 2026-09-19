"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import { apiClient } from "../lib/apiClient";

// Entity type visual tokens with refined analytical aesthetics (Clean light badges)
const ENTITY_CONFIG = {
  PERSON: {
    color: "#1d4ed8",
    bg: "#eff6ff",
    border: "#bfdbfe",
    icon: "👤",
    label: "Person",
  },
  PHONE: {
    color: "#7c3aed",
    bg: "#f5f3ff",
    border: "#ddd6fe",
    icon: "📞",
    label: "Phone",
  },
  BANK_ACCOUNT: {
    color: "#047857",
    bg: "#ecfdf5",
    border: "#a7f3d0",
    icon: "💳",
    label: "Bank Account",
  },
  VEHICLE: {
    color: "#4338ca",
    bg: "#eef2ff",
    border: "#c7d2fe",
    icon: "🚗",
    label: "Vehicle",
  },
  ORGANIZATION: {
    color: "#334155",
    bg: "#f1f5f9",
    border: "#cbd5e1",
    icon: "🏢",
    label: "Organization",
  },
  LOCATION: {
    color: "#be123c",
    bg: "#fff1f2",
    border: "#fecdd3",
    icon: "📍",
    label: "Location",
  },
  EVENT: {
    color: "#c2410c",
    bg: "#fff7ed",
    border: "#fed7aa",
    icon: "🚨",
    label: "Event",
  },
};

// Custom React Flow Node: Investigation Subject / Entity Card
function InvestigationNode({ data, selected }) {
  const isFocus = !!data.isFocus;
  const isSos = !!data.isSos;
  const isDimmed = !!data.isDimmed;
  const degree = data.degree ?? 0;
  const rawType = data.type || "PERSON";
  const config = ENTITY_CONFIG[rawType] || ENTITY_CONFIG.PERSON;

  return (
    <div
      className={`inv-card ${isFocus ? "card-focus" : ""} ${isSos ? "card-sos" : ""} ${
        selected ? "card-selected" : ""
      } ${isDimmed ? "card-dimmed" : ""}`}
    >
      {/* 4 Compass Handles (Source & Target) */}
      <Handle type="target" position={Position.Top} id="target-top" className="inv-handle" />
      <Handle type="source" position={Position.Top} id="source-top" className="inv-handle" />
      <Handle type="target" position={Position.Bottom} id="target-bottom" className="inv-handle" />
      <Handle type="source" position={Position.Bottom} id="source-bottom" className="inv-handle" />
      <Handle type="target" position={Position.Left} id="target-left" className="inv-handle" />
      <Handle type="source" position={Position.Left} id="source-left" className="inv-handle" />
      <Handle type="target" position={Position.Right} id="target-right" className="inv-handle" />
      <Handle type="source" position={Position.Right} id="source-right" className="inv-handle" />

      {/* Top Banner for Focus or High-Threat */}
      {isFocus && (
        <div className="card-top-banner banner-focus">
          <span>SUBJECT UNDER INVESTIGATION</span>
        </div>
      )}
      {!isFocus && isSos && (
        <div className="card-top-banner banner-sos">
          <span>ACCUSED / KEY THREAT</span>
        </div>
      )}

      {/* Header Row: Type Tag + Degree Badge */}
      <div className="card-header-row">
        <span
          className="card-type-tag"
          style={{
            color: config.color,
            background: config.bg,
            border: `1px solid ${config.border}`,
          }}
        >
          <span className="type-icon">{config.icon}</span>
          <span className="type-name">{config.label}</span>
        </span>
        <span
          className="card-degree-badge"
          title={`${degree} Connection${degree === 1 ? "" : "s"}`}
        >
          {degree}
        </span>
      </div>

      {/* Primary Canonical Name (2 Lines Clamped) */}
      <div className="card-title-wrap" title={data.name}>
        <span className={`card-name ${isFocus ? "name-focus" : ""}`}>{data.name}</span>
      </div>

      <style>{`
        .inv-card {
          position: relative;
          width: 176px;
          min-height: 82px;
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-radius: 9px;
          padding: 8px 10px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 10px -2px rgba(0, 0, 0, 0.04);
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          z-index: 3;
          box-sizing: border-box;
        }

        .inv-card:hover {
          background: #f8fafc;
          border-color: #94a3b8;
          box-shadow: 0 4px 14px -2px rgba(0, 0, 0, 0.1);
          transform: translateY(-2px);
          z-index: 8;
        }

        /* Focus Center Subject (Clean neutral border, simple informative card) */
        .card-focus {
          background: #ffffff !important;
          border: 1.5px solid #94a3b8 !important;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
          z-index: 10 !important;
        }

        /* Accused / SOS / Threat (Clean neutral border, simple informative card) */
        .card-sos {
          background: #ffffff !important;
          border: 1.5px solid #94a3b8 !important;
          box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08) !important;
        }

        /* Selected Active State */
        .card-selected {
          border-color: #64748b !important;
          box-shadow: 0 0 0 2px rgba(100, 116, 139, 0.2), 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        }

        /* Dimmed in Focus Mode */
        .card-dimmed {
          opacity: 0.25 !important;
          filter: grayscale(85%) !important;
          pointer-events: auto;
        }

        .card-top-banner {
          font-size: 0.58rem;
          font-weight: 750;
          letter-spacing: 0.04em;
          padding: 2px 4px;
          border-radius: 4px;
          text-align: center;
          margin-bottom: 4px;
        }

        .banner-focus {
          background: #f1f5f9;
          color: #334155;
          border: 1px solid #cbd5e1;
        }

        .banner-sos {
          background: #f1f5f9;
          color: #334155;
          border: 1px solid #cbd5e1;
        }

        .card-header-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 4px;
        }

        .card-type-tag {
          display: inline-flex;
          align-items: center;
          gap: 3px;
          font-size: 0.65rem;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 4px;
          letter-spacing: 0.02em;
          white-space: nowrap;
        }

        .type-icon {
          font-size: 0.72rem;
          line-height: 1;
        }

        .card-degree-badge {
          font-size: 0.66rem;
          font-weight: 700;
          background: #f1f5f9;
          color: #475569;
          padding: 1px 5px;
          border-radius: 9999px;
          line-height: 1.1;
          border: 1px solid #cbd5e1;
        }

        .card-title-wrap {
          margin-top: 4px;
          min-height: 32px;
          display: flex;
          align-items: center;
        }

        .card-name {
          font-size: 0.8rem;
          font-weight: 700;
          color: #0f172a;
          line-height: 1.25;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          text-overflow: ellipsis;
          word-break: break-word;
        }

        .name-focus {
          color: #0f172a;
          font-weight: 800;
        }

        :global(.inv-handle) {
          width: 7px !important;
          height: 7px !important;
          background: #64748b !important;
          border: 1.5px solid #ffffff !important;
          border-radius: 50% !important;
          opacity: 0 !important;
          pointer-events: none !important;
          transition: opacity 0.15s ease !important;
        }

        .inv-card:hover :global(.inv-handle) {
          opacity: 0.8 !important;
        }
      `}</style>
    </div>
  );
}

// Inline Markdown Parser for Dossier Report
function parseInlineMarkdown(text) {
  if (!text || typeof text !== "string") return text;

  const tokens = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIdx = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      tokens.push(text.substring(lastIdx, match.index));
    }
    const chunk = match[0];
    if (chunk.startsWith("**") && chunk.endsWith("**") && chunk.length >= 4) {
      tokens.push(
        <strong key={match.index} className="md-bold">
          {chunk.slice(2, -2)}
        </strong>
      );
    } else if (chunk.startsWith("*") && chunk.endsWith("*") && chunk.length >= 2) {
      tokens.push(
        <em key={match.index} className="md-italic">
          {chunk.slice(1, -1)}
        </em>
      );
    } else if (chunk.startsWith("`") && chunk.endsWith("`") && chunk.length >= 2) {
      tokens.push(
        <code key={match.index} className="md-code">
          {chunk.slice(1, -1)}
        </code>
      );
    } else {
      tokens.push(chunk);
    }
    lastIdx = regex.lastIndex;
  }

  if (lastIdx < text.length) {
    tokens.push(text.substring(lastIdx));
  }

  return tokens.length > 0 ? tokens : text;
}

// Clean Formatted Markdown Renderer for Dossier Report
function DossierMarkdownViewer({ markdown }) {
  if (!markdown) return null;

  const lines = markdown.split("\n");
  const elements = [];
  let currentList = null;

  const flushList = (key) => {
    if (currentList && currentList.items.length > 0) {
      if (currentList.type === "ul") {
        elements.push(
          <ul key={`list-${key}`} className="dossier-md-ul">
            {currentList.items.map((item, idx) => (
              <li key={idx} className="dossier-md-li">
                {parseInlineMarkdown(item)}
              </li>
            ))}
          </ul>
        );
      } else {
        elements.push(
          <ol key={`list-${key}`} className="dossier-md-ol">
            {currentList.items.map((item, idx) => (
              <li key={idx} className="dossier-md-li">
                {parseInlineMarkdown(item)}
              </li>
            ))}
          </ol>
        );
      }
      currentList = null;
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList(index);
      return;
    }

    if (trimmed.startsWith("# ")) {
      flushList(index);
      elements.push(
        <h3 key={`h1-${index}`} className="dossier-md-h1">
          {parseInlineMarkdown(trimmed.substring(2))}
        </h3>
      );
      return;
    }

    if (trimmed.startsWith("## ")) {
      flushList(index);
      elements.push(
        <h4 key={`h2-${index}`} className="dossier-md-h2">
          {parseInlineMarkdown(trimmed.substring(3))}
        </h4>
      );
      return;
    }

    if (trimmed.startsWith("### ")) {
      flushList(index);
      elements.push(
        <h5 key={`h3-${index}`} className="dossier-md-h3">
          {parseInlineMarkdown(trimmed.substring(4))}
        </h5>
      );
      return;
    }

    if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
      const itemText = trimmed.substring(2);
      if (currentList && currentList.type === "ul") {
        currentList.items.push(itemText);
      } else {
        flushList(index);
        currentList = { type: "ul", items: [itemText] };
      }
      return;
    }

    const olMatch = trimmed.match(/^\d+\.\s+(.+)$/);
    if (olMatch) {
      const itemText = olMatch[1];
      if (currentList && currentList.type === "ol") {
        currentList.items.push(itemText);
      } else {
        flushList(index);
        currentList = { type: "ol", items: [itemText] };
      }
      return;
    }

    if (trimmed.startsWith("> ")) {
      flushList(index);
      elements.push(
        <blockquote key={`quote-${index}`} className="dossier-md-quote">
          {parseInlineMarkdown(trimmed.substring(2))}
        </blockquote>
      );
      return;
    }

    flushList(index);
    elements.push(
      <p key={`p-${index}`} className="dossier-md-p">
        {parseInlineMarkdown(trimmed)}
      </p>
    );
  });

  flushList("end");

  return <div className="dossier-markdown-container">{elements}</div>;
}

// Deterministic Hierarchical/Directional Investigation Layout Engine
function buildInvestigationLayout(rfNodes, rawRels, focusNodeId = null, isFocusMode = false) {
  if (!rfNodes || rfNodes.length === 0) {
    return { nodes: [], edges: [] };
  }

  // 1. Build adjacency list & degree mapping
  const degreeMap = new Map();
  const adj = new Map();
  rfNodes.forEach((n) => {
    degreeMap.set(n.id, 0);
    adj.set(n.id, new Set());
  });

  rawRels.forEach((r) => {
    const s = r.source_entity_id || r.source;
    const t = r.target_entity_id || r.target;
    if (adj.has(s) && adj.has(t)) {
      degreeMap.set(s, (degreeMap.get(s) || 0) + 1);
      degreeMap.set(t, (degreeMap.get(t) || 0) + 1);
      adj.get(s).add(t);
      adj.get(t).add(s);
    }
  });

  // 2. Determine Focus Node (Subject of Investigation)
  let focusId = focusNodeId;
  if (!focusId || !adj.has(focusId)) {
    // Pick the highest degree node as default primary subject
    let maxDeg = -1;
    for (const [id, deg] of degreeMap.entries()) {
      if (deg > maxDeg) {
        maxDeg = deg;
        focusId = id;
      }
    }
  }

  // Identify SOS / High-Threat nodes
  const maxDegree = Math.max(1, ...Array.from(degreeMap.values()));
  const sosNodeIds = new Set();
  rfNodes.forEach((n) => {
    const deg = degreeMap.get(n.id) || 0;
    const nameLower = (n.data?.name || "").toLowerCase();
    if (
      (deg >= Math.max(4, maxDegree - 1) && (nameLower.includes("meher") || nameLower.includes("sinha") || deg >= 5)) ||
      nameLower.includes("accused") ||
      nameLower.includes("punjilal")
    ) {
      sosNodeIds.add(n.id);
    }
  });

  const centerX = 640;
  const centerY = 440;

  // 3. BFS levels from focusId
  const level0 = focusId ? [focusId] : [];
  const level1 = [];
  const level2 = [];
  const visited = new Set(level0);

  if (focusId && adj.has(focusId)) {
    for (const neighborId of adj.get(focusId)) {
      if (!visited.has(neighborId)) {
        visited.add(neighborId);
        level1.push(neighborId);
      }
    }
    for (const l1Id of level1) {
      for (const neighborId of adj.get(l1Id)) {
        if (!visited.has(neighborId)) {
          visited.add(neighborId);
          level2.push({ id: neighborId, parentId: l1Id });
        }
      }
    }
  }

  // Remaining nodes in disconnected clusters
  const remaining = rfNodes.filter((n) => !visited.has(n.id)).map((n) => n.id);

  // 4. Coordinates map: nodeId -> { x, y }
  const positions = new Map();

  // Position Level 0 (Focus Subject) exactly at center
  if (focusId) {
    positions.set(focusId, { x: centerX, y: centerY });
  }

  // Position Level 1 Nodes (Direct Relationships) in generous adaptive ring
  const typeOrder = {
    PHONE: 1,
    BANK_ACCOUNT: 2,
    ORGANIZATION: 3,
    PERSON: 4,
    LOCATION: 5,
    VEHICLE: 6,
    EVENT: 7,
  };

  const nodeObjMap = new Map(rfNodes.map((n) => [n.id, n]));

  level1.sort((a, b) => {
    const typeA = nodeObjMap.get(a)?.data?.type || "";
    const typeB = nodeObjMap.get(b)?.data?.type || "";
    return (typeOrder[typeA] || 99) - (typeOrder[typeB] || 99);
  });

  const n1 = level1.length;
  // Adaptive radius: at least 320px, increasing generously with node count
  const radius1 = Math.max(320, 220 + n1 * 28);
  const angleStep1 = n1 > 0 ? (2 * Math.PI) / n1 : 0;

  const l1Angles = new Map();

  level1.forEach((id, i) => {
    // Start from top (-PI/2) and spread clockwise
    const angle = -Math.PI / 2 + i * angleStep1;
    l1Angles.set(id, angle);
    positions.set(id, {
      x: centerX + radius1 * Math.cos(angle),
      y: centerY + radius1 * Math.sin(angle),
    });
  });

  // Position Level 2 Nodes (Secondary Connections)
  const childrenByParent = new Map();
  level2.forEach(({ id, parentId }) => {
    if (!childrenByParent.has(parentId)) childrenByParent.set(parentId, []);
    childrenByParent.get(parentId).push(id);
  });

  const radius2 = radius1 + 240;

  for (const [parentId, childIds] of childrenByParent.entries()) {
    const parentAngle = l1Angles.get(parentId) ?? 0;
    const childCount = childIds.length;
    const fanSpread = Math.min(0.65, 0.22 * childCount);

    childIds.forEach((childId, idx) => {
      const offset = childCount === 1 ? 0 : -fanSpread / 2 + (idx / (childCount - 1)) * fanSpread;
      const childAngle = parentAngle + offset;
      positions.set(childId, {
        x: centerX + radius2 * Math.cos(childAngle),
        y: centerY + radius2 * Math.sin(childAngle),
      });
    });
  }

  // Position any remaining disconnected clusters in clean orbital pods around the network
  if (remaining.length > 0) {
    const remainingSet = new Set(remaining);
    const remClusters = [];
    const remVisited = new Set();

    for (const remId of remaining) {
      if (!remVisited.has(remId)) {
        const cluster = [];
        const queue = [remId];
        remVisited.add(remId);
        while (queue.length > 0) {
          const curr = queue.shift();
          cluster.push(curr);
          const neighbors = adj.get(curr) || new Set();
          for (const nId of neighbors) {
            if (remainingSet.has(nId) && !remVisited.has(nId)) {
              remVisited.add(nId);
              queue.push(nId);
            }
          }
        }
        remClusters.push(cluster);
      }
    }

    // Sort clusters by size (largest first)
    remClusters.sort((a, b) => b.length - a.length);
    const numClusters = remClusters.length;
    const baseOrbitDist = radius2 + 380;

    remClusters.forEach((cluster, cIdx) => {
      // Pick local hub (node with highest degree in this cluster)
      let localHubId = cluster[0];
      let maxLocalDeg = -1;
      for (const cId of cluster) {
        const d = degreeMap.get(cId) || 0;
        if (d > maxLocalDeg) {
          maxLocalDeg = d;
          localHubId = cId;
        }
      }

      // Distribute cluster centers radially around the main graph
      const clusterAngle = -Math.PI / 4 + (cIdx * (2 * Math.PI)) / Math.max(1, numClusters);
      const orbitDist = baseOrbitDist + (cIdx % 2) * 120;
      const clusterCenterX = centerX + orbitDist * Math.cos(clusterAngle);
      const clusterCenterY = centerY + orbitDist * Math.sin(clusterAngle);

      positions.set(localHubId, { x: clusterCenterX, y: clusterCenterY });

      const otherMembers = cluster.filter((id) => id !== localHubId);
      const mCount = otherMembers.length;
      if (mCount > 0) {
        const miniRadius = Math.max(180, 120 + mCount * 18);
        const miniAngleStep = (2 * Math.PI) / mCount;
        otherMembers.forEach((mId, mIdx) => {
          const mAngle = mIdx * miniAngleStep;
          positions.set(mId, {
            x: clusterCenterX + miniRadius * Math.cos(mAngle),
            y: clusterCenterY + miniRadius * Math.sin(mAngle),
          });
        });
      }
    });
  }

  // 5. Analytical Collision Detection & Box-Push Pass
  const minClearanceX = 220;
  const minClearanceY = 135;

  for (let iter = 0; iter < 16; iter++) {
    let hadCollision = false;
    for (let i = 0; i < rfNodes.length; i++) {
      for (let j = i + 1; j < rfNodes.length; j++) {
        const idA = rfNodes[i].id;
        const idB = rfNodes[j].id;
        const posA = positions.get(idA);
        const posB = positions.get(idB);
        if (!posA || !posB) continue;

        const dx = posB.x - posA.x;
        const dy = posB.y - posA.y;
        const absX = Math.abs(dx);
        const absY = Math.abs(dy);

        if (absX < minClearanceX && absY < minClearanceY) {
          hadCollision = true;
          const overlapX = (minClearanceX - absX) * (dx >= 0 ? 1 : -1);
          const overlapY = (minClearanceY - absY) * (dy >= 0 ? 1 : -1);

          if (idA === focusId) {
            posB.x += overlapX;
            posB.y += overlapY;
          } else if (idB === focusId) {
            posA.x -= overlapX;
            posA.y -= overlapY;
          } else {
            posA.x -= overlapX * 0.5;
            posA.y -= overlapY * 0.5;
            posB.x += overlapX * 0.5;
            posB.y += overlapY * 0.5;
          }
        }
      }
    }
    if (!hadCollision) break;
  }

  // 6. Focus Mode Dimming Set
  const focusConnectedSet = new Set(level0.concat(level1));

  // Build Final Nodes
  const formattedNodes = rfNodes.map((n) => {
    const pos = positions.get(n.id) || { x: centerX, y: centerY };
    const deg = degreeMap.get(n.id) || 0;
    const isFocus = n.id === focusId;
    const isSos = sosNodeIds.has(n.id);
    const isDimmed = isFocusMode && !focusConnectedSet.has(n.id);
    const lvl = n.id === focusId ? 0 : level1.includes(n.id) ? 1 : level2.some((c) => c.id === n.id) ? 2 : 3;

    return {
      ...n,
      position: { x: Math.round(pos.x - 88), y: Math.round(pos.y - 41) },
      data: {
        ...n.data,
        degree: deg,
        isFocus,
        isSos,
        isDimmed,
        level: lvl,
      },
    };
  });

  // 7. Optimal Compass Handle Selection for Edges
  const formattedEdges = rawRels.map((r) => {
    const sourceId = r.source_entity_id || r.source;
    const targetId = r.target_entity_id || r.target;
    const posS = positions.get(sourceId) || { x: 0, y: 0 };
    const posT = positions.get(targetId) || { x: 0, y: 0 };

    const dx = posT.x - posS.x;
    const dy = posT.y - posS.y;

    let sourceHandle = "source-bottom";
    let targetHandle = "target-top";

    if (Math.abs(dx) > Math.abs(dy)) {
      if (dx > 0) {
        sourceHandle = "source-right";
        targetHandle = "target-left";
      } else {
        sourceHandle = "source-left";
        targetHandle = "target-right";
      }
    } else {
      if (dy > 0) {
        sourceHandle = "source-bottom";
        targetHandle = "target-top";
      } else {
        sourceHandle = "source-top";
        targetHandle = "target-bottom";
      }
    }

    const isConnectedToFocus = sourceId === focusId || targetId === focusId;
    const isDimmed = isFocusMode && !isConnectedToFocus;

    const isPredicted = r.status === "PREDICTED" || (r.confidence != null && r.confidence < 0.75);
    const strokeColor = isDimmed
      ? "rgba(148, 163, 184, 0.25)"
      : isConnectedToFocus
      ? "#0284c7"
      : isPredicted
      ? "#94a3b8"
      : "#0ea5e9";
    const strokeWidth = isDimmed ? 1.0 : isConnectedToFocus ? 2.5 : isPredicted ? 1.6 : 2.0;
    const relLabel = (r.relationship || "").toLowerCase().replace(/_/g, " ");

    return {
      id: r.relationship_id,
      source: sourceId,
      target: targetId,
      sourceHandle,
      targetHandle,
      type: "smoothstep",
      animated: isConnectedToFocus,
      style: {
        stroke: strokeColor,
        strokeWidth,
        strokeDasharray: isPredicted ? "5 5" : undefined,
        opacity: isDimmed ? 0.2 : 1,
        transition: "all 0.3s ease",
      },
      label: isDimmed ? undefined : relLabel,
      labelStyle: { fill: "#334155", fontWeight: 600, fontSize: 10.5 },
      labelBgStyle: { fill: "#ffffff", fillOpacity: 0.98, rx: 4, ry: 4, stroke: "#cbd5e1", strokeWidth: 1 },
      labelBgPadding: [6, 2],
      data: {
        relationshipId: r.relationship_id,
        relationship: r.relationship,
        status: r.status,
        confidence: r.confidence,
        sourceDocumentId: r.source_document_id,
        evidenceSnippet: r.evidence_snippet,
        sourceEntityId: sourceId,
        targetEntityId: targetId,
      },
    };
  });

  return {
    nodes: formattedNodes,
    edges: formattedEdges,
    focusId,
    focusPos: positions.get(focusId) || { x: centerX, y: centerY },
  };
}


// Helper to escape HTML characters safely for printable reports
function escapeHtmlForReport(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Highlight specific important words (e.g. suspect names, key entities, critical threats) with a yellow highlighter mark
function highlightImportantTerms(text, terms = []) {
  if (!text || typeof text !== "string") return "";
  const validTerms = [...terms]
    .filter((t) => t && typeof t === "string" && t.trim().length > 1)
    .map((t) => t.trim())
    .sort((a, b) => b.length - a.length);

  if (validTerms.length === 0) return text;

  const escapedTerms = validTerms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(<[^>]+>)|\\b(${escapedTerms.join("|")})\\b`, "gi");

  return text.replace(pattern, (match, tag, word) => {
    if (tag) return tag; // preserve existing HTML tag untouched
    return `<mark class="pdf-highlight">${word}</mark>`;
  });
}

// Convert markdown to clean, semantic HTML elements for print output
function convertMarkdownToPrintableHtml(markdown, importantTerms = []) {
  if (!markdown || typeof markdown !== "string") return "";
  const lines = markdown.split("\n");
  const htmlParts = [];
  let inUl = false;
  let inOl = false;
  const closeLists = () => {
    if (inUl) { htmlParts.push("</ul>"); inUl = false; }
    if (inOl) { htmlParts.push("</ol>"); inOl = false; }
  };
  const formatInline = (text) => {
    let escaped = escapeHtmlForReport(text);
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong class="pdf-bold">$1</strong>');
    escaped = escaped.replace(/\*([^*]+)\*/g, '<em class="pdf-italic">$1</em>');
    escaped = escaped.replace(/==([^=]+)==/g, '<mark class="pdf-highlight">$1</mark>');
    escaped = escaped.replace(/`([^`]+)`/g, '<code class="pdf-code">$1</code>');
    if (importantTerms.length > 0) {
      escaped = highlightImportantTerms(escaped, importantTerms);
    }
    return escaped;
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) { closeLists(); return; }
    if (trimmed.startsWith("# ")) {
      closeLists();
      htmlParts.push('<h2 class="pdf-h1">' + formatInline(trimmed.substring(2)) + '</h2>');
      return;
    }
    if (trimmed.startsWith("## ")) {
      closeLists();
      htmlParts.push('<h3 class="pdf-h2">' + formatInline(trimmed.substring(3)) + '</h3>');
      return;
    }
    if (trimmed.startsWith("### ")) {
      closeLists();
      htmlParts.push('<h4 class="pdf-h3">' + formatInline(trimmed.substring(4)) + '</h4>');
      return;
    }
    if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
      if (inOl) closeLists();
      if (!inUl) { htmlParts.push('<ul class="pdf-ul">'); inUl = true; }
      htmlParts.push('<li class="pdf-li">' + formatInline(trimmed.substring(2)) + '</li>');
      return;
    }
    const olMatch = trimmed.match(/^\d+\.\s+(.+)$/);
    if (olMatch) {
      if (inUl) closeLists();
      if (!inOl) { htmlParts.push('<ol class="pdf-ol">'); inOl = true; }
      htmlParts.push('<li class="pdf-li">' + formatInline(olMatch[1]) + '</li>');
      return;
    }
    if (trimmed.startsWith("> ")) {
      closeLists();
      htmlParts.push('<blockquote class="pdf-quote">' + formatInline(trimmed.substring(2)) + '</blockquote>');
      return;
    }
    closeLists();
    htmlParts.push('<p class="pdf-p">' + formatInline(trimmed) + '</p>');
  });
  closeLists();
  return htmlParts.join("\n");
}

// Build fully styled, self-contained printable HTML document
function buildPrintableDossierHtml({ caseId, caseTitle, analysis }) {
  const title = caseTitle || `Case File #${caseId || "INTEL"}`;
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric"
  });
  const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const reportId = "DOSSIER-" + (caseId ? String(caseId).slice(0, 8).toUpperCase() : "INTEL") + "-" + Math.floor(1000 + Math.random() * 9000);

  // Extract key terms (suspect names, key entities, critical threats) to specifically highlight in yellow text
  const poiNames = (analysis.potential_persons_of_interest || [])
    .map((p) => p.name)
    .filter(Boolean);
  const keyEntities = (analysis.key_entities || [])
    .map((e) => e.name)
    .filter(Boolean);
  const criticalThreatTerms = [
    "CRITICAL THREAT",
    "HIGH THREAT",
    "CRITICAL",
    "PRIMARY SUSPECT",
    "PERPETRATOR",
    "FLIGHT RISK"
  ];
  const importantTerms = [...new Set([...poiNames, ...keyEntities, ...criticalThreatTerms])];

  let summaryHtml = "";
  if (analysis.case_summary) {
    summaryHtml = `
      <section class="report-section">
        <div class="section-heading">
          <span class="sec-num">01.</span>
          <h2>Executive Intelligence Summary</h2>
        </div>
        <div class="summary-content">
          <p class="summary-text">${highlightImportantTerms(escapeHtmlForReport(analysis.case_summary), importantTerms)}</p>
        </div>
      </section>
    `;
  }

  let poisHtml = "";
  if (analysis.potential_persons_of_interest && analysis.potential_persons_of_interest.length > 0) {
    poisHtml = `
      <section class="report-section">
        <div class="section-heading">
          <span class="sec-num">02.</span>
          <h2>Identified Persons of Interest & Key Subjects</h2>
        </div>
        <div class="poi-list">
          ${analysis.potential_persons_of_interest.map((poi) => {
            const threat = (poi.threat_level || "MEDIUM").toUpperCase();
            const isHighOrCrit = threat.includes("CRITICAL") || threat.includes("HIGH");
            return `
              <div class="poi-entry">
                <div class="poi-entry-header">
                  <span class="poi-name"><mark class="pdf-highlight">${escapeHtmlForReport(poi.name)}</mark></span>
                  ${poi.role ? `<span class="poi-role">— ${escapeHtmlForReport(poi.role)}</span>` : ""}
                  <span class="threat-text">${isHighOrCrit ? `[<mark class="pdf-highlight">${escapeHtmlForReport(threat)} THREAT</mark>]` : `[${escapeHtmlForReport(threat)} THREAT]`}</span>
                </div>
                <div class="poi-body">
                  <p class="poi-justification"><strong>Forensic Rationale:</strong> ${highlightImportantTerms(escapeHtmlForReport(poi.reason || poi.justification || "Identified key entity in criminal graph."), importantTerms)}</p>
                  ${poi.evidence ? `<p class="poi-evidence"><strong>Corroborating Evidence:</strong> "${highlightImportantTerms(escapeHtmlForReport(poi.evidence), importantTerms)}"</p>` : ""}
                </div>
              </div>
            `;
          }).join("")}
        </div>
      </section>
    `;
  }

  let leadsHtml = "";
  if (analysis.investigative_leads && analysis.investigative_leads.length > 0) {
    leadsHtml = `
      <section class="report-section">
        <div class="section-heading">
          <span class="sec-num">03.</span>
          <h2>Actionable Investigative Leads & Next Steps</h2>
        </div>
        <ol class="leads-list">
          ${analysis.investigative_leads.map((lead) => `
            <li class="lead-item">${highlightImportantTerms(escapeHtmlForReport(lead), importantTerms)}</li>
          `).join("")}
        </ol>
      </section>
    `;
  }

  let evidenceHtml = "";
  if (analysis.supporting_evidence && analysis.supporting_evidence.length > 0) {
    evidenceHtml = `
      <section class="report-section">
        <div class="section-heading">
          <span class="sec-num">04.</span>
          <h2>Evidentiary Citations & Fact Verifications</h2>
        </div>
        <div class="evidence-list">
          ${analysis.supporting_evidence.map((ev) => `
            <div class="ev-entry">
              <div class="ev-claim">• <strong>Fact:</strong> ${highlightImportantTerms(escapeHtmlForReport(ev.claim || "Corroborated Fact"), importantTerms)}</div>
              <blockquote class="ev-quote">"${highlightImportantTerms(escapeHtmlForReport(ev.quote), importantTerms)}"</blockquote>
              ${ev.source_document_id ? `<div class="ev-source">Document Ref: ${escapeHtmlForReport(ev.source_document_id)}</div>` : ""}
            </div>
          `).join("")}
        </div>
      </section>
    `;
  }

  let anomaliesHtml = "";
  if (analysis.contradictions_or_anomalies && analysis.contradictions_or_anomalies.length > 0) {
    anomaliesHtml = `
      <section class="report-section">
        <div class="section-heading heading-alert">
          <span class="sec-num">05.</span>
          <h2>Evidentiary Inconsistencies & Anomalies</h2>
        </div>
        <ul class="anomaly-list">
          ${analysis.contradictions_or_anomalies.map((ano) => `
            <li>${highlightImportantTerms(escapeHtmlForReport(ano), importantTerms)}</li>
          `).join("")}
        </ul>
      </section>
    `;
  }

  let dossierBodyHtml = "";
  if (analysis.dossier_markdown) {
    const formatted = convertMarkdownToPrintableHtml(analysis.dossier_markdown, importantTerms);
    dossierBodyHtml = `
      <section class="report-section">
        <div class="section-heading">
          <span class="sec-num">06.</span>
          <h2>Comprehensive Dossier Analysis & Detailed Intelligence</h2>
        </div>
        <div class="dossier-rendered-content">
          ${formatted}
        </div>
      </section>
    `;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CrimeLens Intelligence Dossier - ${escapeHtmlForReport(title)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f1f5f9;
      color: #0f172a;
      line-height: 1.55;
      font-size: 13.5px;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    /* Screen Topbar Controls */
    .screen-toolbar {
      position: sticky;
      top: 0;
      z-index: 1000;
      background: #0f172a;
      color: #f8fafc;
      padding: 0.75rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }

    .screen-toolbar-title {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 0.92rem;
      font-weight: 700;
      letter-spacing: -0.01em;
    }

    .screen-toolbar-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .btn-print {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      background: #2563eb;
      color: #ffffff;
      border: 1px solid #1d4ed8;
      padding: 0.5rem 1.15rem;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
      transition: all 0.15s ease;
    }

    .btn-print:hover {
      background: #1d4ed8;
      transform: translateY(-1px);
    }

    .btn-close {
      background: rgba(255, 255, 255, 0.1);
      color: #cbd5e1;
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 0.5rem 0.95rem;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .btn-close:hover {
      background: rgba(255, 255, 255, 0.18);
      color: #ffffff;
    }

    /* Printable Document Container */
    .document-wrapper {
      max-width: 860px;
      margin: 1.5rem auto 3rem auto;
      background: #ffffff;
      padding: 2.5rem 3rem;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
    }

    /* Official Department Header */
    .report-header {
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 1.25rem;
      margin-bottom: 1.5rem;
    }

    .agency-banner {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1.25rem;
    }

    .agency-identity {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }

    .agency-logo-icon {
      width: 38px;
      height: 38px;
      background: transparent !important;
      border: 1.5px solid #0f172a;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .agency-titles h1 {
      font-size: 1.2rem;
      font-weight: 900;
      color: #000000;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      line-height: 1.2;
    }

    .agency-titles p {
      font-size: 0.74rem;
      font-weight: 750;
      color: #475569;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      margin-top: 3px;
    }

    .security-badge {
      display: inline-block;
      color: #475569;
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      text-align: right;
    }

    .case-title-row {
      margin-top: 1rem;
      padding-top: 0.75rem;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 1.5rem;
    }

    .case-title-col h2 {
      font-size: 1.45rem;
      font-weight: 900;
      color: #000000;
      letter-spacing: -0.02em;
      line-height: 1.25;
    }

    .case-meta-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.75rem 1.5rem;
      margin-top: 1.25rem;
      padding: 0.85rem 0;
      border-top: 1px solid #cbd5e1;
      border-bottom: 1px solid #cbd5e1;
    }

    .meta-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .meta-label {
      font-size: 0.68rem;
      font-weight: 750;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .meta-value {
      font-size: 0.86rem;
      font-weight: 750;
      color: #000000;
      font-family: 'JetBrains Mono', monospace;
    }

    /* Section Styles */
    .report-section {
      margin-bottom: 1.75rem;
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .section-heading {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      padding-bottom: 0.35rem;
      border-bottom: 1px solid #e2e8f0;
      margin-bottom: 0.75rem;
    }

    .sec-num {
      color: #64748b;
      font-size: 0.82rem;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
    }

    .section-heading h2 {
      font-size: 0.98rem;
      font-weight: 850;
      color: #000000;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }

    .summary-content {
      padding: 0.25rem 0;
    }

    .summary-text {
      font-size: 0.88rem;
      color: #000000;
      line-height: 1.65;
      font-weight: 450;
    }

    /* POI Entries */
    .poi-list {
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }

    .poi-entry {
      padding: 0.55rem 0;
      border-bottom: 1px solid #e2e8f0;
    }

    .poi-entry:last-child {
      border-bottom: none;
    }

    .poi-entry-header {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .poi-name {
      font-size: 0.95rem;
      font-weight: 800;
      color: #000000;
    }

    .poi-role {
      font-size: 0.82rem;
      color: #475569;
      font-weight: 600;
    }

    .threat-text {
      font-size: 0.74rem;
      font-weight: 800;
      margin-left: 0.4rem;
    }

    .poi-justification {
      font-size: 0.84rem;
      color: #000000;
      line-height: 1.55;
      margin-top: 0.25rem;
    }

    .poi-evidence {
      font-size: 0.82rem;
      color: #334155;
      font-style: italic;
      margin-top: 0.25rem;
    }

    /* Leads */
    .leads-list {
      padding-left: 1.4rem;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }

    .lead-item {
      font-size: 0.85rem;
      color: #000000;
      line-height: 1.55;
      font-weight: 500;
    }

    /* Evidence Citations */
    .evidence-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .ev-entry {
      padding: 0.35rem 0;
      border-bottom: 1px solid #e2e8f0;
    }

    .ev-entry:last-child {
      border-bottom: none;
    }

    .ev-claim {
      font-size: 0.82rem;
      font-weight: 700;
      color: #000000;
      margin-bottom: 0.2rem;
    }

    .ev-quote {
      font-size: 0.83rem;
      color: #1e293b;
      font-style: italic;
      line-height: 1.5;
      border-left: 3px solid #94a3b8;
      padding-left: 0.65rem;
      margin: 0.25rem 0;
    }

    .ev-source {
      font-size: 0.7rem;
      color: #64748b;
      font-family: 'JetBrains Mono', monospace;
    }

    /* Anomalies */
    .anomaly-list {
      padding-left: 1.4rem;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      color: #000000;
      font-size: 0.85rem;
      line-height: 1.55;
    }

    /* Rendered Markdown Dossier */
    .dossier-rendered-content {
      padding: 0.25rem 0;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }

    .pdf-h1 {
      font-size: 1.12rem;
      font-weight: 800;
      color: #000000;
      margin: 0.9rem 0 0.35rem 0;
    }

    .pdf-h2 {
      font-size: 0.98rem;
      font-weight: 750;
      color: #000000;
      margin: 0.75rem 0 0.3rem 0;
    }

    .pdf-h3 {
      font-size: 0.88rem;
      font-weight: 700;
      color: #1e293b;
      margin: 0.6rem 0 0.2rem 0;
    }

    .pdf-p {
      font-size: 0.85rem;
      line-height: 1.62;
      color: #000000;
      margin-bottom: 0.4rem;
    }

    .pdf-ul, .pdf-ol {
      padding-left: 1.35rem;
      margin-bottom: 0.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .pdf-li {
      font-size: 0.85rem;
      color: #000000;
      line-height: 1.5;
    }

    .pdf-bold {
      font-weight: 800;
      color: #000000;
    }

    .pdf-italic {
      font-style: italic;
      color: #000000;
    }

    /* Yellow Highlighter Mark on specific terms only */
    .pdf-highlight {
      background-color: #fef08a !important;
      color: #000000 !important;
      padding: 0.1em 0.32em;
      border-radius: 2px;
      font-weight: 750;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }

    .pdf-code {
      font-family: 'JetBrains Mono', monospace;
      background: #f1f5f9;
      color: #0f172a;
      padding: 0.1rem 0.35rem;
      border-radius: 3px;
      font-size: 0.8rem;
    }

    .pdf-quote {
      border-left: 3px solid #94a3b8;
      background: transparent;
      padding: 0.4rem 0.75rem;
      font-style: italic;
      color: #1e293b;
      margin: 0.4rem 0;
      font-size: 0.83rem;
    }

    /* Certification Footer */
    .report-footer {
      margin-top: 2.5rem;
      padding-top: 1.25rem;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.74rem;
      color: #475569;
      font-weight: 600;
    }

    .footer-disclaimer {
      max-width: 600px;
      line-height: 1.4;
      font-style: italic;
    }

    /* Print Overrides */
    @media print {
      body {
        background: #ffffff !important;
        font-size: 11pt !important;
      }

      .screen-toolbar {
        display: none !important;
      }

      .document-wrapper {
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        box-shadow: none !important;
        max-width: 100% !important;
      }

      @page {
        size: A4 portrait;
        margin: 14mm 12mm 16mm 12mm;
      }

      * {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }

      .report-section {
        page-break-inside: avoid;
        break-inside: avoid;
      }
    }
  </style>
</head>
<body>
  <div class="screen-toolbar">
    <div class="screen-toolbar-title">
      <span>CrimeLens Forensic Dossier</span>
      <span style="opacity: 0.5;">|</span>
      <span style="font-weight: 500; font-size: 0.82rem; color: #94a3b8;">${escapeHtmlForReport(title)}</span>
    </div>
    <div class="screen-toolbar-actions">
      <button onclick="window.print()" class="btn-print">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 6 2 18 2 18 9"></polyline>
          <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
          <rect x="6" y="14" width="12" height="8"></rect>
        </svg>
        <span>Print / Save as PDF</span>
      </button>
      <button onclick="window.close()" class="btn-close">Close</button>
    </div>
  </div>

  <main class="document-wrapper">
    <header class="report-header">
      <div class="agency-banner">
        <div class="agency-identity">
          <div class="agency-logo-icon" title="CrimeLens">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2.5V21.5M2.5 12H21.5M5.28 5.28L18.72 18.72M5.28 18.72L18.72 5.28" stroke="#0f172a" stroke-width="3.5" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="agency-titles">
            <h1>CrimeLens Forensic Intelligence Platform</h1>
            <p>Criminal Network Analysis & Evidence Synthesis Division</p>
          </div>
        </div>
        <div class="security-badge">
          Law Enforcement Sensitive // Official Work Product
        </div>
      </div>

      <div class="case-title-row">
        <div class="case-title-col">
          <h2>${escapeHtmlForReport(title)}</h2>
        </div>
      </div>

      <div class="case-meta-grid">
        <div class="meta-item">
          <span class="meta-label">Case Identifier</span>
          <span class="meta-value">${escapeHtmlForReport(caseId || "N/A")}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Report ID</span>
          <span class="meta-value">${escapeHtmlForReport(reportId)}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Generated Timestamp</span>
          <span class="meta-value">${escapeHtmlForReport(dateStr)} ${escapeHtmlForReport(timeStr)}</span>
        </div>
      </div>
    </header>

    ${summaryHtml}
    ${poisHtml}
    ${leadsHtml}
    ${evidenceHtml}
    ${anomaliesHtml}
    ${dossierBodyHtml}

    <footer class="report-footer">
      <div class="footer-disclaimer">
        This intelligence dossier has been generated through deterministic graph reasoning and forensic entity resolution. Inferences must be independently corroborated before prosecutorial action.
      </div>
      <div class="footer-sign">
        <strong>CRIMELENS CORE</strong>
      </div>
    </footer>
  </main>

  <script>
    window.addEventListener('load', function() {
      setTimeout(function() {
        window.print();
      }, 350);
    });
  </script>
</body>
</html>`;
}

// Inner Graph Canvas Component
function GraphCanvas({ caseId, caseTitle, onOpenCopilot }) {
  const reactFlowInstance = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [graphError, setGraphError] = useState(null);
  const [isTruncated, setIsTruncated] = useState(false);

  // Investigation Subject / Focus State
  const [focusEntityId, setFocusEntityId] = useState(null);
  const [isFocusMode, setIsFocusMode] = useState(false);
  const rawNodesRef = useRef([]);
  const rawRelsRef = useRef([]);

  // Inspector & selection state
  const [selectedNodeData, setSelectedNodeData] = useState(null);
  const [loadingNodeDetails, setLoadingNodeDetails] = useState(false);
  const [expanding, setExpanding] = useState(false);
  const [expandFeedback, setExpandFeedback] = useState(null);
  const [selectedEdgeData, setSelectedEdgeData] = useState(null);
  const [loadingEdgeEvidence, setLoadingEdgeEvidence] = useState(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);

  // AI Deep Reasoning Analysis State
  const [analyzingAi, setAnalyzingAi] = useState(false);
  const [aiAnalysisResult, setAiAnalysisResult] = useState(null);
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [savedAiStatus, setSavedAiStatus] = useState({
    hasSavedReport: false,
    isNetworkChanged: false,
    savedAt: null,
  });

  // Check if a saved network intelligence report exists in backend store
  const checkAiReportStatus = useCallback(async () => {
    if (!caseId) return;
    try {
      const st = await apiClient(`/api/cases/${caseId}/intelligence/analyze/status?mode=full`);
      if (st?.has_saved_report) {
        setSavedAiStatus({
          hasSavedReport: true,
          isNetworkChanged: !!st.is_network_changed,
          savedAt: st.saved_at,
        });
        if (st.analysis) {
          setAiAnalysisResult(st.analysis);
        }
      } else {
        setSavedAiStatus({
          hasSavedReport: false,
          isNetworkChanged: false,
          savedAt: null,
        });
      }
    } catch (e) {
      console.warn("Failed checking AI report status:", e);
    }
  }, [caseId]);

  useEffect(() => {
    checkAiReportStatus();
  }, [checkAiReportStatus]);

  // Fullscreen / Expanded Canvas Mode
  const [isExpanded, setIsExpanded] = useState(false);

  // AI Doubt Clarification state for selected element (node or edge)
  const [doubtQuery, setDoubtQuery] = useState("");
  const [clarifyingAi, setClarifyingAi] = useState(false);
  const [aiClarification, setAiClarification] = useState(null);
  const [aiClarificationError, setAiClarificationError] = useState(null);

  // Compute direct connections for the currently selected node
  const selectedNodeConnections = useMemo(() => {
    if (!selectedNodeData?.id || !edges.length) return [];
    return edges
      .filter((e) => e.source === selectedNodeData.id || e.target === selectedNodeData.id)
      .map((e) => {
        const isOut = e.source === selectedNodeData.id;
        const otherNodeId = isOut ? e.target : e.source;
        const otherNode = nodes.find((n) => n.id === otherNodeId);
        return {
          edgeId: e.id,
          relationship: e.data?.relationship || "CONNECTED_TO",
          status: e.data?.status || "PREDICTED",
          confidence: e.data?.confidence,
          isOut,
          otherId: otherNodeId,
          otherName: otherNode?.data?.name || "Unknown Entity",
          otherType: otherNode?.data?.type || "Entity",
          evidenceSnippet: e.data?.evidenceSnippet,
          sourceDocumentId: e.data?.sourceDocumentId,
        };
      });
  }, [selectedNodeData, edges, nodes]);

  const handleClarifyDoubt = async (customQuestion = null) => {
    const q = (customQuestion || doubtQuery).trim();
    if (!q || clarifyingAi) return;

    setClarifyingAi(true);
    setAiClarificationError(null);

    let contextPrompt = "";
    if (selectedNodeData) {
      contextPrompt = `Regarding entity "${selectedNodeData.canonical_name || selectedNodeData.name}" (${selectedNodeData.type}): ${q}. Please answer clearly, citing verified case evidence, connections, and document sources.`;
    } else if (selectedEdgeData) {
      contextPrompt = `Regarding the relationship "${selectedEdgeData.relationship}" between entities in this case: ${q}. Please explain the evidence anchor, confidence, and investigative significance.`;
    }

    try {
      const res = await apiClient(`/api/cases/${caseId}/intelligence/copilot`, {
        method: "POST",
        body: JSON.stringify({
          question: contextPrompt,
          history: [],
        }),
      });
      setAiClarification({
        question: q,
        answer: res.answer || "No response received from intelligence engine.",
      });
      setDoubtQuery("");
    } catch (err) {
      setAiClarificationError("Could not clarify doubt at this time. Please retry.");
    } finally {
      setClarifyingAi(false);
    }
  };

  const handleToggleExpand = useCallback(() => {
    setIsExpanded((prev) => {
      const next = !prev;
      if (next) {
        try {
          const elem = document.documentElement;
          if (elem.requestFullscreen && !document.fullscreenElement) {
            elem.requestFullscreen().catch(() => {});
          }
        } catch {}
      } else {
        try {
          if (document.fullscreenElement && document.exitFullscreen) {
            document.exitFullscreen().catch(() => {});
          }
        } catch {}
      }
      setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.15, duration: 350 });
      }, 180);
      return next;
    });
  }, [reactFlowInstance]);

  // Handle ESC key & Fullscreen API change
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isExpanded) {
        setIsExpanded(false);
        try {
          if (document.fullscreenElement && document.exitFullscreen) {
            document.exitFullscreen().catch(() => {});
          }
        } catch {}
        setTimeout(() => {
          reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
        }, 150);
      }
    };

    const handleFullscreenChange = () => {
      if (!document.fullscreenElement && isExpanded) {
        setIsExpanded(false);
        setTimeout(() => {
          reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
        }, 150);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, [isExpanded, reactFlowInstance]);

  const nodeTypes = useMemo(
    () => ({
      investigationNode: InvestigationNode,
    }),
    []
  );

  // Compute and apply investigation network layout
  const applyNetworkLayout = useCallback(
    (rawNodes, rawRels, overrideFocusId = null, overrideFocusMode = null) => {
      if (!rawNodes || rawNodes.length === 0) {
        setNodes([]);
        setEdges([]);
        return null;
      }

      // Client-side sanitizer: filter out pronouns, generic fragments, and empty labels
      const JUNK_LABELS = new Set([
        "who", "by", "whom", "whose", "which", "what", "that", "this", "these", "those",
        "he", "she", "it", "they", "them", "him", "her", "his", "their", "theirs", "its",
        "someone", "anyone", "everyone", "nobody", "no one", "somebody", "anybody",
        "4y", "11thwards", "the sting", "sound of furniture's rustle"
      ]);

      const isJunkName = (name) => {
        if (!name) return true;
        const norm = name.trim().toLowerCase();
        return norm.length <= 1 || JUNK_LABELS.has(norm);
      };

      const validRawNodes = (rawNodes || []).filter((n) => !isJunkName(n.name));
      const validEntityIds = new Set(validRawNodes.map((n) => n.entity_id || n.id));

      const validRels = (rawRels || []).filter((r) => {
        const s = r.source_entity_id || r.source;
        const t = r.target_entity_id || r.target;
        return validEntityIds.has(s) && validEntityIds.has(t);
      });

      // Safety guard: only nodes participating in an active relationship are rendered
      const connectedEntityIds = new Set();
      validRels.forEach((r) => {
        const s = r.source_entity_id || r.source;
        const t = r.target_entity_id || r.target;
        if (s) connectedEntityIds.add(s);
        if (t) connectedEntityIds.add(t);
      });

      const activeNodes = validRawNodes.filter((n) =>
        connectedEntityIds.has(n.entity_id || n.id)
      );

      if (activeNodes.length === 0) {
        setNodes([]);
        setEdges([]);
        return null;
      }

      const rfNodesBase = activeNodes.map((n) => ({
        id: n.entity_id || n.id,
        type: "investigationNode",
        position: { x: 500, y: 350 },
        data: {
          name: n.name,
          type: n.type,
          entityId: n.entity_id || n.id,
        },
      }));

      const targetFocusId =
        overrideFocusId !== null && overrideFocusId !== undefined
          ? overrideFocusId
          : focusEntityId;
      const targetFocusMode =
        overrideFocusMode !== null && overrideFocusMode !== undefined
          ? overrideFocusMode
          : isFocusMode;

      const layoutResult = buildInvestigationLayout(
        rfNodesBase,
        validRels,
        targetFocusId,
        targetFocusMode
      );

      setNodes(layoutResult.nodes);
      setEdges(layoutResult.edges);
      setFocusEntityId(layoutResult.focusId);

      return layoutResult;
    },
    [focusEntityId, isFocusMode, setNodes, setEdges]
  );

  // Fetch initial case graph
  const loadGraph = useCallback(async () => {
    if (!caseId) return;
    setLoading(true);
    setGraphError(null);
    setSelectedNodeData(null);
    setSelectedEdgeData(null);
    setExpandFeedback(null);
    setIsInspectorOpen(false);

    try {
      const data = await apiClient(`/api/cases/${caseId}/graph`);
      setIsTruncated(!!data?.truncated);

      const rawNodes = data?.nodes || [];
      const rawRels = data?.relationships || [];
      rawNodesRef.current = rawNodes;
      rawRelsRef.current = rawRels;

      setIsFocusMode(false);
      const layout = applyNetworkLayout(rawNodes, rawRels, null, false);

      setTimeout(() => {
        if (layout?.focusPos) {
          reactFlowInstance.setCenter(layout.focusPos.x, layout.focusPos.y, {
            zoom: 1,
            duration: 450,
          });
        } else {
          reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
        }
      }, 120);
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
  }, [caseId, applyNetworkLayout, reactFlowInstance]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Handle Node Click: Selects node & reorganizes graph with node as the visual center
  const onNodeClick = async (_event, node) => {
    setSelectedEdgeData(null);
    setExpandFeedback(null);
    setIsInspectorOpen(true);
    setDoubtQuery("");
    setAiClarification(null);
    setAiClarificationError(null);
    setClarifyingAi(false);
    setSelectedNodeData({
      id: node.id,
      name: node.data.name,
      type: node.data.type,
      cases: [],
    });
    setLoadingNodeDetails(true);

    if (node.id !== focusEntityId) {
      setFocusEntityId(node.id);
      const layout = applyNetworkLayout(
        rawNodesRef.current,
        rawRelsRef.current,
        node.id,
        isFocusMode
      );
      if (layout?.focusPos) {
        setTimeout(() => {
          reactFlowInstance.setCenter(layout.focusPos.x, layout.focusPos.y, {
            zoom: reactFlowInstance.getZoom() || 1,
            duration: 400,
          });
        }, 50);
      }
    }

    try {
      const entityDetails = await apiClient(`/api/entities/${node.id}`);
      setSelectedNodeData((prev) => ({
        ...prev,
        canonical_name: entityDetails.canonical_name || prev.name,
        cases: entityDetails.cases || [],
        attributes: entityDetails.attributes || {},
      }));
    } catch {
      // Retain basic node data
    } finally {
      setLoadingNodeDetails(false);
    }
  };

  // Handle Edge Click
  const onEdgeClick = async (_event, edge) => {
    setSelectedNodeData(null);
    setExpandFeedback(null);
    setIsInspectorOpen(true);
    setDoubtQuery("");
    setAiClarification(null);
    setAiClarificationError(null);
    setClarifyingAi(false);
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

  // Toggle Focus Mode (Dim unrelated nodes & secondary ties)
  const handleToggleFocusMode = () => {
    const nextMode = !isFocusMode;
    setIsFocusMode(nextMode);
    applyNetworkLayout(rawNodesRef.current, rawRelsRef.current, focusEntityId, nextMode);
  };

  // Center Camera Smoothly on Active Investigation Subject
  const handleCenterSubject = () => {
    const targetNode = nodes.find((n) => n.id === focusEntityId);
    if (targetNode) {
      reactFlowInstance.setCenter(
        targetNode.position.x + 88,
        targetNode.position.y + 41,
        { zoom: 1, duration: 400 }
      );
    } else {
      reactFlowInstance.fitView({ padding: 0.2, duration: 300 });
    }
  };

  // Reset Graph to Default Highest-Degree Suspect & Fit View
  const handleResetLayout = () => {
    setIsFocusMode(false);
    const layout = applyNetworkLayout(rawNodesRef.current, rawRelsRef.current, null, false);
    setTimeout(() => {
      if (layout?.focusPos) {
        reactFlowInstance.setCenter(layout.focusPos.x, layout.focusPos.y, {
          zoom: 1,
          duration: 400,
        });
      } else {
        reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
      }
    }, 100);
  };

  // Expand 1-Hop Connections for Selected Entity with Structured Radial Integration
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

      let addedNodesCount = 0;
      let addedEdgesCount = 0;

      connections.forEach((conn) => {
        if (!rawNodesRef.current.some((n) => (n.entity_id || n.id) === conn.entity_id)) {
          rawNodesRef.current.push({
            entity_id: conn.entity_id,
            name: conn.name,
            type: conn.type,
          });
          addedNodesCount++;
        }
        if (!rawRelsRef.current.some((r) => r.relationship_id === conn.relationship_id)) {
          rawRelsRef.current.push({
            relationship_id: conn.relationship_id,
            source_entity_id: selectedNodeData.id,
            target_entity_id: conn.entity_id,
            relationship: conn.relationship,
            confidence: conn.confidence,
            status: conn.status,
            source_document_id: conn.source_document_id,
            evidence_snippet: conn.evidence_snippet,
          });
          addedEdgesCount++;
        }
      });

      const layout = applyNetworkLayout(
        rawNodesRef.current,
        rawRelsRef.current,
        selectedNodeData.id,
        isFocusMode
      );

      setExpandFeedback({
        type: "success",
        text: `Expanded ${addedNodesCount} new entities and ${addedEdgesCount} relationships.`,
      });

      setTimeout(() => {
        if (layout?.focusPos) {
          reactFlowInstance.setCenter(layout.focusPos.x, layout.focusPos.y, {
            zoom: 0.95,
            duration: 400,
          });
        }
      }, 100);
    } catch {
      setExpandFeedback({
        type: "error",
        text: "Failed to expand entity connections.",
      });
    } finally {
      setExpanding(false);
    }
  };

  // Export & Download Official Structured PDF Dossier
  const handleDownloadPdf = () => {
    if (!aiAnalysisResult) return;
    try {
      const htmlContent = buildPrintableDossierHtml({
        caseId,
        caseTitle,
        analysis: aiAnalysisResult,
      });

      const printWindow = window.open("", "_blank");
      if (!printWindow) {
        alert("Popup blocked! Please allow popups for CrimeLens to view and save the PDF dossier.");
        return;
      }
      printWindow.document.open();
      printWindow.document.write(htmlContent);
      printWindow.document.close();
    } catch (err) {
      console.error("Failed to generate PDF dossier:", err);
      alert("Failed to compile PDF report. Please try again.");
    }
  };

  // Trigger Deep AI Reasoning Analysis (Mode A or Mode B)
  const handleRunAiAnalysis = async (mode = "full", targetNodeId = null, forceRefresh = false) => {
    if (!caseId) return;

    // Instant open if report is already saved and network has not changed
    if (
      mode === "full" &&
      !targetNodeId &&
      !forceRefresh &&
      savedAiStatus.hasSavedReport &&
      !savedAiStatus.isNetworkChanged &&
      aiAnalysisResult
    ) {
      setIsAiModalOpen(true);
      return;
    }

    setAnalyzingAi(true);
    try {
      const selectedIds = targetNodeId
        ? [targetNodeId]
        : (selectedNodeData ? [selectedNodeData.id] : []);
      const result = await apiClient(`/api/cases/${caseId}/intelligence/analyze`, {
        method: "POST",
        body: JSON.stringify({
          mode,
          selected_node_ids: selectedIds,
          hops: 2,
          force_refresh: forceRefresh,
        }),
      });
      setAiAnalysisResult(result);
      if (mode === "full" && !targetNodeId) {
        setSavedAiStatus({
          hasSavedReport: true,
          isNetworkChanged: false,
          savedAt: result.saved_at || new Date().toISOString(),
        });
      }
      setIsAiModalOpen(true);
    } catch (err) {
      alert("AI analysis failed: " + (err?.message || "Please check backend connection"));
    } finally {
      setAnalyzingAi(false);
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
    <div className={`graph-workspace-layout ${isExpanded ? "is-expanded" : ""}`}>
      {/* Back button in fullscreen mode */}
      {/* 1. TOP GRAPH TOOLBAR */}
      <div className="graph-toolbar">
        <div className="toolbar-left">
          {isExpanded && (
            <>
              <button
                onClick={handleToggleExpand}
                className="btn-exit-fullscreen"
                title="Back to standard view (or press Esc)"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                <span>Back</span>
                <kbd className="fs-kbd-badge">ESC</kbd>
              </button>
              <div className="toolbar-divider" />
            </>
          )}

          {/* Metrics summary pills */}
          <div className="toolbar-stats-group">
            <span className="metric-pill" title="Total Entities in Graph">
              <span className="metric-count">{nodes.length}</span>
              <span className="metric-label">Entities</span>
            </span>
            <span className="metric-pill" title="Total Relationships/Connections">
              <span className="metric-count">{edges.length}</span>
              <span className="metric-label">Connections</span>
            </span>
          </div>

          <div className="toolbar-divider" />

          {/* Clean Topology Legend */}
          <div className="network-topology-legend">
            <span className="legend-chip" title="Investigation Subject">
              <span className="legend-dot-focus" />
              <span>Subject</span>
            </span>
            <span className="legend-chip" title="Threat / SOS Alert">
              <span className="legend-dot-sos" />
              <span>Threat</span>
            </span>
            <span className="legend-chip" title="Entity Node">
              <span className="legend-dot-entity" />
              <span>Entity</span>
            </span>
            <span className="legend-chip" title="Direct Verified Connection">
              <span className="legend-line-dot cyan-line-dot" />
              <span>Direct</span>
            </span>
            <span className="legend-chip" title="Inferred / Predicted Connection">
              <span className="legend-line-dot dashed-line-dot" />
              <span>Inferred</span>
            </span>
          </div>

          {isTruncated && (
            <span className="truncated-badge" title="Query limit reached. Showing partial subgraph.">
              Truncated
            </span>
          )}
        </div>

        <div className="toolbar-actions">
          {/* AI Network Analysis Button */}
          <button
            onClick={() => handleRunAiAnalysis("full")}
            className={`tool-btn tool-btn-primary ${savedAiStatus.hasSavedReport && !savedAiStatus.isNetworkChanged ? "tool-btn-saved" : ""}`}
            disabled={analyzingAi}
            title={
              savedAiStatus.hasSavedReport && !savedAiStatus.isNetworkChanged
                ? "Saved Analysis Report (Network Synced) - Click to view"
                : savedAiStatus.hasSavedReport && savedAiStatus.isNetworkChanged
                ? "Network modified since last analysis - Click to update report"
                : "Analyze Network with Gemini"
            }
          >
            {analyzingAi ? (
              <span className="ai-spark-icon">
                <svg className="spinning" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                  <path d="M12 2a10 10 0 0 1 10 10" />
                </svg>
              </span>
            ) : null}
            <span>
              {analyzingAi
                ? "Analyzing Network..."
                : savedAiStatus.hasSavedReport && !savedAiStatus.isNetworkChanged
                ? "AI Network Report"
                : savedAiStatus.hasSavedReport && savedAiStatus.isNetworkChanged
                ? "Update AI Analysis"
                : "AI Network Analysis"}
            </span>
          </button>

          <div className="toolbar-divider action-divider" />

          <div className="tool-btn-group">
            {/* Expand Screen / Fullscreen Toggle (In place of Fit Network) */}
            <button
              onClick={handleToggleExpand}
              className={`tool-btn ${isExpanded ? "tool-btn-active tool-btn-expanded" : ""}`}
              title={isExpanded ? "Exit full screen (Esc)" : "Expand canvas to occupy entire screen (hides sidebars)"}
            >
              {isExpanded ? (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                  </svg>
                  <span>Exit Fullscreen</span>
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                  </svg>
                  <span>Expand Screen</span>
                </>
              )}
            </button>

            {/* Inspector Toggle */}
            <button
              onClick={() => setIsInspectorOpen((prev) => !prev)}
              className={`tool-btn ${isInspectorOpen ? "tool-btn-active" : ""}`}
              title="Toggle details inspector"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M9 3v18M13 8h4m-4 4h4m-4 4h3" />
              </svg>
              <span>{isInspectorOpen ? "Hide Inspector" : "Inspector"}</span>
            </button>

            {/* Refresh */}
            <button
              onClick={loadGraph}
              className="tool-btn"
              disabled={loading}
              title="Reload initial graph"
            >
              <svg
                width="14"
                height="14"
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
              <h4>No Connected Relationship Network Found</h4>
              <p>
                No sufficiently supported connected relationship network found. Entities extracted without evidence-backed relationships remain safely stored in the document store.
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
              setIsInspectorOpen(false);
            }}
            fitView
            minZoom={0.2}
            maxZoom={2.5}
            attributionPosition="bottom-left"
          >
            {/* Soft grid background matching light reference background */}
            <Background color="#cbd5e1" gap={24} size={1.2} />
            <Controls className="rf-controls-custom" showInteractive={false} />
            <MiniMap
              className="rf-minimap-custom"
              nodeColor={(n) => (n.data?.isSos ? "#ef4444" : "#f59e0b")}
              maskColor="rgba(241, 245, 249, 0.75)"
            />
          </ReactFlow>
        </div>

        {/* 3. DETAILS SIDE PANEL (INSPECTOR) */}
        {isInspectorOpen && (
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
                    onClick={() => {
                      setSelectedNodeData(null);
                      setIsInspectorOpen(false);
                    }}
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
                        color: ENTITY_CONFIG[selectedNodeData.type]?.color || "#0ea5e9",
                        background: ENTITY_CONFIG[selectedNodeData.type]?.bg || "rgba(14, 165, 233, 0.12)",
                      }}
                    >
                      {selectedNodeData.type}
                    </span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-key">UUID:</span>
                    <span className="detail-val font-mono">{selectedNodeData.id?.slice(0, 16)}...</span>
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

                  {/* 1. Aliases */}
                  {selectedNodeData.attributes?.aliases?.length > 0 && (
                    <div className="entity-meta-section">
                      <span className="meta-section-label">Known Aliases:</span>
                      <div className="meta-chips-wrap">
                        {selectedNodeData.attributes.aliases.map((alias, idx) => (
                          <span key={idx} className="meta-chip alias-chip">
                            {alias}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 2. Phone Numbers */}
                  {selectedNodeData.attributes?.phone_numbers?.length > 0 && (
                    <div className="entity-meta-section">
                      <span className="meta-section-label">Phone Numbers:</span>
                      <div className="meta-chips-wrap">
                        {selectedNodeData.attributes.phone_numbers.map((phone, idx) => (
                          <span key={idx} className="meta-chip phone-chip font-mono">
                            {phone}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 3. Locations */}
                  {selectedNodeData.attributes?.locations?.length > 0 && (
                    <div className="entity-meta-section">
                      <span className="meta-section-label">Known Locations:</span>
                      <div className="meta-chips-wrap">
                        {selectedNodeData.attributes.locations.map((loc, idx) => (
                          <span key={idx} className="meta-chip location-chip">
                            {loc}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 4. Vehicles */}
                  {selectedNodeData.attributes?.vehicles?.length > 0 && (
                    <div className="entity-meta-section">
                      <span className="meta-section-label">Vehicles:</span>
                      <div className="meta-chips-wrap">
                        {selectedNodeData.attributes.vehicles.map((veh, idx) => (
                          <span key={idx} className="meta-chip vehicle-chip font-mono">
                            {veh}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 5. Organizations */}
                  {selectedNodeData.attributes?.organizations?.length > 0 && (
                    <div className="entity-meta-section">
                      <span className="meta-section-label">Affiliated Organizations:</span>
                      <div className="meta-chips-wrap">
                        {selectedNodeData.attributes.organizations.map((org, idx) => (
                          <span key={idx} className="meta-chip org-chip">
                            {org}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 6. Source Documents */}
                  {selectedNodeData.attributes?.source_documents?.length > 0 && (
                    <div className="entity-meta-section">
                      <span className="meta-section-label">Source Evidence Documents:</span>
                      <div className="meta-chips-wrap">
                        {selectedNodeData.attributes.source_documents.map((doc, idx) => (
                          <span key={idx} className="meta-chip doc-chip">
                            {doc}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 7. Verbatim Evidence Snippets */}
                  {selectedNodeData.attributes?.evidence_snippets?.length > 0 && (
                    <div className="entity-meta-section">
                      <span className="meta-section-label">Document Evidence Anchors:</span>
                      <div className="evidence-snippets-stack">
                        {selectedNodeData.attributes.evidence_snippets.slice(0, 3).map((snip, idx) => (
                          <blockquote key={idx} className="evidence-quote-small">
                            "{snip}"
                          </blockquote>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 8. VERIFIED DIRECT CONNECTIONS & EVIDENCE */}
                  <div className="entity-meta-section connections-meta-section">
                    <div className="section-title-badge-row">
                      <span className="meta-section-label">Verified Connections ({selectedNodeConnections.length}):</span>
                    </div>

                    {selectedNodeConnections.length > 0 ? (
                      <div className="node-connections-list">
                        {selectedNodeConnections.map((conn, idx) => (
                          <div key={idx} className="node-connection-card">
                            <div className="connection-header-row">
                              <span className="connection-rel-tag">
                                {conn.isOut ? "➔" : "⬅"} {conn.relationship}
                              </span>
                              {conn.confidence && (
                                <span className="connection-conf-badge">
                                  {Math.round(conn.confidence * 100)}%
                                </span>
                              )}
                            </div>
                            <div className="connection-target-row">
                              <span className="target-indicator">•</span>
                              <button
                                type="button"
                                className="target-entity-link"
                                onClick={() => {
                                  const targetNode = nodes.find((n) => n.id === conn.otherId);
                                  if (targetNode) onNodeClick(null, targetNode);
                                }}
                                title="Click to inspect this entity"
                              >
                                {conn.otherName}
                              </button>
                              <span className="target-type-chip">{conn.otherType}</span>
                            </div>
                            {conn.evidenceSnippet && (
                              <blockquote className="connection-snippet">
                                "{conn.evidenceSnippet}"
                              </blockquote>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="no-data-text">No direct connections recorded in current view.</span>
                    )}
                  </div>

                  {/* 9. AI SIDE CHAT INQUIRY */}
                  <div className="ai-entity-chat-card">
                    <div className="entity-chat-content">
                      <div className="entity-chat-badge">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.5">
                          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                        </svg>
                        <span>Ask AI Assistant</span>
                      </div>
                      <p className="entity-chat-desc">
                        Ask AI about <strong>{selectedNodeData.canonical_name || selectedNodeData.name}</strong>, motives, and evidence.
                      </p>
                    </div>
                    {onOpenCopilot && (
                      <button
                        type="button"
                        onClick={() => onOpenCopilot(`What is known about ${selectedNodeData.canonical_name || selectedNodeData.name} and what evidence connects them?`)}
                        className="entity-chat-btn"
                        title="Open side chat assistant"
                      >
                        <span>Chat about this Entity</span>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <line x1="5" y1="12" x2="19" y2="12" />
                          <polyline points="12 5 19 12 12 19" />
                        </svg>
                      </button>
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
                    onClick={() => {
                      setSelectedEdgeData(null);
                      setIsInspectorOpen(false);
                    }}
                    className="close-panel-btn"
                    title="Close panel"
                  >
                    ✕
                  </button>
                </div>

                <div className="panel-body">
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

                  {selectedEdgeData.source_document_id && (
                    <div className="detail-row">
                      <span className="detail-key">Source Doc ID:</span>
                      <span className="detail-val font-mono">
                        {selectedEdgeData.source_document_id.slice(0, 14)}...
                      </span>
                    </div>
                  )}

                  {/* Verbatim Snippet */}
                  <div className="evidence-snippet-section">
                    <span className="snippet-heading">Verbatim Evidence Anchor:</span>
                    {loadingEdgeEvidence ? (
                      <div className="details-loading-spinner">Retrieving evidence text...</div>
                    ) : selectedEdgeData.evidence_snippet ? (
                      <blockquote className="evidence-quote">
                        "{selectedEdgeData.evidence_snippet}"
                      </blockquote>
                    ) : (
                      <span className="no-snippet-text">No verbatim text anchor cited.</span>
                    )}
                  </div>

                  {/* AI SIDE CHAT INQUIRY */}
                  <div className="ai-entity-chat-card">
                    <div className="entity-chat-content">
                      <div className="entity-chat-badge">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.5">
                          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                        </svg>
                        <span>Ask AI Assistant</span>
                      </div>
                      <p className="entity-chat-desc">
                        Ask AI why this <strong>{selectedEdgeData.relationship}</strong> connection is significant.
                      </p>
                    </div>
                    {onOpenCopilot && (
                      <button
                        type="button"
                        onClick={() => onOpenCopilot(`Explain the significance of the ${selectedEdgeData.relationship} connection and its corroborating evidence.`)}
                        className="entity-chat-btn"
                        title="Open side chat for this connection"
                      >
                        <span>Chat about this Link</span>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <line x1="5" y1="12" x2="19" y2="12" />
                          <polyline points="12 5 19 12 12 19" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* C. IDLE STATE */}
            {!selectedNodeData && !selectedEdgeData && (
              <div className="panel-idle-card">
                <div className="idle-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                </div>
                <h4 className="idle-title">Select Network Element</h4>
                <p className="idle-desc">
                  Click any sphere node or relationship line to inspect its attributes, citations, and run AI Dossiers.
                </p>
              </div>
            )}
          </aside>
        )}
      </div>

      {/* 4. AI INTELLIGENCE REASONING MODAL / DRAWER */}
      {isAiModalOpen && aiAnalysisResult && (
        <div className="ai-modal-backdrop" onClick={() => setIsAiModalOpen(false)}>
          <div className="ai-modal-container" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="ai-modal-header">
              <div className="ai-modal-title-group">
                <div className="ai-title-row">
                  <span className="ai-badge-pulse">CrimeLens Intelligence Engine</span>
                </div>
                <h2 className="ai-modal-heading">
                  {aiAnalysisResult.mode === "node" && selectedNodeData
                    ? `Investigative Dossier: ${selectedNodeData.canonical_name || selectedNodeData.name}`
                    : "Comprehensive Network Intelligence Dossier"}
                </h2>
                <p className="ai-modal-sub">
                  In-Scope: {aiAnalysisResult.in_scope_entities || 0} Entities • {aiAnalysisResult.in_scope_relationships || 0} Relationships • Confidence {Math.round((aiAnalysisResult.confidence_score || 0.85) * 100)}%
                  {savedAiStatus.savedAt && ` • Saved ${new Date(savedAiStatus.savedAt).toLocaleDateString()} ${new Date(savedAiStatus.savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`}
                </p>
              </div>

              <div className="ai-header-actions">
                <button
                  type="button"
                  onClick={() => handleRunAiAnalysis("full", null, true)}
                  className="ai-modal-reanalyze-btn"
                  disabled={analyzingAi}
                  title="Re-analyze and update the saved report"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                  </svg>
                  <span>{analyzingAi ? "Analyzing..." : "Re-analyze"}</span>
                </button>

                <button onClick={() => setIsAiModalOpen(false)} className="ai-close-btn" title="Close Dossier">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 6 6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="ai-modal-body">
              {/* Executive Summary Card */}
              <div className="ai-card ai-summary-card">
                <h4 className="ai-card-title">
                  <span>Executive Intelligence Summary</span>
                </h4>
                <p className="ai-summary-text">{aiAnalysisResult.case_summary}</p>
              </div>

              {/* Persons of Interest / Threats */}
              {aiAnalysisResult.potential_persons_of_interest && aiAnalysisResult.potential_persons_of_interest.length > 0 && (
                <div className="ai-card">
                  <h4 className="ai-card-title">
                    <span>Potential Persons of Interest & Key Actors</span>
                  </h4>
                  <div className="ai-poi-grid">
                    {aiAnalysisResult.potential_persons_of_interest.map((poi, idx) => {
                      const threat = (poi.threat_level || "MEDIUM").toUpperCase();
                      const threatClass = threat.includes("CRIT") ? "threat-crit" : threat.includes("HIGH") ? "threat-high" : "threat-med";
                      return (
                        <div key={idx} className={`ai-poi-card ${threatClass}`}>
                          <div className="ai-poi-header">
                            <span className="ai-poi-name">{poi.name}</span>
                            <span className={`ai-threat-badge ${threatClass}`}>{threat} RISK</span>
                          </div>
                          <p className="ai-poi-reason">{poi.reason}</p>
                          {poi.evidence && (
                            <div className="ai-poi-evidence">
                              <span className="ev-tag">Evidence:</span> "{poi.evidence}"
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Actionable Investigative Leads */}
              {aiAnalysisResult.investigative_leads && aiAnalysisResult.investigative_leads.length > 0 && (
                <div className="ai-card">
                  <h4 className="ai-card-title">
                    <span>Recommended Investigative Leads</span>
                  </h4>
                  <ul className="ai-leads-list">
                    {aiAnalysisResult.investigative_leads.map((lead, idx) => (
                      <li key={idx} className="ai-lead-item">
                        <span className="lead-number">{idx + 1}</span>
                        <span className="lead-text">{lead}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Supporting Evidence Quotes */}
              {aiAnalysisResult.supporting_evidence && aiAnalysisResult.supporting_evidence.length > 0 && (
                <div className="ai-card">
                  <h4 className="ai-card-title">
                    <span>Evidentiary Citations & Grounded Quotes</span>
                  </h4>
                  <div className="ai-evidence-grid">
                    {aiAnalysisResult.supporting_evidence.map((ev, idx) => (
                      <div key={idx} className="ai-ev-item">
                        <span className="ai-ev-claim">{ev.claim || "Cited Fact"}:</span>
                        <blockquote className="ai-ev-quote">"{ev.quote}"</blockquote>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Contradictions or Anomalies */}
              {aiAnalysisResult.contradictions_or_anomalies && aiAnalysisResult.contradictions_or_anomalies.length > 0 && (
                <div className="ai-card ai-anomalies-card">
                  <h4 className="ai-card-title">
                    <span>Anomalies & Evidentiary Conflicts</span>
                  </h4>
                  <ul className="ai-anomalies-list">
                    {aiAnalysisResult.contradictions_or_anomalies.map((ano, idx) => (
                      <li key={idx}>{ano}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Full Markdown Dossier */}
              {aiAnalysisResult.dossier_markdown && (
                <div className="ai-card">
                  <div className="ai-card-title-row">
                    <h4 className="ai-card-title">
                      <span>Full Intelligence Dossier Report</span>
                    </h4>
                    <div className="ai-card-actions">
                      <button
                        onClick={handleDownloadPdf}
                        className="ai-pdf-btn"
                        title="Download structured PDF report"
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="7 10 12 15 17 10" />
                          <line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                        <span>Download PDF</span>
                      </button>
                      <button
                        onClick={() => {
                          navigator.clipboard?.writeText(aiAnalysisResult.dossier_markdown);
                          alert("Dossier copied to clipboard!");
                        }}
                        className="ai-copy-btn"
                        title="Copy markdown dossier to clipboard"
                      >
                        Copy Dossier
                      </button>
                    </div>
                  </div>
                  <DossierMarkdownViewer markdown={aiAnalysisResult.dossier_markdown} />
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="ai-modal-footer">
              <span className="ai-footer-note">
                CrimeLens AI reasoning strictly separates criminal methodology from factual case evidence.
              </span>
              <div className="ai-footer-actions">
                <button
                  onClick={handleDownloadPdf}
                  className="ai-footer-pdf-btn"
                  title="Download complete dossier as structured PDF"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  <span>Download PDF Report</span>
                </button>
                <button onClick={() => setIsAiModalOpen(false)} className="ai-done-btn">
                  Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .graph-workspace-layout {
          display: flex;
          flex-direction: column;
          height: calc(100vh - 120px);
          min-height: 600px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          position: relative;
          overflow: hidden;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          transition: height 0.2s ease, width 0.2s ease;
        }

        .graph-workspace-layout.is-expanded {
          position: fixed !important;
          inset: 0 !important;
          top: 0 !important;
          left: 0 !important;
          right: 0 !important;
          bottom: 0 !important;
          width: 100vw !important;
          height: 100vh !important;
          min-height: 100vh !important;
          max-width: 100vw !important;
          max-height: 100vh !important;
          margin: 0 !important;
          z-index: 9999999 !important;
          border-radius: 0 !important;
          border: none !important;
          background: #f8fafc !important;
        }

        .tool-btn-expanded {
          background: #eff6ff !important;
          color: #1d4ed8 !important;
          border-color: #2563eb !important;
        }

        .graph-workspace-layout.is-expanded .graph-main-split {
          height: calc(100vh - 54px) !important;
        }

        .btn-exit-fullscreen {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          padding: 0.32rem 0.75rem;
          background: #f1f5f9;
          border: 1.5px solid #cbd5e1;
          border-radius: 6px;
          font-size: 0.76rem;
          font-weight: 700;
          color: #0f172a;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .btn-exit-fullscreen:hover {
          background: #2563eb;
          color: #ffffff;
          border-color: #1d4ed8;
        }

        .btn-exit-fullscreen:hover .fs-kbd-badge {
          background: rgba(255, 255, 255, 0.25);
          color: #ffffff;
          border-color: rgba(255, 255, 255, 0.4);
        }

        .fs-kbd-badge {
          font-size: 0.62rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          background: #e2e8f0;
          color: #475569;
          padding: 1px 4px;
          border-radius: 4px;
          border: 1px solid #cbd5e1;
          line-height: 1;
        }

        .fullscreen-floating-back {
          position: absolute;
          top: 14px;
          left: 14px;
          z-index: 50;
        }

        .fullscreen-floating-back-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          background: rgba(255, 255, 255, 0.94);
          border: 1.5px solid #cbd5e1;
          color: #0f172a;
          padding: 0.38rem 0.8rem;
          border-radius: 8px;
          font-size: 0.78rem;
          font-weight: 750;
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
          cursor: pointer;
          transition: all 0.15s ease;
          backdrop-filter: blur(8px);
        }

        .fullscreen-floating-back-btn:hover {
          background: #2563eb;
          color: #ffffff;
          border-color: #1d4ed8;
          transform: translateY(-1px);
          box-shadow: 0 6px 18px rgba(37, 99, 235, 0.3);
        }

        .fullscreen-floating-back-btn:hover .fs-kbd-pill {
          background: rgba(255, 255, 255, 0.25);
          color: #ffffff;
          border-color: rgba(255, 255, 255, 0.4);
        }

        .fs-kbd-pill {
          font-size: 0.62rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          background: #e2e8f0;
          color: #475569;
          padding: 1px 5px;
          border-radius: 4px;
          border: 1px solid #cbd5e1;
          line-height: 1.1;
        }

        /* Top Toolbar */
        .graph-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.55rem 1rem;
          background: #ffffff;
          border-bottom: 1px solid #e2e8f0;
          z-index: 10;
          gap: 1rem;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        }

        .toolbar-left {
          display: flex;
          align-items: center;
          gap: 0.85rem;
          flex-wrap: wrap;
        }

        .toolbar-stats-group {
          display: flex;
          align-items: center;
          gap: 0.4rem;
        }

        .metric-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.22rem 0.55rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          font-size: 0.74rem;
        }

        .metric-count {
          font-weight: 700;
          color: #0f172a;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .metric-label {
          color: #64748b;
          font-weight: 500;
        }

        .toolbar-divider {
          width: 1px;
          height: 18px;
          background: #e2e8f0;
        }

        .action-divider {
          margin: 0 0.2rem;
        }

        .network-topology-legend {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .legend-chip {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          font-size: 0.73rem;
          font-weight: 500;
          color: #475569;
        }

        .legend-dot-focus {
          width: 9px;
          height: 9px;
          border-radius: 2px;
          background: #d97706;
          border: 1.5px solid #b45309;
          display: inline-block;
        }

        .legend-dot-sos {
          width: 9px;
          height: 9px;
          border-radius: 2px;
          background: #dc2626;
          border: 1.5px solid #b91c1c;
          display: inline-block;
        }

        .legend-dot-entity {
          width: 9px;
          height: 9px;
          border-radius: 2px;
          background: #64748b;
          border: 1.5px solid #475569;
          display: inline-block;
        }

        .cyan-line-dot {
          width: 14px;
          height: 2.5px;
          background: #0284c7;
          border-radius: 2px;
          display: inline-block;
        }

        .dashed-line-dot {
          width: 14px;
          height: 0px;
          border-top: 2px dashed #d97706;
          display: inline-block;
        }

        .truncated-badge {
          font-size: 0.7rem;
          font-weight: 600;
          color: #b45309;
          background: #fef3c7;
          border: 1px solid #fde68a;
          padding: 0.15rem 0.5rem;
          border-radius: 6px;
        }

        .toolbar-actions {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .tool-btn-group {
          display: flex;
          align-items: center;
          gap: 0.35rem;
        }

        .tool-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.4rem 0.75rem;
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          color: #334155;
          font-size: 0.78rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s ease;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
          white-space: nowrap;
        }

        .tool-btn:hover:not(:disabled) {
          background: #f8fafc;
          border-color: #94a3b8;
          color: #0f172a;
        }

        .tool-btn:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .tool-btn-primary, .ai-analyze-btn {
          background: #2563eb !important;
          border: 1px solid #1d4ed8 !important;
          color: #ffffff !important;
          font-weight: 600 !important;
          box-shadow: 0 1px 3px rgba(37, 99, 235, 0.25) !important;
        }

        .tool-btn-primary:hover:not(:disabled), .ai-analyze-btn:hover:not(:disabled) {
          background: #1d4ed8 !important;
          border-color: #1e40af !important;
          box-shadow: 0 2px 5px rgba(37, 99, 235, 0.35) !important;
        }

        .tool-btn-active, .inspector-toggle-active {
          background: #eff6ff !important;
          border-color: #93c5fd !important;
          color: #1d4ed8 !important;
          font-weight: 600 !important;
        }

        .ai-spark-icon {
          font-size: 0.88rem;
          line-height: 1;
        }

        /* Main Canvas Layout */
        .graph-main-split {
          display: flex;
          flex: 1;
          position: relative;
          overflow: hidden;
        }

        .graph-viewport-area {
          flex: 1;
          position: relative;
          background: #f8fafc;
        }

        /* Overlays */
        .graph-overlay-loading,
        .graph-overlay-error,
        .graph-overlay-empty {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          z-index: 5;
          padding: 2rem;
          text-align: center;
        }

        .graph-overlay-loading {
          background: rgba(248, 250, 252, 0.92);
          color: #2563eb;
          font-weight: 600;
          font-size: 0.9rem;
          gap: 0.85rem;
        }

        .mini-radar-pulse {
          width: 36px;
          height: 36px;
          border: 3px solid #2563eb;
          border-radius: 50%;
          animation: radarPulse 1.2s infinite cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }

        @keyframes radarPulse {
          0% { transform: scale(0.5); opacity: 1; }
          100% { transform: scale(1.6); opacity: 0; }
        }

        .graph-overlay-error {
          background: rgba(248, 250, 252, 0.96);
          color: #dc2626;
          gap: 0.75rem;
          font-size: 0.88rem;
        }

        .retry-btn {
          margin-top: 0.5rem;
          padding: 0.45rem 1.15rem;
          background: #2563eb;
          color: #ffffff;
          border: 1px solid #1d4ed8;
          border-radius: 6px;
          font-size: 0.8rem;
          font-weight: 750;
          cursor: pointer;
        }

        .graph-overlay-empty {
          background: #f8fafc;
          color: #475569;
          max-width: 440px;
          margin: 0 auto;
        }

        .graph-overlay-empty h4 {
          font-size: 1.05rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0.75rem 0 0.4rem 0;
        }

        .graph-overlay-empty p {
          font-size: 0.82rem;
          color: #64748b;
          line-height: 1.5;
          margin: 0 0 1rem 0;
        }

        /* Inspector Sidebar - Clean surface matching webpage */
        .graph-details-sidebar {
          width: 350px;
          background: #ffffff;
          border-left: 1px solid #e2e8f0;
          display: flex;
          flex-direction: column;
          overflow-y: auto;
          box-shadow: -4px 0 20px rgba(0, 0, 0, 0.05);
          z-index: 8;
        }

        .rf-minimap-custom {
          background: #ffffff !important;
          border: 1px solid #cbd5e1 !important;
          border-radius: 10px !important;
          overflow: hidden !important;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
        }

        .panel-card {
          padding: 1.25rem;
          background: #ffffff;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
          padding-bottom: 0.75rem;
          border-bottom: 1px solid #e2e8f0;
        }

        .panel-title-group {
          display: flex;
          flex-direction: column;
          gap: 0.15rem;
        }

        .panel-type-label {
          font-size: 0.68rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: #2563eb;
        }

        .panel-entity-name {
          font-size: 1.1rem;
          font-weight: 700;
          color: #0f172a;
          line-height: 1.3;
          margin: 0;
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
          color: #0f172a;
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
          color: #64748b;
          font-weight: 500;
        }

        .detail-val {
          color: #0f172a;
        }

        .entity-badge-pill {
          font-size: 0.68rem;
          font-weight: 700;
          padding: 0.2rem 0.55rem;
          border-radius: 4px;
          letter-spacing: 0.04em;
        }

        .associated-cases-block {
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
          font-size: 0.78rem;
        }

        .entity-meta-section {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
          margin-top: 0.2rem;
          font-size: 0.78rem;
        }

        .meta-section-label {
          font-weight: 600;
          color: #64748b;
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.03em;
        }

        .meta-chips-wrap {
          display: flex;
          flex-wrap: wrap;
          gap: 0.35rem;
        }

        .meta-chip {
          font-size: 0.72rem;
          padding: 0.2rem 0.5rem;
          border-radius: 5px;
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
        }

        .alias-chip {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          color: #1d4ed8;
        }

        .phone-chip {
          background: #f5f3ff;
          border: 1px solid #ddd6fe;
          color: #7c3aed;
        }

        .location-chip {
          background: #fff1f2;
          border: 1px solid #fecdd3;
          color: #be123c;
        }

        .vehicle-chip {
          background: #eef2ff;
          border: 1px solid #c7d2fe;
          color: #4338ca;
        }

        .org-chip {
          background: #f1f5f9;
          border: 1px solid #cbd5e1;
          color: #334155;
        }

        .doc-chip {
          background: #fff7ed;
          border: 1px solid #fed7aa;
          color: #c2410c;
        }

        .evidence-snippets-stack {
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
        }

        .evidence-quote-small {
          margin: 0;
          padding: 0.45rem 0.65rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-left: 3px solid #2563eb;
          border-radius: 0 4px 4px 0;
          font-size: 0.72rem;
          color: #1e293b;
          font-style: italic;
          line-height: 1.4;
        }

        .case-chips-wrap {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
        }

        .case-chip {
          font-size: 0.7rem;
          padding: 0.15rem 0.45rem;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 4px;
          color: #1d4ed8;
        }

        .details-loading-spinner,
        .no-data-text {
          font-size: 0.75rem;
          color: #64748b;
        }

        /* AI Node Action Button */
        .ai-node-action-box {
          margin-top: 0.5rem;
        }

        .ai-node-analyze-btn {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.45rem;
          padding: 0.6rem 0.85rem;
          background: #2563eb;
          border: 1px solid #1d4ed8;
          border-radius: 8px;
          color: #ffffff;
          font-size: 0.8rem;
          font-weight: 750;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
        }

        .ai-node-analyze-btn:hover:not(:disabled) {
          background: #1d4ed8;
          transform: translateY(-1px);
        }

        /* Expand Button */
        .expansion-action-box {
          margin-top: 0.25rem;
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
          background: #f8fafc;
          border: 1px solid #cbd5e1;
          border-radius: 8px;
          color: #0f172a;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .expand-connections-btn:hover:not(:disabled) {
          background: #eff6ff;
          border-color: #2563eb;
          color: #1d4ed8;
        }

        .expand-connections-btn:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .mini-spin {
          width: 12px;
          height: 12px;
          border: 2px solid #e2e8f0;
          border-top-color: #2563eb;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .feedback-banner {
          font-size: 0.74rem;
          padding: 0.45rem 0.65rem;
          border-radius: 6px;
          line-height: 1.4;
        }

        .banner-success {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          color: #1d4ed8;
        }

        .banner-info {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          color: #1d4ed8;
        }

        .banner-error {
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #b91c1c;
        }

        /* Evidence */
        .status-pill-small {
          font-size: 0.68rem;
          font-weight: 700;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
        }

        .badge-confirmed {
          background: #eff6ff;
          color: #1d4ed8;
          border: 1px solid #bfdbfe;
        }

        .badge-inferred {
          background: #fffbeb;
          color: #b45309;
          border: 1px solid #fde68a;
        }

        .badge-predicted {
          background: #fffbeb;
          color: #b45309;
          border: 1px solid #fde68a;
        }

        .evidence-snippet-section {
          margin-top: 0.5rem;
          padding-top: 0.75rem;
          border-top: 1px solid #e2e8f0;
        }

        .snippet-heading {
          display: block;
          font-size: 0.75rem;
          font-weight: 600;
          color: #64748b;
          margin-bottom: 0.5rem;
        }

        .evidence-quote {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-left: 3px solid #2563eb;
          border-radius: 0 6px 6px 0;
          padding: 0.75rem;
          font-size: 0.8rem;
          font-style: italic;
          color: #1e293b;
          line-height: 1.5;
          margin: 0;
        }

        .no-snippet-text {
          font-size: 0.75rem;
          color: #64748b;
          line-height: 1.4;
        }

        /* Direct Connections List in Node Inspector */
        .connections-meta-section {
          margin-top: 0.75rem;
          padding-top: 0.75rem;
          border-top: 1px solid #e2e8f0;
        }

        .section-title-badge-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 0.4rem;
        }

        .node-connections-list {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
          margin-top: 0.35rem;
        }

        .node-connection-card {
          padding: 0.5rem 0.65rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 7px;
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          transition: all 0.15s ease;
        }

        .node-connection-card:hover {
          border-color: #bfdbfe;
          background: #f0fdf4;
        }

        .connection-header-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.4rem;
        }

        .connection-rel-tag {
          font-size: 0.64rem;
          font-weight: 750;
          color: #2563eb;
          letter-spacing: 0.03em;
        }

        .connection-conf-badge {
          font-size: 0.6rem;
          font-weight: 700;
          color: #15803d;
          background: #f0fdf4;
          border: 1px solid #bbf7d0;
          padding: 1px 5px;
          border-radius: 3px;
        }

        .connection-target-row {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          flex-wrap: wrap;
        }

        .target-indicator {
          color: #94a3b8;
          font-weight: bold;
        }

        .target-entity-link {
          background: none;
          border: none;
          padding: 0;
          color: #0f172a;
          font-size: 0.76rem;
          font-weight: 650;
          cursor: pointer;
          text-decoration: underline;
          text-decoration-color: #cbd5e1;
          transition: color 0.15s ease;
          text-align: left;
        }

        .target-entity-link:hover {
          color: #2563eb;
          text-decoration-color: #2563eb;
        }

        .target-type-chip {
          font-size: 0.58rem;
          font-weight: 700;
          padding: 1px 5px;
          background: #e2e8f0;
          color: #475569;
          border-radius: 3px;
          text-transform: uppercase;
        }

        .connection-snippet {
          margin: 0.15rem 0 0;
          padding: 0.25rem 0.45rem;
          background: #ffffff;
          border-left: 2.5px solid #2563eb;
          border-radius: 0 3px 3px 0;
          font-size: 0.68rem;
          color: #334155;
          font-style: italic;
          line-height: 1.35;
        }

        /* AI Entity Side Chat Card in Inspector */
        .ai-entity-chat-card {
          margin-top: 1rem;
          padding: 0.85rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          display: flex;
          flex-direction: column;
          gap: 0.65rem;
          transition: border-color 0.15s ease;
        }

        .ai-entity-chat-card:hover {
          border-color: #cbd5e1;
        }

        .entity-chat-content {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }

        .entity-chat-badge {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.74rem;
          font-weight: 750;
          color: #1d4ed8;
          text-transform: uppercase;
          letter-spacing: 0.03em;
        }

        .entity-chat-desc {
          font-size: 0.76rem;
          color: #475569;
          margin: 0;
          line-height: 1.45;
        }

        .entity-chat-btn {
          display: inline-flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.5rem;
          width: 100%;
          padding: 0.55rem 0.85rem;
          background: #2563eb;
          color: #ffffff;
          border: none;
          border-radius: 7px;
          font-size: 0.75rem;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.15s ease;
          box-shadow: 0 1px 3px rgba(37, 99, 235, 0.2);
        }

        .entity-chat-btn:hover {
          background: #1d4ed8;
          transform: translateY(-1px);
          box-shadow: 0 3px 8px rgba(37, 99, 235, 0.3);
        }

        .entity-chat-btn span {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .panel-idle-card {
          padding: 3rem 1.5rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          color: #64748b;
          margin: auto 0;
        }

        .idle-icon {
          color: #94a3b8;
          margin-bottom: 0.85rem;
        }

        .idle-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: #0f172a;
          margin-bottom: 0.35rem;
        }

        .idle-desc {
          font-size: 0.78rem;
          color: #64748b;
          line-height: 1.5;
        }

        /* AI Modal */
        .ai-modal-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(15, 23, 42, 0.65);
          backdrop-filter: blur(8px);
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 1.5rem;
        }

        .ai-modal-container {
          background: #ffffff;
          border: 1.5px solid #0f172a;
          border-radius: 16px;
          width: 100%;
          max-width: 960px;
          max-height: 88vh;
          display: flex;
          flex-direction: column;
          box-shadow: 0 25px 60px -12px rgba(15, 23, 42, 0.35), 0 0 0 1px rgba(15, 23, 42, 0.05);
          overflow: hidden;
          animation: modalPopIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes modalPopIn {
          from { opacity: 0; transform: scale(0.97) translateY(12px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }

        .ai-modal-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding: 1.35rem 1.75rem;
          background: #f8fafc;
          border-bottom: 1px solid #e2e8f0;
        }

        .ai-title-row {
          display: flex;
          align-items: center;
          gap: 0.65rem;
          margin-bottom: 0.4rem;
          flex-wrap: wrap;
        }

        .ai-badge-pulse {
          font-size: 0.74rem;
          font-weight: 750;
          color: #1d4ed8;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .ai-modal-heading {
          font-size: 1.32rem;
          font-weight: 750;
          color: #0f172a;
          margin: 0;
          letter-spacing: -0.01em;
        }

        .ai-modal-sub {
          font-size: 0.78rem;
          color: #475569;
          margin: 0.35rem 0 0 0;
          font-weight: 500;
        }

        .ai-close-btn {
          background: transparent;
          border: none;
          color: #64748b;
          cursor: pointer;
          padding: 0.4rem;
          border-radius: 8px;
          transition: all 0.15s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .ai-close-btn:hover {
          color: #0f172a;
          background: #e2e8f0;
        }

        .ai-modal-body {
          padding: 1.5rem 1.75rem;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
          background: #ffffff;
        }

        .ai-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 1.25rem 1.35rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
        }

        .ai-summary-card {
          border: 1px solid #bfdbfe;
          border-left: 4px solid #2563eb;
          background: #f0f7ff;
        }

        .ai-anomalies-card {
          border: 1px solid #fde68a;
          border-left: 4px solid #d97706;
          background: #fffbeb;
        }

        .ai-card-title {
          font-size: 0.92rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0 0 0.75rem 0;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .ai-card-title-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 0.75rem;
        }

        .ai-summary-text {
          font-size: 0.88rem;
          color: #1e293b;
          line-height: 1.65;
          margin: 0;
          font-weight: 500;
        }

        .ai-poi-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 0.85rem;
        }

        .ai-poi-card {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 0.95rem 1.1rem;
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
        }

        .ai-poi-card.threat-crit {
          border-color: #fca5a5;
          background: #fff5f5;
        }

        .ai-poi-card.threat-high {
          border-color: #fde68a;
          background: #fffbeb;
        }

        .ai-poi-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .ai-poi-name {
          font-size: 0.9rem;
          font-weight: 750;
          color: #0f172a;
        }

        .ai-threat-badge {
          font-size: 0.64rem;
          font-weight: 800;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          letter-spacing: 0.04em;
        }

        .ai-threat-badge.threat-crit {
          background: #fef2f2;
          border: 1px solid #fecaca;
          color: #b91c1c;
        }

        .ai-threat-badge.threat-high {
          background: #fffbeb;
          border: 1px solid #fde68a;
          color: #b45309;
        }

        .ai-threat-badge.threat-med {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          color: #1d4ed8;
        }

        .ai-poi-reason {
          font-size: 0.8rem;
          color: #334155;
          margin: 0;
          line-height: 1.5;
        }

        .ai-poi-evidence {
          font-size: 0.74rem;
          color: #475569;
          font-style: italic;
          background: #f1f5f9;
          border: 1px solid #e2e8f0;
          padding: 0.4rem 0.6rem;
          border-radius: 6px;
        }

        .ev-tag {
          font-weight: 700;
          color: #1d4ed8;
          margin-right: 4px;
        }

        .ai-leads-list {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: 0.55rem;
        }

        .ai-lead-item {
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          background: #f8fafc;
          padding: 0.75rem 0.95rem;
          border-radius: 8px;
          border: 1px solid #e2e8f0;
        }

        .lead-number {
          background: #2563eb;
          color: #ffffff;
          font-size: 0.7rem;
          font-weight: 800;
          width: 22px;
          height: 22px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          margin-top: 1px;
        }

        .lead-text {
          font-size: 0.84rem;
          color: #0f172a;
          line-height: 1.5;
          font-weight: 500;
        }

        .ai-evidence-grid {
          display: flex;
          flex-direction: column;
          gap: 0.65rem;
        }

        .ai-ev-item {
          background: #f8fafc;
          padding: 0.75rem 1rem;
          border-radius: 8px;
          border: 1px solid #e2e8f0;
          border-left: 4px solid #2563eb;
        }

        .ai-ev-claim {
          font-size: 0.76rem;
          font-weight: 700;
          color: #1d4ed8;
          display: block;
          margin-bottom: 0.25rem;
        }

        .ai-ev-quote {
          font-size: 0.8rem;
          color: #334155;
          margin: 0;
          font-style: italic;
          line-height: 1.5;
        }

        .ai-anomalies-list {
          margin: 0;
          padding-left: 1.25rem;
          font-size: 0.84rem;
          color: #78350f;
          font-weight: 500;
          line-height: 1.6;
        }


        .ai-header-actions {
          display: flex;
          align-items: center;
          gap: 0.6rem;
        }
        .ai-modal-reanalyze-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          background: #f1f5f9;
          border: 1px solid #cbd5e1;
          color: #0f172a;
          font-size: 0.74rem;
          font-weight: 700;
          padding: 0.35rem 0.75rem;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .ai-modal-reanalyze-btn:hover:not(:disabled) {
          background: #e2e8f0;
          border-color: #94a3b8;
        }
        .ai-modal-reanalyze-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .ai-card-actions {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .ai-pdf-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          background: #2563eb;
          border: 1px solid #1d4ed8;
          color: #ffffff;
          font-size: 0.74rem;
          font-weight: 700;
          padding: 0.3rem 0.75rem;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.15s ease;
          box-shadow: 0 1px 4px rgba(37, 99, 235, 0.2);
        }

        .ai-pdf-btn:hover {
          background: #1d4ed8;
          transform: translateY(-1px);
          box-shadow: 0 3px 8px rgba(37, 99, 235, 0.35);
        }

        .ai-footer-actions {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .ai-footer-pdf-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          background: #ffffff;
          border: 1.5px solid #2563eb;
          color: #2563eb;
          font-size: 0.82rem;
          font-weight: 700;
          padding: 0.5rem 1.1rem;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .ai-footer-pdf-btn:hover {
          background: #eff6ff;
          border-color: #1d4ed8;
          color: #1d4ed8;
        }

        .ai-copy-btn {
          background: #f1f5f9;
          border: 1.5px solid #cbd5e1;
          color: #0f172a;
          font-size: 0.74rem;
          font-weight: 650;
          padding: 0.3rem 0.75rem;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .ai-copy-btn:hover {
          background: #2563eb;
          color: #ffffff;
          border-color: #2563eb;
        }

        .dossier-markdown-container {
          background: #f8fafc;
          border: 1.5px solid #e2e8f0;
          border-radius: 12px;
          padding: 1.35rem 1.6rem;
          max-height: 440px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
        }

        .dossier-md-h1 {
          font-size: 1.2rem;
          font-weight: 800;
          color: #0f172a;
          margin: 0.2rem 0 0.7rem 0;
          padding-bottom: 0.55rem;
          border-bottom: 2px solid #e2e8f0;
          letter-spacing: -0.01em;
          line-height: 1.35;
        }

        .dossier-md-h2 {
          font-size: 0.98rem;
          font-weight: 750;
          color: #1d4ed8;
          margin: 0.85rem 0 0.35rem 0;
          letter-spacing: 0.01em;
          display: flex;
          align-items: center;
          gap: 0.45rem;
        }

        .dossier-md-h3 {
          font-size: 0.88rem;
          font-weight: 700;
          color: #0f172a;
          margin: 0.55rem 0 0.25rem 0;
        }

        .dossier-md-p {
          font-size: 0.86rem;
          line-height: 1.68;
          color: #1e293b;
          margin: 0 0 0.45rem 0;
          font-weight: 450;
        }

        .dossier-md-ul,
        .dossier-md-ol {
          margin: 0 0 0.6rem 0;
          padding-left: 1.35rem;
          display: flex;
          flex-direction: column;
          gap: 0.3rem;
        }

        .dossier-md-li {
          font-size: 0.85rem;
          color: #1e293b;
          line-height: 1.55;
        }

        .dossier-md-quote {
          margin: 0.5rem 0;
          padding: 0.6rem 1rem;
          background: #eff6ff;
          border-left: 4px solid #2563eb;
          border-radius: 4px;
          color: #1e40af;
          font-style: italic;
          font-size: 0.84rem;
        }

        .md-bold {
          font-weight: 750;
          color: #0f172a;
        }

        .md-italic {
          color: #64748b;
          font-style: italic;
        }

        .md-code {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          background: #e2e8f0;
          color: #0f172a;
          padding: 0.12rem 0.4rem;
          border-radius: 4px;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .ai-modal-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.1rem 1.75rem;
          background: #f8fafc;
          border-top: 1px solid #e2e8f0;
        }

        .ai-footer-note {
          font-size: 0.74rem;
          color: #64748b;
          font-style: italic;
        }

        .ai-done-btn {
          background: #2563eb;
          color: #ffffff;
          border: 1px solid #1d4ed8;
          font-size: 0.84rem;
          font-weight: 750;
          padding: 0.5rem 1.4rem;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .ai-done-btn:hover {
          background: #1d4ed8;
          box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
        }

        .font-mono {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .spinning {
          animation: spin 1s linear infinite;
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
            border-top: 1px solid rgba(242, 247, 242, 0.1);
          }
        }
      `}</style>
    </div>
  );
}

// Wrapper providing ReactFlow context
export default function CaseGraphView({ caseId, caseTitle, onOpenCopilot }) {
  return (
    <ReactFlowProvider>
      <GraphCanvas caseId={caseId} caseTitle={caseTitle} onOpenCopilot={onOpenCopilot} />
    </ReactFlowProvider>
  );
}
