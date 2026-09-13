"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { apiClient } from "../lib/apiClient";
import AuthLayout from "../components/Layout";

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorState, setErrorState] = useState(null);

  const fetchCases = useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setErrorState(null);

    try {
      const data = await apiClient("/api/cases");
      setCases(Array.isArray(data) ? data : []);
    } catch (err) {
      if (err?.status === 403) {
        setErrorState({
          type: "403",
          title: "Clearance Restriction (403)",
          message: "You lack authorized security clearance to view case files in this jurisdiction.",
        });
      } else if (err?.status === 401) {
        // Handled by apiClient: automatic logout and redirect
      } else {
        setErrorState({
          type: "api_error",
          title: "System Synchronization Error",
          message: "Unable to retrieve case intelligence files from the backend service.",
        });
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const formatDate = (dateString) => {
    if (!dateString) return "Unknown";
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateString;
    }
  };

  return (
    <AuthLayout>
      <div className="dashboard-container">
        {/* MAIN TITLE BAR */}
        <div className="dashboard-header-bar">
          <div className="dashboard-title-group">
            <div className="title-with-badge">
              <h1 className="dashboard-title">Cases</h1>
              {!loading && !errorState && (
                <span className="case-count-badge">
                  {cases.length} {cases.length === 1 ? "case" : "cases"} accessible
                </span>
              )}
            </div>
            <p className="dashboard-subtitle">
              Accessible intelligence files and active investigation records across authorized jurisdictions.
            </p>
          </div>

          <div className="dashboard-actions">
            <button
              onClick={() => fetchCases(true)}
              className="action-btn refresh-btn"
              disabled={loading || refreshing}
              title="Refresh case repository"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`refresh-icon ${refreshing ? "spinning" : ""}`}
              >
                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
              </svg>
              <span>{refreshing ? "Synchronizing..." : "Refresh"}</span>
            </button>
          </div>
        </div>

        {/* ERROR STATE */}
        {errorState && (
          <div className={`status-banner ${errorState.type === "403" ? "banner-warning" : "banner-error"}`}>
            <div className="banner-icon-container">
              {errorState.type === "403" ? (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              ) : (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              )}
            </div>
            <div className="banner-content">
              <h3 className="banner-title">{errorState.title}</h3>
              <p className="banner-desc">{errorState.message}</p>
            </div>
            <button onClick={() => fetchCases(true)} className="banner-retry-btn">
              Retry
            </button>
          </div>
        )}

        {/* LOADING STATE */}
        {loading && (
          <div className="loading-state-wrapper">
            <div className="loading-radar-ring">
              <div className="loading-radar-pulse" />
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="radar-icon">
                <circle cx="16" cy="16" r="14" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.5" />
                <circle cx="16" cy="16" r="8" stroke="#0ea5e9" strokeWidth="1.5" opacity="0.8" />
                <circle cx="16" cy="16" r="3" fill="#38bdf8" />
              </svg>
            </div>
            <p className="loading-text">Synchronizing authorized investigation records...</p>
          </div>
        )}

        {/* EMPTY STATE */}
        {!loading && !errorState && cases.length === 0 && (
          <div className="empty-state-card">
            <div className="empty-icon-wrap">
              <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                <line x1="12" y1="11" x2="12" y2="17" />
                <line x1="9" y1="14" x2="15" y2="14" />
              </svg>
            </div>
            <h3 className="empty-title">No Investigation Cases</h3>
            <p className="empty-subtitle">
              There are currently no active or archived cases assigned to your investigator clearance profile.
            </p>
            <button onClick={() => fetchCases(true)} className="empty-action-btn">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
              </svg>
              <span>Refresh Workspace</span>
            </button>
          </div>
        )}

        {/* CASE CARDS GRID */}
        {!loading && !errorState && cases.length > 0 && (
          <div className="cases-grid">
            {cases.map((c) => {
              const isOpen = c.status === "OPEN";
              return (
                <Link href={`/cases/${c.id}`} key={c.id} className="case-card-link">
                  <article className={`case-card ${isOpen ? "case-card-open" : "case-card-closed"}`}>
                    {/* CARD TOP META */}
                    <div className="card-top-row">
                      <span className="case-number-badge" title="Unique Case Identifier">
                        {c.case_number}
                      </span>
                      <span
                        className={`status-pill ${isOpen ? "status-pill-open" : "status-pill-closed"}`}
                      >
                        <span className={`status-dot ${isOpen ? "status-dot-open" : "status-dot-closed"}`} />
                        {isOpen ? "OPEN" : "CLOSED"}
                      </span>
                    </div>

                    {/* TITLE */}
                    <h2 className="case-card-title">{c.title}</h2>

                    {/* DESCRIPTION (if present or fallback) */}
                    <p className="case-card-description">
                      {c.description ? c.description : "Investigation file registered in intelligence repository."}
                    </p>

                    {/* CARD FOOTER META */}
                    <div className="card-bottom-row">
                      <div className="case-timestamp">
                        <svg
                          width="13"
                          height="13"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <circle cx="12" cy="12" r="10" />
                          <polyline points="12 6 12 12 16 14" />
                        </svg>
                        <span>{formatDate(c.created_at)}</span>
                      </div>
                      <span className="open-case-indicator">
                        <span>Details</span>
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="arrow-icon"
                        >
                          <line x1="5" y1="12" x2="19" y2="12" />
                          <polyline points="12 5 19 12 12 19" />
                        </svg>
                      </span>
                    </div>
                  </article>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      <style>{`
        .dashboard-container {
          max-width: 1280px;
          margin: 0 auto;
          padding: 2.25rem 1.5rem 3.5rem;
        }

        /* HEADER BAR */
        .dashboard-header-bar {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1.5rem;
          margin-bottom: 2.25rem;
          padding-bottom: 1.5rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }

        .dashboard-title-group {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }

        .title-with-badge {
          display: flex;
          align-items: center;
          gap: 0.85rem;
          flex-wrap: wrap;
        }

        .dashboard-title {
          font-size: 1.85rem;
          font-weight: 700;
          letter-spacing: -0.025em;
          color: #f8fafc;
          line-height: 1.15;
        }

        .case-count-badge {
          font-size: 0.75rem;
          font-weight: 600;
          color: #38bdf8;
          background: rgba(14, 165, 233, 0.12);
          border: 1px solid rgba(56, 189, 248, 0.25);
          border-radius: 9999px;
          padding: 0.2rem 0.65rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          letter-spacing: 0.02em;
        }

        .dashboard-subtitle {
          font-size: 0.9rem;
          color: #94a3b8;
          line-height: 1.45;
          max-width: 620px;
        }

        .dashboard-actions {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .action-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.55rem 1rem;
          border-radius: 8px;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .refresh-btn {
          background: rgba(15, 23, 42, 0.75);
          border: 1px solid rgba(56, 189, 248, 0.2);
          color: #e2e8f0;
        }

        .refresh-btn:hover:not(:disabled) {
          background: rgba(30, 41, 59, 0.85);
          border-color: rgba(56, 189, 248, 0.4);
          color: #38bdf8;
        }

        .refresh-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .refresh-icon.spinning {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        /* STATUS BANNER (ERRORS / 403) */
        .status-banner {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem 1.25rem;
          border-radius: 10px;
          margin-bottom: 2rem;
        }

        .banner-warning {
          background: rgba(245, 158, 11, 0.08);
          border: 1px solid rgba(245, 158, 11, 0.3);
          color: #fbbf24;
        }

        .banner-error {
          background: rgba(239, 68, 68, 0.08);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #f87171;
        }

        .banner-icon-container {
          flex-shrink: 0;
        }

        .banner-content {
          flex: 1;
        }

        .banner-title {
          font-size: 0.9rem;
          font-weight: 700;
          margin-bottom: 0.15rem;
        }

        .banner-desc {
          font-size: 0.82rem;
          color: #cbd5e1;
        }

        .banner-retry-btn {
          padding: 0.4rem 0.85rem;
          border-radius: 6px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          color: #ffffff;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.15s ease;
        }

        .banner-retry-btn:hover {
          background: rgba(255, 255, 255, 0.2);
        }

        /* LOADING STATE */
        .loading-state-wrapper {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 5rem 2rem;
          text-align: center;
        }

        .loading-radar-ring {
          position: relative;
          width: 72px;
          height: 72px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 1.25rem;
        }

        .loading-radar-pulse {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          background: rgba(14, 165, 233, 0.15);
          animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
        }

        @keyframes ping {
          75%, 100% {
            transform: scale(1.6);
            opacity: 0;
          }
        }

        .radar-icon {
          position: relative;
          z-index: 2;
        }

        .loading-text {
          font-size: 0.88rem;
          color: #94a3b8;
          letter-spacing: 0.02em;
        }

        /* EMPTY STATE */
        .empty-state-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 4.5rem 2rem;
          background: rgba(11, 16, 27, 0.6);
          border: 1px dashed rgba(56, 189, 248, 0.2);
          border-radius: 12px;
          text-align: center;
        }

        .empty-icon-wrap {
          color: #0ea5e9;
          margin-bottom: 1.25rem;
          opacity: 0.85;
        }

        .empty-title {
          font-size: 1.15rem;
          font-weight: 700;
          color: #f1f5f9;
          margin-bottom: 0.35rem;
        }

        .empty-subtitle {
          font-size: 0.86rem;
          color: #94a3b8;
          max-width: 440px;
          line-height: 1.5;
          margin-bottom: 1.5rem;
        }

        .empty-action-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.55rem 1.15rem;
          background: rgba(14, 165, 233, 0.12);
          border: 1px solid rgba(56, 189, 248, 0.3);
          border-radius: 8px;
          color: #38bdf8;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .empty-action-btn:hover {
          background: rgba(14, 165, 233, 0.2);
          border-color: rgba(56, 189, 248, 0.5);
          color: #7dd3fc;
        }

        /* CASE GRID */
        .cases-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 1.5rem;
        }

        .case-card-link {
          text-decoration: none;
          display: block;
        }

        .case-card {
          background: rgba(15, 23, 42, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 1.4rem;
          display: flex;
          flex-direction: column;
          gap: 0.85rem;
          min-height: 195px;
          transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
          position: relative;
          overflow: hidden;
        }

        .case-card::before {
          content: "";
          position: absolute;
          top: 0;
          left: 0;
          width: 3px;
          height: 100%;
          transition: background 0.2s ease;
        }

        .case-card-open::before {
          background: #0ea5e9;
        }

        .case-card-closed::before {
          background: #475569;
        }

        .case-card:hover {
          transform: translateY(-3px);
          background: rgba(22, 33, 58, 0.8);
          border-color: rgba(56, 189, 248, 0.35);
          box-shadow:
            0 10px 25px -5px rgba(0, 0, 0, 0.4),
            0 0 20px -5px rgba(14, 165, 233, 0.15);
        }

        /* CARD TOP ROW */
        .card-top-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 0.75rem;
        }

        .case-number-badge {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          color: #38bdf8;
          background: rgba(14, 165, 233, 0.09);
          border: 1px solid rgba(56, 189, 248, 0.2);
          border-radius: 5px;
          padding: 0.2rem 0.5rem;
        }

        /* STATUS PILLS */
        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.7rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          padding: 0.2rem 0.55rem;
          border-radius: 9999px;
          text-transform: uppercase;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .status-pill-open {
          background: rgba(16, 185, 129, 0.12);
          color: #34d399;
          border: 1px solid rgba(52, 211, 153, 0.3);
        }

        .status-pill-closed {
          background: rgba(148, 163, 184, 0.1);
          color: #94a3b8;
          border: 1px solid rgba(148, 163, 184, 0.25);
        }

        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
        }

        .status-dot-open {
          background-color: #10b981;
          box-shadow: 0 0 6px #10b981;
        }

        .status-dot-closed {
          background-color: #64748b;
        }

        /* CARD TITLE */
        .case-card-title {
          font-size: 1.1rem;
          font-weight: 600;
          color: #f1f5f9;
          line-height: 1.35;
          letter-spacing: -0.01em;
          margin: 0;
          transition: color 0.15s ease;
        }

        .case-card:hover .case-card-title {
          color: #38bdf8;
        }

        /* CARD DESCRIPTION */
        .case-card-description {
          font-size: 0.83rem;
          color: #94a3b8;
          line-height: 1.5;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          margin-bottom: auto;
        }

        /* CARD FOOTER */
        .card-bottom-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 0.85rem;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
          font-size: 0.74rem;
          color: #64748b;
        }

        .case-timestamp {
          display: flex;
          align-items: center;
          gap: 0.35rem;
        }

        .open-case-indicator {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          color: #0ea5e9;
          font-weight: 600;
          transition: transform 0.15s ease;
        }

        .case-card:hover .open-case-indicator {
          transform: translateX(3px);
          color: #38bdf8;
        }

        .arrow-icon {
          transition: transform 0.15s ease;
        }

        @media (max-width: 768px) {
          .dashboard-header-bar {
            flex-direction: column;
            align-items: stretch;
          }
          .cases-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </AuthLayout>
  );
}

