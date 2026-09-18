"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { apiClient } from "../lib/apiClient";
import AuthLayout from "../components/Layout";

export const CRIME_CATEGORIES = [
  { id: "HOMICIDE", label: "Homicide & Murder", color: "#dc2626", bg: "#fef2f2", border: "#fecaca" },
  { id: "ORGANIZED_CRIME", label: "Organized Crime & Gang", color: "#7c3aed", bg: "#faf5ff", border: "#e9d5ff" },
  { id: "FINANCIAL_FRAUD", label: "Financial Fraud & Laundering", color: "#d97706", bg: "#fffbeb", border: "#fde68a" },
  { id: "CYBERCRIME", label: "Cybercrime & Digital Extortion", color: "#0284c7", bg: "#f0f9ff", border: "#bae6fd" },
  { id: "NARCOTICS", label: "Narcotics & Contraband", color: "#0d9488", bg: "#f0fdfa", border: "#99f6e4" },
  { id: "KIDNAPPING", label: "Kidnapping & Missing Person", color: "#ea580c", bg: "#fff7ed", border: "#fed7aa" },
  { id: "ARMED_ROBBERY", label: "Armed Robbery & Heist", color: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
  { id: "CORRUPTION", label: "Public Corruption & Bribery", color: "#4f46e5", bg: "#eef2ff", border: "#c7d2fe" },
  { id: "OTHER", label: "General Investigation", color: "#475569", bg: "#f8fafc", border: "#e2e8f0" },
];

export function CrimeCategoryIcon({ categoryId, size = 15, color = "currentColor", className = "" }) {
  switch (categoryId) {
    case "HOMICIDE":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="2" x2="12" y2="6" />
          <line x1="12" y1="18" x2="12" y2="22" />
          <line x1="2" y1="12" x2="6" y2="12" />
          <line x1="18" y1="12" x2="22" y2="12" />
          <circle cx="12" cy="12" r="2.5" />
        </svg>
      );
    case "ORGANIZED_CRIME":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "FINANCIAL_FRAUD":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <rect x="2" y="5" width="20" height="14" rx="2" />
          <line x1="2" y1="10" x2="22" y2="10" />
          <line x1="6" y1="15" x2="10" y2="15" />
        </svg>
      );
    case "CYBERCRIME":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
      );
    case "NARCOTICS":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M10 2v7.31L4.15 20.3A2 2 0 0 0 5.89 23h12.22a2 2 0 0 0 1.74-2.7L14 9.31V2" />
          <line x1="8.5" y1="2" x2="15.5" y2="2" />
          <line x1="7" y1="16" x2="17" y2="16" />
        </svg>
      );
    case "KIDNAPPING":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <circle cx="12" cy="8" r="4" />
          <path d="M6 21v-2a6 6 0 0 1 12 0v2" />
          <line x1="12" y1="11" x2="12" y2="13" />
        </svg>
      );
    case "ARMED_ROBBERY":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          <circle cx="12" cy="16" r="1.5" />
        </svg>
      );
    case "CORRUPTION":
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M3 21h18" />
          <path d="M5 21V10" />
          <path d="M19 21V10" />
          <path d="M9 21V10" />
          <path d="M15 21V10" />
          <path d="M2 10h20" />
          <path d="M12 3L2 10h20L12 3z" />
        </svg>
      );
    case "OTHER":
    default:
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      );
  }
}

export function CategoryFilterDropdown({
  value,
  onChange,
  casesCount,
  categoryCounts = {},
  includeAll = true,
  allLabel = "All Crime Categories",
  disabled = false,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(e) {
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const selectedCategory = CRIME_CATEGORIES.find((c) => c.id === value);

  return (
    <div className={`custom-category-dropdown ${disabled ? "is-disabled" : ""}`} ref={dropdownRef}>
      <button
        type="button"
        className={`dropdown-trigger-btn ${isOpen ? "is-open" : ""} ${value !== "ALL" ? "has-filter" : ""}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <div className="trigger-left-content">
          {value === "ALL" || !selectedCategory ? (
            <>
              <span className="trigger-icon-box trigger-icon-all">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                </svg>
              </span>
              <span className="trigger-label">{allLabel}</span>
            </>
          ) : (
            <>
              <span
                className="trigger-icon-box"
                style={{
                  background: selectedCategory.bg,
                  borderColor: selectedCategory.border,
                }}
              >
                <CrimeCategoryIcon categoryId={selectedCategory.id} size={13} color={selectedCategory.color} />
              </span>
              <span className="trigger-label">{selectedCategory.label}</span>
            </>
          )}
        </div>

        <div className="trigger-right-actions">
          {includeAll && value !== "ALL" && !disabled && (
            <span
              role="button"
              tabIndex={0}
              className="trigger-clear-btn"
              title="Clear classification filter"
              onClick={(e) => {
                e.stopPropagation();
                onChange("ALL");
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.stopPropagation();
                  onChange("ALL");
                }
              }}
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </span>
          )}
          <span className={`trigger-chevron ${isOpen ? "rotate-up" : ""}`}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </span>
        </div>
      </button>

      {isOpen && (
        <div className="dropdown-popover-menu" role="listbox">
          <div className="dropdown-popover-header">
            <span>CLASSIFICATION FILTER</span>
          </div>

          <div className="dropdown-options-list">
            {includeAll && (
              <button
                type="button"
                className={`dropdown-option-item ${value === "ALL" ? "is-active-option" : ""}`}
                onClick={() => {
                  onChange("ALL");
                  setIsOpen(false);
                }}
                role="option"
                aria-selected={value === "ALL"}
              >
                <div className="option-left-content">
                  <span className="option-icon-badge badge-all">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                    </svg>
                  </span>
                  <span className="option-label">{allLabel}</span>
                </div>
                <div className="option-right-content">
                  {casesCount !== undefined && (
                    <span className="option-count-pill">{casesCount}</span>
                  )}
                  {value === "ALL" && (
                    <span className="option-checkmark">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </span>
                  )}
                </div>
              </button>
            )}

            {CRIME_CATEGORIES.map((cat) => {
              const isSelected = value === cat.id;
              const count = categoryCounts[cat.id];
              return (
                <button
                  key={cat.id}
                  type="button"
                  className={`dropdown-option-item ${isSelected ? "is-active-option" : ""}`}
                  onClick={() => {
                    onChange(cat.id);
                    setIsOpen(false);
                  }}
                  role="option"
                  aria-selected={isSelected}
                >
                  <div className="option-left-content">
                    <span
                      className="option-icon-badge"
                      style={{
                        background: cat.bg,
                        borderColor: cat.border,
                      }}
                    >
                      <CrimeCategoryIcon categoryId={cat.id} size={13} color={cat.color} />
                    </span>
                    <span className="option-label">{cat.label}</span>
                  </div>

                  <div className="option-right-content">
                    {count !== undefined && count > 0 && (
                      <span className="option-count-pill">{count}</span>
                    )}
                    {isSelected && (
                      <span className="option-checkmark">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={cat.color} strokeWidth="2.5">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <style jsx>{`
        .custom-category-dropdown {
          position: relative;
          width: 100%;
          font-family: inherit;
        }

        .dropdown-trigger-btn {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          height: 42px;
          padding: 0 0.85rem;
          border-radius: 10px;
          border: 1px solid #dce7f1;
          background: #f8fbfe;
          color: #1e293b;
          font-size: 0.82rem;
          font-weight: 650;
          cursor: pointer;
          transition: all 0.18s ease;
          gap: 0.55rem;
          user-select: none;
          box-shadow: none;
        }

        .dropdown-trigger-btn:hover {
          background: #ffffff;
          border-color: #bae6fd;
        }

        .dropdown-trigger-btn.is-open {
          background: #ffffff;
          border-color: #0787d1;
          box-shadow: 0 0 0 2.5px rgba(7, 135, 209, 0.15);
        }

        .dropdown-trigger-btn.has-filter {
          background: #f0f9ff;
          border-color: #b9e6fe;
        }

        .trigger-left-content {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .trigger-icon-box {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          border-radius: 6px;
          border: 1px solid transparent;
          flex-shrink: 0;
        }

        .trigger-icon-all {
          background: #e2e8f0;
          color: #475569;
        }

        .trigger-label {
          font-size: 0.8rem;
          font-weight: 650;
          color: #1e293b;
          text-overflow: ellipsis;
          overflow: hidden;
          white-space: nowrap;
        }

        .trigger-right-actions {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          flex-shrink: 0;
          margin-left: auto;
        }

        .trigger-clear-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: #e2e8f0;
          color: #475569;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .trigger-clear-btn:hover {
          background: #cbd5e1;
          color: #0f172a;
        }

        .trigger-chevron {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          color: #64748b;
          transition: transform 0.2s ease;
        }

        .trigger-chevron.rotate-up {
          transform: rotate(180deg);
        }

        .dropdown-popover-menu {
          position: absolute;
          top: calc(100% + 6px);
          left: 0;
          min-width: 260px;
          background: #ffffff;
          border: 1px solid #dce7f1;
          border-radius: 12px;
          box-shadow: 0 16px 36px rgba(15, 23, 42, 0.12), 0 4px 10px rgba(15, 23, 42, 0.04);
          z-index: 100;
          padding: 6px;
          animation: dropdownFadeIn 0.15s ease-out;
        }

        @keyframes dropdownFadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .dropdown-popover-header {
          padding: 6px 8px 4px;
          font-size: 0.65rem;
          font-weight: 800;
          letter-spacing: 0.08em;
          color: #94a3b8;
          border-bottom: 1px solid #f1f5f9;
          margin-bottom: 4px;
        }

        .dropdown-options-list {
          display: flex;
          flex-direction: column;
          gap: 2px;
          max-height: 290px;
          overflow-y: auto;
        }

        .dropdown-option-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          padding: 6px 8px;
          border-radius: 8px;
          background: transparent;
          border: none;
          cursor: pointer;
          text-align: left;
          transition: all 0.15s ease;
          gap: 0.5rem;
        }

        .dropdown-option-item:hover {
          background: #f1f5f9;
        }

        .dropdown-option-item.is-active-option {
          background: #eef2ff;
        }

        .option-left-content {
          display: flex;
          align-items: center;
          gap: 0.6rem;
          overflow: hidden;
        }

        .option-icon-badge {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          border-radius: 6px;
          border: 1px solid transparent;
          flex-shrink: 0;
        }

        .badge-all {
          background: #f1f5f9;
          border-color: #e2e8f0;
          color: #64748b;
        }

        .option-label {
          font-size: 0.78rem;
          font-weight: 600;
          color: #1e293b;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .option-right-content {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          margin-left: auto;
          flex-shrink: 0;
        }

        .option-count-pill {
          padding: 1px 6px;
          border-radius: 9999px;
          background: #f1f5f9;
          color: #64748b;
          font-size: 0.68rem;
          font-weight: 700;
        }

        .option-checkmark {
          display: flex;
          align-items: center;
        }
      `}</style>
    </div>
  );
}

export const PRIORITY_LEVELS = [
  { id: "CRITICAL", label: "Critical Threat", color: "#dc2626", bg: "#fef2f2", border: "#fecaca" },
  { id: "HIGH", label: "High Priority", color: "#ea580c", bg: "#fff7ed", border: "#fed7aa" },
  { id: "MEDIUM", label: "Medium Priority", color: "#0284c7", bg: "#f0f9ff", border: "#bae6fd" },
  { id: "LOW", label: "Routine / Low", color: "#64748b", bg: "#f8fafc", border: "#e2e8f0" },
];

// Helper to parse case metadata from description
export function parseCaseMeta(caseItem) {
  let meta = {
    category: "OTHER",
    priority: "MEDIUM",
    subStatus: caseItem.status === "CLOSED" ? "SOLVED" : "ACTIVE",
    incidentDate: null,
    location: null,
    leadOfficer: null,
    narrative: caseItem.description || "",
  };

  if (caseItem.description && typeof caseItem.description === "string") {
    const trimmed = caseItem.description.trim();
    if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed && typeof parsed === "object") {
          meta.category = parsed.category || meta.category;
          meta.priority = parsed.priority || meta.priority;
          meta.subStatus = parsed.subStatus || (caseItem.status === "CLOSED" ? "SOLVED" : "ACTIVE");
          meta.incidentDate = parsed.incidentDate || null;
          meta.location = parsed.location || null;
          meta.leadOfficer = parsed.leadOfficer || null;
          meta.narrative = parsed.narrative || "";
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

export function serializeCaseMeta({ category, priority, subStatus, incidentDate, location, leadOfficer, narrative }) {
  return JSON.stringify({
    category: category || "OTHER",
    priority: priority || "MEDIUM",
    subStatus: subStatus || "ACTIVE",
    incidentDate: incidentDate || null,
    location: location || null,
    leadOfficer: leadOfficer || null,
    narrative: narrative || "",
  });
}

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [errorState, setErrorState] = useState(null);
  const [feedbackBanner, setFeedbackBanner] = useState(null);

  // Search & Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL"); // ALL | ACTIVE | ON_HOLD | SOLVED
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL"); // ALL | CRITICAL | HIGH

  // Create Case Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: "",
    category: "HOMICIDE",
    priority: "HIGH",
    incidentDate: "",
    location: "",
    leadOfficer: "",
    narrative: "",
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState(null);

  // Delete Case Modal
  const [caseToDelete, setCaseToDelete] = useState(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  // Status Updating State
  const [updatingCaseId, setUpdatingCaseId] = useState(null);

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
        // Handled by apiClient: auto redirect
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

  // Derived Cases with Parsed Metadata
  const enrichedCases = useMemo(() => {
    return cases.map((c) => ({
      ...c,
      meta: parseCaseMeta(c),
    }));
  }, [cases]);

  // KPIs
  const kpis = useMemo(() => {
    const total = enrichedCases.length;
    const active = enrichedCases.filter((c) => c.meta.subStatus === "ACTIVE" && c.status === "OPEN").length;
    const onHold = enrichedCases.filter((c) => c.meta.subStatus === "ON_HOLD" && c.status === "OPEN").length;
    const solved = enrichedCases.filter((c) => c.status === "CLOSED" || c.meta.subStatus === "SOLVED").length;
    const critical = enrichedCases.filter((c) => c.meta.priority === "CRITICAL" && c.status === "OPEN").length;

    return { total, active, onHold, solved, critical };
  }, [enrichedCases]);

  // Category counts
  const categoryCounts = useMemo(() => {
    const counts = {};
    enrichedCases.forEach((c) => {
      const cat = c.meta?.category || "OTHER";
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return counts;
  }, [enrichedCases]);

  // Filtered Cases
  const filteredCases = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return enrichedCases.filter((c) => {
      // Status Filter
      if (statusFilter === "ACTIVE" && (c.status !== "OPEN" || c.meta.subStatus !== "ACTIVE")) return false;
      if (statusFilter === "ON_HOLD" && (c.status !== "OPEN" || c.meta.subStatus !== "ON_HOLD")) return false;
      if (statusFilter === "SOLVED" && c.status !== "CLOSED" && c.meta.subStatus !== "SOLVED") return false;

      // Category Filter
      if (categoryFilter !== "ALL" && c.meta.category !== categoryFilter) return false;

      // Priority Filter
      if (priorityFilter !== "ALL" && c.meta.priority !== priorityFilter) return false;

      // Search Query
      if (q) {
        const catObj = CRIME_CATEGORIES.find((cat) => cat.id === c.meta.category);
        const searchStr = `${c.title || ""} ${c.case_number || ""} ${c.meta.location || ""} ${c.meta.narrative || ""} ${catObj?.label || ""}`.toLowerCase();
        if (!searchStr.includes(q)) return false;
      }

      return true;
    });
  }, [enrichedCases, searchTerm, statusFilter, categoryFilter, priorityFilter]);

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    try {
      const d = new Date(dateString);
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  // Handle Case Creation with Rich Details
  const handleCreateCase = async (e) => {
    e.preventDefault();
    if (!createForm.title.trim()) {
      setCreateError("Case title is required.");
      return;
    }

    setCreateSubmitting(true);
    setCreateError(null);

    try {
      const serializedDescription = serializeCaseMeta({
        category: createForm.category,
        priority: createForm.priority,
        subStatus: "ACTIVE",
        incidentDate: createForm.incidentDate || null,
        location: createForm.location.trim() || null,
        leadOfficer: createForm.leadOfficer.trim() || null,
        narrative: createForm.narrative.trim() || null,
      });

      await apiClient("/api/cases", {
        method: "POST",
        body: {
          title: createForm.title.trim(),
          description: serializedDescription,
          status: "OPEN",
        },
      });

      setIsCreateModalOpen(false);
      setCreateForm({
        title: "",
        category: "HOMICIDE",
        priority: "HIGH",
        incidentDate: "",
        location: "",
        leadOfficer: "",
        narrative: "",
      });
      setFeedbackBanner({ type: "success", text: "New case record created successfully." });
      fetchCases(true);
      setTimeout(() => setFeedbackBanner(null), 4000);
    } catch (err) {
      setCreateError(err.message || "Failed to create investigation case.");
    } finally {
      setCreateSubmitting(false);
    }
  };

  // Handle Status Update (Active / On Hold / Solved)
  const handleStatusChange = async (caseItem, newSubStatus) => {
    if (updatingCaseId === caseItem.id) return;
    setUpdatingCaseId(caseItem.id);

    const newDbStatus = newSubStatus === "SOLVED" ? "CLOSED" : "OPEN";
    const updatedDescription = serializeCaseMeta({
      ...caseItem.meta,
      subStatus: newSubStatus,
    });

    try {
      await apiClient(`/api/cases/${caseItem.id}`, {
        method: "PATCH",
        body: {
          status: newDbStatus,
          description: updatedDescription,
        },
      });

      setFeedbackBanner({
        type: "success",
        text: `Case ${caseItem.case_number} marked as ${newSubStatus === "ACTIVE" ? "Active Investigation" : newSubStatus === "ON_HOLD" ? "On Hold" : "Solved / Closed"}.`,
      });
      fetchCases(true);
      setTimeout(() => setFeedbackBanner(null), 4000);
    } catch (err) {
      setFeedbackBanner({ type: "error", text: err.message || "Failed to update case status." });
      setTimeout(() => setFeedbackBanner(null), 4000);
    } finally {
      setUpdatingCaseId(null);
    }
  };

  // Handle Case Deletion
  const handleDeleteCase = async () => {
    if (!caseToDelete || deleteSubmitting) return;
    setDeleteSubmitting(true);
    setDeleteError(null);

    try {
      await apiClient(`/api/cases/${caseToDelete.id}`, {
        method: "DELETE",
      });

      const deletedTitle = caseToDelete.title;
      setCaseToDelete(null);
      setFeedbackBanner({ type: "success", text: `Case "${deletedTitle}" deleted successfully.` });
      fetchCases(true);
      setTimeout(() => setFeedbackBanner(null), 4000);
    } catch (err) {
      setDeleteError(err.message || "Failed to delete case file.");
    } finally {
      setDeleteSubmitting(false);
    }
  };

  return (
    <AuthLayout>
      <div className="dashboard-root">
        {/* FEEDBACK BANNER */}
        {feedbackBanner && (
          <div className={`notification-pill ${feedbackBanner.type === "error" ? "notif-error" : "notif-success"}`}>
            <span>{feedbackBanner.text}</span>
            <button onClick={() => setFeedbackBanner(null)}>✕</button>
          </div>
        )}

        {/* 1. CENTRALIZED HERO HEADER */}
        <header className="central-command-hero">
          <div className="hero-status-pill">
            <span className="live-radar-dot" />
            <span>CRIMELENS CASE INTELLIGENCE</span>
          </div>

          <h1 className="central-hero-title">Forensic & Case Investigation Hub</h1>

          <p className="central-hero-desc">
            Centralized intelligence platform for detectives, forensic specialists, and law enforcement teams. Cross-reference disparate case evidence, track suspect syndicates, and maintain chain-of-custody across all departmental case files in real time.
          </p>

          <div className="central-hero-actions">
            <button onClick={() => setIsCreateModalOpen(true)} className="action-btn-primary">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              <span>New Investigation File</span>
            </button>

            <button
              onClick={() => fetchCases(true)}
              className="action-btn-secondary"
              disabled={loading || refreshing}
              title="Refresh Repository"
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className={refreshing ? "spin-animation" : ""}
              >
                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
              </svg>
              <span>{refreshing ? "Syncing…" : "Refresh"}</span>
            </button>
          </div>
        </header>

        {/* 2. CENTRALIZED SEARCH & CLASSIFICATION BAR */}
        {!loading && !errorState && (
          <section className="central-search-shelf">
            <div className="unified-search-filter-box">
              {/* Category Dropdown */}
              <div className="category-select-wrapper">
                <CategoryFilterDropdown
                  value={categoryFilter}
                  onChange={setCategoryFilter}
                  casesCount={enrichedCases.length}
                  categoryCounts={categoryCounts}
                  includeAll={true}
                  allLabel="All Crime Categories"
                />
              </div>

              <div className="search-shelf-divider" />

              {/* Search Field */}
              <div className="search-field-box">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <input
                  type="text"
                  placeholder="Search cases by title, case ID, location, or narrative…"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="search-input"
                />
                {searchTerm && (
                  <button className="search-clear-btn" onClick={() => setSearchTerm("")} title="Clear search">
                    ✕
                  </button>
                )}
              </div>

              {/* Quick Reset if filtered */}
              {(categoryFilter !== "ALL" || searchTerm) && (
                <button
                  type="button"
                  className="search-shelf-reset-btn"
                  onClick={() => {
                    setCategoryFilter("ALL");
                    setSearchTerm("");
                  }}
                  title="Reset classification and search"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                  <span>Reset</span>
                </button>
              )}
            </div>
          </section>
        )}

        {/* 4. CONTENT AREA: ERROR / LOADING / EMPTY / GRID */}
        {errorState && (
          <div className="dashboard-error-card">
            <h3>{errorState.title}</h3>
            <p>{errorState.message}</p>
            <button onClick={() => fetchCases(true)} className="action-btn-secondary">
              Retry Connection
            </button>
          </div>
        )}

        {loading && (
          <div className="dashboard-loading-box">
            <span className="loading-radar-ring" />
            <p>Loading authorized investigation records…</p>
          </div>
        )}

        {!loading && !errorState && filteredCases.length === 0 && (
          <div className="dashboard-empty-card">
            <div className="empty-icon-circle">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <h3>No Investigation Records Found</h3>
            <p>
              {searchTerm || statusFilter !== "ALL" || categoryFilter !== "ALL" || priorityFilter !== "ALL"
                ? "No case file matches your selected filters. Try resetting the filters or clearing the search term."
                : "There are currently no cases recorded in your clearance workspace. Create your first investigation file to begin."}
            </p>
            {(searchTerm || statusFilter !== "ALL" || categoryFilter !== "ALL" || priorityFilter !== "ALL") && (
              <button
                onClick={() => {
                  setSearchTerm("");
                  setStatusFilter("ALL");
                  setCategoryFilter("ALL");
                  setPriorityFilter("ALL");
                }}
                className="action-btn-secondary"
              >
                Reset Filters
              </button>
            )}
          </div>
        )}

        {!loading && !errorState && filteredCases.length > 0 && (
          <div className="cases-cards-grid">
            {filteredCases.map((c) => {
              const meta = c.meta;
              const categoryConfig = CRIME_CATEGORIES.find((cat) => cat.id === meta.category) || CRIME_CATEGORIES[CRIME_CATEGORIES.length - 1];
              const priorityConfig = PRIORITY_LEVELS.find((p) => p.id === meta.priority) || PRIORITY_LEVELS[2];

              const isUpdating = updatingCaseId === c.id;

              return (
                <article key={c.id} className="case-record-card">
                  {/* CARD HEADER: Category (Left) + Status Badge (Right) */}
                  <div className="card-top-header">
                    <span
                      className="card-category-badge"
                      style={{
                        color: categoryConfig.color,
                        background: categoryConfig.bg,
                        borderColor: categoryConfig.border,
                      }}
                    >
                      <CrimeCategoryIcon categoryId={categoryConfig.id} size={12} color={categoryConfig.color} />
                      <span>{categoryConfig.label}</span>
                    </span>

                    <div className="card-status-wrapper">
                      {meta.subStatus === "ACTIVE" && (
                        <span className="status-badge status-active">
                          <span className="status-pulse-dot" /> ACTIVE
                        </span>
                      )}
                      {meta.subStatus === "ON_HOLD" && (
                        <span className="status-badge status-hold">
                          <span className="status-dot dot-amber" /> ON HOLD
                        </span>
                      )}
                      {meta.subStatus === "SOLVED" && (
                        <span className="status-badge status-solved">
                          <span className="status-dot dot-blue" /> SOLVED
                        </span>
                      )}
                    </div>
                  </div>

                  {/* CASE ID & TITLE */}
                  <div className="card-title-section">
                    <span className="case-uuid-pill font-mono">{c.case_number}</span>
                    <Link href={`/cases/${c.id}`} className="card-title-link">
                      <h3 className="card-case-title">{c.title}</h3>
                    </Link>
                  </div>

                  {/* METADATA LINE */}
                  <div className="card-meta-line">
                    <span className="meta-item" title="Case Created Date">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                        <line x1="16" y1="2" x2="16" y2="6" />
                        <line x1="8" y1="2" x2="8" y2="6" />
                        <line x1="3" y1="10" x2="21" y2="10" />
                      </svg>
                      <span>Initiated: {formatDate(c.created_at)}</span>
                    </span>

                    {meta.location && (
                      <span className="meta-item" title="Jurisdiction / Location">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                          <circle cx="12" cy="10" r="3" />
                        </svg>
                        <span>{meta.location}</span>
                      </span>
                    )}

                    {meta.incidentDate && (
                      <span className="meta-item" title="Incident Date">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="10" />
                          <polyline points="12 6 12 12 16 14" />
                        </svg>
                        <span>Incident: {formatDate(meta.incidentDate)}</span>
                      </span>
                    )}
                  </div>

                  {/* NARRATIVE PREVIEW */}
                  <p className="card-narrative-preview">
                    {meta.narrative || "Investigation dossier registered in the authorized forensic case repository."}
                  </p>

                  {/* CARD ACTIONS FOOTER */}
                  <div className="card-actions-footer">
                    <Link href={`/cases/${c.id}`} className="view-workspace-action-btn">
                      <span>Open File</span>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="5" y1="12" x2="19" y2="12" />
                        <polyline points="12 5 19 12 12 19" />
                      </svg>
                    </Link>

                    <div className="card-secondary-actions">
                      {/* STATUS SELECTOR */}
                      <select
                        value={meta.subStatus}
                        onChange={(e) => handleStatusChange(c, e.target.value)}
                        disabled={isUpdating}
                        className="quick-status-selector"
                        title="Change Case Status"
                      >
                        <option value="ACTIVE">Active</option>
                        <option value="ON_HOLD">On Hold</option>
                        <option value="SOLVED">Solved</option>
                      </select>

                      {/* DELETE BUTTON */}
                      <button
                        onClick={() => setCaseToDelete(c)}
                        className="delete-case-btn"
                        title="Delete Investigation Record"
                        aria-label="Delete Case"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {/* 5. CREATE CASE MODAL */}
        {isCreateModalOpen && (
          <div
            className="modal-backdrop-layer"
            onClick={(e) => {
              if (e.target === e.currentTarget && !createSubmitting) setIsCreateModalOpen(false);
            }}
          >
            <div className="modal-dialog-box modal-dialog-wide">
              <div className="modal-top-bar">
                <div className="modal-title-wrap">
                  <span className="modal-kicker">NEW INVESTIGATION</span>
                  <h2>Initiate Case File</h2>
                </div>
                <button
                  onClick={() => setIsCreateModalOpen(false)}
                  className="modal-close-cross-btn"
                  disabled={createSubmitting}
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateCase} className="modal-form-body">
                {createError && <div className="modal-error-notice">{createError}</div>}

                {/* ROW 1: Title */}
                <div className="modal-input-group">
                  <label htmlFor="modal-case-title">
                    Case Title / Codename <span className="star-required">*</span>
                  </label>
                  <input
                    id="modal-case-title"
                    type="text"
                    value={createForm.title}
                    onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                    placeholder="e.g. Operation Silk Highway, Sector 14 Extortion Ring"
                    disabled={createSubmitting}
                    required
                    maxLength={255}
                    className="modal-text-input"
                  />
                </div>

                {/* ROW 2: Crime Category & Priority */}
                <div className="modal-two-column-row">
                  <div className="modal-input-group">
                    <label htmlFor="modal-case-category">
                      Crime Category / Case Type <span className="star-required">*</span>
                    </label>
                    <CategoryFilterDropdown
                      value={createForm.category}
                      onChange={(catId) => setCreateForm({ ...createForm, category: catId })}
                      includeAll={false}
                      allLabel="Select Category"
                      disabled={createSubmitting}
                    />
                  </div>

                  <div className="modal-input-group">
                    <label htmlFor="modal-case-priority">
                      Priority / Threat Severity <span className="star-required">*</span>
                    </label>
                    <select
                      id="modal-case-priority"
                      value={createForm.priority}
                      onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                      disabled={createSubmitting}
                      className="modal-select-input"
                    >
                      {PRIORITY_LEVELS.map((pri) => (
                        <option key={pri.id} value={pri.id}>
                          {pri.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* ROW 3: Incident Date & Location */}
                <div className="modal-two-column-row">
                  <div className="modal-input-group">
                    <label htmlFor="modal-incident-date">Date of Incident</label>
                    <input
                      id="modal-incident-date"
                      type="date"
                      value={createForm.incidentDate}
                      onChange={(e) => setCreateForm({ ...createForm, incidentDate: e.target.value })}
                      disabled={createSubmitting}
                      className="modal-text-input"
                    />
                  </div>

                  <div className="modal-input-group">
                    <label htmlFor="modal-location">Location / Police Station Jurisdiction</label>
                    <input
                      id="modal-location"
                      type="text"
                      value={createForm.location}
                      onChange={(e) => setCreateForm({ ...createForm, location: e.target.value })}
                      placeholder="e.g. South Port Wharf, Sector 4"
                      disabled={createSubmitting}
                      className="modal-text-input"
                    />
                  </div>
                </div>

                {/* ROW 4: Lead Investigator */}
                <div className="modal-input-group">
                  <label htmlFor="modal-lead-officer">Lead Investigator / Special Investigation Unit</label>
                  <input
                    id="modal-lead-officer"
                    type="text"
                    value={createForm.leadOfficer}
                    onChange={(e) => setCreateForm({ ...createForm, leadOfficer: e.target.value })}
                    placeholder="e.g. Inspector R. Sharma, Anti-Corruption Branch"
                    disabled={createSubmitting}
                    className="modal-text-input"
                  />
                </div>

                {/* ROW 5: Narrative Scope */}
                <div className="modal-input-group">
                  <label htmlFor="modal-narrative">Initial Case Narrative & Operational Scope</label>
                  <textarea
                    id="modal-narrative"
                    value={createForm.narrative}
                    onChange={(e) => setCreateForm({ ...createForm, narrative: e.target.value })}
                    placeholder="Provide overview of reported incident, suspects identified, or intelligence lead..."
                    disabled={createSubmitting}
                    rows={3}
                    className="modal-textarea-input"
                  />
                </div>

                <div className="modal-action-buttons-bar">
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="modal-secondary-cancel-btn"
                    disabled={createSubmitting}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="modal-primary-submit-btn"
                    disabled={createSubmitting || !createForm.title.trim()}
                  >
                    {createSubmitting ? "Creating File…" : "Create Investigation File"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* 6. DELETE CASE CONFIRMATION DIALOG */}
        {caseToDelete && (
          <div
            className="modal-backdrop-layer"
            onClick={(e) => {
              if (e.target === e.currentTarget && !deleteSubmitting) setCaseToDelete(null);
            }}
          >
            <div className="modal-dialog-box modal-dialog-danger">
              <div className="modal-top-bar">
                <div className="modal-title-wrap">
                  <span className="modal-kicker kicker-danger">DANGER ZONE</span>
                  <h2>Delete Investigation Case</h2>
                </div>
                <button
                  onClick={() => setCaseToDelete(null)}
                  className="modal-close-cross-btn"
                  disabled={deleteSubmitting}
                >
                  ✕
                </button>
              </div>

              <div className="delete-dialog-body">
                {deleteError && <div className="modal-error-notice">{deleteError}</div>}

                <div className="delete-warning-card">
                  <p>
                    Are you sure you want to permanently delete case record{" "}
                    <strong>"{caseToDelete.title}"</strong> ({caseToDelete.case_number})?
                  </p>
                  <p className="delete-critical-notice">
                    ⚠️ This action cannot be undone. All associated documents, extracted entities, relationships, and forensic ledger blocks for this case will be permanently removed.
                  </p>
                </div>

                <div className="modal-action-buttons-bar">
                  <button
                    type="button"
                    onClick={() => setCaseToDelete(null)}
                    className="modal-secondary-cancel-btn"
                    disabled={deleteSubmitting}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleDeleteCase}
                    className="modal-danger-confirm-btn"
                    disabled={deleteSubmitting}
                  >
                    {deleteSubmitting ? "Deleting Case…" : "Confirm Permanent Deletion"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <style jsx>{`
          .dashboard-root {
            max-width: 1440px;
            margin: 0 auto;
            padding: 1.5rem clamp(1.25rem, 3.5vw, 2.5rem) 4rem;
            display: flex;
            flex-direction: column;
            gap: 1.75rem;
          }

          /* FEEDBACK NOTIFICATION */
          .notification-pill {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.65rem 1rem;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;
          }

          .notif-success {
            background: #edfcf6;
            border: 1px solid #b6ebd4;
            color: #078158;
          }

          .notif-error {
            background: #fff5f5;
            border: 1px solid #f5c5cb;
            color: #b33441;
          }

          .notification-pill button {
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            font-size: 0.9rem;
          }

          /* 1. CENTRALIZED HERO HEADER */
          .central-command-hero {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            max-width: 860px;
            margin: 1.25rem auto 0;
            padding: 0 1rem;
          }

          .hero-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            background: #e7f5ff;
            border: 1px solid #bae6fd;
            color: #0369a1;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin-bottom: 0.85rem;
          }

          .live-radar-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #0787d1;
            box-shadow: 0 0 0 3px rgba(7, 135, 209, 0.18);
          }

          .central-hero-title {
            margin: 0;
            font-size: clamp(1.85rem, 3.4vw, 2.5rem);
            font-weight: 800;
            letter-spacing: -0.035em;
            color: #111e33;
            line-height: 1.2;
          }

          .central-hero-desc {
            margin: 0.95rem 0 1.6rem;
            font-size: 0.94rem;
            line-height: 1.65;
            color: #556c86;
            max-width: 720px;
          }

          .central-hero-actions {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.85rem;
            flex-wrap: wrap;
          }

          .action-btn-primary {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.65rem 1.25rem;
            border-radius: 9px;
            border: 1px solid #0787d1;
            background: #0787d1;
            color: #ffffff;
            font-size: 0.84rem;
            font-weight: 650;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(7, 135, 209, 0.18);
            transition: all 0.18s ease;
          }

          .action-btn-primary:hover {
            background: #056eaf;
            border-color: #056eaf;
            transform: translateY(-1px);
          }

          .action-btn-secondary {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.65rem 1.15rem;
            border-radius: 9px;
            border: 1px solid #d4e1ec;
            background: #ffffff;
            color: #556c86;
            font-size: 0.84rem;
            font-weight: 650;
            cursor: pointer;
            transition: all 0.18s ease;
          }

          .action-btn-secondary:hover:not(:disabled) {
            background: #f4fbfe;
            color: #0787d1;
            border-color: #bce1f7;
          }

          .spin-animation {
            animation: spin 0.8s linear infinite;
          }

          @keyframes spin {
            to { transform: rotate(360deg); }
          }

          /* 2. CENTRALIZED SEARCH & CLASSIFICATION BAR */
          .central-search-shelf {
            width: 100%;
            display: flex;
            justify-content: center;
            margin: 1.5rem auto 1.5rem;
          }

          .unified-search-filter-box {
            display: flex;
            align-items: center;
            width: 100%;
            max-width: 820px;
            background: #ffffff;
            border: 1px solid #dce7f1;
            border-radius: 14px;
            padding: 0.45rem 0.6rem;
            box-shadow: 0 8px 24px rgba(34, 72, 104, 0.05);
            gap: 0.6rem;
            transition: all 0.2s ease;
          }

          .unified-search-filter-box:focus-within {
            border-color: #38bdf8;
            box-shadow: 0 10px 30px rgba(7, 135, 209, 0.1), 0 0 0 3px rgba(7, 135, 209, 0.08);
          }

          .category-select-wrapper {
            min-width: 220px;
            flex-shrink: 0;
          }

          .search-shelf-divider {
            width: 1px;
            height: 28px;
            background: #e2e8f0;
            flex-shrink: 0;
          }

          .search-field-box {
            display: flex;
            align-items: center;
            flex: 1;
            gap: 0.65rem;
            padding: 0 0.5rem;
            min-width: 0;
          }

          .search-input {
            width: 100%;
            border: none;
            background: transparent;
            outline: none;
            font-size: 0.88rem;
            color: #162033;
            padding: 0.5rem 0;
          }

          .search-input::placeholder {
            color: #8c9eb2;
          }

          .search-clear-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: #f1f5f9;
            border: none;
            color: #64748b;
            font-size: 0.72rem;
            cursor: pointer;
            transition: all 0.15s ease;
            flex-shrink: 0;
          }

          .search-clear-btn:hover {
            background: #e2e8f0;
            color: #0f172a;
          }

          .search-shelf-reset-btn {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.45rem 0.8rem;
            border-radius: 8px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            color: #475569;
            font-size: 0.78rem;
            font-weight: 650;
            cursor: pointer;
            transition: all 0.15s ease;
            white-space: nowrap;
            flex-shrink: 0;
          }

          .search-shelf-reset-btn:hover {
            background: #f1f5f9;
            color: #0f172a;
            border-color: #cbd5e1;
          }

          @media (max-width: 640px) {
            .unified-search-filter-box {
              flex-direction: column;
              align-items: stretch;
              padding: 0.65rem;
              gap: 0.65rem;
            }
            .search-shelf-divider {
              display: none;
            }
            .category-select-wrapper {
              min-width: 100%;
            }
            .search-field-box {
              padding: 0;
            }
          }

          /* 4. CARDS GRID & RESPONSIVE LAYOUT */
          .cases-cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.35rem;
          }

          .case-record-card {
            padding: 1.35rem;
            border-radius: 14px;
            background: #ffffff;
            border: 1px solid #dce7f1;
            box-shadow: 0 4px 18px rgba(34, 72, 104, 0.04);
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
          }

          .case-record-card:hover {
            transform: translateY(-2px);
            border-color: #bae6fd;
            box-shadow: 0 12px 28px rgba(34, 72, 104, 0.08);
          }

          .card-top-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
          }

          .card-category-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            border: 1px solid;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.01em;
          }

          .card-status-wrapper {
            display: flex;
            align-items: center;
            flex-shrink: 0;
          }

          .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.38rem;
            padding: 0.22rem 0.65rem;
            border-radius: 9999px;
            font-size: 0.67rem;
            font-weight: 800;
            letter-spacing: 0.04em;
          }

          .status-active {
            background: #ecfdf5;
            color: #065f46;
            border: 1px solid #a7f3d0;
          }

          .status-hold {
            background: #fffbeb;
            color: #92400e;
            border: 1px solid #fde68a;
          }

          .status-solved {
            background: #eff6ff;
            color: #1e40af;
            border: 1px solid #bfdbfe;
          }

          .status-pulse-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 0 2.5px rgba(16, 185, 129, 0.25);
          }

          .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
          }

          .dot-amber { background: #f59e0b; }
          .dot-blue { background: #3b82f6; }

          .card-title-section {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
          }

          .case-uuid-pill {
            display: inline-block;
            align-self: flex-start;
            font-size: 0.7rem;
            font-weight: 700;
            color: #0369a1;
            background: #f0f9ff;
            padding: 0.12rem 0.5rem;
            border-radius: 4px;
            border: 1px solid #bae6fd;
            letter-spacing: 0.02em;
          }

          .card-title-link {
            text-decoration: none;
          }

          .card-case-title {
            margin: 0;
            font-size: 1.12rem;
            font-weight: 750;
            color: #162033;
            line-height: 1.35;
            letter-spacing: -0.015em;
            transition: color 0.15s ease;
          }

          .card-case-title:hover {
            color: #0787d1;
          }

          .card-meta-line {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            flex-wrap: wrap;
            font-size: 0.73rem;
            color: #64748b;
          }

          .meta-item {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            font-weight: 500;
          }

          .meta-item svg {
            color: #94a3b8;
            flex-shrink: 0;
          }

          .card-narrative-preview {
            margin: 0;
            font-size: 0.82rem;
            line-height: 1.55;
            color: #556c86;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            min-height: 2.5em;
          }

          .card-actions-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            padding-top: 0.85rem;
            border-top: 1px solid #f1f5f9;
            margin-top: auto;
            flex-wrap: wrap;
          }

          .view-workspace-action-btn {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.48rem 0.95rem;
            border-radius: 8px;
            border: 1px solid #0787d1;
            background: #e7f5ff;
            color: #0787d1;
            font-size: 0.78rem;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.18s ease;
          }

          .view-workspace-action-btn:hover {
            background: #0787d1;
            color: #ffffff;
            box-shadow: 0 4px 10px rgba(7, 135, 209, 0.2);
          }

          .card-secondary-actions {
            display: flex;
            align-items: center;
            gap: 0.45rem;
          }

          .quick-status-selector {
            height: 34px;
            padding: 0 0.65rem;
            border-radius: 8px;
            border: 1px solid #dce7f1;
            background: #f8fafc;
            font-size: 0.75rem;
            font-weight: 600;
            color: #334155;
            cursor: pointer;
            outline: none;
            transition: border-color 0.15s ease;
          }

          .quick-status-selector:focus {
            border-color: #0787d1;
          }

          .delete-case-btn {
            width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            border: 1px solid #ecdbe0;
            background: #ffffff;
            color: #8c9eb2;
            cursor: pointer;
            transition: all 0.15s ease;
          }

          .delete-case-btn:hover {
            background: #fef2f2;
            border-color: #fca5a5;
            color: #dc2626;
          }

          @media (max-width: 768px) {
            .cases-cards-grid {
              grid-template-columns: 1fr;
              gap: 1rem;
            }
          }

          @media (max-width: 440px) {
            .card-actions-footer {
              flex-direction: column;
              align-items: stretch;
              gap: 0.65rem;
            }
            .view-workspace-action-btn {
              justify-content: center;
            }
            .card-secondary-actions {
              justify-content: space-between;
              width: 100%;
            }
            .quick-status-selector {
              flex: 1;
            }
          }

          /* STATES */
          .dashboard-loading-box,
          .dashboard-empty-card,
          .dashboard-error-card {
            padding: 3rem 1.5rem;
            text-align: center;
            border-radius: 14px;
            background: #ffffff;
            border: 1px dashed #dce7f1;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.65rem;
          }

          .empty-icon-circle {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: #eaf5fd;
            display: grid;
            place-items: center;
            font-size: 1.35rem;
          }

          .dashboard-empty-card h3,
          .dashboard-error-card h3 {
            margin: 0;
            font-size: 1.05rem;
            color: #162033;
          }

          .dashboard-empty-card p,
          .dashboard-error-card p {
            margin: 0;
            font-size: 0.82rem;
            color: #64778f;
            max-width: 480px;
            line-height: 1.5;
          }

          .loading-radar-ring {
            width: 36px;
            height: 36px;
            border: 3px solid #e1ecf4;
            border-top-color: #0787d1;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
          }

          /* 5. MODAL DIALOGS */
          .modal-backdrop-layer {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(22, 32, 51, 0.45);
            backdrop-filter: blur(4px);
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
          }

          .modal-dialog-box {
            background: #ffffff;
            border-radius: 14px;
            border: 1px solid #dce7f1;
            box-shadow: 0 20px 45px rgba(22, 32, 51, 0.18);
            width: 100%;
            max-width: 540px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            max-height: 90vh;
          }

          .modal-dialog-wide {
            max-width: 640px;
          }

          .modal-dialog-danger {
            max-width: 500px;
          }

          .modal-top-bar {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            padding: 1.2rem 1.4rem;
            background: #f8fbfe;
            border-bottom: 1px solid #dce7f1;
          }

          .modal-kicker {
            font-size: 0.62rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            color: #0787d1;
            display: block;
            margin-bottom: 0.15rem;
          }

          .kicker-danger {
            color: #dc2626;
          }

          .modal-title-wrap h2 {
            margin: 0;
            font-size: 1.15rem;
            font-weight: 750;
            color: #162033;
          }

          .modal-close-cross-btn {
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
            border: 1px solid #dce7f1;
            background: #ffffff;
            color: #64778f;
            cursor: pointer;
            font-size: 0.85rem;
          }

          .modal-close-cross-btn:hover {
            color: #ef4444;
            background: #fef2f2;
          }

          .modal-form-body {
            padding: 1.4rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
          }

          .modal-error-notice {
            padding: 0.65rem 0.85rem;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            color: #dc2626;
            font-size: 0.78rem;
          }

          .modal-input-group {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
          }

          .modal-input-group label {
            font-size: 0.74rem;
            font-weight: 700;
            color: #37485e;
          }

          .star-required {
            color: #dc2626;
          }

          .modal-two-column-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
          }

          .modal-text-input,
          .modal-select-input,
          .modal-textarea-input {
            width: 100%;
            padding: 0.65rem 0.85rem;
            border-radius: 8px;
            border: 1px solid #d4e1ec;
            background: #ffffff;
            font-size: 0.82rem;
            color: #1e2c3f;
            outline: none;
            font-family: inherit;
          }

          .modal-text-input:focus,
          .modal-select-input:focus,
          .modal-textarea-input:focus {
            border-color: #0787d1;
            box-shadow: 0 0 0 2px rgba(7, 135, 209, 0.12);
          }

          .modal-textarea-input {
            resize: vertical;
          }

          .modal-action-buttons-bar {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.65rem;
            padding-top: 0.65rem;
            border-top: 1px solid #eef3f7;
            margin-top: 0.5rem;
          }

          .modal-secondary-cancel-btn {
            padding: 0.65rem 1.1rem;
            border-radius: 8px;
            border: 1px solid #d4e1ec;
            background: #ffffff;
            color: #556c86;
            font-size: 0.8rem;
            font-weight: 650;
            cursor: pointer;
          }

          .modal-secondary-cancel-btn:hover {
            background: #f4fbfe;
          }

          .modal-primary-submit-btn {
            padding: 0.65rem 1.25rem;
            border-radius: 8px;
            border: 1px solid #0787d1;
            background: #0787d1;
            color: #ffffff;
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.16s ease;
          }

          .modal-primary-submit-btn:hover:not(:disabled) {
            background: #056eaf;
          }

          .modal-primary-submit-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }

          /* DELETE CONFIRM BODY */
          .delete-dialog-body {
            padding: 1.4rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
          }

          .delete-warning-card {
            padding: 1rem;
            border-radius: 8px;
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #991b1b;
            font-size: 0.84rem;
            line-height: 1.5;
          }

          .delete-critical-notice {
            margin: 0.5rem 0 0;
            font-size: 0.76rem;
            color: #b91c1c;
            font-weight: 600;
          }

          .modal-danger-confirm-btn {
            padding: 0.65rem 1.25rem;
            border-radius: 8px;
            border: 1px solid #dc2626;
            background: #dc2626;
            color: #ffffff;
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.16s ease;
          }

          .modal-danger-confirm-btn:hover:not(:disabled) {
            background: #b91c1c;
          }

          /* RESPONSIVE */
          @media (max-width: 1024px) {
            .kpi-metrics-ribbon {
              grid-template-columns: repeat(2, 1fr);
            }
          }

          @media (max-width: 768px) {
            .command-header {
              flex-direction: column;
              align-items: stretch;
            }

            .command-actions-row {
              width: 100%;
            }

            .command-actions-row button {
              flex: 1;
            }

            .kpi-metrics-ribbon {
              grid-template-columns: 1fr;
            }

            .filter-controls-shelf {
              flex-direction: column;
              align-items: stretch;
            }

            .search-and-select-group {
              flex-direction: column;
              align-items: stretch;
            }

            .modal-two-column-row {
              grid-template-columns: 1fr;
            }

            .cases-cards-grid {
              grid-template-columns: 1fr;
            }
          }
        `}</style>
      </div>
    </AuthLayout>
  );
}
