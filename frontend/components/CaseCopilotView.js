"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { apiClient } from "../lib/apiClient";
import CrimeLensLogo from "./CrimeLensLogo";

export default function CaseCopilotView({ caseId, onClose, isSidebar = true, initialQuery = "" }) {
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Ask me anything about your case files, suspect connections, financial trails, or evidence records.",
      referencedDocs: [],
    },
  ]);
  const [inputQuery, setInputQuery] = useState(initialQuery || "");
  const [isQuerying, setIsQuerying] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (initialQuery) {
      setInputQuery(initialQuery);
    }
  }, [initialQuery]);

  // Fetch registered case evidence documents
  const fetchCaseDocuments = useCallback(async () => {
    if (!caseId) return;
    try {
      const data = await apiClient(`/api/cases/${caseId}/documents`);
      if (Array.isArray(data)) {
        setDocuments(data);
      }
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCaseDocuments();
  }, [fetchCaseDocuments]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isQuerying]);

  // Match referenced documents
  const findReferencedDocs = (text) => {
    if (!documents || documents.length === 0 || !text) return [];
    const lower = text.toLowerCase();
    const matched = documents.filter((doc) => {
      const name = (doc.filename || "").toLowerCase();
      const base = name.split(".")[0];
      return lower.includes(name) || (base.length > 3 && lower.includes(base));
    });
    if (matched.length > 0) return matched;
    return documents.slice(0, 2);
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const userText = inputQuery.trim();
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

      const answerText = response.answer || "No response received.";
      const relevantDocs = findReferencedDocs(`${userText} ${answerText}`);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: answerText,
          referencedDocs: relevantDocs,
        },
      ]);
    } catch (err) {
      console.error("Query failed:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Unable to process request. Please check service connectivity and retry.",
          referencedDocs: [],
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className={`clean-copilot-root ${isSidebar ? "is-sidebar-mode" : ""}`}>
      {/* 1. MINIMAL COMPACT HEADER */}
      <header className="copilot-header">
        <div className="header-info">
          <CrimeLensLogo size={32} iconSize={18} withBadge={true} />
          <div className="header-text-block">
            <h3 className="header-title">Investigation Assistant</h3>
            <p className="header-subtitle">Ask about case files, suspect links & connections</p>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="header-close-btn"
            title="Close"
            aria-label="Close"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </header>

      {/* 2. FULL-HEIGHT MESSAGES FEED */}
      <div className="chat-messages-area">
        {messages.map((message, index) => {
          const isUser = message.role === "user";
          const refDocs = message.referencedDocs || [];

          return (
            <div
              className={`message-wrapper ${isUser ? "user-message" : "assistant-message"}`}
              key={`${message.role}-${index}`}
            >
              <div className={`message-card ${isUser ? "card-user" : "card-assistant"}`}>
                <div className="card-sender">
                  {isUser ? "You" : "CrimeLens Assistant"}
                </div>
                <div className="card-content">{message.content}</div>

                {/* REFERENCED DOCUMENTS / EVIDENCE */}
                {!isUser && refDocs.length > 0 && (
                  <div className="evidence-sources-box">
                    <span className="sources-label">Referenced Evidence:</span>
                    <div className="sources-chips">
                      {refDocs.map((doc, dIdx) => {
                        const isPdf = (doc.filename || "").toLowerCase().endsWith(".pdf");
                        return (
                          <div className="source-doc-pill" key={doc.id || dIdx} title={`File: ${doc.filename}`}>
                            <span className={`pill-type ${isPdf ? "pdf-type" : "doc-type"}`}>
                              {isPdf ? "PDF" : "DOC"}
                            </span>
                            <span className="pill-name">{doc.filename}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {isQuerying && (
          <div className="loading-state-row">
            <div className="loading-card">
              <span className="dot-pulse" />
              <span className="dot-pulse" />
              <span className="dot-pulse" />
              <span>Analyzing case files & connections…</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* 3. COMPOSER BAR */}
      <form onSubmit={handleSendMessage} className="chat-composer">
        <input
          id="investigation-chat-input"
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          placeholder="Ask about files, suspects, or connections…"
          disabled={isQuerying}
          className="composer-text-input"
        />
        <button
          type="submit"
          disabled={isQuerying || !inputQuery.trim()}
          className="composer-submit-btn"
          title="Send"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>

      <style jsx>{`
        .clean-copilot-root {
          display: flex;
          flex-direction: column;
          width: 100%;
          height: 100%;
          background: #ffffff;
          border-radius: 12px;
          overflow: hidden;
          font-family: inherit;
        }

        .is-sidebar-mode {
          min-height: 520px;
          height: 100%;
        }

        /* HEADER */
        .copilot-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.85rem 1.15rem;
          background: #ffffff;
          border-bottom: 1px solid #f1f5f9;
        }

        .header-info {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          min-width: 0;
        }

        .header-text-block {
          min-width: 0;
        }

        .header-title {
          font-size: 0.94rem;
          font-weight: 750;
          color: #0f172a;
          margin: 0;
          line-height: 1.25;
          letter-spacing: -0.015em;
        }

        .header-subtitle {
          font-size: 0.71rem;
          color: #64748b;
          margin: 0.15rem 0 0 0;
          line-height: 1.35;
          font-weight: 500;
        }

        .header-close-btn {
          width: 28px;
          height: 28px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 6px;
          border: 1px solid #e2e8f0;
          background: #f8fafc;
          color: #64748b;
          cursor: pointer;
          transition: all 0.15s ease;
          flex-shrink: 0;
        }

        .header-close-btn:hover {
          background: #fee2e2;
          color: #dc2626;
          border-color: #fca5a5;
        }

        /* CHAT AREA */
        .chat-messages-area {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          background: #f8fafc;
        }

        .message-wrapper {
          display: flex;
          width: 100%;
        }

        .user-message {
          justify-content: flex-end;
        }

        .assistant-message {
          justify-content: flex-start;
        }

        .message-card {
          max-width: 90%;
          padding: 0.75rem 0.95rem;
          border-radius: 10px;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        }

        .card-user {
          background: #2563eb;
          color: #ffffff;
          border-bottom-right-radius: 2px;
        }

        .card-assistant {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          color: #1e293b;
          border-bottom-left-radius: 2px;
        }

        .card-sender {
          font-size: 0.62rem;
          font-weight: 750;
          letter-spacing: 0.04em;
          margin-bottom: 0.25rem;
        }

        .card-user .card-sender {
          color: #bfdbfe;
        }

        .card-assistant .card-sender {
          color: #2563eb;
        }

        .card-content {
          font-size: 0.81rem;
          line-height: 1.55;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .card-user .card-content {
          font-weight: 500;
        }

        /* EVIDENCE SOURCES BOX */
        .evidence-sources-box {
          margin-top: 0.6rem;
          padding-top: 0.5rem;
          border-top: 1px dashed #e2e8f0;
        }

        .sources-label {
          font-size: 0.62rem;
          font-weight: 700;
          color: #64748b;
          display: block;
          margin-bottom: 0.3rem;
          text-transform: uppercase;
          letter-spacing: 0.03em;
        }

        .sources-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 0.3rem;
        }

        .source-doc-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 2px 7px;
          background: #f1f5f9;
          border: 1px solid #e2e8f0;
          border-radius: 4px;
          font-size: 0.68rem;
          max-width: 100%;
        }

        .pill-type {
          font-size: 0.56rem;
          font-weight: 800;
          padding: 1px 4px;
          border-radius: 3px;
        }

        .pdf-type {
          background: #ef4444;
          color: #ffffff;
        }

        .doc-type {
          background: #2563eb;
          color: #ffffff;
        }

        .pill-name {
          font-weight: 600;
          color: #0f172a;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        /* LOADING INDICATOR */
        .loading-state-row {
          display: flex;
          justify-content: flex-start;
          width: 100%;
        }

        .loading-card {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.45rem 0.8rem;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 7px;
          font-size: 0.73rem;
          color: #2563eb;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        }

        .dot-pulse {
          width: 4.5px;
          height: 4.5px;
          border-radius: 50%;
          background: #2563eb;
          animation: pulse 1s infinite alternate;
        }

        .dot-pulse:nth-child(2) {
          animation-delay: 0.2s;
        }
        .dot-pulse:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes pulse {
          to {
            opacity: 0.2;
            transform: translateY(-2px);
          }
        }

        /* COMPOSER */
        .chat-composer {
          display: flex;
          gap: 0.45rem;
          padding: 0.7rem 0.9rem;
          background: #ffffff;
          border-top: 1px solid #f1f5f9;
        }

        .composer-text-input {
          flex: 1;
          min-width: 0;
          height: 38px;
          padding: 0 0.8rem;
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-radius: 7px;
          font-size: 0.78rem;
          color: #0f172a;
          outline: none;
          transition: border-color 0.15s ease;
        }

        .composer-text-input:focus {
          border-color: #2563eb;
          box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
        }

        .composer-submit-btn {
          width: 38px;
          height: 38px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 7px;
          border: none;
          background: #2563eb;
          color: #ffffff;
          cursor: pointer;
          transition: all 0.15s ease;
          flex-shrink: 0;
        }

        .composer-submit-btn:hover:not(:disabled) {
          background: #1d4ed8;
        }

        .composer-submit-btn:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
