"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { apiClient } from "../lib/apiClient";
import AuthLayout from "../components/Layout";

export const CRIME_CATEGORIES = [
  { id: "HOMICIDE", label: "Homicide & Murder", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
  { id: "ORGANIZED_CRIME", label: "Organized Crime & Gang", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
  { id: "FINANCIAL_FRAUD", label: "Financial Fraud & Laundering", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
  { id: "CYBERCRIME", label: "Cybercrime & Digital Extortion", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
  { id: "NARCOTICS", label: "Narcotics & Contraband", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
  { id: "KIDNAPPING", label: "Kidnapping & Missing Person", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
  { id: "ARMED_ROBBERY", label: "Armed Robbery & Heist", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
  { id: "CORRUPTION", label: "Public Corruption & Bribery", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
  { id: "OTHER", label: "General Investigation", color: "#94a3b8", bg: "rgba(148, 163, 184, 0.10)", border: "rgba(148, 163, 184, 0.20)" },
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

export function highlightMatch(text, query) {
  if (!text) return "";
  if (!query) return text;
  const q = query.trim();
  if (!q) return text;
  const index = text.toLowerCase().indexOf(q.toLowerCase());
  if (index === -1) return text;
  return (
    <>
      {text.slice(0, index)}
      <mark className="search-highlight">{text.slice(index, index + q.length)}</mark>
      {text.slice(index + q.length)}
    </>
  );
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
          border: 1px solid #e2e8f0;
          background: #ffffff;
          color: #0f172a;
          font-size: 0.82rem;
          font-weight: 650;
          cursor: pointer;
          transition: all 0.18s ease;
          gap: 0.55rem;
          user-select: none;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        }

        .dropdown-trigger-btn:hover {
          background: #f8fafc;
          border-color: #cbd5e1;
        }

        .dropdown-trigger-btn.is-open {
          background: #ffffff;
          border-color: #2563eb;
          box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
        }

        .dropdown-trigger-btn.has-filter {
          background: #eff6ff;
          border-color: #bfdbfe;
          color: #2563eb;
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
          background: #f1f5f9;
          color: #475569;
        }

        .trigger-label {
          font-size: 0.8rem;
          font-weight: 650;
          color: #0f172a;
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
          background: #f1f5f9;
          color: #64748b;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .trigger-clear-btn:hover {
          background: #e2e8f0;
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
          border: 1px solid #e2e8f0;
          border-radius: 14px;
          box-shadow: 0 10px 25px -4px rgba(0, 0, 0, 0.1), 0 4px 10px -2px rgba(0, 0, 0, 0.05);
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
          color: #64748b;
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
          background: #f8fafc;
        }

        .dropdown-option-item.is-active-option {
          background: #eff6ff;
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
          color: #475569;
        }

        .option-label {
          font-size: 0.78rem;
          font-weight: 600;
          color: #0f172a;
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
          color: #475569;
          font-size: 0.68rem;
          font-weight: 700;
        }

        .option-checkmark {
          display: flex;
          align-items: center;
          color: #2563eb;
        }
      `}</style>
    </div>
  );
}

export const PRIORITY_LEVELS = [
  { id: "CRITICAL", label: "Critical Threat", color: "#b45309", bg: "#fffbeb", border: "#fde68a" },
  { id: "HIGH", label: "High Priority", color: "#b45309", bg: "#fffbeb", border: "#fde68a" },
  { id: "MEDIUM", label: "Medium Priority", color: "#2563eb", bg: "#eff6ff", border: "#bfdbfe" },
  { id: "LOW", label: "Routine / Low", color: "#475569", bg: "#f1f5f9", border: "#e2e8f0" },
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
  const [searchFocused, setSearchFocused] = useState(false);
  const searchContainerRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target)) {
        setSearchFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

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

  // Recommended Cases for live search popover
  const recommendedCases = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    if (!q) return [];
    return enrichedCases.filter((c) => {
      const catObj = CRIME_CATEGORIES.find((cat) => cat.id === c.meta.category);
      const searchStr = `${c.title || ""} ${c.case_number || ""} ${c.meta.location || ""} ${c.meta.narrative || ""} ${catObj?.label || ""}`.toLowerCase();
      return searchStr.includes(q);
    }).slice(0, 6);
  }, [enrichedCases, searchTerm]);

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

        {/* 1. CENTRALIZED HEADER */}
        <header className="central-command-hero">
          <h1 className="central-hero-title">Investigation Case Files</h1>

          <p className="central-hero-desc">
            Authorized departmental dossiers, evidence records, and criminal network intelligence.
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
            <div className="unified-search-filter-box" ref={searchContainerRef}>
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
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setSearchFocused(true);
                  }}
                  onFocus={() => setSearchFocused(true)}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") {
                      setSearchFocused(false);
                    }
                  }}
                  className="search-input"
                />
                {searchTerm && (
                  <button
                    className="search-clear-btn"
                    onClick={() => {
                      setSearchTerm("");
                      setSearchFocused(false);
                    }}
                    title="Clear search"
                  >
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
                    setSearchFocused(false);
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

              {/* LIVE SEARCH RECOMMENDATIONS & AUTOCOMPLETE POPOVER */}
              {searchFocused && searchTerm.trim().length > 0 && (
                <div className="search-recommendations-popover">
                  {recommendedCases.length > 0 ? (
                    <>
                      <div className="rec-popover-header">
                        <span className="rec-header-label">
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#35a7ff" strokeWidth="2.5">
                            <circle cx="11" cy="11" r="8" />
                            <line x1="21" y1="21" x2="16.65" y2="16.65" />
                          </svg>
                          CASE RECOMMENDATIONS ({recommendedCases.length})
                        </span>
                        <span className="rec-header-hint">Click to select or open</span>
                      </div>
                      <div className="rec-popover-list">
                        {recommendedCases.map((c) => {
                          const cat = CRIME_CATEGORIES.find((cat) => cat.id === c.meta.category) || CRIME_CATEGORIES[CRIME_CATEGORIES.length - 1];
                          return (
                            <div
                              key={c.id}
                              className="rec-popover-item"
                              onClick={() => {
                                setSearchTerm(c.title);
                                setSearchFocused(false);
                              }}
                            >
                              <div className="rec-item-left">
                                <span
                                  className="rec-cat-badge-icon"
                                  style={{ background: cat.bg, color: cat.color, borderColor: cat.border }}
                                >
                                  <CrimeCategoryIcon categoryId={cat.id} size={13} color={cat.color} />
                                </span>
                                <div className="rec-item-text-col">
                                  <div className="rec-title-row">
                                    <span className="rec-case-title">{highlightMatch(c.title, searchTerm)}</span>
                                    <span className="rec-case-number font-mono">{c.case_number}</span>
                                  </div>
                                  <div className="rec-meta-row">
                                    <span className="rec-cat-name" style={{ color: cat.color }}>{cat.label}</span>
                                    {c.meta.location && <span className="rec-dot">• {c.meta.location}</span>}
                                    {c.meta.subStatus && (
                                      <span className="rec-status-tag">
                                        {c.meta.subStatus}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>

                              <Link
                                href={`/cases/${c.id}`}
                                className="rec-open-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSearchFocused(false);
                                }}
                                title="Open case workspace"
                              >
                                <span>Open</span>
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                  <path d="M5 12h14M12 5l7 7-7 7" />
                                </svg>
                              </Link>
                            </div>
                          );
                        })}
                      </div>
                    </>
                  ) : (
                    <div className="rec-not-found-card">
                      <div className="rec-not-found-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fcba04" strokeWidth="2">
                          <circle cx="11" cy="11" r="8" />
                          <line x1="21" y1="21" x2="16.65" y2="16.65" />
                          <line x1="8" y1="11" x2="14" y2="11" />
                        </svg>
                      </div>
                      <div className="rec-not-found-content">
                        <div className="rec-not-found-title">No Recommendations Found</div>
                        <div className="rec-not-found-desc">
                          No active case file matches <strong>&quot;{searchTerm}&quot;</strong>.
                        </div>
                      </div>
                      <button
                        type="button"
                        className="rec-not-found-action"
                        onClick={() => {
                          setSearchTerm("");
                          setSearchFocused(false);
                        }}
                      >
                        Clear
                      </button>
                    </div>
                  )}
                </div>
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
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fcba04" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                <line x1="8" y1="11" x2="14" y2="11" />
              </svg>
            </div>
            <h3 className="empty-title-text">
              {searchTerm ? `No Cases Found Matching "${searchTerm}"` : "No Investigation Records Found"}
            </h3>
            <p className="empty-desc-text">
              {searchTerm
                ? `No investigation dossiers match your search term "${searchTerm}". Check for typos or reset your filters to view all available cases.`
                : categoryFilter !== "ALL" || statusFilter !== "ALL" || priorityFilter !== "ALL"
                ? "No case files match your selected category or status filter. Reset filters to view all records."
                : "There are currently no cases recorded in your clearance workspace. Create your first investigation file to begin."}
            </p>
            <div className="empty-actions-row">
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm("")}
                  className="action-btn-primary"
                >
                  Clear Search
                </button>
              )}
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
                  Reset All Filters
                </button>
              )}
            </div>
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
                        <span className="status-text-only status-active-text">ACTIVE</span>
                      )}
                      {meta.subStatus === "ON_HOLD" && (
                        <span className="status-text-only status-hold-text">ON HOLD</span>
                      )}
                      {meta.subStatus === "SOLVED" && (
                        <span className="status-text-only status-solved-text">SOLVED</span>
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
            background: #ecfdf5;
            border: 1px solid #a7f3d0;
            color: #059669;
          }

          .notif-error {
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #dc2626;
          }

          .notification-pill button {
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            font-size: 0.9rem;
          }

          /* 1. CENTRALIZED HEADER */
          .central-command-hero {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            max-width: 780px;
            margin: 1rem auto 0;
            padding: 0 1rem;
          }

          .central-hero-title {
            margin: 0;
            font-size: clamp(1.65rem, 2.8vw, 2.2rem);
            font-weight: 800;
            letter-spacing: -0.03em;
            color: #0f172a;
            line-height: 1.2;
          }

          .central-hero-desc {
            margin: 0.55rem 0 1.25rem;
            font-size: 0.9rem;
            line-height: 1.5;
            color: #475569;
            max-width: 580px;
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
            border-radius: 10px;
            border: 1px solid #1d4ed8;
            background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
            color: #ffffff;
            font-size: 0.84rem;
            font-weight: 750;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
            transition: all 0.18s ease;
          }

          .action-btn-primary:hover {
            background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
            border-color: #2563eb;
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
          }

          .action-btn-secondary {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.65rem 1.15rem;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            background: #ffffff;
            color: #334155;
            font-size: 0.84rem;
            font-weight: 650;
            cursor: pointer;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
            transition: all 0.18s ease;
          }

          .action-btn-secondary:hover:not(:disabled) {
            background: #f8fafc;
            color: #0f172a;
            border-color: #cbd5e1;
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
            position: relative;
            display: flex;
            align-items: center;
            width: 100%;
            max-width: 820px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 0.45rem 0.6rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
            gap: 0.6rem;
            transition: all 0.2s ease;
          }

          .unified-search-filter-box:focus-within {
            border-color: #2563eb;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 0 0 2px rgba(37, 99, 235, 0.15);
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
            color: #0f172a;
            padding: 0.5rem 0;
          }

          .search-input::placeholder {
            color: #94a3b8;
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
            background: #ffffff;
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
            background: #f8fafc;
            color: #0f172a;
            border-color: #cbd5e1;
          }

          /* SEARCH RECOMMENDATIONS POPOVER & AUTOCOMPLETE */
          .search-recommendations-popover {
            position: absolute;
            top: calc(100% + 8px);
            left: 0;
            right: 0;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.1);
            z-index: 120;
            overflow: hidden;
            animation: recDropdownFade 0.16s cubic-bezier(0.16, 1, 0.3, 1);
          }

          @keyframes recDropdownFade {
            from {
              opacity: 0;
              transform: translateY(-6px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }

          .rec-popover-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1.1rem 0.6rem;
            border-bottom: 1px solid #f1f5f9;
            background: #f8fafc;
          }

          .rec-header-label {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            color: #2563eb;
            text-transform: uppercase;
          }

          .rec-header-hint {
            font-size: 0.72rem;
            color: #64748b;
          }

          .rec-popover-list {
            display: flex;
            flex-direction: column;
            max-height: 380px;
            overflow-y: auto;
            padding: 0.4rem 0.5rem;
            gap: 3px;
          }

          .rec-popover-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.65rem 0.85rem;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.14s ease;
            gap: 0.85rem;
          }

          .rec-popover-item:hover {
            background: #f8fafc;
          }

          .rec-item-left {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-width: 0;
            flex: 1;
          }

          .rec-cat-badge-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 8px;
            border: 1px solid;
            flex-shrink: 0;
          }

          .rec-item-text-col {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
            min-width: 0;
            flex: 1;
          }

          .rec-title-row {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            min-width: 0;
          }

          .rec-case-title {
            font-size: 0.86rem;
            font-weight: 700;
            color: #0f172a;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          .rec-case-number {
            font-size: 0.68rem;
            color: #2563eb;
            background: rgba(37, 99, 235, 0.08);
            padding: 1px 6px;
            border-radius: 4px;
            flex-shrink: 0;
            border: 1px solid rgba(37, 99, 235, 0.2);
          }

          .rec-meta-row {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.73rem;
            color: #64748b;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }

          .rec-cat-name {
            font-weight: 600;
          }

          .rec-dot {
            color: #94a3b8;
          }

          .rec-status-tag {
            font-size: 0.64rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            padding: 1px 5px;
            border-radius: 4px;
            background: #fffbeb;
            color: #b45309;
            border: 1px solid #fde68a;
          }

          .rec-open-btn {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.4rem 0.75rem;
            border-radius: 7px;
            background: rgba(37, 99, 235, 0.08);
            border: 1px solid rgba(37, 99, 235, 0.25);
            color: #2563eb;
            font-size: 0.75rem;
            font-weight: 700;
            text-decoration: none;
            flex-shrink: 0;
            transition: all 0.15s ease;
          }

          .rec-open-btn:hover {
            background: #2563eb;
            color: #ffffff;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
          }

          .search-highlight {
            background: #fef08a;
            color: #854d0e;
            font-weight: 800;
            border-radius: 3px;
            padding: 0 3px;
          }

          /* NOT FOUND CARD IN RECOMMENDATION DROPDOWN */
          .rec-not-found-card {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1.25rem 1.4rem;
            background: #ffffff;
          }

          .rec-not-found-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: #fffbeb;
            border: 1px solid #fde68a;
            color: #b45309;
            flex-shrink: 0;
          }

          .rec-not-found-content {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
            flex: 1;
            min-width: 0;
          }

          .rec-not-found-title {
            font-size: 0.88rem;
            font-weight: 700;
            color: #0f172a;
          }

          .rec-not-found-desc {
            font-size: 0.78rem;
            color: #64748b;
            line-height: 1.4;
          }

          .rec-not-found-desc strong {
            color: #b45309;
          }

          .rec-not-found-action {
            padding: 0.45rem 0.85rem;
            border-radius: 8px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            color: #0f172a;
            font-size: 0.76rem;
            font-weight: 700;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.15s ease;
          }

          .rec-not-found-action:hover {
            background: #f1f5f9;
            border-color: #cbd5e1;
          }

          .empty-actions-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
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
            padding: 1.4rem;
            border-radius: 18px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 12px -2px rgba(0, 0, 0, 0.03);
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
          }

          .case-record-card:hover {
            transform: translateY(-2px);
            background: #ffffff;
            border-color: #cbd5e1;
            box-shadow: 0 10px 25px -4px rgba(0, 0, 0, 0.08);
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

          .status-text-only {
            display: inline-flex;
            align-items: center;
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            line-height: 1;
            background: none !important;
            border: none !important;
            padding: 0 !important;
          }

          .status-active-text {
            color: #d97706;
          }

          .status-hold-text {
            color: #d97706;
          }

          .status-solved-text {
            color: #059669;
          }

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
            color: #2563eb;
            background: rgba(37, 99, 235, 0.08);
            padding: 0.12rem 0.5rem;
            border-radius: 4px;
            border: 1px solid rgba(37, 99, 235, 0.2);
            letter-spacing: 0.02em;
          }

          .card-title-link {
            text-decoration: none;
          }

          .card-case-title {
            margin: 0;
            font-size: 1.12rem;
            font-weight: 750;
            color: #0f172a;
            line-height: 1.35;
            letter-spacing: -0.015em;
            transition: color 0.15s ease;
          }

          .card-case-title:hover {
            color: #2563eb;
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
            color: #64748b;
            flex-shrink: 0;
          }

          .card-narrative-preview {
            margin: 0;
            font-size: 0.82rem;
            line-height: 1.55;
            color: #475569;
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
            border-radius: 9px;
            border: 1px solid rgba(37, 99, 235, 0.25);
            background: rgba(37, 99, 235, 0.08);
            color: #2563eb;
            font-size: 0.78rem;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.18s ease;
          }

          .view-workspace-action-btn:hover {
            background: #2563eb;
            color: #ffffff;
            border-color: #2563eb;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
          }

          .card-secondary-actions {
            display: flex;
            align-items: center;
            gap: 0.45rem;
          }

          .quick-status-selector {
            height: 34px;
            padding: 0 0.65rem;
            border-radius: 9px;
            border: 1px solid #cbd5e1;
            background: #ffffff;
            font-size: 0.75rem;
            font-weight: 600;
            color: #0f172a;
            cursor: pointer;
            outline: none;
            transition: border-color 0.15s ease;
          }

          .quick-status-selector:focus {
            border-color: #2563eb;
          }

          .delete-case-btn {
            width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 9px;
            border: 1px solid #e2e8f0;
            background: #ffffff;
            color: #64748b;
            cursor: pointer;
            transition: all 0.15s ease;
          }

          .delete-case-btn:hover {
            background: #fef2f2;
            border-color: #fecaca;
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
            border-radius: 18px;
            background: #ffffff;
            border: 1px dashed #cbd5e1;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.65rem;
          }

          .empty-icon-circle {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: rgba(37, 99, 235, 0.08);
            color: #2563eb;
            border: 1px solid rgba(37, 99, 235, 0.2);
            display: grid;
            place-items: center;
            font-size: 1.35rem;
          }

          .dashboard-empty-card h3,
          .dashboard-error-card h3 {
            margin: 0;
            font-size: 1.05rem;
            font-weight: 750;
            color: #0f172a;
          }

          .dashboard-empty-card p,
          .dashboard-error-card p {
            margin: 0;
            font-size: 0.84rem;
            color: #475569;
            max-width: 480px;
            line-height: 1.55;
          }

          .loading-radar-ring {
            width: 36px;
            height: 36px;
            border: 3px solid #e2e8f0;
            border-top-color: #2563eb;
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
            background: rgba(15, 23, 42, 0.45);
            backdrop-filter: blur(4px);
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
          }

          .modal-dialog-box {
            background: #ffffff;
            border-radius: 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.15);
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
            padding: 1.35rem 1.6rem;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
          }

          .modal-kicker {
            font-size: 0.64rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            color: #2563eb;
            display: block;
            margin-bottom: 0.15rem;
          }

          .kicker-danger {
            color: #d97706;
          }

          .modal-title-wrap h2 {
            margin: 0;
            font-size: 1.2rem;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.02em;
          }

          .modal-close-cross-btn {
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 9px;
            border: 1px solid #e2e8f0;
            background: #ffffff;
            color: #64748b;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.15s ease;
          }

          .modal-close-cross-btn:hover {
            color: #0f172a;
            background: #f1f5f9;
            border-color: #cbd5e1;
          }

          .modal-form-body {
            padding: 1.5rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1.15rem;
          }

          .modal-error-notice {
            padding: 0.65rem 0.85rem;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            color: #dc2626;
            font-size: 0.78rem;
            font-weight: 600;
          }

          .modal-input-group {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
          }

          .modal-input-group label {
            font-size: 0.76rem;
            font-weight: 650;
            color: #0f172a;
          }

          .star-required {
            color: #d97706;
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
            border-radius: 10px;
            border: 1px solid #cbd5e1;
            background: #ffffff;
            font-size: 0.85rem;
            color: #0f172a;
            outline: none;
            font-family: inherit;
            transition: border-color 0.16s ease, box-shadow 0.16s ease;
          }

          .modal-text-input:focus,
          .modal-select-input:focus,
          .modal-textarea-input:focus {
            border-color: #2563eb;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
          }

          .modal-textarea-input {
            resize: vertical;
          }

          .modal-action-buttons-bar {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.75rem;
            padding-top: 0.85rem;
            border-top: 1px solid #e2e8f0;
            margin-top: 0.5rem;
          }

          .modal-secondary-cancel-btn {
            padding: 0.65rem 1.15rem;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            background: #ffffff;
            color: #334155;
            font-size: 0.82rem;
            font-weight: 650;
            cursor: pointer;
            transition: all 0.16s ease;
          }

          .modal-secondary-cancel-btn:hover {
            background: #f8fafc;
            color: #0f172a;
            border-color: #cbd5e1;
          }

          .modal-primary-submit-btn {
            padding: 0.65rem 1.35rem;
            border-radius: 10px;
            border: 1px solid #1d4ed8;
            background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
            color: #ffffff;
            font-size: 0.82rem;
            font-weight: 750;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
            transition: all 0.18s ease;
          }

          .modal-primary-submit-btn:hover:not(:disabled) {
            background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
            border-color: #2563eb;
          }

          .modal-primary-submit-btn:disabled {
            opacity: 0.55;
            cursor: not-allowed;
            box-shadow: none;
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
            background: #fffbeb;
            border: 1px solid #fde68a;
            color: #b45309;
            font-size: 0.84rem;
            line-height: 1.5;
          }

          .delete-critical-notice {
            margin: 0.5rem 0 0;
            font-size: 0.76rem;
            color: #b45309;
            font-weight: 600;
          }

          .modal-danger-confirm-btn {
            padding: 0.65rem 1.35rem;
            border-radius: 10px;
            border: 1px solid #dc2626;
            background: #dc2626;
            color: #ffffff;
            font-size: 0.82rem;
            font-weight: 750;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(220, 38, 38, 0.25);
            transition: all 0.16s ease;
          }

          .modal-danger-confirm-btn:hover:not(:disabled) {
            background: #b91c1c;
            border-color: #b91c1c;
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
