"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { apiClient } from "../lib/apiClient";
import CrimeLensLogo from "./CrimeLensLogo";

export default function CaseInvestigatorChatView({ caseId, caseData, documents = [] }) {
  const [messages, setMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Match referenced documents from response text
  const matchReferencedDocs = (text) => {
    if (!documents || documents.length === 0 || !text) return [];
    const lower = text.toLowerCase();
    const matched = documents.filter((doc) => {
      const name = (doc.filename || "").toLowerCase();
      const base = name.split(".")[0];
      return lower.includes(name) || (base.length > 3 && lower.includes(base));
    });
    if (matched.length > 0) return matched;
    return documents.slice(0, Math.min(2, documents.length));
  };

  // Load persisted chat history from PostgreSQL
  useEffect(() => {
    if (!caseId) return;
    let isMounted = true;
    (async () => {
      try {
        setLoadingHistory(true);
        const data = await apiClient(`/api/cases/${caseId}/intelligence/chat`);
        if (isMounted && Array.isArray(data)) {
          const loaded = data.map((m) => {
            const time = m.created_at
              ? new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
              : "";
            return {
              id: m.id,
              role: m.role,
              content: m.content,
              model: m.model,
              timestamp: time,
              referencedDocs: m.role === "assistant" ? matchReferencedDocs(m.content) : [],
            };
          });
          setMessages(loaded);
        }
      } catch (err) {
        console.warn("Failed to load chat history from DB:", err);
      } finally {
        if (isMounted) setLoadingHistory(false);
      }
    })();
    return () => {
      isMounted = false;
    };
  }, [caseId]);

  // Auto-scroll to latest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isQuerying]);

  const handleSendMessage = async (textToSend) => {
    const query = (typeof textToSend === "string" ? textToSend : inputQuery).trim();
    if (!query || isQuerying) return;

    const userTimestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const newHistory = [
      ...messages,
      { role: "user", content: query, timestamp: userTimestamp },
    ];

    setMessages(newHistory);
    setInputQuery("");
    setIsQuerying(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      const response = await apiClient(`/api/cases/${caseId}/intelligence/copilot`, {
        method: "POST",
        body: JSON.stringify({
          question: query,
          history: newHistory
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      const answerText = response.answer || "No response received from intelligence engine.";
      const relevantDocs = matchReferencedDocs(`${query} ${answerText}`);
      const assistantTimestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

      setMessages((prev) => {
        const updated = [...prev];
        if (updated.length > 0 && response.user_message_id) {
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            id: response.user_message_id,
          };
        }
        return [
          ...updated,
          {
            id: response.assistant_message_id,
            role: "assistant",
            content: answerText,
            referencedDocs: relevantDocs,
            timestamp: assistantTimestamp,
            model: response.model,
          },
        ];
      });
    } catch (err) {
      console.error("Investigator chat failed:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "⚠️ **Investigative Engine Notice**: Unable to complete synthesis. Please verify that documents have been processed and backend services are operational.",
          referencedDocs: [],
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleTextareaInput = (e) => {
    setInputQuery(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
  };

  const handleCopyMessage = (content, index) => {
    navigator.clipboard.writeText(content);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2500);
  };

  const handleDeleteAll = async () => {
    setIsDeleting(true);
    try {
      await apiClient(`/api/cases/${caseId}/intelligence/chat`, { method: "DELETE" });
      setMessages([]);
      setInputQuery("");
      setConfirmDeleteAll(false);
    } catch (err) {
      console.error("Failed to delete chat history:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteSingleMessage = async (msgId, index) => {
    if (msgId) {
      try {
        await apiClient(`/api/cases/${caseId}/intelligence/chat/${msgId}`, { method: "DELETE" });
      } catch (err) {
        console.error("Failed to delete individual message:", err);
      }
    }
    setMessages((prev) => prev.filter((_, i) => i !== index));
  };

  // Helper to format markdown text
  const renderFormattedContent = (content) => {
    if (!content) return null;

    const lines = content.split("\n");
    return lines.map((line, idx) => {
      // Header 3
      if (line.startsWith("### ")) {
        return <h4 key={idx} className="msg-h3">{line.replace("### ", "")}</h4>;
      }
      // Header 2 / 1
      if (line.startsWith("## ") || line.startsWith("# ")) {
        return <h3 key={idx} className="msg-h2">{line.replace(/^#+\s/, "")}</h3>;
      }
      // Bullet list item
      if (line.trim().startsWith("* ") || line.trim().startsWith("- ")) {
        const itemText = line.trim().replace(/^[\*\-]\s+/, "");
        return (
          <div key={idx} className="msg-bullet-item">
            <span className="bullet-dot">•</span>
            <span>{renderInlineFormatting(itemText)}</span>
          </div>
        );
      }
      // Numbered list item
      if (/^\d+\.\s/.test(line.trim())) {
        const match = line.trim().match(/^(\d+)\.\s+(.*)/);
        if (match) {
          return (
            <div key={idx} className="msg-numbered-item">
              <span className="number-badge">{match[1]}.</span>
              <span>{renderInlineFormatting(match[2])}</span>
            </div>
          );
        }
      }
      // Empty line
      if (!line.trim()) {
        return <div key={idx} className="msg-spacer" />;
      }
      // Regular paragraph
      return <p key={idx} className="msg-paragraph">{renderInlineFormatting(line)}</p>;
    });
  };

  // Helper for inline bold, quotes, and monospace
  const renderInlineFormatting = (text) => {
    if (!text) return "";
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={pIdx}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return <code key={pIdx} className="msg-code">{part.slice(1, -1)}</code>;
      }
      return part;
    });
  };


  return (
    <div className="investigator-chat-workspace">
      {/* 1. WORKSPACE TOP HEADER */}
      <header className="chat-top-header">
        <div className="header-left-col">
          <div className="header-branding-row">
            <CrimeLensLogo size={32} iconSize={18} withBadge={true} />
            <div className="header-titles">
              <h2 className="workspace-main-title">Investigator Assistant</h2>
            </div>
          </div>
        </div>

        <div className="header-right-col">
          {messages.length > 0 && !confirmDeleteAll && (
            <button
              type="button"
              onClick={() => setConfirmDeleteAll(true)}
              className="delete-chat-btn"
              title="Delete chat conversation history"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                <line x1="10" y1="11" x2="10" y2="17" />
                <line x1="14" y1="11" x2="14" y2="17" />
              </svg>
              <span>Delete Chat</span>
            </button>
          )}

          {confirmDeleteAll && (
            <div className="confirm-delete-box">
              <span className="confirm-text">Delete all messages?</span>
              <button
                type="button"
                onClick={handleDeleteAll}
                disabled={isDeleting}
                className="confirm-yes-btn"
              >
                {isDeleting ? "Deleting..." : "Yes, Delete"}
              </button>
              <button
                type="button"
                onClick={() => setConfirmDeleteAll(false)}
                disabled={isDeleting}
                className="confirm-cancel-btn"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </header>

      {/* 2. CHAT CONVERSATION AREA */}
      <div className="chat-conversation-area">
          {/* MESSAGES SCROLL CONTAINER */}
          <div className="messages-scroll-viewport">
            <div className="messages-inner-thread">
              {/* EMPTY CHAT STATE */}
              {messages.length === 0 && (
                <div className="empty-chat-state">
                  <div className="empty-chat-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.8">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                  </div>
                  <p className="empty-chat-hint">Ask a question below to start analyzing case evidence and documents.</p>
                </div>
              )}

              {/* MESSAGES LIST */}
              {messages.map((msg, index) => {
                const isUser = msg.role === "user";
                const refDocs = msg.referencedDocs || [];

                if (isUser) {
                  return (
                    <div key={`${msg.role}-${index}`} className="message-row user-row">
                      <div className="user-bubble-container">
                        <button
                          type="button"
                          className="msg-del-icon-btn"
                          onClick={() => handleDeleteSingleMessage(msg.id, index)}
                          title="Delete message"
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                        <div className="user-bubble">
                          <div className="user-bubble-text">{msg.content}</div>
                          {msg.timestamp && <span className="user-bubble-time">{msg.timestamp}</span>}
                        </div>
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={`${msg.role}-${index}`} className="message-row assistant-row">
                    <div className="assistant-avatar">
                      <CrimeLensLogo size={28} iconSize={15} withBadge={true} />
                    </div>
                    <div className="assistant-bubble">
                      {/* BUBBLE CONTENT */}
                      <div className="bubble-body">
                        {renderFormattedContent(msg.content)}
                      </div>

                      {/* REFERENCED DOCUMENTS FOOTER */}
                      {refDocs.length > 0 && (
                        <div className="bubble-evidence-footer">
                          <div className="evidence-header-label">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.5">
                              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                            </svg>
                            <span>EVIDENTIARY CITATIONS:</span>
                          </div>
                          <div className="evidence-pills-wrap">
                            {refDocs.map((doc, dIdx) => {
                              const isPdf = (doc.filename || "").toLowerCase().endsWith(".pdf");
                              return (
                                <div key={doc.id || dIdx} className="doc-cite-pill" title={`SHA-256: ${doc.sha256_hash || "Verified"}`}>
                                  <span className={`cite-type-tag ${isPdf ? "tag-pdf" : "tag-doc"}`}>
                                    {isPdf ? "PDF" : "FILE"}
                                  </span>
                                  <span className="cite-filename">{doc.filename}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* ASSISTANT ACTIONS FOOTER */}
                      <div className="assistant-bottom-bar">
                        {msg.timestamp && <span className="bubble-time">{msg.timestamp}</span>}
                        <div className="assistant-actions-group">
                          <button
                            type="button"
                            className="copy-btn"
                            onClick={() => handleCopyMessage(msg.content, index)}
                            title="Copy response"
                          >
                            {copiedIndex === index ? (
                              <>
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.5">
                                  <polyline points="20 6 9 17 4 12" />
                                </svg>
                                <span style={{ color: "#059669" }}>Copied</span>
                              </>
                            ) : (
                              <>
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                </svg>
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                          <button
                            type="button"
                            className="msg-del-action-btn"
                            onClick={() => handleDeleteSingleMessage(msg.id, index)}
                            title="Delete this message"
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                              <polyline points="3 6 5 6 21 6" />
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            </svg>
                            <span>Delete</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* ANALYZING STATE */}
              {isQuerying && (
                <div className="message-row assistant-row">
                  <div className="assistant-avatar">
                    <CrimeLensLogo size={28} iconSize={15} withBadge={true} />
                  </div>
                  <div className="assistant-bubble analyzing-bubble">
                    <div className="analyzing-content">
                      <div className="radar-pulse-dots">
                        <span className="pulse-dot dot-1" />
                        <span className="pulse-dot dot-2" />
                        <span className="pulse-dot dot-3" />
                      </div>
                      <span className="analyzing-text">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>
          </div>

          {/* 3. CHATGPT-LIKE FLOATING BOTTOM COMPOSER */}
          <div className="chat-composer-dock">
            <div className="composer-container-card">
              <div className="composer-input-row">
                <textarea
                  ref={textareaRef}
                  value={inputQuery}
                  onChange={handleTextareaInput}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about this case..."
                  disabled={isQuerying}
                  rows={1}
                  className="composer-textarea"
                />

                <button
                  type="button"
                  onClick={() => handleSendMessage()}
                  disabled={isQuerying || !inputQuery.trim()}
                  className="send-message-btn"
                  title="Send message (Enter)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              </div>

              <div className="composer-footer-hint">
                <span>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for new line</span>
                <span className="hint-separator">•</span>
                <span>Grounds strictly on case evidence & document dossiers</span>
              </div>
            </div>
          </div>
        </div>

      <style jsx>{`
        .investigator-chat-workspace {
          display: flex;
          flex-direction: column;
          width: 100%;
          height: calc(100vh - 105px);
          min-height: 600px;
          background: #f8fafc;
          border-radius: 16px;
          border: 1px solid #e2e8f0;
          overflow: hidden;
          box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
        }

        /* 1. TOP HEADER */
        .chat-top-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.95rem 1.4rem;
          background: #ffffff;
          border-bottom: 1px solid #e2e8f0;
          flex-shrink: 0;
          gap: 1rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        }

        .header-left-col {
          display: flex;
          align-items: center;
        }

        .header-branding-row {
          display: flex;
          align-items: center;
          gap: 0.85rem;
        }

        .header-titles {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .header-title-row {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex-wrap: wrap;
        }

        .workspace-main-title {
          font-size: 1.05rem;
          font-weight: 800;
          color: #0f172a;
          margin: 0;
          letter-spacing: -0.02em;
        }

        .header-right-col {
          display: flex;
          align-items: center;
          gap: 0.65rem;
        }

        .delete-chat-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          padding: 0.45rem 0.85rem;
          background: #ffffff;
          border: 1.5px solid #dc2626;
          border-radius: 8px;
          font-size: 0.78rem;
          font-weight: 700;
          color: #dc2626;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .delete-chat-btn:hover {
          background: #dc2626;
          color: #ffffff;
          border-color: #b91c1c;
        }

        .confirm-delete-box {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: #ffffff;
          border: 1.5px solid #b91c1c;
          padding: 0.3rem 0.6rem;
          border-radius: 8px;
        }

        .confirm-text {
          font-size: 0.76rem;
          font-weight: 700;
          color: #991b1b;
        }

        .confirm-yes-btn {
          padding: 0.35rem 0.75rem;
          background: #dc2626;
          border: 1px solid #b91c1c;
          border-radius: 6px;
          font-size: 0.74rem;
          font-weight: 700;
          color: #ffffff;
          cursor: pointer;
          transition: background 0.15s ease;
        }

        .confirm-yes-btn:hover {
          background: #b91c1c;
        }

        .confirm-cancel-btn {
          padding: 0.35rem 0.75rem;
          background: #f1f5f9;
          border: 1px solid #94a3b8;
          border-radius: 6px;
          font-size: 0.74rem;
          font-weight: 700;
          color: #334155;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .confirm-cancel-btn:hover {
          background: #e2e8f0;
          color: #0f172a;
        }

        /* 2. CHAT AREA */
        .chat-conversation-area {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          position: relative;
        }

        .messages-scroll-viewport {
          flex: 1;
          overflow-y: auto;
          padding: 1.25rem 1.5rem;
          display: flex;
          flex-direction: column;
        }

        .messages-inner-thread {
          width: 100%;
          max-width: 900px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 1.4rem;
        }

        /* EMPTY CHAT STATE */
        .empty-chat-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          margin: auto;
          padding: 4rem 1.5rem;
          text-align: center;
        }

        .empty-chat-icon {
          width: 56px;
          height: 56px;
          border-radius: 16px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 0.85rem;
        }

        .empty-chat-hint {
          font-size: 0.88rem;
          color: #64748b;
          margin: 0;
          max-width: 400px;
          line-height: 1.5;
        }

        /* MESSAGES */
        .message-row {
          display: flex;
          width: 100%;
        }

        .user-row {
          justify-content: flex-end;
        }

        .user-bubble-container {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          max-width: 80%;
          justify-content: flex-end;
        }

        .msg-del-icon-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 26px;
          height: 26px;
          background: #ffffff;
          border: 1.5px solid #cbd5e1;
          border-radius: 6px;
          color: #64748b;
          cursor: pointer;
          transition: all 0.15s ease;
          flex-shrink: 0;
          opacity: 0;
        }

        .user-row:hover .msg-del-icon-btn {
          opacity: 1;
        }

        .msg-del-icon-btn:hover {
          background: #dc2626;
          color: #ffffff;
          border-color: #b91c1c;
        }

        .user-bubble {
          background: #2563eb;
          color: #ffffff;
          padding: 0.75rem 1.15rem;
          border-radius: 18px 18px 4px 18px;
          max-width: 100%;
          box-shadow: 0 2px 8px rgba(37, 99, 235, 0.18);
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.25rem;
        }

        .user-bubble-text {
          font-size: 0.94rem;
          line-height: 1.5;
          color: #ffffff;
          word-break: break-word;
          white-space: pre-wrap;
          text-align: left;
        }

        .user-bubble-time {
          font-size: 0.65rem;
          color: #e0e7ff;
          font-family: 'JetBrains Mono', monospace;
        }

        .assistant-row {
          justify-content: flex-start;
          display: flex;
          align-items: flex-start;
          gap: 0.7rem;
        }

        .assistant-avatar {
          width: 30px;
          height: 30px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .assistant-bubble {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          color: #0f172a;
          border-radius: 4px 18px 18px 18px;
          padding: 1.1rem 1.35rem;
          max-width: 90%;
          box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .assistant-bottom-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-top: 0.45rem;
          border-top: 1px solid #f1f5f9;
          margin-top: 0.2rem;
        }

        .assistant-actions-group {
          display: flex;
          align-items: center;
          gap: 0.45rem;
        }

        .bubble-time {
          font-size: 0.68rem;
          color: #94a3b8;
          font-family: 'JetBrains Mono', monospace;
        }

        .copy-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.3rem;
          padding: 0.2rem 0.5rem;
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-size: 0.68rem;
          font-weight: 600;
          color: #475569;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .copy-btn:hover {
          background: #f1f5f9;
          border-color: #94a3b8;
          color: #0f172a;
        }

        .msg-del-action-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.3rem;
          padding: 0.2rem 0.5rem;
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          font-size: 0.68rem;
          font-weight: 600;
          color: #64748b;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .msg-del-action-btn:hover {
          background: #dc2626;
          color: #ffffff;
          border-color: #b91c1c;
        }

        .bubble-body {
          font-size: 0.9rem;
          line-height: 1.65;
        }

        .user-bubble .bubble-body {
          color: #ffffff;
        }

        .msg-h2 {
          font-size: 1.05rem;
          font-weight: 800;
          margin: 0.85rem 0 0.4rem;
          color: #0f172a;
          letter-spacing: -0.01em;
        }

        .msg-h3 {
          font-size: 0.95rem;
          font-weight: 750;
          margin: 0.75rem 0 0.3rem;
          color: #1e293b;
        }

        .msg-paragraph {
          margin: 0.4rem 0;
          color: inherit;
        }

        .msg-bullet-item {
          display: flex;
          align-items: flex-start;
          gap: 0.5rem;
          margin: 0.35rem 0;
        }

        .bullet-dot {
          color: #2563eb;
          font-weight: 900;
        }

        .msg-numbered-item {
          display: flex;
          align-items: flex-start;
          gap: 0.5rem;
          margin: 0.35rem 0;
        }

        .number-badge {
          font-family: 'JetBrains Mono', monospace;
          font-weight: 700;
          color: #2563eb;
          font-size: 0.85rem;
        }

        .msg-code {
          background: #f1f5f9;
          border: 1px solid #cbd5e1;
          border-radius: 4px;
          padding: 0.1rem 0.35rem;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.82rem;
          color: #0f172a;
        }

        .user-bubble .msg-code {
          background: rgba(255, 255, 255, 0.2);
          border-color: rgba(255, 255, 255, 0.3);
          color: #ffffff;
        }

        .msg-spacer {
          height: 0.5rem;
        }

        /* EVIDENCE FOOTER IN MESSAGE */
        .bubble-evidence-footer {
          margin-top: 0.5rem;
          padding-top: 0.65rem;
          border-top: 1px solid #f1f5f9;
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
        }

        .evidence-header-label {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          font-size: 0.68rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          color: #64748b;
          font-family: 'JetBrains Mono', monospace;
        }

        .evidence-pills-wrap {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .doc-cite-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.2rem 0.55rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          font-size: 0.74rem;
          color: #334155;
        }

        .cite-type-tag {
          font-size: 0.62rem;
          font-weight: 800;
          padding: 0.05rem 0.3rem;
          border-radius: 3px;
          font-family: 'JetBrains Mono', monospace;
        }

        .tag-pdf {
          background: #fee2e2;
          color: #dc2626;
        }

        .tag-doc {
          background: #eff6ff;
          color: #2563eb;
        }

        .cite-filename {
          font-weight: 600;
        }

        /* ANALYZING STATE */
        .analyzing-bubble {
          border-left: 3px solid #2563eb;
          background: #ffffff;
        }

        .analyzing-content {
          display: flex;
          align-items: center;
          gap: 0.85rem;
          padding: 0.5rem 0;
        }

        .radar-pulse-dots {
          display: flex;
          align-items: center;
          gap: 0.3rem;
        }

        .pulse-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #2563eb;
          animation: dot-pulse-anim 1.4s ease infinite;
        }

        .dot-1 { animation-delay: 0s; }
        .dot-2 { animation-delay: 0.25s; }
        .dot-3 { animation-delay: 0.5s; }

        @keyframes dot-pulse-anim {
          0%, 100% { transform: scale(0.7); opacity: 0.4; }
          50% { transform: scale(1.2); opacity: 1; }
        }

        .analyzing-text {
          font-size: 0.85rem;
          color: #475569;
          font-style: italic;
        }

        /* 3. FLOATING BOTTOM COMPOSER */
        .chat-composer-dock {
          padding: 0.85rem 1.5rem 1.15rem;
          background: linear-gradient(180deg, rgba(248, 250, 252, 0) 0%, rgba(248, 250, 252, 0.92) 25%, #f8fafc 100%);
          display: flex;
          justify-content: center;
          flex-shrink: 0;
        }

        .composer-container-card {
          width: 100%;
          max-width: 860px;
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-radius: 18px;
          padding: 0.65rem 0.95rem;
          box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.08);
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
          transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .composer-container-card:focus-within {
          border-color: #2563eb;
          box-shadow: 0 4px 24px -2px rgba(37, 99, 235, 0.16);
        }



        .chip-btn {
          white-space: nowrap;
          display: inline-flex;
          align-items: center;
          gap: 0.3rem;
          padding: 0.25rem 0.6rem;
          background: #f1f5f9;
          border: 1px solid #e2e8f0;
          border-radius: 9999px;
          font-size: 0.72rem;
          font-weight: 600;
          color: #475569;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .chip-btn:hover {
          background: #e2e8f0;
          color: #0f172a;
          border-color: #cbd5e1;
        }

        .composer-input-row {
          display: flex;
          align-items: flex-end;
          gap: 0.65rem;
        }

        .composer-textarea {
          flex: 1;
          border: none;
          outline: none;
          resize: none;
          padding: 0.45rem 0.25rem;
          font-family: inherit;
          font-size: 0.92rem;
          line-height: 1.5;
          color: #0f172a;
          background: transparent;
          max-height: 160px;
        }

        .composer-textarea::placeholder {
          color: #94a3b8;
        }

        .send-message-btn {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: #2563eb;
          border: none;
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
          flex-shrink: 0;
          margin-bottom: 2px;
        }

        .send-message-btn:hover:not(:disabled) {
          background: #1d4ed8;
          transform: scale(1.05);
        }

        .send-message-btn:disabled {
          background: #cbd5e1;
          color: #94a3b8;
          cursor: not-allowed;
        }

        .composer-footer-hint {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          font-size: 0.68rem;
          color: #94a3b8;
          padding-top: 0.15rem;
        }

        .hint-separator {
          opacity: 0.5;
        }

        @media (max-width: 768px) {
          .chat-top-header {
            flex-direction: column;
            align-items: flex-start;
          }
          .header-right-col {
            width: 100%;
            justify-content: space-between;
          }
          .message-bubble {
            max-width: 95%;
          }
        }
      `}</style>
    </div>
  );
}
