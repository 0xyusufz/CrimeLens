"use client";

import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { apiClient } from "../lib/apiClient";

function TabIcon({ name }) {
  if (name === "matrix") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    );
  }
  if (name === "brief") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6M8 13h8M8 17h6" />
      </svg>
    );
  }
  if (name === "path") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
      <path d="M8 11h.01M12 11h.01M16 11h.01" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9">
      <path d="M21 12a9 9 0 0 1-15.4 6.3L3 16M3 12A9 9 0 0 1 18.4 5.7L21 8" />
      <path d="M3 21v-5h5M21 3v5h-5" />
    </svg>
  );
}

// Helper to parse markdown tables into structured records
function parseMarkdownTable(md) {
  if (!md || typeof md !== "string") return [];
  const lines = md.trim().split("\n").filter((l) => l.trim().startsWith("|"));
  if (lines.length < 3) return [];
  const headers = lines[0].split("|").slice(1, -1).map((h) => h.trim());
  const rows = [];
  for (let i = 2; i < lines.length; i++) {
    const cols = lines[i].split("|").slice(1, -1).map((c) => c.trim());
    if (cols.length === headers.length) {
      const rowObj = {};
      headers.forEach((h, idx) => {
        rowObj[h] = cols[idx];
      });
      rows.push(rowObj);
    }
  }
  return rows;
}

export default function CaseCopilotView({ caseId, onClose, isSidebar = true }) {
  const [networkTables, setNetworkTables] = useState(null);
  const [loadingTables, setLoadingTables] = useState(true);
  const [brief, setBrief] = useState(null);
  const [loadingBrief, setLoadingBrief] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "I am your Case Intelligence Copilot. I analyze verified relationships, extracted entities, and evidence trails for this investigation. How can I assist your review?",
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState("chat");
  const [relationFilter, setRelationFilter] = useState("");
  const chatEndRef = useRef(null);

  // Quick Path finder state inside sidebar
  const [pathEntities, setPathEntities] = useState([]);
  const [pathSourceId, setPathSourceId] = useState("");
  const [pathTargetId, setPathTargetId] = useState("");
  const [pathQuerying, setPathQuerying] = useState(false);
  const [pathResult, setPathResult] = useState(null);
  const [pathError, setPathError] = useState(null);

  const fetchTables = useCallback(async () => {
    if (!caseId) return;
    setLoadingTables(true);
    try {
      const data = await apiClient(`/api/cases/${caseId}/intelligence/tables`);
      setNetworkTables(data);
    } catch (err) {
      console.error("Failed to load network tables:", err);
    } finally {
      setLoadingTables(false);
    }
  }, [caseId]);

  const generateBrief = useCallback(async () => {
    if (!caseId) return;
    setLoadingBrief(true);
    try {
      const data = await apiClient(`/api/cases/${caseId}/intelligence/brief`);
      setBrief(data.brief);
    } catch (err) {
      console.error("Failed to generate brief:", err);
      setBrief("Unable to generate a network brief at this time.");
    } finally {
      setLoadingBrief(false);
    }
  }, [caseId]);

  // Load graph entities for quick path finder
  const loadPathEntities = useCallback(async () => {
    if (!caseId) return;
    try {
      const data = await apiClient(`/api/cases/${caseId}/graph`);
      const nodes = data?.nodes || [];
      setPathEntities(nodes.map((n) => ({ id: n.entity_id, name: n.name, type: n.type })));
    } catch {
      // silent fallback
    }
  }, [caseId]);

  useEffect(() => {
    fetchTables();
    loadPathEntities();
  }, [fetchTables, loadPathEntities]);

  useEffect(() => {
    if (activeSubTab === "chat") {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isQuerying, activeSubTab]);

  const handleSendMessage = async (e, customPrompt = null) => {
    if (e) e.preventDefault();
    const userText = (customPrompt || inputQuery).trim();
    if (!userText || isQuerying) return;

    setInputQuery("");
    const newHistory = [...messages, { role: "user", content: userText }];
    setMessages(newHistory);
    setIsQuerying(true);

    try {
      const response = await apiClient(`/api/cases/${caseId}/intelligence/copilot`, {
        method: "POST",
        body: JSON.stringify({
          question: userText,
          history: newHistory.map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer || "No response received." },
      ]);
    } catch (err) {
      console.error("Copilot query failed:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "The case intelligence service could not complete that request. Please verify connectivity and try again.",
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  const selectTab = (tab) => {
    setActiveSubTab(tab);
    if (tab === "brief" && !brief && !loadingBrief) generateBrief();
  };

  // Structured relations parsed from backend markdown
  const parsedRelationships = useMemo(() => {
    if (!networkTables?.relationships_table_md) return [];
    return parseMarkdownTable(networkTables.relationships_table_md);
  }, [networkTables]);

  const filteredRelationships = useMemo(() => {
    if (!relationFilter.trim()) return parsedRelationships;
    const q = relationFilter.toLowerCase();
    return parsedRelationships.filter((r) =>
      Object.values(r).some((v) => String(v).toLowerCase().includes(q))
    );
  }, [parsedRelationships, relationFilter]);

  // Quick path query
  const handleQuickPathQuery = async (e) => {
    if (e) e.preventDefault();
    if (!pathSourceId || !pathTargetId || pathSourceId === pathTargetId || pathQuerying) return;
    setPathQuerying(true);
    setPathError(null);
    setPathResult(null);
    try {
      const params = new URLSearchParams({
        case_id: caseId,
        source_entity_id: pathSourceId,
        target_entity_id: pathTargetId,
        max_hops: 5,
      });
      const result = await apiClient(`/api/investigation/path?${params.toString()}`);
      setPathResult(result);
    } catch (err) {
      if (err?.status === 404) setPathError("One or both entities not found.");
      else setPathError("Failed to trace path. Please retry.");
    } finally {
      setPathQuerying(false);
    }
  };

  return (
    <div className={`copilot-sidebar-root ${isSidebar ? "is-sidebar-mode" : ""}`}>
      {/* 1. SIDEBAR HEADER */}
      <header className="copilot-sidebar-header">
        <div className="copilot-header-info">
          <div className="copilot-badge-row">
            <span className="copilot-live-dot" />
            <span className="copilot-badge-text">CASE INTELLIGENCE</span>
          </div>
          <h3 className="copilot-title">Investigator Copilot</h3>
          <p className="copilot-subtitle">Evidence-grounded network assistant</p>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="copilot-close-btn"
            title="Close Copilot Sidebar"
            aria-label="Close"
          >
            ✕
          </button>
        )}
      </header>

      {/* 2. TAB NAVIGATION PILLS */}
      <nav className="copilot-nav-pills" aria-label="Copilot Modes">
        <button
          className={`nav-pill-btn ${activeSubTab === "chat" ? "is-active" : ""}`}
          onClick={() => selectTab("chat")}
        >
          <TabIcon name="chat" />
          <span>Chat</span>
        </button>

        <button
          className={`nav-pill-btn ${activeSubTab === "brief" ? "is-active" : ""}`}
          onClick={() => selectTab("brief")}
        >
          <TabIcon name="brief" />
          <span>Brief</span>
        </button>

        <button
          className={`nav-pill-btn ${activeSubTab === "table" ? "is-active" : ""}`}
          onClick={() => selectTab("table")}
        >
          <TabIcon name="matrix" />
          <span>Relations</span>
          <span className="count-pill">{networkTables?.relationships_count ?? 0}</span>
        </button>

        <button
          className={`nav-pill-btn ${activeSubTab === "path" ? "is-active" : ""}`}
          onClick={() => selectTab("path")}
        >
          <TabIcon name="path" />
          <span>Path</span>
        </button>
      </nav>

      {/* 3. SUB-TAB CONTENT PANELS */}
      <div className="copilot-tab-body">
        {/* SUBTAB A: COPILOT CHAT */}
        {activeSubTab === "chat" && (
          <section className="copilot-chat-container">
            <div className="copilot-context-status">
              <span className="status-indicator-dot" />
              <span>Verified Case Context Active • Grounded in Evidence</span>
            </div>

            {/* Quick Prompt Chips */}
            {messages.length <= 2 && (
              <div className="quick-suggestions-block">
                <span className="suggestions-title">SUGGESTED INQUIRIES</span>
                <div className="suggestions-chips">
                  <button
                    className="suggestion-chip"
                    onClick={(e) => handleSendMessage(e, "Summarize the primary suspects and key entities in this case.")}
                  >
                    🔍 Key suspects summary
                  </button>
                  <button
                    className="suggestion-chip"
                    onClick={(e) => handleSendMessage(e, "What are the suspicious financial or transaction links discovered?")}
                  >
                    💳 Financial connections
                  </button>
                  <button
                    className="suggestion-chip"
                    onClick={(e) => handleSendMessage(e, "Show chronological timeline of critical evidence events.")}
                  >
                    ⏱️ Evidence timeline
                  </button>
                </div>
              </div>
            )}

            {/* Message Feed */}
            <div className="copilot-messages-feed">
              {messages.map((message, index) => {
                const isUser = message.role === "user";
                return (
                  <article
                    className={`copilot-bubble ${isUser ? "bubble-user" : "bubble-copilot"}`}
                    key={`${message.role}-${index}`}
                  >
                    <div className="bubble-header">
                      <span className="bubble-author">
                        {isUser ? "INVESTIGATOR" : "CRIMELENS COPILOT"}
                      </span>
                    </div>
                    <div className="bubble-text">{message.content}</div>
                  </article>
                );
              })}
              {isQuerying && (
                <div className="copilot-thinking-pill" aria-live="polite">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                  <span>Reviewing case network & documents…</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input Composer */}
            <form onSubmit={handleSendMessage} className="copilot-composer-form">
              <input
                id="copilot-sidebar-input"
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Ask about a person, entity, or link…"
                disabled={isQuerying}
                className="copilot-input-field"
              />
              <button
                type="submit"
                disabled={isQuerying || !inputQuery.trim()}
                className="copilot-send-action-btn"
                title="Send inquiry"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="m22 2-7 20-4-9-9-4Z" />
                  <path d="M22 2 11 13" />
                </svg>
              </button>
            </form>
          </section>
        )}

        {/* SUBTAB B: NETWORK BRIEF */}
        {activeSubTab === "brief" && (
          <section className="copilot-brief-container">
            <div className="brief-action-bar">
              <div>
                <span className="section-eyebrow">EXECUTIVE BRIEF</span>
                <h4 className="section-heading">Case Network Dossier</h4>
              </div>
              <button
                className="brief-refresh-btn"
                onClick={generateBrief}
                disabled={loadingBrief}
              >
                <RefreshIcon />
                <span>{loadingBrief ? "Generating…" : "Refresh"}</span>
              </button>
            </div>

            {loadingBrief ? (
              <div className="copilot-loading-state">
                <span className="loading-spinner" />
                <p>Generating evidence-grounded intelligence brief…</p>
              </div>
            ) : brief ? (
              <div className="brief-card-content">
                <p className="brief-paragraph">{brief}</p>
              </div>
            ) : (
              <div className="brief-empty-card">
                <p>Click "Refresh" to synthesize the case network with Gemini AI.</p>
              </div>
            )}
          </section>
        )}

        {/* SUBTAB C: RELATIONS MATRIX */}
        {activeSubTab === "table" && (
          <section className="copilot-matrix-container">
            <div className="matrix-action-bar">
              <div>
                <span className="section-eyebrow">NETWORK REGISTER</span>
                <h4 className="section-heading">Extracted Relationships</h4>
              </div>
              <button
                className="matrix-refresh-btn"
                onClick={fetchTables}
                disabled={loadingTables}
              >
                <RefreshIcon />
              </button>
            </div>

            {/* Filter Input */}
            <div className="matrix-search-box">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="Filter by person, type, or entity…"
                value={relationFilter}
                onChange={(e) => setRelationFilter(e.target.value)}
                className="matrix-search-input"
              />
              {relationFilter && (
                <button className="matrix-clear-btn" onClick={() => setRelationFilter("")}>
                  ✕
                </button>
              )}
            </div>

            {loadingTables ? (
              <div className="copilot-loading-state">
                <span className="loading-spinner" />
                <p>Loading case relationships…</p>
              </div>
            ) : filteredRelationships.length > 0 ? (
              <div className="matrix-cards-list">
                {filteredRelationships.map((row, idx) => {
                  const src = row["Source Entity"] || "Unknown";
                  const tgt = row["Target Entity"] || "Unknown";
                  const rel = row["Relationship"] || "CONNECTED_TO";
                  const conf = row["Confidence"] ? `${Math.round(parseFloat(row["Confidence"]) * 100)}%` : null;
                  const snippet = row["Evidence Snippet"];

                  return (
                    <div key={idx} className="matrix-rel-card">
                      <div className="rel-card-header">
                        <span className="rel-type-pill">{rel}</span>
                        {conf && <span className="rel-conf-pill">{conf}</span>}
                      </div>

                      <div className="rel-card-entities">
                        <div className="entity-box entity-src" title={src}>
                          <span className="entity-dot" />
                          <span className="entity-label">{src}</span>
                        </div>
                        <div className="rel-arrow-connector">➔</div>
                        <div className="entity-box entity-tgt" title={tgt}>
                          <span className="entity-dot dot-tgt" />
                          <span className="entity-label">{tgt}</span>
                        </div>
                      </div>

                      {snippet && (
                        <div className="rel-card-snippet">
                          <span className="snippet-quote">“{snippet}”</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="matrix-empty-state">
                <p>No matching relationships found.</p>
              </div>
            )}
          </section>
        )}

        {/* SUBTAB D: QUICK PATH FINDER */}
        {activeSubTab === "path" && (
          <section className="copilot-path-container">
            <div className="path-intro-header">
              <span className="section-eyebrow">CONNECTION FINDER</span>
              <h4 className="section-heading">Trace Entity Link</h4>
              <p className="path-subtext">Pick two entities to discover how they connect.</p>
            </div>

            <form onSubmit={handleQuickPathQuery} className="path-quick-form">
              <div className="form-group-compact">
                <label className="compact-label">FROM (SOURCE)</label>
                <select
                  value={pathSourceId}
                  onChange={(e) => setPathSourceId(e.target.value)}
                  className="compact-select"
                >
                  <option value="">Select starting entity…</option>
                  {pathEntities.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name} ({e.type})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group-compact">
                <label className="compact-label">TO (TARGET)</label>
                <select
                  value={pathTargetId}
                  onChange={(e) => setPathTargetId(e.target.value)}
                  className="compact-select"
                >
                  <option value="">Select target entity…</option>
                  {pathEntities.map((e) => (
                    <option key={e.id} value={e.id} disabled={e.id === pathSourceId}>
                      {e.name} ({e.type})
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={!pathSourceId || !pathTargetId || pathSourceId === pathTargetId || pathQuerying}
                className="path-trace-btn"
              >
                {pathQuerying ? "Tracing Connection…" : "Trace Path"}
              </button>
            </form>

            {pathError && <div className="path-inline-error">{pathError}</div>}

            {pathResult && pathResult.found && pathResult.nodes && (
              <div className="quick-path-chain-results">
                <div className="path-found-banner">
                  <span>✓ Connection established ({pathResult.hops} hops)</span>
                </div>
                <div className="quick-chain-vertical">
                  {pathResult.nodes.map((node, i) => {
                    const rel = pathResult.relationships?.[i];
                    return (
                      <div key={node.entity_id || i} className="chain-step-group">
                        <div className={`chain-node-box ${i === 0 ? "is-start" : i === pathResult.nodes.length - 1 ? "is-end" : ""}`}>
                          <span className="node-type-micro">{node.type}</span>
                          <span className="node-name-text">{node.name}</span>
                        </div>
                        {rel && (
                          <div className="chain-rel-connector">
                            <span className="chain-rel-pill">{rel.relationship}</span>
                            <div className="chain-rel-line" />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {pathResult && !pathResult.found && (
              <div className="path-none-found">
                <span>No direct or multi-hop path found between selected entities.</span>
              </div>
            )}
          </section>
        )}
      </div>

      <style jsx>{`
        .copilot-sidebar-root {
          display: flex;
          flex-direction: column;
          width: 100%;
          height: 100%;
          background: #171D1C;
          border: 1px solid rgba(242, 247, 242, 0.12);
          border-radius: 12px;
          overflow: hidden;
          font-family: inherit;
        }

        .is-sidebar-mode {
          min-height: 540px;
          height: 100%;
        }

        /* 1. HEADER */
        .copilot-sidebar-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          padding: 1rem 1.15rem;
          background: #171D1C;
          border-bottom: 1px solid rgba(242, 247, 242, 0.1);
        }

        .copilot-header-info {
          min-width: 0;
        }

        .copilot-badge-row {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          margin-bottom: 0.2rem;
        }

        .copilot-live-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #FCBA04;
          box-shadow: 0 0 0 3px rgba(252, 186, 4, 0.2);
        }

        .copilot-badge-text {
          font-size: 0.65rem;
          font-weight: 800;
          letter-spacing: 0.08em;
          color: #FCBA04;
        }

        .copilot-title {
          font-size: 1rem;
          font-weight: 750;
          color: #F2F7F2;
          margin: 0;
          line-height: 1.25;
        }

        .copilot-subtitle {
          font-size: 0.73rem;
          color: #c8d4cf;
          margin: 0.15rem 0 0;
        }

        .copilot-close-btn {
          width: 28px;
          height: 28px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 6px;
          border: 1px solid rgba(242, 247, 242, 0.15);
          background: #18202b;
          color: #c8d4cf;
          cursor: pointer;
          font-size: 0.85rem;
          transition: all 0.16s ease;
        }

        .copilot-close-btn:hover {
          background: rgba(252, 186, 4, 0.15);
          color: #FCBA04;
          border-color: rgba(252, 186, 4, 0.4);
        }

        /* 2. SUB-NAVIGATION PILLS */
        .copilot-nav-pills {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.45rem 0.65rem;
          background: #171D1C;
          border-bottom: 1px solid rgba(242, 247, 242, 0.1);
        }

        .nav-pill-btn {
          flex: 1;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 0.35rem;
          padding: 0.42rem 0.5rem;
          border-radius: 7px;
          border: 1px solid transparent;
          background: transparent;
          color: #c8d4cf;
          font-size: 0.74rem;
          font-weight: 650;
          cursor: pointer;
          transition: all 0.16s ease;
        }

        .nav-pill-btn :global(svg) {
          width: 14px;
          height: 14px;
        }

        .nav-pill-btn:hover {
          color: #35A7FF;
          background: rgba(53, 167, 255, 0.12);
        }

        .nav-pill-btn.is-active {
          color: #171D1C;
          background: #35A7FF;
          border-color: #35A7FF;
          font-weight: 750;
          box-shadow: 0 2px 6px rgba(53, 167, 255, 0.3);
        }

        .count-pill {
          padding: 0 0.28rem;
          border-radius: 10px;
          font-size: 0.62rem;
          background: #18202b;
          color: #F2F7F2;
        }

        .is-active .count-pill {
          background: #171D1C;
          color: #35A7FF;
        }

        /* 3. TAB BODY */
        .copilot-tab-body {
          flex: 1;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          min-height: 0;
          background: #171D1C;
        }

        /* CHAT SECTION */
        .copilot-chat-container {
          display: flex;
          flex-direction: column;
          flex: 1;
          min-height: 0;
          background: #171D1C;
        }

        .copilot-context-status {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.45rem 0.85rem;
          background: #171D1C;
          border-bottom: 1px solid rgba(242, 247, 242, 0.08);
          font-size: 0.68rem;
          font-weight: 600;
          color: #c8d4cf;
        }

        .status-indicator-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #FCBA04;
        }

        .quick-suggestions-block {
          padding: 0.75rem 0.85rem;
          background: #171D1C;
          border-bottom: 1px solid rgba(242, 247, 242, 0.08);
        }

        .suggestions-title {
          font-size: 0.61rem;
          font-weight: 800;
          letter-spacing: 0.06em;
          color: #c8d4cf;
          display: block;
          margin-bottom: 0.4rem;
        }

        .suggestions-chips {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }

        .suggestion-chip {
          display: block;
          text-align: left;
          padding: 0.38rem 0.65rem;
          border-radius: 6px;
          border: 1px solid rgba(242, 247, 242, 0.12);
          background: #141a22;
          color: #F2F7F2;
          font-size: 0.72rem;
          font-weight: 550;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .suggestion-chip:hover {
          background: rgba(53, 167, 255, 0.15);
          border-color: #35A7FF;
          color: #35A7FF;
        }

        .copilot-messages-feed {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          min-height: 260px;
          max-height: 480px;
          background: #171D1C;
        }

        .copilot-bubble {
          max-width: 90%;
          padding: 0.65rem 0.85rem;
          border-radius: 8px;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
        }

        .bubble-copilot {
          align-self: flex-start;
          background: #141a22;
          border: 1px solid rgba(220, 230, 242, 0.1);
        }

        .bubble-user {
          align-self: flex-end;
          background: #35A7FF;
          border: 1px solid #35A7FF;
          color: #171D1C;
        }

        .bubble-header {
          margin-bottom: 0.25rem;
        }

        .bubble-author {
          font-size: 0.58rem;
          font-weight: 800;
          letter-spacing: 0.07em;
          color: #35A7FF;
        }

        .bubble-user .bubble-author {
          color: #171D1C;
        }

        .bubble-text {
          font-size: 0.8rem;
          line-height: 1.5;
          color: #F2F7F2;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .bubble-user .bubble-text {
          color: #171D1C;
          font-weight: 600;
        }

        .copilot-thinking-pill {
          align-self: flex-start;
          display: flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.45rem 0.75rem;
          background: #141a22;
          border: 1px solid rgba(53, 167, 255, 0.35);
          border-radius: 7px;
          font-size: 0.72rem;
          color: #35A7FF;
        }

        .copilot-thinking-pill .dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #35A7FF;
          animation: dot-pulse 1s infinite alternate;
        }

        .copilot-thinking-pill .dot:nth-child(2) {
          animation-delay: 0.2s;
        }
        .copilot-thinking-pill .dot:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes dot-pulse {
          to {
            opacity: 0.25;
            transform: translateY(-2px);
          }
        }

        .copilot-composer-form {
          display: flex;
          gap: 0.45rem;
          padding: 0.75rem 0.85rem;
          background: #171D1C;
          border-top: 1px solid rgba(242, 247, 242, 0.1);
        }

        .copilot-input-field {
          flex: 1;
          min-width: 0;
          height: 38px;
          padding: 0 0.75rem;
          background: #0d1218;
          border: 1px solid rgba(220, 230, 242, 0.15);
          border-radius: 8px;
          font-size: 0.78rem;
          color: #F2F7F2;
          outline: none;
        }

        .copilot-input-field:focus {
          border-color: #35A7FF;
          box-shadow: 0 0 0 2px rgba(53, 167, 255, 0.2);
        }

        .copilot-send-action-btn {
          width: 38px;
          height: 38px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 8px;
          border: 1px solid #35A7FF;
          background: #35A7FF;
          color: #171D1C;
          cursor: pointer;
          transition: all 0.16s ease;
          font-weight: 750;
        }

        .copilot-send-action-btn:hover:not(:disabled) {
          background: #2392ea;
        }

        .copilot-send-action-btn:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }

        /* BRIEF SECTION */
        .copilot-brief-container {
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.85rem;
          background: #171D1C;
        }

        .brief-action-bar,
        .matrix-action-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-bottom: 0.65rem;
          border-bottom: 1px solid rgba(242, 247, 242, 0.1);
        }

        .section-eyebrow {
          font-size: 0.6rem;
          font-weight: 800;
          letter-spacing: 0.08em;
          color: #FCBA04;
        }

        .section-heading {
          margin: 0.1rem 0 0;
          font-size: 0.88rem;
          font-weight: 700;
          color: #F2F7F2;
        }

        .brief-refresh-btn,
        .matrix-refresh-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.35rem 0.65rem;
          border-radius: 6px;
          border: 1px solid rgba(242, 247, 242, 0.15);
          background: #18202b;
          color: #F2F7F2;
          font-size: 0.72rem;
          font-weight: 600;
          cursor: pointer;
        }

        .brief-refresh-btn:hover,
        .matrix-refresh-btn:hover {
          background: #35A7FF;
          color: #171D1C;
          border-color: #35A7FF;
        }

        .brief-refresh-btn :global(svg),
        .matrix-refresh-btn :global(svg) {
          width: 13px;
          height: 13px;
        }

        .brief-card-content {
          padding: 1rem;
          border-radius: 8px;
          border: 1px solid rgba(220, 230, 242, 0.1);
          background: #141a22;
        }

        .brief-paragraph {
          margin: 0;
          font-size: 0.8rem;
          line-height: 1.65;
          color: #F2F7F2;
          white-space: pre-wrap;
        }

        .brief-empty-card,
        .matrix-empty-state,
        .copilot-loading-state {
          padding: 1.5rem;
          text-align: center;
          font-size: 0.78rem;
          color: #c8d4cf;
          border: 1px dashed rgba(220, 230, 242, 0.15);
          border-radius: 8px;
          background: #141a22;
        }

        .loading-spinner {
          display: inline-block;
          width: 20px;
          height: 20px;
          border: 2px solid rgba(53, 167, 255, 0.2);
          border-top-color: #35A7FF;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
          margin-bottom: 0.5rem;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        /* MATRIX SECTION */
        .copilot-matrix-container {
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          background: #171D1C;
        }

        .matrix-search-box {
          position: relative;
          display: flex;
          align-items: center;
        }

        .matrix-search-box svg {
          position: absolute;
          left: 0.65rem;
          color: #c8d4cf;
          pointer-events: none;
        }

        .matrix-search-input {
          width: 100%;
          height: 34px;
          padding: 0 1.8rem 0 2rem;
          border-radius: 6px;
          border: 1px solid rgba(220, 230, 242, 0.15);
          background: #0d1218;
          font-size: 0.75rem;
          color: #F2F7F2;
          outline: none;
        }

        .matrix-search-input:focus {
          border-color: #35A7FF;
        }

        .matrix-clear-btn {
          position: absolute;
          right: 0.5rem;
          background: none;
          border: none;
          color: #c8d4cf;
          font-size: 0.75rem;
          cursor: pointer;
        }

        .matrix-cards-list {
          display: flex;
          flex-direction: column;
          gap: 0.6rem;
          max-height: 480px;
          overflow-y: auto;
        }

        .matrix-rel-card {
          padding: 0.7rem 0.8rem;
          border-radius: 8px;
          border: 1px solid rgba(220, 230, 242, 0.1);
          background: #141a22;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
        }

        .rel-card-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 0.4rem;
        }

        .rel-type-pill {
          font-size: 0.64rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          padding: 0.15rem 0.4rem;
          border-radius: 4px;
          background: rgba(53, 167, 255, 0.15);
          color: #35A7FF;
          font-family: ui-monospace, monospace;
        }

        .rel-conf-pill {
          font-size: 0.62rem;
          font-weight: 700;
          color: #FCBA04;
          font-family: ui-monospace, monospace;
        }

        .rel-card-entities {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .entity-box {
          flex: 1;
          min-width: 0;
          display: flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.35rem 0.5rem;
          background: #171D1C;
          border: 1px solid rgba(242, 247, 242, 0.1);
          border-radius: 6px;
        }

        .entity-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #35A7FF;
          flex-shrink: 0;
        }

        .dot-tgt {
          background: #FCBA04;
        }

        .entity-label {
          font-size: 0.74rem;
          font-weight: 650;
          color: #F2F7F2;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .rel-arrow-connector {
          font-size: 0.8rem;
          color: #c8d4cf;
          flex-shrink: 0;
        }

        .rel-card-snippet {
          margin-top: 0.45rem;
          padding-top: 0.4rem;
          border-top: 1px dashed rgba(242, 247, 242, 0.1);
        }

        .snippet-quote {
          font-size: 0.68rem;
          line-height: 1.4;
          color: #c8d4cf;
          font-style: italic;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        /* PATH SECTION */
        .copilot-path-container {
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.85rem;
          background: #171D1C;
        }

        .path-intro-header {
          border-bottom: 1px solid rgba(242, 247, 242, 0.1);
          padding-bottom: 0.65rem;
        }

        .path-subtext {
          font-size: 0.72rem;
          color: #c8d4cf;
          margin: 0.15rem 0 0;
        }

        .path-quick-form {
          display: flex;
          flex-direction: column;
          gap: 0.65rem;
        }

        .form-group-compact {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .compact-label {
          font-size: 0.62rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          color: #c8d4cf;
        }

        .compact-select {
          width: 100%;
          height: 36px;
          padding: 0 0.65rem;
          border-radius: 6px;
          border: 1px solid rgba(220, 230, 242, 0.15);
          background: #0d1218;
          font-size: 0.76rem;
          color: #F2F7F2;
          outline: none;
        }

        .compact-select:focus {
          border-color: #35A7FF;
        }

        .path-trace-btn {
          width: 100%;
          height: 38px;
          border-radius: 6px;
          border: 1px solid #35A7FF;
          background: #35A7FF;
          color: #171D1C;
          font-size: 0.78rem;
          font-weight: 750;
          cursor: pointer;
          transition: all 0.16s ease;
          margin-top: 0.25rem;
        }

        .path-trace-btn:hover:not(:disabled) {
          background: #2392ea;
        }

        .path-trace-btn:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }

        .path-inline-error {
          padding: 0.5rem 0.65rem;
          background: rgba(252, 186, 4, 0.12);
          border: 1px solid rgba(252, 186, 4, 0.35);
          border-radius: 6px;
          color: #FCBA04;
          font-size: 0.72rem;
        }

        .path-found-banner {
          padding: 0.45rem 0.65rem;
          background: rgba(53, 167, 255, 0.15);
          border: 1px solid rgba(53, 167, 255, 0.35);
          border-radius: 6px;
          color: #35A7FF;
          font-size: 0.72rem;
          font-weight: 650;
          margin-bottom: 0.65rem;
        }

        .quick-chain-vertical {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }

        .chain-step-group {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .chain-node-box {
          width: 100%;
          padding: 0.55rem 0.75rem;
          border-radius: 6px;
          border: 1px solid rgba(220, 230, 242, 0.1);
          background: #141a22;
          display: flex;
          flex-direction: column;
          gap: 0.15rem;
        }

        .chain-node-box.is-start {
          border-color: #35A7FF;
          background: rgba(53, 167, 255, 0.12);
        }

        .chain-node-box.is-end {
          border-color: #FCBA04;
          background: rgba(252, 186, 4, 0.12);
        }

        .node-type-micro {
          font-size: 0.58rem;
          font-weight: 800;
          color: #35A7FF;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .node-name-text {
          font-size: 0.78rem;
          font-weight: 700;
          color: #F2F7F2;
        }

        .chain-rel-connector {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 0.35rem 0;
        }

        .chain-rel-pill {
          font-size: 0.62rem;
          font-weight: 800;
          padding: 0.12rem 0.45rem;
          border-radius: 4px;
          background: #171D1C;
          color: #F2F7F2;
          font-family: ui-monospace, monospace;
        }

        .chain-rel-line {
          width: 2px;
          height: 12px;
          background: rgba(242, 247, 242, 0.2);
        }

        .path-none-found {
          padding: 1rem;
          border-radius: 6px;
          background: #141a22;
          border: 1px dashed rgba(220, 230, 242, 0.15);
          font-size: 0.74rem;
          color: #c8d4cf;
          text-align: center;
        }
      `}</style>
    </div>
  );
}
