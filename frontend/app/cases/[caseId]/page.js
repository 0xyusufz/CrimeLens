"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient } from "../../../lib/apiClient";
import AuthLayout from "../../../components/Layout";
import CaseGraphView from "../../../components/CaseGraphView";
import InvestigationPathView from "../../../components/InvestigationPathView";
import CaseInsightsView from "../../../components/CaseInsightsView";
import CaseCopilotView from "../../../components/CaseCopilotView";
import CaseInvestigatorChatView from "../../../components/CaseInvestigatorChatView";

export function parseCaseMeta(caseItem) {
  let meta = {
    category: "OTHER",
    priority: "MEDIUM",
    subStatus: caseItem?.status === "CLOSED" ? "SOLVED" : "ACTIVE",
    incidentDate: null,
    location: null,
    leadOfficer: null,
    narrative: caseItem?.description || "",
  };

  if (!caseItem) return meta;

  if (caseItem.description && typeof caseItem.description === "string") {
    const trimmed = caseItem.description.trim();
    if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed && typeof parsed === "object") {
          meta.category = parsed.category || meta.category;
          meta.priority = parsed.priority || meta.priority;
          meta.subStatus = parsed.subStatus || (caseItem.status === "CLOSED" ? "SOLVED" : "ACTIVE");
          meta.incidentDate = parsed.incidentDate || parsed.date || null;
          meta.location = parsed.location || null;
          meta.leadOfficer = parsed.leadOfficer || parsed.lead_officer || parsed.officer || null;
          meta.narrative = parsed.narrative || parsed.description || parsed.notes || "";
        }
      } catch {
        meta.narrative = trimmed;
      }
    } else {
      meta.narrative = trimmed;
    }
  }

  if (caseItem.status === "CLOSED" && meta.subStatus !== "SOLVED") {
    meta.subStatus = "SOLVED";
  }

  return meta;
}

export default function CaseDetailsPage() {
  const { caseId } = useParams();
  const router = useRouter();
  const fileInputRef = useRef(null);

  // Workspace Tab: "graph" | "documents" | "path" | "insights"
  const [activeTab, setActiveTab] = useState("graph");
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [copilotInitialQuery, setCopilotInitialQuery] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Case data states
  const [caseData, setCaseData] = useState(null);
  const caseMeta = parseCaseMeta(caseData);
  const [documents, setDocuments] = useState([]);
  const [loadingCase, setLoadingCase] = useState(true);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [caseError, setCaseError] = useState(null);

  // Upload states
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  // Process document states: keyed by document ID
  // processStates[id] = { status: 'idle'|'processing'|'success'|'error', message: string|null }
  const [processStates, setProcessStates] = useState({});

  // Bump this key to force graph/insights child components to re-fetch
  const [graphRefreshKey, setGraphRefreshKey] = useState(0);

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

  // Handle multi-file selection (max 5 files at once)
  const handleFileSelect = (fileList) => {
    setUploadError(null);
    setUploadSuccess(null);

    const newFiles = Array.from(fileList || []);
    if (!newFiles.length) return;

    const allowed = [".pdf", ".csv", ".txt", ".docx", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"];
    const invalidFile = newFiles.find((file) => {
      const ext = "." + file.name.split(".").pop().toLowerCase();
      return !allowed.includes(ext);
    });

    if (invalidFile) {
      setUploadError("Unsupported file type. Use PDF, DOCX, CSV, TXT, PNG, JPG, TIFF, BMP, or GIF files.");
      return;
    }

    const maxBytes = 100 * 1024 * 1024;
    const oversizedFile = newFiles.find((file) => file.size > maxBytes);
    if (oversizedFile) {
      setUploadError(`File "${oversizedFile.name}" exceeds the 100 MB limit (${(oversizedFile.size / (1024 * 1024)).toFixed(1)} MB).`);
      return;
    }

    setSelectedFiles((prev) => {
      const combined = [...prev, ...newFiles];
      const unique = [];
      const seen = new Set();
      for (const f of combined) {
        const key = `${f.name}_${f.size}`;
        if (!seen.has(key)) {
          seen.add(key);
          unique.push(f);
        }
      }

      if (unique.length > 5) {
        setUploadError("Maximum 5 documents can be uploaded at once. Staged the first 5 documents.");
        return unique.slice(0, 5);
      }
      return unique;
    });
  };

  const handleRemoveFile = (indexToRemove) => {
    setSelectedFiles((prev) => prev.filter((_, idx) => idx !== indexToRemove));
    setUploadError(null);
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
      handleFileSelect(e.dataTransfer.files);
    }
  };

  // Process a single document
  const handleProcessDocument = async (docId) => {
    setProcessStates((prev) => ({
      ...prev,
      [docId]: { status: "processing", message: null },
    }));

    try {
      await apiClient(`/api/documents/${docId}/process`, { method: "POST" });
      setProcessStates((prev) => ({
        ...prev,
        [docId]: { status: "success", message: null },
      }));
      // Trigger graph and intelligence panels to re-fetch
      setGraphRefreshKey((k) => k + 1);
    } catch (err) {
      let msg;
      if (err?.status === 401) {
        msg = "Session expired. Please log in again.";
      } else if (err?.status === 403) {
        msg = "You do not have permission to process this document.";
      } else if (err?.status === 404) {
        msg = "Document not found. It may have been removed.";
      } else if (err?.status === 422) {
        // Includes CSV schema errors and ML contract failures
        msg = err.message || "Processing failed: document format could not be validated.";
      } else if (err?.status >= 500) {
        msg = "A server error occurred during processing. Please try again.";
      } else if (err?.message?.includes("Network")) {
        msg = "Network error. Please ensure the backend is running.";
      } else {
        msg = err.message || "Processing failed. Please try again.";
      }
      setProcessStates((prev) => ({
        ...prev,
        [docId]: { status: "error", message: msg },
      }));
    }
  };

  // Upload up to 5 files via batch endpoint with single-file fallback
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFiles.length || uploading || !caseId) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const count = selectedFiles.length;

    try {
      // 1. Try batch upload endpoint
      const formData = new FormData();
      for (const file of selectedFiles) {
        formData.append("files", file);
      }

      try {
        await apiClient(`/api/cases/${caseId}/documents/batch`, {
          method: "POST",
          body: formData,
        });
      } catch (batchErr) {
        if (batchErr?.status === 413) {
          throw batchErr;
        }
        // Fallback: sequential upload if batch endpoint encounters format mismatch
        for (const file of selectedFiles) {
          const singleFormData = new FormData();
          singleFormData.append("file", file);
          await apiClient(`/api/cases/${caseId}/documents`, {
            method: "POST",
            body: singleFormData,
          });
        }
      }

      setUploadSuccess(`Successfully registered ${count} evidentiary document${count === 1 ? "" : "s"} to case! Cryptographic hashing complete.`);
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";

      // Refresh documents list
      await fetchDocuments();
    } catch (err) {
      if (err?.status === 415) {
        setUploadError("Unsupported media type. Use PDF, DOCX, CSV, TXT, or supported image files.");
      } else if (err?.status === 413) {
        setUploadError(err?.detail || err?.message || "One or more files exceed the maximum allowed upload size (100 MB).");
      } else if (err?.status === 400) {
        setUploadError(err?.detail || err?.message || "Invalid upload files.");
      } else {
        setUploadError(err?.detail || err?.message || "Failed to upload documents. Please check server connectivity and try again.");
      }
    } finally {
      setUploading(false);
    }
  };

  // Batch process all registered documents
  const [batchProcessing, setBatchProcessing] = useState(false);
  const handleProcessAllDocuments = async () => {
    if (!documents.length || batchProcessing) return;
    setBatchProcessing(true);
    for (const doc of documents) {
      if (processStates[doc.id]?.status !== "success") {
        await handleProcessDocument(doc.id);
      }
    }
    setBatchProcessing(false);
  };

  // Formatting helpers
  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
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
        {/* BACK NAVIGATION (Only when loading or on error; otherwise sidebar provides navigation) */}
        {(loadingCase || caseError) && (
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
        )}

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

        {/* CASE CONTENT WITH COLLAPSIBLE SIDEBAR */}
        {!loadingCase && !caseError && caseData && (
          <div className={`case-app-split-layout ${isSidebarOpen ? "with-sidebar" : "without-sidebar"}`}>
            {/* 1. COLLAPSIBLE CASE SIDEBAR */}
            {isSidebarOpen && (
              <aside className="case-control-sidebar">
                {/* Top Actions: Back to Dashboard & Hide Sidebar Button */}
                <div className="sidebar-top-bar">
                  <Link href="/" className="sidebar-back-link" title="Return to Cases Dashboard">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="19" y1="12" x2="5" y2="12" />
                      <polyline points="12 19 5 12 12 5" />
                    </svg>
                    <span>All Cases</span>
                  </Link>

                  <button
                    onClick={() => setIsSidebarOpen(false)}
                    className="sidebar-toggle-hide-btn"
                    title="Hide sidebar (Focus mode)"
                    aria-label="Hide Sidebar"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="18" height="18" x="3" y="3" rx="2" />
                      <path d="M9 3v18" />
                      <path d="m14 9-3 3 3 3" />
                    </svg>
                  </button>
                </div>

                {/* Case Dossier Information Block */}
                <div className="sidebar-dossier-block">
                  <div className="dossier-badges-row">
                    <span className="case-number-badge" title="Official Case Identifier">
                      {caseData.case_number}
                    </span>
                    <div className="badges-right-group">
                      {caseMeta.priority && (
                        <span className={`priority-tag priority-${caseMeta.priority.toLowerCase()}`}>
                          {caseMeta.priority}
                        </span>
                      )}
                      <span
                        className={`status-pill ${caseData.status === "OPEN" ? "status-pill-open" : "status-pill-closed"}`}
                      >
                        {caseData.status}
                      </span>
                    </div>
                  </div>

                  <h1 className="sidebar-dossier-title">{caseData.title}</h1>

                  {(caseMeta.category || caseMeta.location) && (
                    <div className="sidebar-chips-row">
                      {caseMeta.category && (
                        <span className="sidebar-meta-chip category-chip">
                          {caseMeta.category.replace(/_/g, " ")}
                        </span>
                      )}
                      {caseMeta.location && (
                        <span className="sidebar-meta-chip location-chip">
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                            <circle cx="12" cy="10" r="3" />
                          </svg>
                          <span>{caseMeta.location}</span>
                        </span>
                      )}
                    </div>
                  )}

                  {caseMeta.narrative ? (
                    <div className="sidebar-narrative-box">
                      <p className="sidebar-narrative-text">{caseMeta.narrative}</p>
                    </div>
                  ) : null}

                  <div className="sidebar-dossier-meta">
                    <div className="dossier-meta-item">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                      <span>{formatDate(caseData.created_at)}</span>
                    </div>

                    {(caseMeta.leadOfficer || caseData.created_by) && (
                      <div className="dossier-meta-item">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                        <span>
                          Lead: <strong className="lead-name-highlight">
                            {caseMeta.leadOfficer || (caseData.created_by?.length > 16 ? `Det. ${caseData.created_by.slice(0, 8)}` : caseData.created_by)}
                          </strong>
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Workspace Navigation Views */}
                <div className="sidebar-nav-section">
                  <div className="sidebar-nav-section-title">WORKSPACE VIEWS</div>
                  <nav className="sidebar-nav-menu">
                    <button
                      onClick={() => setActiveTab("graph")}
                      className={`sidebar-nav-item ${activeTab === "graph" ? "active" : ""}`}
                    >
                      <div className="nav-item-icon">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="6" cy="6" r="3" />
                          <circle cx="18" cy="18" r="3" />
                          <circle cx="18" cy="6" r="3" />
                          <line x1="8.5" y1="7.5" x2="15.5" y2="16.5" />
                          <line x1="9" y1="6" x2="15" y2="6" />
                        </svg>
                      </div>
                      <span className="nav-item-label">Network Graph</span>
                    </button>

                    <button
                      onClick={() => setActiveTab("documents")}
                      className={`sidebar-nav-item ${activeTab === "documents" ? "active" : ""}`}
                    >
                      <div className="nav-item-icon">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                        </svg>
                      </div>
                      <span className="nav-item-label">Evidence & Documents</span>
                      <span className="nav-item-count">{documents.length}</span>
                    </button>

                    <button
                      onClick={() => setActiveTab("path")}
                      className={`sidebar-nav-item ${activeTab === "path" ? "active" : ""}`}
                    >
                      <div className="nav-item-icon">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                        </svg>
                      </div>
                      <span className="nav-item-label">Investigation Path</span>
                    </button>

                    <button
                      onClick={() => setActiveTab("insights")}
                      className={`sidebar-nav-item ${activeTab === "insights" ? "active" : ""}`}
                    >
                      <div className="nav-item-icon">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                        </svg>
                      </div>
                      <span className="nav-item-label">Intelligence Assistant</span>
                    </button>
                  </nav>
                </div>
              </aside>
            )}

            {/* 2. MAIN WORKSPACE VIEWPORT */}
            <main className="case-main-viewport">
              {!isSidebarOpen && (
                <div className="collapsed-top-floating-bar">
                  <Link href="/" className="collapsed-back-link" title="Return to All Cases">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="19" y1="12" x2="5" y2="12" />
                      <polyline points="12 19 5 12 12 5" />
                    </svg>
                    <span>All Cases</span>
                  </Link>
                  <button
                    onClick={() => setIsSidebarOpen(true)}
                    className="sidebar-floating-toggle-btn"
                    title="Show Case Sidebar"
                    aria-label="Show Sidebar"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="18" height="18" x="3" y="3" rx="2" />
                      <path d="M9 3v18" />
                      <path d="m11 15 3-3-3-3" />
                    </svg>
                    <span>Show Sidebar</span>
                  </button>
                  <button
                    onClick={() => setIsCopilotOpen((prev) => !prev)}
                    className={`copilot-floating-toggle-btn ${isCopilotOpen ? "active" : ""}`}
                    title={isCopilotOpen ? "Close AI Copilot" : "Open AI Copilot"}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                    <span>AI Copilot</span>
                  </button>
                </div>
              )}

              {/* Workspace Layout with active tab content */}
              <div className={`case-workspace-layout ${isCopilotOpen ? "has-copilot-open" : ""}`}>
                <div className="workspace-main-column">
                {/* TAB 1: NETWORK GRAPH INVESTIGATION */}
                {(activeTab === "graph" || activeTab === "copilot") && (
                  <section className="graph-workspace-section">
                    <CaseGraphView
                      key={graphRefreshKey}
                      caseId={caseId}
                      caseTitle={caseData?.title}
                      onOpenCopilot={(q) => {
                        if (typeof q === "string" && q) setCopilotInitialQuery(q);
                        setIsCopilotOpen(true);
                      }}
                    />
                  </section>
                )}

                {/* TAB 3: INVESTIGATION PATH */}
                {activeTab === "path" && (
                  <section className="path-workspace-section">
                    <InvestigationPathView caseId={caseId} />
                  </section>
                )}

                {/* TAB 4: INTELLIGENCE ASSISTANT & CHAT WORKSPACE */}
                {activeTab === "insights" && (
                  <section className="graph-workspace-section" style={{ padding: 0, height: "100%" }}>
                    <CaseInvestigatorChatView
                      key={graphRefreshKey}
                      caseId={caseId}
                      caseData={caseData}
                      documents={documents}
                    />
                  </section>
                )}

                {/* TAB 2: DOCUMENTS MANAGEMENT SECTION */}
                {activeTab === "documents" && (
                  <section className="documents-section">
                    <div className="section-header-bar">
                      <div className="section-title-group">
                        <h2 className="section-title">Evidence & Documents</h2>
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
                  Authorized formats: <strong>PDF</strong>, <strong>DOCX</strong>, <strong>CSV</strong>, <strong>TXT</strong>, and common image files. Files are cryptographically hashed upon ingestion.
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
                    className={`dropzone-box ${isDragging ? "dropzone-dragging" : ""} ${selectedFiles.length ? "dropzone-has-file" : ""}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.csv,.txt,.docx,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.gif,application/pdf,text/csv,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/*"
                      multiple
                      className="hidden-file-input"
                      onChange={(e) => {
                        if (e.target.files && e.target.files.length > 0) {
                          handleFileSelect(e.target.files);
                        }
                      }}
                    />

                    {!selectedFiles.length ? (
                      <div className="dropzone-prompt">
                        <div className="upload-icon-circle">
                          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="17 8 12 3 7 8" />
                            <line x1="12" y1="3" x2="12" y2="15" />
                          </svg>
                        </div>
                        <div className="dropzone-text-group">
                          <span className="dropzone-main-text">
                            <strong>Click to select</strong> or drag up to 5 evidentiary documents here
                          </span>
                          <span className="dropzone-sub-text">
                            Batch upload at once (Max 5 files) · PDF, DOCX, CSV, TXT, Images
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="staged-files-container" onClick={(e) => e.stopPropagation()}>
                        <div className="staged-files-header">
                          <div className="staged-counter-pill">
                            <span>STAGED DOCUMENTS ({selectedFiles.length} / 5 MAX)</span>
                          </div>
                          <div className="staged-header-actions">
                            <span className="staged-total-size">
                              Total: {formatFileSize(selectedFiles.reduce((total, file) => total + file.size, 0))}
                            </span>
                            {selectedFiles.length < 5 && (
                              <button
                                type="button"
                                className="btn-add-more-files"
                                onClick={() => fileInputRef.current?.click()}
                              >
                                + Add More
                              </button>
                            )}
                            <button
                              type="button"
                              className="btn-clear-all-staged"
                              onClick={() => {
                                setSelectedFiles([]);
                                if (fileInputRef.current) fileInputRef.current.value = "";
                              }}
                            >
                              Clear All
                            </button>
                          </div>
                        </div>

                        <div className="staged-files-grid">
                          {selectedFiles.map((file, idx) => {
                            const ext = file.name.split(".").pop().toUpperCase();
                            return (
                              <div key={idx} className="staged-file-card">
                                <div className="staged-file-left">
                                  <span className={`staged-ext-badge ext-${ext.toLowerCase()}`}>{ext}</span>
                                  <div className="staged-meta">
                                    <span className="staged-filename" title={file.name}>{file.name}</span>
                                    <span className="staged-size">{formatFileSize(file.size)}</span>
                                  </div>
                                </div>
                                <button
                                  type="button"
                                  className="staged-remove-btn"
                                  onClick={() => handleRemoveFile(idx)}
                                  title={`Remove ${file.name}`}
                                >
                                  ✕
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>

                  {selectedFiles.length > 0 && (
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
                            <span>Upload All {selectedFiles.length} Documents</span>
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
                      There are currently no documents registered to this case file. Upload a PDF, DOCX, CSV, TXT, or image record above to begin evidence ingestion.
                    </p>
                  </div>
                ) : (
                  <div className="documents-table-container">
                    <div className="docs-table-top-bar">
                      <span className="docs-count-label">
                        {documents.length} Evidentiary Document{documents.length === 1 ? "" : "s"} Registered
                      </span>
                      <button
                        type="button"
                        onClick={handleProcessAllDocuments}
                        disabled={batchProcessing || !documents.length}
                        className="btn-batch-process-all"
                        title="Run AI extraction and intelligence pipeline on all documents"
                      >
                        <span>{batchProcessing ? "Processing Documents..." : "Process All Documents with AI"}</span>
                      </button>
                    </div>
                    <div className="docs-list">
                        {documents.map((doc) => {
                        const fileType = getFileType(doc.filename);
                        const procState = processStates[doc.id] || { status: "idle", message: null };
                        const isProcessing = procState.status === "processing";
                        const isSuccess = procState.status === "success";
                        const isError = procState.status === "error";
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
                                  <span className="doc-id-badge" title={`Document System UUID: ${doc.id}`}>
                                    <span className="id-tag">ID</span>
                                    <span className="id-val font-mono">{doc.id ? doc.id.slice(0, 8) : "—"}</span>
                                  </span>
                                  <span className="meta-separator">•</span>
                                  <span className="doc-date-text">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="meta-clock-icon">
                                      <circle cx="12" cy="12" r="10" />
                                      <polyline points="12 6 12 12 16 14" />
                                    </svg>
                                    Uploaded {formatDate(doc.uploaded_at)}
                                  </span>
                                </div>
                                {/* Per-doc error message */}
                                {isError && (
                                  <p className="doc-process-error">{procState.message}</p>
                                )}
                              </div>
                            </div>

                            {/* ACTIONS: Process button + SHA-256 badge */}
                            <div className="doc-actions-group">
                              {/* PROCESS DOCUMENT BUTTON */}
                              {isSuccess ? (
                                <div className="doc-process-success" title="ML pipeline ran: graph and intelligence updated">
                                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <polyline points="20 6 9 17 4 12" />
                                  </svg>
                                  <span>Processed</span>
                                </div>
                              ) : (
                                <button
                                  id={`process-btn-${doc.id}`}
                                  className={`doc-process-btn${isProcessing ? " doc-process-btn--loading" : ""}${isError ? " doc-process-btn--error" : ""}`}
                                  onClick={() => handleProcessDocument(doc.id)}
                                  disabled={isProcessing}
                                  title={isError ? "Retry processing" : "Run ML pipeline on this document"}
                                >
                                  {isProcessing ? (
                                    <>
                                      <span className="mini-spinner" />
                                      <span>Processing...</span>
                                    </>
                                  ) : (
                                    <>
                                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <polygon points="5 3 19 12 5 21 5 3" />
                                      </svg>
                                      <span>{isError ? "Retry" : "Process"}</span>
                                    </>
                                  )}
                                </button>
                              )}

                              {/* SHA-256 HASH VERIFICATION PILL */}
                              <div className="doc-hash-wrapper" title={`Forensic Cryptographic SHA-256 Hash: ${doc.sha256_hash || "Verified"}`}>
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="hash-shield-icon">
                                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                                </svg>
                                <span className="hash-label">SHA-256</span>
                                <span className="hash-value font-mono">
                                  {doc.sha256_hash ? `${doc.sha256_hash.slice(0, 8)}...${doc.sha256_hash.slice(-6)}` : "Verified"}
                                </span>
                              </div>
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

                {/* COPILOT SIDEBAR DRAWER */}
                {isCopilotOpen && (
                  <>
                    <div
                      className="copilot-mobile-backdrop"
                      onClick={() => setIsCopilotOpen(false)}
                      aria-hidden="true"
                    />
                    <aside className="workspace-copilot-sidebar">
                      <CaseCopilotView
                        caseId={caseId}
                        onClose={() => setIsCopilotOpen(false)}
                        isSidebar={true}
                        initialQuery={copilotInitialQuery}
                      />
                    </aside>
                  </>
                )}
              </div>

              {/* FLOATING QUICK-ACCESS TRIGGER (HIDDEN ON NETWORK PATH & EVIDENCE & DOCUMENTS) */}
              {!isCopilotOpen && activeTab === "graph" && (
                <button
                  onClick={() => setIsCopilotOpen(true)}
                  className="floating-copilot-bubble-btn"
                  title="Open AI Copilot & Network Sidebar"
                >
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                  <span>Investigation Assistant</span>
                </button>
              )}
            </main>
          </div>
        )}
      </div>

      <style>{`
        .case-details-container {
          max-width: 100% !important;
          margin: 0 auto;
          padding: 0.75rem 1.25rem 0.75rem;
          min-height: calc(100vh - 72px);
          box-sizing: border-box;
        }

        /* Split Workspace Layout */
        .case-app-split-layout {
          display: flex;
          gap: 1.25rem;
          align-items: flex-start;
          width: 100%;
          position: relative;
        }

        /* Collapsible Sidebar */
        .case-control-sidebar {
          width: 320px;
          min-width: 320px;
          max-width: 330px;
          flex-shrink: 0;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 14px;
          padding: 1.25rem 1.15rem;
          box-shadow: 0 2px 12px -2px rgba(0, 0, 0, 0.04);
          position: sticky;
          top: 76px;
          height: fit-content;
          max-height: calc(100vh - 96px);
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
          z-index: 20;
          scrollbar-width: thin;
          scrollbar-color: #cbd5e1 transparent;
        }

        .case-control-sidebar::-webkit-scrollbar {
          width: 3px;
        }
        .case-control-sidebar::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 3px;
        }

        .sidebar-top-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.5rem;
          padding-bottom: 0.85rem;
          border-bottom: 1px solid #f1f5f9;
        }

        .sidebar-back-link {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          color: #64748b;
          font-size: 0.82rem;
          font-weight: 600;
          padding: 0.25rem 0.5rem;
          border-radius: 6px;
          transition: all 0.15s ease;
          text-decoration: none;
        }

        .sidebar-back-link:hover {
          color: #0f172a;
          background: #f1f5f9;
        }

        .sidebar-toggle-hide-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 30px;
          height: 30px;
          border-radius: 6px;
          color: #64748b;
          background: transparent;
          border: 1px solid #e2e8f0;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .sidebar-toggle-hide-btn:hover {
          color: #0f172a;
          background: #f8fafc;
          border-color: #cbd5e1;
        }

        /* Case Dossier Information Block (Generous vertical spacing) */
        .sidebar-dossier-block {
          display: flex;
          flex-direction: column;
          gap: 0.95rem;
          padding-bottom: 1.25rem;
          border-bottom: 1px solid #f1f5f9;
        }

        .dossier-badges-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .case-number-badge {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.72rem;
          font-weight: 700;
          color: #1d4ed8 !important;
          background: #eff6ff !important;
          border: 1px solid #bfdbfe !important;
          padding: 2.5px 8px;
          border-radius: 6px;
          letter-spacing: 0.04em;
          box-shadow: 0 1px 2px rgba(37, 99, 235, 0.05);
        }

        .badges-right-group {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 2px;
          text-align: right;
          line-height: 1.2;
        }

        .priority-tag {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.65rem;
          font-weight: 800;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          background: none !important;
          border: none !important;
          padding: 0 !important;
          margin: 0 !important;
          color: #475569 !important;
        }

        .priority-critical,
        .priority-high,
        .priority-medium,
        .priority-low {
          background: none !important;
          border: none !important;
          padding: 0 !important;
          color: #475569 !important;
        }

        .status-pill {
          display: inline-flex;
          align-items: center;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.65rem;
          font-weight: 800;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          background: none !important;
          border: none !important;
          padding: 0 !important;
          margin: 0 !important;
          color: #64748b !important;
        }

        .status-pill-open,
        .status-pill-closed {
          background: none !important;
          border: none !important;
          padding: 0 !important;
          color: #64748b !important;
        }

        .sidebar-dossier-title {
          font-family: 'Plus Jakarta Sans', var(--font-sans);
          font-size: 1.15rem;
          font-weight: 800;
          color: #0b0f19;
          line-height: 1.35;
          letter-spacing: -0.015em;
          margin: 0.2rem 0;
          word-break: break-word;
        }

        .sidebar-chips-row {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .sidebar-meta-chip {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          font-size: 0.74rem;
          font-weight: 600;
          padding: 3px 9px;
          border-radius: 6px;
          line-height: 1.3;
          background: #f1f5f9 !important;
          color: #0f172a !important;
          border: 1px solid #cbd5e1 !important;
        }

        .category-chip,
        .location-chip {
          background: #f1f5f9 !important;
          color: #0f172a !important;
          border: 1px solid #cbd5e1 !important;
        }

        .location-chip svg {
          color: #475569;
        }

        .sidebar-narrative-box {
          background: #f8fafc;
          border: 1px solid #cbd5e1;
          border-left: 3.5px solid #0f172a;
          border-radius: 7px;
          padding: 0.8rem 0.95rem;
          min-height: 72px;
          max-height: 120px;
          overflow-y: auto;
          scrollbar-width: thin;
          scrollbar-color: #cbd5e1 transparent;
        }

        .sidebar-narrative-box::-webkit-scrollbar {
          width: 3px;
        }
        .sidebar-narrative-box::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 3px;
        }

        .sidebar-narrative-text {
          font-size: 0.78rem;
          color: #1e293b;
          line-height: 1.5;
          margin: 0;
          word-break: break-word;
          font-weight: 500;
        }

        .sidebar-dossier-meta {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
          font-size: 0.76rem;
          color: #64748b;
          padding-top: 0.45rem;
        }

        .dossier-meta-item {
          display: flex;
          align-items: center;
          gap: 0.45rem;
        }

        .lead-name-highlight {
          color: #0f172a;
          font-weight: 700;
        }

        /* Workspace Navigation Views */
        .sidebar-nav-section {
          display: flex;
          flex-direction: column;
          gap: 0.55rem;
        }

        .sidebar-nav-section-title {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.62rem;
          font-weight: 750;
          letter-spacing: 0.09em;
          color: #94a3b8;
          text-transform: uppercase;
          padding: 0 0.2rem;
        }

        .sidebar-nav-menu {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
        }

        .sidebar-nav-item {
          display: flex;
          align-items: center;
          gap: 0.65rem;
          padding: 0.6rem 0.75rem;
          border-radius: 9px;
          border: 1px solid transparent;
          background: transparent;
          color: #475569;
          font-size: 0.84rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s ease;
          width: 100%;
          text-align: left;
        }

        .sidebar-nav-item:hover {
          background: #f8fafc;
          color: #0f172a;
        }

        /* Solid website primary brand blue for active navigation tab */
        .sidebar-nav-item.active {
          background: #2563eb !important;
          color: #ffffff !important;
          border: 1px solid #1d4ed8 !important;
          font-weight: 700 !important;
          box-shadow: 0 2px 6px rgba(37, 99, 235, 0.22) !important;
        }

        .sidebar-nav-item.active:hover {
          background: #1d4ed8 !important;
        }

        .sidebar-nav-item.active .nav-item-icon {
          color: #ffffff !important;
        }

        .nav-item-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: inherit;
        }

        .nav-item-label {
          flex: 1;
        }

        .nav-item-count {
          font-size: 0.67rem;
          font-weight: 700;
          padding: 1px 5px;
          border-radius: 9999px;
          background: #e2e8f0;
          color: #475569;
        }

        .sidebar-nav-item.active .nav-item-count {
          background: rgba(255, 255, 255, 0.28) !important;
          color: #ffffff !important;
        }



        .collapsed-sidebar-nav-actions {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .collapsed-back-link {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.38rem 0.65rem;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          font-size: 0.78rem;
          font-weight: 600;
          color: #475569;
          transition: all 0.15s ease;
          text-decoration: none;
        }

        .collapsed-back-link:hover {
          color: #0f172a;
          background: #f1f5f9;
          border-color: #cbd5e1;
        }

        /* Main Workspace Viewport */
        .case-main-viewport {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          width: 100%;
        }

        .collapsed-top-floating-bar {
          display: flex;
          align-items: center;
          gap: 0.6rem;
          margin-bottom: 0.75rem;
        }

        .sidebar-floating-toggle-btn, .copilot-floating-toggle-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          padding: 0.4rem 0.8rem;
          background: #ffffff;
          color: #334155;
          border: 1px solid #cbd5e1;
          border-radius: 8px;
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.18s ease;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        }

        .sidebar-floating-toggle-btn:hover, .copilot-floating-toggle-btn:hover {
          background: #f8fafc;
          border-color: #94a3b8;
          color: #0f172a;
        }

        .copilot-floating-toggle-btn.active {
          background: #eff6ff;
          border-color: #bfdbfe;
          color: #1d4ed8;
        }

        .workspace-tabs-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.75rem;
          margin-bottom: 1.75rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          padding-bottom: 0.85rem;
          flex-wrap: wrap;
        }

        .tabs-primary-row {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .tabs-secondary-row {
          display: flex;
          align-items: center;
        }

        .workspace-tab-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.55rem;
          padding: 0.6rem 1.15rem;
          background: rgba(24, 32, 44, 0.75);
          border: 1px solid #1f2836;
          border-top: 1px solid rgba(255, 255, 255, 0.16);
          border-radius: 8px;
          color: rgba(226, 232, 240, 0.75);
          font-size: 0.84rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
        }

        .workspace-tab-btn:hover {
          background: rgba(34, 45, 62, 0.92);
          color: #ffffff;
          border-color: rgba(220, 230, 242, 0.25);
        }

        .tab-btn-active {
          background: rgba(53, 167, 255, 0.16);
          border-color: #35a7ff;
          color: #35a7ff;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }

        .copilot-toggle-btn {
          border-color: rgba(53, 167, 255, 0.35) !important;
          background: rgba(53, 167, 255, 0.1) !important;
          color: #35a7ff !important;
        }

        .copilot-toggle-btn:hover {
          background: rgba(53, 167, 255, 0.2) !important;
          border-color: #35a7ff !important;
        }

        .copilot-sidebar-indicator {
          display: inline-flex;
          align-items: center;
          gap: 0.3rem;
          padding: 0.1rem 0.4rem;
          border-radius: 4px;
          background: rgba(53, 167, 255, 0.14);
          font-size: 0.62rem;
          font-weight: 800;
          letter-spacing: 0.04em;
        }

        .live-dot-pulse {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #fcba04;
        }

        .case-workspace-layout {
          display: flex;
          width: 100%;
          gap: 1.25rem;
          align-items: flex-start;
          position: relative;
        }

        .workspace-main-column {
          flex: 1;
          min-width: 0;
          width: 100%;
        }

        .workspace-copilot-sidebar {
          width: 420px;
          flex-shrink: 0;
          position: sticky;
          top: 85px;
          max-height: calc(100vh - 110px);
          overflow: hidden;
          border-radius: 12px;
          border: 1px solid #e2e8f0;
          background: #ffffff;
          box-shadow: 0 12px 36px rgba(15, 23, 42, 0.12);
          display: flex;
          flex-direction: column;
          z-index: 40;
        }

        @media (max-width: 1180px) {
          .workspace-copilot-sidebar {
            position: fixed;
            top: 0;
            right: 0;
            bottom: 0;
            width: min(440px, 94vw);
            max-height: 100vh;
            border-radius: 0;
            z-index: 1000;
            box-shadow: -10px 0 35px rgba(0, 0, 0, 0.25);
          }

          .copilot-mobile-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(15, 23, 42, 0.45);
            backdrop-filter: blur(4px);
            z-index: 999;
          }
        }

        .floating-copilot-bubble-btn {
          position: fixed;
          right: 1.75rem;
          bottom: 1.75rem;
          z-index: 80;
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.65rem 1.1rem;
          border-radius: 30px;
          background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
          color: #ffffff;
          border: 1px solid rgba(255, 255, 255, 0.2);
          box-shadow: 0 8px 24px rgba(37, 99, 235, 0.35);
          font-size: 0.82rem;
          font-weight: 750;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .floating-copilot-bubble-btn:hover {
          background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%);
          transform: translateY(-2px);
          box-shadow: 0 12px 28px rgba(37, 99, 235, 0.45);
        }

        .bubble-live-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: #fcba04;
          box-shadow: 0 0 0 2px rgba(252, 186, 4, 0.3);
        }

        .graph-workspace-section {
          margin-bottom: 0;
        }

        .top-nav-bar {
          margin-bottom: 1.5rem;
        }

        .back-link {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          color: rgba(242, 247, 242, 0.72);
          font-size: 0.85rem;
          font-weight: 500;
          text-decoration: none;
          transition: color 0.15s ease;
        }

        .back-link:hover {
          color: #35a7ff;
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
          background: rgba(53, 167, 255, 0.15);
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
          color: rgba(242, 247, 242, 0.72);
          letter-spacing: 0.02em;
        }

        .case-error-card {
          background: rgba(18, 24, 33, 0.65);
          border: 1px solid rgba(252, 186, 4, 0.3);
          border-radius: 12px;
          padding: 3rem 2rem;
          text-align: center;
          max-width: 540px;
          margin: 3rem auto;
        }

        .error-icon-box {
          color: #fcba04;
          margin-bottom: 1rem;
        }

        .error-title {
          font-size: 1.25rem;
          font-weight: 700;
          color: #f2f7f2;
          margin-bottom: 0.5rem;
        }

        .error-desc {
          font-size: 0.88rem;
          color: rgba(242, 247, 242, 0.72);
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
          background: rgba(24, 32, 44, 0.75);
          border: 1px solid rgba(220, 230, 242, 0.12);
          color: #f1f5f9;
          text-decoration: none;
        }

        .btn-primary-action {
          display: inline-flex;
          align-items: center;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 750;
          background: linear-gradient(180deg, #35a7ff 0%, #1e8fe6 100%);
          border: 1px solid rgba(255, 255, 255, 0.3);
          color: #0a0d10;
          cursor: pointer;
        }

        /* 1. CASE HEADER CARD */
        .case-header-card {
          background: linear-gradient(180deg, rgba(22, 30, 42, 0.88) 0%, rgba(13, 18, 26, 0.94) 100%);
          border: 1px solid rgba(220, 230, 242, 0.09);
          border-top: 1px solid rgba(255, 255, 255, 0.16);
          border-radius: 14px;
          padding: 1.75rem 2rem;
          margin-bottom: 2rem;
          box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
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
          color: #1d4ed8;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 6px;
          padding: 0.2rem 0.6rem;
          box-shadow: 0 1px 2px rgba(37, 99, 235, 0.05);
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
          background: rgba(252, 186, 4, 0.12);
          color: #fcba04;
          border: 1px solid rgba(252, 186, 4, 0.3);
        }

        .status-pill-closed {
          background: rgba(53, 167, 255, 0.12);
          color: #35a7ff;
          border: 1px solid rgba(53, 167, 255, 0.28);
        }

        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
        }

        .dot-open {
          background-color: #fcba04;
          box-shadow: 0 0 6px #fcba04;
        }

        .dot-closed {
          background-color: #35a7ff;
        }

        .case-created-meta {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.78rem;
          color: rgba(242, 247, 242, 0.72);
        }

        .case-main-title {
          font-size: 1.75rem;
          font-weight: 700;
          color: #f2f7f2;
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
          color: #f2f7f2;
          margin-bottom: 0.5rem;
        }

        .narrative-box {
          background: rgba(23, 29, 28, 0.8);
          border: 1px solid rgba(242, 247, 242, 0.08);
          border-radius: 8px;
          padding: 1rem 1.25rem;
        }

        .narrative-text {
          font-size: 0.88rem;
          line-height: 1.6;
          color: #f2f7f2;
        }

        .case-technical-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 1.5rem;
          padding-top: 1.25rem;
          border-top: 1px solid rgba(242, 247, 242, 0.08);
          font-size: 0.75rem;
        }

        .meta-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .meta-label {
          color: rgba(242, 247, 242, 0.55);
        }

        .meta-value {
          color: rgba(242, 247, 242, 0.85);
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
          color: #f2f7f2;
          letter-spacing: -0.01em;
        }

        .doc-count-badge {
          font-size: 0.72rem;
          font-weight: 600;
          color: #35a7ff;
          background: rgba(53, 167, 255, 0.12);
          border: 1px solid rgba(53, 167, 255, 0.25);
          border-radius: 9999px;
          padding: 0.15rem 0.55rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .section-desc {
          font-size: 0.82rem;
          color: rgba(242, 247, 242, 0.72);
        }

        .refresh-docs-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.4rem 0.75rem;
          border-radius: 6px;
          background: rgba(24, 32, 44, 0.75);
          border: 1px solid rgba(220, 230, 242, 0.12);
          color: #f1f5f9;
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .refresh-docs-btn:hover:not(:disabled) {
          background: rgba(34, 45, 62, 0.9);
          border-color: #35a7ff;
          color: #35a7ff;
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
          background: rgba(16, 22, 30, 0.6);
          border: 1px solid rgba(220, 230, 242, 0.08);
          border-radius: 12px;
          padding: 1.5rem;
        }

        .upload-card-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: #f2f7f2;
          margin-bottom: 0.25rem;
        }

        .upload-card-subtitle {
          font-size: 0.78rem;
          color: rgba(242, 247, 242, 0.65);
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
          background: rgba(252, 186, 4, 0.12);
          border: 1px solid rgba(252, 186, 4, 0.3);
          color: #fcba04;
        }

        .banner-danger {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #f87171;
        }

        .dropzone-box {
          border: 2px dashed #cbd5e1;
          background: #f8fafc;
          border-radius: 12px;
          padding: 2rem 1.5rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .dropzone-box:hover, .dropzone-dragging {
          border-color: #2563eb;
          background: #eff6ff;
        }

        .dropzone-has-file {
          border-style: solid;
          border-color: #93c5fd;
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
          width: 46px;
          height: 46px;
          border-radius: 50%;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #2563eb;
        }

        .dropzone-text-group {
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }

        .dropzone-main-text {
          font-size: 0.88rem;
          color: #0f172a;
          font-weight: 600;
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
          background: rgba(53, 167, 255, 0.15);
          border: 1px solid rgba(53, 167, 255, 0.35);
          color: #35a7ff;
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
          color: #f2f7f2;
        }

        .selected-filesize {
          font-size: 0.72rem;
          color: rgba(242, 247, 242, 0.65);
        }

        .remove-file-btn {
          background: rgba(252, 186, 4, 0.12);
          border: 1px solid rgba(252, 186, 4, 0.3);
          color: #fcba04;
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
          background: rgba(252, 186, 4, 0.25);
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
          background: #2563eb;
          border: 1px solid #1d4ed8;
          border-radius: 8px;
          color: #ffffff;
          font-size: 0.85rem;
          font-weight: 750;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
        }

        .upload-submit-btn:hover:not(:disabled) {
          background: #1d4ed8;
          box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
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
          border: 2px solid rgba(255, 255, 255, 0.35);
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
          background: rgba(18, 24, 33, 0.6);
          border: 1px dashed rgba(220, 230, 242, 0.14);
          border-radius: 12px;
          padding: 3rem 1.5rem;
          text-align: center;
        }

        .empty-docs-icon {
          color: rgba(242, 247, 242, 0.4);
          margin-bottom: 0.85rem;
        }

        .empty-docs-title {
          font-size: 0.98rem;
          font-weight: 600;
          color: #f2f7f2;
          margin-bottom: 0.35rem;
        }

        .empty-docs-desc {
          font-size: 0.8rem;
          color: rgba(242, 247, 242, 0.65);
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
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 1rem 1.25rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }

        .doc-item-card:hover {
          border-color: #93c5fd;
          background: #f8fafc;
          box-shadow: 0 4px 14px -2px rgba(37, 99, 235, 0.08);
          transform: translateY(-1px);
        }

        .doc-primary-info {
          display: flex;
          align-items: center;
          gap: 1rem;
          min-width: 0;
        }

        .doc-icon-badge {
          width: 42px;
          height: 42px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.74rem;
          font-weight: 800;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          flex-shrink: 0;
        }

        .badge-pdf {
          background: #ef4444;
          border: 1px solid #dc2626;
          color: #ffffff;
          box-shadow: 0 1px 3px rgba(220, 38, 38, 0.25);
        }

        .badge-csv {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          color: #1d4ed8;
        }

        .badge-txt {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          color: #475569;
        }

        .doc-details-block {
          min-width: 0;
        }

        .doc-filename {
          font-size: 0.94rem;
          font-weight: 700;
          color: #0f172a;
          margin-bottom: 0.25rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .doc-meta-row {
          display: flex;
          align-items: center;
          gap: 0.55rem;
          font-size: 0.74rem;
          color: #64748b;
          font-weight: 500;
          margin-top: 0.2rem;
          flex-wrap: wrap;
        }

        .doc-id-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.3rem;
          padding: 0.12rem 0.45rem;
          background: rgba(100, 116, 139, 0.08);
          border: 1px solid rgba(148, 163, 184, 0.22);
          border-radius: 5px;
          font-size: 0.68rem;
          transition: all 0.15s ease;
        }

        .doc-id-badge:hover {
          background: rgba(37, 99, 235, 0.08);
          border-color: rgba(37, 99, 235, 0.3);
        }

        .id-tag {
          font-weight: 800;
          color: #475569;
          font-size: 0.62rem;
          letter-spacing: 0.04em;
        }

        .id-val {
          color: #334155;
          font-weight: 600;
        }

        .doc-date-text {
          display: inline-flex;
          align-items: center;
          gap: 0.3rem;
          color: #64748b;
        }

        .meta-clock-icon {
          opacity: 0.7;
          color: #64748b;
          flex-shrink: 0;
        }

        .meta-separator {
          color: #cbd5e1;
        }

        /* HASH VERIFICATION (Transparent light blue glass badge) */
        .doc-hash-wrapper {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          padding: 0.32rem 0.75rem;
          background: rgba(37, 99, 235, 0.05);
          border: 1px solid rgba(37, 99, 235, 0.18);
          border-radius: 8px;
          font-size: 0.72rem;
          flex-shrink: 0;
          transition: all 0.15s ease;
          backdrop-filter: blur(4px);
        }

        .doc-hash-wrapper:hover {
          background: rgba(37, 99, 235, 0.1);
          border-color: rgba(37, 99, 235, 0.35);
          box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
        }

        .hash-shield-icon {
          color: #2563eb;
          flex-shrink: 0;
          opacity: 0.85;
        }

        .hash-label {
          font-weight: 800;
          color: #2563eb;
          font-size: 0.65rem;
          letter-spacing: 0.05em;
          background: rgba(37, 99, 235, 0.1);
          padding: 1.5px 5px;
          border-radius: 4px;
          border: 1px solid rgba(37, 99, 235, 0.2);
        }

        .hash-value {
          color: #1e40af;
          font-size: 0.72rem;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-weight: 600;
          letter-spacing: -0.01em;
        }

        /* PROCESS DOCUMENT BUTTON */
        .doc-actions-group {
          display: flex;
          align-items: center;
          gap: 0.65rem;
          flex-shrink: 0;
        }

        .doc-process-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          padding: 0.38rem 0.85rem;
          border-radius: 8px;
          background: #f0f7ff;
          border: 1px solid #bfdbfe;
          color: #1d4ed8;
          font-size: 0.76rem;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.15s ease;
          white-space: nowrap;
        }

        .doc-process-btn:hover:not(:disabled) {
          background: #2563eb;
          border-color: #1d4ed8;
          color: #ffffff;
          box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
          transform: translateY(-1px);
        }

        .doc-process-btn:disabled {
          opacity: 0.65;
          cursor: not-allowed;
          transform: none;
        }

        .doc-process-btn--error {
          background: rgba(252, 186, 4, 0.12);
          border-color: rgba(252, 186, 4, 0.35);
          color: #fcba04;
        }

        .doc-process-btn--error:hover:not(:disabled) {
          background: rgba(252, 186, 4, 0.25);
          border-color: #fcba04;
          box-shadow: 0 0 10px rgba(252, 186, 4, 0.2);
        }

        .doc-process-success {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.35rem 0.8rem;
          border-radius: 6px;
          background: rgba(53, 167, 255, 0.14);
          border: 1px solid rgba(53, 167, 255, 0.35);
          color: #35a7ff;
          font-size: 0.75rem;
          font-weight: 700;
          white-space: nowrap;
        }

        .doc-process-error {
          font-size: 0.72rem;
          color: #fcba04;
          margin-top: 0.25rem;
          max-width: 340px;
          line-height: 1.4;
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
          .doc-actions-group {
            width: 100%;
            justify-content: space-between;
          }
          .doc-hash-wrapper {
            flex: 1;
          }
        }

        /* Staged Files Tray for Multi-Document Upload */
        .staged-files-container {
          width: 100%;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          padding: 0.25rem;
        }

        .staged-files-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-bottom: 0.5rem;
          border-bottom: 1px solid rgba(242, 247, 242, 0.08);
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .staged-counter-pill {
          background: rgba(53, 167, 255, 0.14);
          color: #35a7ff;
          font-size: 0.72rem;
          font-weight: 800;
          padding: 0.2rem 0.6rem;
          border-radius: 9999px;
          border: 1px solid rgba(53, 167, 255, 0.3);
          letter-spacing: 0.04em;
        }

        .staged-header-actions {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .staged-total-size {
          font-size: 0.75rem;
          color: rgba(242, 247, 242, 0.65);
          font-weight: 600;
        }

        .btn-add-more-files {
          background: rgba(24, 32, 44, 0.75);
          border: 1px solid rgba(220, 230, 242, 0.12);
          color: #35a7ff;
          font-size: 0.74rem;
          font-weight: 700;
          padding: 0.2rem 0.55rem;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.15s;
        }

        .btn-add-more-files:hover {
          background: rgba(34, 45, 62, 0.9);
          border-color: #35a7ff;
        }

        .btn-clear-all-staged {
          background: transparent;
          border: none;
          color: #fcba04;
          font-size: 0.74rem;
          font-weight: 600;
          cursor: pointer;
          padding: 0.2rem 0.4rem;
        }

        .btn-clear-all-staged:hover {
          text-decoration: underline;
        }

        .staged-files-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 0.6rem;
        }

        .staged-file-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 8px;
          padding: 0.55rem 0.75rem;
          display: flex;
          align-items: center;
          justify-content: space-between;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }

        .staged-file-left {
          display: flex;
          align-items: center;
          gap: 0.6rem;
          overflow: hidden;
        }

        .staged-ext-badge {
          font-size: 0.65rem;
          font-weight: 800;
          padding: 0.15rem 0.45rem;
          border-radius: 4px;
          letter-spacing: 0.04em;
          background: #f1f5f9;
          color: #334155;
        }

        .ext-pdf { background: #ef4444; color: #ffffff; }
        .ext-docx { background: #eff6ff; color: #1d4ed8; }
        .ext-csv { background: #eff6ff; color: #1d4ed8; }
        .ext-txt { background: #f1f5f9; color: #334155; }
        .ext-png, .ext-jpg, .ext-jpeg { background: #fffbeb; color: #b45309; }

        .staged-meta {
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .staged-filename {
          font-size: 0.78rem;
          font-weight: 700;
          color: #0f172a;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 190px;
        }

        .staged-size {
          font-size: 0.7rem;
          color: #64748b;
        }

        .staged-remove-btn {
          background: transparent;
          border: none;
          color: rgba(242, 247, 242, 0.6);
          font-size: 0.85rem;
          cursor: pointer;
          padding: 0.2rem 0.35rem;
          border-radius: 4px;
          transition: all 0.15s;
        }

        .staged-remove-btn:hover {
          color: #fcba04;
          background: rgba(252, 186, 4, 0.15);
        }

        /* Batch Process All Header Bar */
        .docs-table-top-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem 1.15rem;
          background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
          border: 1px solid #1d4ed8;
          border-radius: 12px 12px 0 0;
          margin-bottom: 0.65rem;
          box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
        }

        .docs-count-label {
          font-size: 0.84rem;
          font-weight: 700;
          color: #ffffff;
          letter-spacing: 0.01em;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .btn-batch-process-all {
          display: inline-flex;
          align-items: center;
          gap: 0.45rem;
          padding: 0.42rem 0.95rem;
          background: #ffffff;
          color: #1d4ed8;
          border: 1px solid #ffffff;
          border-radius: 8px;
          font-size: 0.78rem;
          font-weight: 750;
          cursor: pointer;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
          transition: all 0.15s ease;
        }

        .btn-batch-process-all:hover:not(:disabled) {
          background: #eff6ff;
          color: #1e40af;
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
        }

        .btn-batch-process-all:disabled {
          opacity: 0.65;
          background: rgba(255, 255, 255, 0.5);
          color: #64748b;
          cursor: not-allowed;
        }

      `}</style>
    </AuthLayout>
  );
}

