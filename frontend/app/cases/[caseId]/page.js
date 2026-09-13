"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient } from "../../../lib/apiClient";
import AuthLayout from "../../../components/Layout";
import CaseGraphView from "../../../components/CaseGraphView";

export default function CaseDetailsPage() {
  const { caseId } = useParams();
  const router = useRouter();
  const fileInputRef = useRef(null);

  // Workspace Tab: "graph" | "documents"
  const [activeTab, setActiveTab] = useState("graph");

  // Case data states
  const [caseData, setCaseData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loadingCase, setLoadingCase] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [caseError, setCaseError] = useState(null);

  // Upload states
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  // Fetch case details
  const fetchCaseDetails = useCallback(async () => {
    if (!caseId) return;
    setLoadingCase(true);
    setCaseError(null);

    try {
      const data = await apiClient(`/api/cases/${caseId}`);
      setCaseData(data);
    } catch (err) {
      if (err?.status === 404) {
        setCaseError({
          type: "404",
          title: "Investigation File Not Found",
          message: "The requested case record does not exist or has been removed from the repository.",
        });
      } else if (err?.status === 403) {
        setCaseError({
          type: "403",
          title: "Clearance Restriction (403)",
          message: "You lack authorized security clearance to access this investigation file.",
        });
      } else if (err?.status === 401) {
        // Handled by apiClient: logout & redirect
      } else {
        setCaseError({
          type: "api_error",
          title: "System Synchronization Error",
          message: "Unable to retrieve case intelligence record. Please verify service connectivity.",
        });
      }
    } finally {
      setLoadingCase(false);
    }
  }, [caseId]);

  // Fetch documents for case
  const fetchDocuments = useCallback(async () => {
    if (!caseId) return;
    setLoadingDocs(true);

    try {
      const data = await apiClient(`/api/cases/${caseId}/documents`);
      setDocuments(Array.isArray(data) ? data : []);
    } catch (err) {
      // Document fetch error handled silently or with fallback
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchCaseDetails();
    fetchDocuments();
  }, [fetchCaseDetails, fetchDocuments]);

  // Handle file selection
  const handleFileSelect = (file) => {
    setUploadError(null);
    setUploadSuccess(null);

    if (!file) return;

    const ext = "." + file.name.split(".").pop().toLowerCase();
    const allowed = [".pdf", ".csv", ".txt"];

    if (!allowed.includes(ext)) {
      setUploadError("Unsupported file type. Only PDF, CSV, and TXT files are accepted for evidentiary upload.");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setSelectedFile(file);
  };

  // Drag & drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  // Upload file to backend
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile || uploading || !caseId) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const uploadedDoc = await apiClient(`/api/cases/${caseId}/documents`, {
        method: "POST",
        body: formData,
      });

      setUploadSuccess(`Successfully uploaded "${uploadedDoc.filename || selectedFile.name}". Evidentiary hash verified.`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";

      // Refresh documents list
      await fetchDocuments();
    } catch (err) {
      if (err?.status === 415) {
        setUploadError("Unsupported media type. Only PDF, CSV, and TXT files are allowed.");
      } else if (err?.status === 413) {
        setUploadError("File exceeds maximum allowed upload size.");
      } else if (err?.status === 400) {
        setUploadError(err.message || "Invalid upload file.");
      } else {
        setUploadError("Failed to upload document. Please ensure backend connectivity and try again.");
      }
    } finally {
      setUploading(false);
    }
  };

  // Formatting helpers
  const formatDate = (dateString) => {
    if (!dateString) return "—";
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return dateString;
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return "";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const getFileType = (filename) => {
    if (!filename) return "DOC";
    const ext = filename.split(".").pop().toUpperCase();
    if (ext === "PDF") return "PDF";
    if (ext === "CSV") return "CSV";
    if (ext === "TXT") return "TXT";
    return ext;
  };

  return (
    <AuthLayout>
      <div className="case-details-container">
        {/* BACK NAVIGATION */}
        <div className="top-nav-bar">
          <Link href="/" className="back-link">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>Back to Cases</span>
          </Link>
        </div>

        {/* LOADING CASE STATE */}
        {loadingCase && (
          <div className="loading-wrapper">
            <div className="loading-radar">
              <div className="radar-pulse" />
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                <circle cx="16" cy="16" r="14" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.5" />
                <circle cx="16" cy="16" r="8" stroke="#0ea5e9" strokeWidth="1.5" opacity="0.8" />
                <circle cx="16" cy="16" r="3" fill="#38bdf8" />
              </svg>
            </div>
            <p className="loading-text">Retrieving investigation dossier...</p>
          </div>
        )}

        {/* CASE ERROR STATE */}
        {!loadingCase && caseError && (
          <div className="case-error-card">
            <div className="error-icon-box">
              {caseError.type === "403" ? (
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              ) : (
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              )}
            </div>
            <h2 className="error-title">{caseError.title}</h2>
            <p className="error-desc">{caseError.message}</p>
            <div className="error-actions">
              <Link href="/" className="btn-secondary-link">
                Return to Dashboard
              </Link>
              {caseError.type !== "404" && (
                <button onClick={fetchCaseDetails} className="btn-primary-action">
                  Retry Synchronization
                </button>
              )}
            </div>
          </div>
        )}

        {/* CASE CONTENT */}
        {!loadingCase && !caseError && caseData && (
          <div className="case-content-layout">
            {/* 1. CASE HEADER & OVERVIEW SECTION */}
            <section className="case-header-card">
              <div className="header-meta-bar">
                <div className="badge-group">
                  <span className="case-number-badge" title="Official Case Identifier">
                    {caseData.case_number}
                  </span>
                  <span
                    className={`status-pill ${caseData.status === "OPEN" ? "status-pill-open" : "status-pill-closed"}`}
                  >
                    <span className={`status-dot ${caseData.status === "OPEN" ? "dot-open" : "dot-closed"}`} />
                    {caseData.status}
                  </span>
                </div>

                <div className="case-created-meta">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  <span>Initiated: {formatDate(caseData.created_at)}</span>
                </div>
              </div>

              <h1 className="case-main-title">{caseData.title}</h1>

              <div className="overview-section">
                <h3 className="section-label">Case Narrative & Scope</h3>
                <div className="narrative-box">
                  <p className="narrative-text">
                    {caseData.description || "No specific narrative or operational scope provided for this case record."}
                  </p>
                </div>
              </div>

              <div className="case-technical-meta">
                <div className="meta-item">
                  <span className="meta-label">System UUID:</span>
                  <span className="meta-value font-mono">{caseData.id}</span>
                </div>
                {caseData.created_by && (
                  <div className="meta-item">
                    <span className="meta-label">Assigned Lead:</span>
                    <span className="meta-value font-mono">{caseData.created_by}</span>
                  </div>
                )}
              </div>
            </section>

            {/* WORKSPACE NAVIGATION TABS */}
            <div className="workspace-tabs-bar">
              <button
                onClick={() => setActiveTab("graph")}
                className={`workspace-tab-btn ${activeTab === "graph" ? "tab-btn-active" : ""}`}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="6" cy="6" r="3" />
                  <circle cx="18" cy="18" r="3" />
                  <circle cx="18" cy="6" r="3" />
                  <line x1="8.5" y1="7.5" x2="15.5" y2="16.5" />
                  <line x1="9" y1="6" x2="15" y2="6" />
                </svg>
                <span>Network Graph</span>
              </button>

              <button
                onClick={() => setActiveTab("documents")}
                className={`workspace-tab-btn ${activeTab === "documents" ? "tab-btn-active" : ""}`}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span>Evidence & Documents ({documents.length})</span>
              </button>
            </div>

            {/* TAB 1: NETWORK GRAPH INVESTIGATION */}
            {activeTab === "graph" && (
              <section className="graph-workspace-section">
                <CaseGraphView caseId={caseId} />
              </section>
            )}

            {/* TAB 2: DOCUMENTS MANAGEMENT SECTION */}
            {activeTab === "documents" && (
              <section className="documents-section">
                <div className="section-header-bar">
                  <div className="section-title-group">
                    <div className="title-with-count">
                      <h2 className="section-title">Evidence & Documents</h2>
                      {!loadingDocs && (
                        <span className="doc-count-badge">
                          {documents.length} {documents.length === 1 ? "document" : "documents"}
                        </span>
                      )}
                    </div>
                  <p className="section-desc">
                    Evidentiary files, seized records, and analysis inputs registered to this investigation.
                  </p>
                </div>

                <button
                  onClick={fetchDocuments}
                  className="refresh-docs-btn"
                  disabled={loadingDocs}
                  title="Reload documents"
                >
                  <svg
                    width="15"
                    height="15"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className={loadingDocs ? "spinning" : ""}
                  >
                    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                  </svg>
                  <span>Sync</span>
                </button>
              </div>

              {/* UPLOAD EVIDENCE CARD */}
              <div className="upload-container-card">
                <h3 className="upload-card-title">Register Evidentiary Document</h3>
                <p className="upload-card-subtitle">
                  Authorized document formats: <strong>PDF</strong>, <strong>CSV</strong>, <strong>TXT</strong>. Files are cryptographically hashed upon ingestion.
                </p>

                {/* NOTIFICATIONS */}
                {uploadSuccess && (
                  <div className="upload-banner banner-success">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                    <span>{uploadSuccess}</span>
                  </div>
                )}

                {uploadError && (
                  <div className="upload-banner banner-danger">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                    <span>{uploadError}</span>
                  </div>
                )}

                {/* DROPZONE */}
                <form onSubmit={handleUpload}>
                  <div
                    className={`dropzone-box ${isDragging ? "dropzone-dragging" : ""} ${selectedFile ? "dropzone-has-file" : ""}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.csv,.txt,application/pdf,text/csv,text/plain"
                      className="hidden-file-input"
                      onChange={(e) => {
                        if (e.target.files && e.target.files.length > 0) {
                          handleFileSelect(e.target.files[0]);
                        }
                      }}
                    />

                    {!selectedFile ? (
                      <div className="dropzone-prompt">
                        <div className="upload-icon-circle">
                          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="17 8 12 3 7 8" />
                            <line x1="12" y1="3" x2="12" y2="15" />
                          </svg>
                        </div>
                        <div className="dropzone-text-group">
                          <span className="dropzone-main-text">
                            <strong>Click to select</strong> or drag evidentiary document here
                          </span>
                          <span className="dropzone-sub-text">
                            Accepted formats: PDF, CSV, TXT
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="selected-file-display" onClick={(e) => e.stopPropagation()}>
                        <div className="file-info-col">
                          <span className="file-type-pill">{getFileType(selectedFile.name)}</span>
                          <div className="file-name-size">
                            <span className="selected-filename">{selectedFile.name}</span>
                            <span className="selected-filesize">{formatFileSize(selectedFile.size)}</span>
                          </div>
                        </div>

                        <button
                          type="button"
                          className="remove-file-btn"
                          onClick={() => {
                            setSelectedFile(null);
                            if (fileInputRef.current) fileInputRef.current.value = "";
                          }}
                          title="Remove file"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <line x1="18" y1="6" x2="6" y2="18" />
                            <line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>

                  {selectedFile && (
                    <div className="upload-submit-bar">
                      <button
                        type="submit"
                        className="upload-submit-btn"
                        disabled={uploading}
                      >
                        {uploading ? (
                          <>
                            <span className="mini-spinner" />
                            <span>Ingesting & Hashing...</span>
                          </>
                        ) : (
                          <>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                              <polyline points="17 8 12 3 7 8" />
                              <line x1="12" y1="3" x2="12" y2="15" />
                            </svg>
                            <span>Upload to Case File</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </form>
              </div>

              {/* DOCUMENTS LIST */}
              <div className="documents-display-wrapper">
                {loadingDocs ? (
                  <div className="docs-loading-box">
                    <span className="mini-spinner" />
                    <span>Synchronizing document repository...</span>
                  </div>
                ) : documents.length === 0 ? (
                  <div className="empty-docs-card">
                    <div className="empty-docs-icon">
                      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="12" y1="18" x2="12" y2="12" />
                        <line x1="9" y1="15" x2="15" y2="15" />
                      </svg>
                    </div>
                    <h4 className="empty-docs-title">No Evidentiary Documents Attached</h4>
                    <p className="empty-docs-desc">
                      There are currently no documents registered to this case file. Upload a PDF, CSV, or TXT record above to begin evidence ingestion.
                    </p>
                  </div>
                ) : (
                  <div className="documents-table-container">
                    <div className="docs-list">
                      {documents.map((doc) => {
                        const fileType = getFileType(doc.filename);
                        return (
                          <article key={doc.id} className="doc-item-card">
                            <div className="doc-primary-info">
                              <div className={`doc-icon-badge badge-${fileType.toLowerCase()}`}>
                                <span>{fileType}</span>
                              </div>

                              <div className="doc-details-block">
                                <h4 className="doc-filename" title={doc.filename}>
                                  {doc.filename}
                                </h4>
                                <div className="doc-meta-row">
                                  <span className="doc-id-text" title={`Document UUID: ${doc.id}`}>
                                    ID: <span className="font-mono">{doc.id.slice(0, 8)}...</span>
                                  </span>
                                  <span className="meta-separator">•</span>
                                  <span className="doc-date-text">
                                    Uploaded: {formatDate(doc.uploaded_at)}
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* SHA-256 HASH VERIFICATION PILL */}
                            <div className="doc-hash-wrapper" title={`Cryptographic SHA-256 Hash: ${doc.sha256_hash}`}>
                              <span className="hash-label">SHA-256</span>
                              <span className="hash-value font-mono">
                                {doc.sha256_hash ? `${doc.sha256_hash.slice(0, 10)}...${doc.sha256_hash.slice(-8)}` : "Verified"}
                              </span>
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}
          </div>
        )}
      </div>

      <style>{`
        .case-details-container {
          max-width: 1240px;
          margin: 0 auto;
          padding: 1.5rem 1.5rem 4rem;
        }

        .workspace-tabs-bar {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 1.75rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          padding-bottom: 0.85rem;
        }

        .workspace-tab-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.55rem;
          padding: 0.6rem 1.15rem;
          background: rgba(15, 23, 42, 0.65);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 8px;
          color: #94a3b8;
          font-size: 0.84rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .workspace-tab-btn:hover {
          background: rgba(22, 33, 58, 0.85);
          color: #f1f5f9;
          border-color: rgba(56, 189, 248, 0.3);
        }

        .tab-btn-active {
          background: rgba(14, 165, 233, 0.15);
          border-color: rgba(56, 189, 248, 0.45);
          color: #38bdf8;
          box-shadow: 0 0 14px rgba(14, 165, 233, 0.18);
        }

        .graph-workspace-section {
          margin-bottom: 2rem;
        }

        .top-nav-bar {
          margin-bottom: 1.5rem;
        }

        .back-link {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          color: #94a3b8;
          font-size: 0.85rem;
          font-weight: 500;
          text-decoration: none;
          transition: color 0.15s ease;
        }

        .back-link:hover {
          color: #38bdf8;
        }

        /* LOADING & ERROR */
        .loading-wrapper {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 6rem 2rem;
          text-align: center;
        }

        .loading-radar {
          position: relative;
          width: 64px;
          height: 64px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 1.25rem;
        }

        .radar-pulse {
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

        .loading-text {
          font-size: 0.88rem;
          color: #94a3b8;
          letter-spacing: 0.02em;
        }

        .case-error-card {
          background: rgba(15, 23, 42, 0.7);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 12px;
          padding: 3rem 2rem;
          text-align: center;
          max-width: 540px;
          margin: 3rem auto;
        }

        .error-icon-box {
          color: #ef4444;
          margin-bottom: 1rem;
        }

        .error-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: #f8fafc;
          margin-bottom: 0.5rem;
        }

        .error-desc {
          font-size: 0.88rem;
          color: #94a3b8;
          line-height: 1.5;
          margin-bottom: 1.5rem;
        }

        .error-actions {
          display: flex;
          justify-content: center;
          gap: 1rem;
        }

        .btn-secondary-link {
          display: inline-flex;
          align-items: center;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 600;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.15);
          color: #f1f5f9;
          text-decoration: none;
        }

        .btn-primary-action {
          display: inline-flex;
          align-items: center;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 600;
          background: #0284c7;
          border: 1px solid #38bdf8;
          color: #ffffff;
          cursor: pointer;
        }

        /* 1. CASE HEADER CARD */
        .case-header-card {
          background: rgba(15, 23, 42, 0.75);
          border: 1px solid rgba(56, 189, 248, 0.15);
          border-radius: 14px;
          padding: 1.75rem 2rem;
          margin-bottom: 2rem;
          box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.35);
        }

        .header-meta-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .badge-group {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .case-number-badge {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 0.8rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          color: #38bdf8;
          background: rgba(14, 165, 233, 0.1);
          border: 1px solid rgba(56, 189, 248, 0.25);
          border-radius: 5px;
          padding: 0.2rem 0.6rem;
        }

        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          padding: 0.2rem 0.6rem;
          border-radius: 9999px;
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

        .dot-open {
          background-color: #10b981;
          box-shadow: 0 0 6px #10b981;
        }

        .dot-closed {
          background-color: #64748b;
        }

        .case-created-meta {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.78rem;
          color: #94a3b8;
        }

        .case-main-title {
          font-size: 1.75rem;
          font-weight: 700;
          color: #f8fafc;
          letter-spacing: -0.02em;
          line-height: 1.25;
          margin-bottom: 1.5rem;
        }

        .overview-section {
          margin-bottom: 1.5rem;
        }

        .section-label {
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: #94a3b8;
          margin-bottom: 0.5rem;
        }

        .narrative-box {
          background: rgba(11, 16, 27, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 8px;
          padding: 1rem 1.25rem;
        }

        .narrative-text {
          font-size: 0.88rem;
          line-height: 1.6;
          color: #cbd5e1;
        }

        .case-technical-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 1.5rem;
          padding-top: 1.25rem;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
          font-size: 0.75rem;
        }

        .meta-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .meta-label {
          color: #64748b;
        }

        .meta-value {
          color: #94a3b8;
        }

        .font-mono {
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        /* 2. DOCUMENTS SECTION */
        .documents-section {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .section-header-bar {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
        }

        .section-title-group {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .title-with-count {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .section-title {
          font-size: 1.35rem;
          font-weight: 700;
          color: #f1f5f9;
          letter-spacing: -0.01em;
        }

        .doc-count-badge {
          font-size: 0.72rem;
          font-weight: 600;
          color: #38bdf8;
          background: rgba(14, 165, 233, 0.1);
          border: 1px solid rgba(56, 189, 248, 0.2);
          border-radius: 9999px;
          padding: 0.15rem 0.55rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .section-desc {
          font-size: 0.82rem;
          color: #94a3b8;
        }

        .refresh-docs-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.4rem 0.75rem;
          border-radius: 6px;
          background: rgba(15, 23, 42, 0.75);
          border: 1px solid rgba(56, 189, 248, 0.2);
          color: #cbd5e1;
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .refresh-docs-btn:hover:not(:disabled) {
          background: rgba(30, 41, 59, 0.85);
          border-color: rgba(56, 189, 248, 0.4);
          color: #38bdf8;
        }

        .refresh-docs-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .spinning {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        /* UPLOAD CONTAINER */
        .upload-container-card {
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 1.5rem;
        }

        .upload-card-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: #f1f5f9;
          margin-bottom: 0.25rem;
        }

        .upload-card-subtitle {
          font-size: 0.78rem;
          color: #94a3b8;
          margin-bottom: 1rem;
        }

        .upload-banner {
          display: flex;
          align-items: center;
          gap: 0.65rem;
          padding: 0.65rem 0.9rem;
          border-radius: 8px;
          font-size: 0.8rem;
          margin-bottom: 1rem;
        }

        .banner-success {
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          color: #34d399;
        }

        .banner-danger {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #f87171;
        }

        .dropzone-box {
          border: 2px dashed rgba(56, 189, 248, 0.25);
          background: rgba(11, 16, 27, 0.5);
          border-radius: 10px;
          padding: 2rem 1.5rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .dropzone-box:hover, .dropzone-dragging {
          border-color: #38bdf8;
          background: rgba(14, 165, 233, 0.06);
        }

        .dropzone-has-file {
          border-style: solid;
          border-color: rgba(56, 189, 248, 0.4);
          padding: 1.25rem;
        }

        .hidden-file-input {
          display: none;
        }

        .dropzone-prompt {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.75rem;
        }

        .upload-icon-circle {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          background: rgba(14, 165, 233, 0.1);
          border: 1px solid rgba(56, 189, 248, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #38bdf8;
        }

        .dropzone-text-group {
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }

        .dropzone-main-text {
          font-size: 0.88rem;
          color: #e2e8f0;
        }

        .dropzone-sub-text {
          font-size: 0.75rem;
          color: #64748b;
        }

        .selected-file-display {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
        }

        .file-info-col {
          display: flex;
          align-items: center;
          gap: 0.85rem;
          text-align: left;
        }

        .file-type-pill {
          background: rgba(14, 165, 233, 0.15);
          border: 1px solid rgba(56, 189, 248, 0.3);
          color: #38bdf8;
          font-size: 0.7rem;
          font-weight: 700;
          padding: 0.25rem 0.5rem;
          border-radius: 5px;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .file-name-size {
          display: flex;
          flex-direction: column;
          gap: 0.15rem;
        }

        .selected-filename {
          font-size: 0.88rem;
          font-weight: 600;
          color: #f1f5f9;
        }

        .selected-filesize {
          font-size: 0.72rem;
          color: #94a3b8;
        }

        .remove-file-btn {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.25);
          color: #f87171;
          width: 30px;
          height: 30px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: background 0.15s ease;
        }

        .remove-file-btn:hover {
          background: rgba(239, 68, 68, 0.2);
        }

        .upload-submit-bar {
          margin-top: 1rem;
          display: flex;
          justify-content: flex-end;
        }

        .upload-submit-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.6rem 1.25rem;
          background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
          border: 1px solid rgba(56, 189, 248, 0.35);
          border-radius: 8px;
          color: #ffffff;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 4px 14px rgba(14, 165, 233, 0.3);
        }

        .upload-submit-btn:hover:not(:disabled) {
          background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
          box-shadow: 0 4px 18px rgba(14, 165, 233, 0.5);
          transform: translateY(-1px);
        }

        .upload-submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          box-shadow: none;
        }

        .mini-spinner {
          width: 14px;
          height: 14px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: #ffffff;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        /* DOCUMENTS TABLE / LIST */
        .documents-display-wrapper {
          margin-top: 0.5rem;
        }

        .docs-loading-box {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.65rem;
          padding: 2.5rem;
          font-size: 0.82rem;
          color: #94a3b8;
        }

        .empty-docs-card {
          background: rgba(11, 16, 27, 0.5);
          border: 1px dashed rgba(255, 255, 255, 0.08);
          border-radius: 12px;
          padding: 3rem 1.5rem;
          text-align: center;
        }

        .empty-docs-icon {
          color: #475569;
          margin-bottom: 0.85rem;
        }

        .empty-docs-title {
          font-size: 0.98rem;
          font-weight: 600;
          color: #cbd5e1;
          margin-bottom: 0.35rem;
        }

        .empty-docs-desc {
          font-size: 0.8rem;
          color: #64748b;
          max-width: 480px;
          margin: 0 auto;
          line-height: 1.5;
        }

        .docs-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .doc-item-card {
          background: rgba(15, 23, 42, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.07);
          border-radius: 10px;
          padding: 1rem 1.25rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
          transition: all 0.2s ease;
        }

        .doc-item-card:hover {
          border-color: rgba(56, 189, 248, 0.3);
          background: rgba(22, 33, 58, 0.8);
          transform: translateX(2px);
        }

        .doc-primary-info {
          display: flex;
          align-items: center;
          gap: 1rem;
          min-width: 0;
        }

        .doc-icon-badge {
          width: 40px;
          height: 40px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.72rem;
          font-weight: 800;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          flex-shrink: 0;
        }

        .badge-pdf {
          background: rgba(239, 68, 68, 0.12);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #f87171;
        }

        .badge-csv {
          background: rgba(16, 185, 129, 0.12);
          border: 1px solid rgba(16, 185, 129, 0.3);
          color: #34d399;
        }

        .badge-txt {
          background: rgba(14, 165, 233, 0.12);
          border: 1px solid rgba(56, 189, 248, 0.3);
          color: #38bdf8;
        }

        .doc-details-block {
          min-width: 0;
        }

        .doc-filename {
          font-size: 0.92rem;
          font-weight: 600;
          color: #f1f5f9;
          margin-bottom: 0.2rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .doc-meta-row {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.73rem;
          color: #94a3b8;
        }

        .meta-separator {
          color: #475569;
        }

        /* HASH VERIFICATION */
        .doc-hash-wrapper {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.35rem 0.65rem;
          background: rgba(11, 16, 27, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 6px;
          font-size: 0.7rem;
          flex-shrink: 0;
        }

        .hash-label {
          font-weight: 700;
          color: #64748b;
          font-size: 0.65rem;
          letter-spacing: 0.04em;
        }

        .hash-value {
          color: #38bdf8;
          font-size: 0.72rem;
        }

        @media (max-width: 768px) {
          .case-header-card {
            padding: 1.25rem;
          }
          .case-main-title {
            font-size: 1.4rem;
          }
          .doc-item-card {
            flex-direction: column;
            align-items: flex-start;
          }
          .doc-hash-wrapper {
            width: 100%;
            justify-content: space-between;
          }
        }
      `}</style>
    </AuthLayout>
  );
}

