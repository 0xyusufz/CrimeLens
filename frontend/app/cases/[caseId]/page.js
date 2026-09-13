"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient } from "../../../lib/apiClient";
import AuthLayout from "../../../components/Layout";
import Spinner from "../../../components/Spinner";
import ErrorMessage from "../../../components/ErrorMessage";

export default function CaseDetails() {
  const { caseId } = useParams();
  const router = useRouter();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!caseId) return;

    const fetchCaseDetails = async () => {
      try {
        const data = await apiClient(`/api/cases/${caseId}`);
        setCaseData(data);
      } catch (err) {
        setError(err.message || "Failed to load case details.");
      } finally {
        setLoading(false);
      }
    };
    fetchCaseDetails();
  }, [caseId]);

  const getStatusColor = (status) => {
    switch (status) {
      case "OPEN": return "var(--warning)";
      case "CLOSED": return "var(--success)";
      case "ARCHIVED": return "var(--text-muted)";
      default: return "var(--primary)";
    }
  };

  return (
    <AuthLayout>
      <div className="container">
        <Link href="/" className="back-link mb-4 flex items-center text-sm text-muted hover-text-primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          Back to Dashboard
        </Link>

        <ErrorMessage message={error} />

        {loading ? (
          <Spinner />
        ) : !caseData ? (
          <div className="card p-6 text-center text-muted">
            Case not found or access denied.
          </div>
        ) : (
          <div className="case-details">
            <header className="case-header card mb-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h1 className="text-2xl font-bold mb-2">{caseData.title}</h1>
                  <p className="text-muted">ID: <span className="font-mono text-xs">{caseData.id}</span></p>
                </div>
                <span 
                  className="case-status" 
                  style={{ 
                    backgroundColor: `${getStatusColor(caseData.status)}20`,
                    color: getStatusColor(caseData.status),
                    border: `1px solid ${getStatusColor(caseData.status)}40`
                  }}
                >
                  {caseData.status}
                </span>
              </div>
              <div className="case-meta text-sm flex gap-4 text-muted mb-6">
                <div>
                  <strong>Created:</strong> {new Date(caseData.created_at).toLocaleString()}
                </div>
                {caseData.updated_at && (
                  <div>
                    <strong>Updated:</strong> {new Date(caseData.updated_at).toLocaleString()}
                  </div>
                )}
              </div>
              
              <h3 className="font-semibold mb-2">Description</h3>
              <p className="case-description bg-surface-hover p-4 rounded text-sm leading-relaxed">
                {caseData.description || "No description provided."}
              </p>
            </header>

            <div className="modules-grid">
              <div className="card text-center opacity-50 p-6">
                <h3 className="font-semibold mb-2">Graph Analysis</h3>
                <p className="text-sm text-muted">Graph visualization is not implemented yet.</p>
              </div>
              <div className="card text-center opacity-50 p-6">
                <h3 className="font-semibold mb-2">Intelligence Insights</h3>
                <p className="text-sm text-muted">Insights module is not implemented yet.</p>
              </div>
              <div className="card text-center opacity-50 p-6">
                <h3 className="font-semibold mb-2">Evidence Ledger</h3>
                <p className="text-sm text-muted">Ledger view is not implemented yet.</p>
              </div>
              <div className="card text-center opacity-50 p-6">
                <h3 className="font-semibold mb-2">Audit Trail</h3>
                <p className="text-sm text-muted">Audit logs are not implemented yet.</p>
              </div>
            </div>
          </div>
        )}
      </div>
      <style>{`
        .back-link {
          display: inline-flex;
          align-items: center;
          transition: color 0.2s;
        }
        .hover-text-primary:hover {
          color: var(--primary);
        }
        .case-status {
          font-size: 0.875rem;
          font-weight: 600;
          padding: 0.25rem 0.75rem;
          border-radius: 999px;
        }
        .font-mono {
          font-family: monospace;
        }
        .bg-surface-hover {
          background-color: var(--background);
          border: 1px solid var(--border);
        }
        .rounded {
          border-radius: 6px;
        }
        .leading-relaxed {
          line-height: 1.6;
        }
        .modules-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 1rem;
        }
        .opacity-50 { opacity: 0.5; }
        .mr-1 { margin-right: 0.25rem; }
      `}</style>
    </AuthLayout>
  );
}
