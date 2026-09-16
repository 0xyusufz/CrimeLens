"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { apiClient } from "../lib/apiClient";

export default function CaseCopilotView({ caseId }) {
  const [networkTables, setNetworkTables] = useState(null);
  const [loadingTables, setLoadingTables] = useState(true);
  const [brief, setBrief] = useState(null);
  const [loadingBrief, setLoadingBrief] = useState(false);

  // Chat Copilot State
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Greetings Investigator. I am CrimeLens AI Copilot powered by Gemini 3.6-Flash and Groq extraction. I have direct access to this case's verified network connections, extracted entities, and evidence snippets. Ask me anything about the suspects, connections, or financial trails.",
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const chatEndRef = useRef(null);

  // Active subview in copilot: "chat" | "table" | "brief"
  const [activeSubTab, setActiveSubTab] = useState("chat");

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
      setBrief("Unable to generate network brief at this time.");
    } finally {
      setLoadingBrief(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isQuerying]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || isQuerying) return;

    const userText = inputQuery.trim();
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
          content: "⚠️ An error occurred while consulting the intelligence model. Please verify backend connectivity.",
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem", minHeight: "650px" }}>
      {/* HEADER BAR */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "#0d1527",
          border: "1px solid #1e2d4d",
          borderRadius: "8px",
          padding: "0.85rem 1.25rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: "#10b981",
              boxShadow: "0 0 8px #10b981",
            }}
          />
          <div>
            <h3 style={{ margin: 0, fontSize: "0.95rem", color: "#f1f5f9", fontWeight: 600 }}>
              CrimeLens AI Copilot & Network Matrix
            </h3>
            <p style={{ margin: 0, fontSize: "0.75rem", color: "#94a3b8" }}>
              Tier 1 Groq (openai/gpt-oss-20b) Extraction &bull; Tier 2 Gemini 3.6-Flash Network Reasoning
            </p>
          </div>
        </div>

        {/* SUBTABS */}
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            onClick={() => setActiveSubTab("chat")}
            style={{
              padding: "0.4rem 0.85rem",
              borderRadius: "6px",
              fontSize: "0.8rem",
              fontWeight: 500,
              cursor: "pointer",
              background: activeSubTab === "chat" ? "#2563eb" : "#1e293b",
              color: "#ffffff",
              border: "1px solid #3b82f6",
            }}
          >
            💬 Copilot Chat
          </button>
          <button
            onClick={() => setActiveSubTab("table")}
            style={{
              padding: "0.4rem 0.85rem",
              borderRadius: "6px",
              fontSize: "0.8rem",
              fontWeight: 500,
              cursor: "pointer",
              background: activeSubTab === "table" ? "#2563eb" : "#1e293b",
              color: "#ffffff",
              border: "1px solid #334155",
            }}
          >
            📊 Relations Matrix ({networkTables?.relationships_count ?? 0})
          </button>
          <button
            onClick={() => {
              setActiveSubTab("brief");
              if (!brief && !loadingBrief) generateBrief();
            }}
            style={{
              padding: "0.4rem 0.85rem",
              borderRadius: "6px",
              fontSize: "0.8rem",
              fontWeight: 500,
              cursor: "pointer",
              background: activeSubTab === "brief" ? "#2563eb" : "#1e293b",
              color: "#ffffff",
              border: "1px solid #334155",
            }}
          >
            📑 Gemini Network Brief
          </button>
        </div>
      </div>

      {/* VIEW 1: COPILOT CHAT */}
      {activeSubTab === "chat" && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            background: "#0a0f1d",
            border: "1px solid #1e2d4d",
            borderRadius: "8px",
            height: "600px",
            overflow: "hidden",
          }}
        >
          {/* MESSAGES LIST */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "1.25rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
            }}
          >
            {messages.map((msg, idx) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={idx}
                  style={{
                    alignSelf: isUser ? "flex-end" : "flex-start",
                    maxWidth: "80%",
                    background: isUser ? "#1d4ed8" : "#131d33",
                    border: isUser ? "1px solid #2563eb" : "1px solid #1e2d4d",
                    borderRadius: isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                    padding: "0.85rem 1.15rem",
                    color: "#f8fafc",
                    fontSize: "0.88rem",
                    lineHeight: "1.5",
                    whiteSpace: "pre-wrap",
                    boxShadow: "0 2px 6px rgba(0,0,0,0.25)",
                  }}
                >
                  <div
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      marginBottom: "0.35rem",
                      color: isUser ? "#bfdbfe" : "#38bdf8",
                    }}
                  >
                    {isUser ? "Investigator" : "Gemini Copilot"}
                  </div>
                  {msg.content}
                </div>
              );
            })}

            {isQuerying && (
              <div
                style={{
                  alignSelf: "flex-start",
                  background: "#131d33",
                  border: "1px solid #1e2d4d",
                  borderRadius: "12px 12px 12px 2px",
                  padding: "0.75rem 1.25rem",
                  color: "#94a3b8",
                  fontSize: "0.85rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: "#38bdf8",
                    animation: "pulse 1s infinite alternate",
                  }}
                />
                Consulting relation tables and case graph...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* INPUT FORM */}
          <form
            onSubmit={handleSendMessage}
            style={{
              display: "flex",
              gap: "0.5rem",
              padding: "0.85rem 1rem",
              background: "#0d1527",
              borderTop: "1px solid #1e2d4d",
            }}
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask Copilot about any suspect, account, connection, or evidence..."
              disabled={isQuerying}
              style={{
                flex: 1,
                background: "#070b14",
                border: "1px solid #1e293b",
                borderRadius: "6px",
                padding: "0.65rem 1rem",
                color: "#f1f5f9",
                fontSize: "0.88rem",
                outline: "none",
              }}
            />
            <button
              type="submit"
              disabled={isQuerying || !inputQuery.trim()}
              style={{
                background: isQuerying || !inputQuery.trim() ? "#334155" : "#2563eb",
                color: "#ffffff",
                border: "none",
                borderRadius: "6px",
                padding: "0 1.25rem",
                fontWeight: 600,
                fontSize: "0.85rem",
                cursor: isQuerying || !inputQuery.trim() ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: "0.4rem",
              }}
            >
              Send
            </button>
          </form>
        </div>
      )}

      {/* VIEW 2: EXTRACTED RELATIONS MATRIX TABLE */}
      {activeSubTab === "table" && (
        <div
          style={{
            background: "#0a0f1d",
            border: "1px solid #1e2d4d",
            borderRadius: "8px",
            padding: "1.25rem",
            color: "#e2e8f0",
            overflowX: "auto",
          }}
        >
          <div style={{ marginBottom: "1rem", display: "flex", justifyContent: "space-between" }}>
            <div>
              <h4 style={{ margin: 0, color: "#f8fafc", fontSize: "0.95rem" }}>
                Case Relations Network Table
              </h4>
              <p style={{ margin: "0.2rem 0 0", color: "#94a3b8", fontSize: "0.78rem" }}>
                Extracted via Groq `openai/gpt-oss-20b` with source citations.
              </p>
            </div>
            <button
              onClick={fetchTables}
              style={{
                background: "#1e293b",
                border: "1px solid #334155",
                color: "#94a3b8",
                padding: "0.3rem 0.75rem",
                borderRadius: "4px",
                fontSize: "0.75rem",
                cursor: "pointer",
              }}
            >
              🔄 Refresh Tables
            </button>
          </div>

          {loadingTables ? (
            <div style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>
              Loading case relations table...
            </div>
          ) : (
            <div
              style={{
                fontFamily: "ui-monospace, monospace",
                fontSize: "0.8rem",
                lineHeight: "1.6",
                whiteSpace: "pre-wrap",
                background: "#050811",
                padding: "1rem",
                borderRadius: "6px",
                border: "1px solid #152238",
              }}
            >
              <div style={{ color: "#38bdf8", fontWeight: 700, marginBottom: "0.5rem" }}>
                ═══ RELATIONSHIPS MATRIX ═══
              </div>
              {networkTables?.relationships_table_md}

              <div style={{ color: "#38bdf8", fontWeight: 700, margin: "1.5rem 0 0.5rem" }}>
                ═══ ENTITIES INVENTORY ═══
              </div>
              {networkTables?.entities_table_md}
            </div>
          )}
        </div>
      )}

      {/* VIEW 3: GEMINI NETWORK BRIEF */}
      {activeSubTab === "brief" && (
        <div
          style={{
            background: "#0a0f1d",
            border: "1px solid #1e2d4d",
            borderRadius: "8px",
            padding: "1.5rem",
            color: "#e2e8f0",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1.25rem",
            }}
          >
            <div>
              <h4 style={{ margin: 0, color: "#f8fafc", fontSize: "1rem" }}>
                Gemini 3.6-Flash Network Intelligence Brief
              </h4>
              <p style={{ margin: "0.2rem 0 0", color: "#94a3b8", fontSize: "0.8rem" }}>
                Autonomous reasoning over the extracted relationship table and network graph.
              </p>
            </div>
            <button
              onClick={generateBrief}
              disabled={loadingBrief}
              style={{
                background: "#2563eb",
                color: "#ffffff",
                border: "none",
                borderRadius: "6px",
                padding: "0.45rem 1rem",
                fontSize: "0.8rem",
                fontWeight: 600,
                cursor: loadingBrief ? "not-allowed" : "pointer",
              }}
            >
              {loadingBrief ? "Synthesizing with Gemini..." : "⚡ Re-analyze Network"}
            </button>
          </div>

          {loadingBrief ? (
            <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
              <div style={{ marginBottom: "0.75rem", fontSize: "1.2rem" }}>🧠</div>
              Gemini 3.6-Flash is inspecting the network topology and synthesizing evidence...
            </div>
          ) : (
            <div
              style={{
                background: "#050811",
                padding: "1.25rem",
                borderRadius: "6px",
                border: "1px solid #152238",
                fontSize: "0.9rem",
                lineHeight: "1.7",
                color: "#cbd5e1",
                whiteSpace: "pre-wrap",
              }}
            >
              {brief || "Click 'Re-analyze Network' to generate the executive dossier."}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
