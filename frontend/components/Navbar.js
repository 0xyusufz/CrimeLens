"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getUser, logout } from "../lib/auth";
import CrimeLensLogo from "./CrimeLensLogo";

export default function Navbar() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  const displayName = "Officer";
  const displayRole = "Administrator";

  return (
    <header className="investigation-header">
      <div className="header-container">
        {/* BRANDING */}
        <div className="header-brand-group">
          <Link href="/" className="header-logo-link" aria-label="CrimeLens Dashboard">
            <CrimeLensLogo size={36} iconSize={20} withBadge={true} />
            <div className="header-titles">
              <span className="brand-name">
                Crime<span className="brand-name-accent">Lens</span>
              </span>
              <span className="system-subtitle">Investigation Dashboard</span>
            </div>
          </Link>
        </div>

        {/* USER PROFILE & LOGOUT */}
        <div className="header-actions-group">
          <div className="user-profile-card">
            <div className="user-avatar-indicator" title="Officer Profile">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div className="user-details">
              <div className="user-name-role">
                <span className="user-name">{displayName}</span>
                <span className="role-badge">{displayRole}</span>
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            className="logout-button"
            title="Logout"
            aria-label="Logout"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="logout-icon"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
        </div>
      </div>

      <style>{`
        .investigation-header {
          background-color: rgba(11, 16, 27, 0.92);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border-bottom: 1px solid rgba(56, 189, 248, 0.12);
          position: sticky;
          top: 0;
          z-index: 50;
        }

        .header-container {
          max-width: 1280px;
          margin: 0 auto;
          padding: 0.85rem 1.5rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .header-brand-group {
          display: flex;
          align-items: center;
        }

        .header-logo-link {
          display: flex;
          align-items: center;
          gap: 0.85rem;
          text-decoration: none;
        }

        .header-logo-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          background: rgba(14, 165, 233, 0.08);
          border: 1px solid rgba(56, 189, 248, 0.25);
          border-radius: 9px;
          box-shadow: 0 0 12px rgba(14, 165, 233, 0.2);
        }

        .header-titles {
          display: flex;
          flex-direction: column;
          gap: 0.1rem;
        }

        .brand-name {
          font-size: 1.15rem;
          font-weight: 700;
          letter-spacing: -0.02em;
          color: #f8fafc;
          line-height: 1.1;
        }

        .system-subtitle {
          font-size: 0.72rem;
          font-weight: 500;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          color: #38bdf8;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .header-actions-group {
          display: flex;
          align-items: center;
          gap: 1.25rem;
        }

        .user-profile-card {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.4rem 0.85rem;
          background: rgba(15, 23, 42, 0.65);
          border: 1px solid rgba(255, 255, 255, 0.07);
          border-radius: 8px;
        }

        .user-avatar-indicator {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          background: rgba(56, 189, 248, 0.15);
          color: #38bdf8;
          border-radius: 50%;
        }

        .user-details {
          display: flex;
          flex-direction: column;
          line-height: 1.2;
        }

        .user-name-role {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          justify-content: center;
          gap: 1px;
          line-height: 1.15;
        }

        .user-name {
          font-size: 0.96rem;
          font-weight: 700;
          color: #1e293b;
          line-height: 1.15;
          margin: 0;
          padding: 0;
        }

        .role-badge {
          font-size: 0.78rem;
          font-weight: 500;
          letter-spacing: 0.01em;
          color: #64748b;
          background: transparent;
          border: none;
          border-radius: 0;
          padding: 0;
          margin: 0;
          text-transform: capitalize;
          font-family: inherit;
          line-height: 1.15;
        }

        .logout-button {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 38px;
          height: 38px;
          padding: 0;
          background: #ffffff;
          border: 1px solid #dce7f1;
          border-radius: 10px;
          color: #64748b;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .logout-button:hover {
          background: #fef2f2;
          border-color: #fca5a5;
          color: #ef4444;
        }

        .logout-button:active {
          transform: translateY(1px);
        }

        .logout-icon {
          flex-shrink: 0;
        }

        @media (max-width: 640px) {
          .system-subtitle {
            display: none;
          }
          .user-email {
            display: none;
          }
          .header-container {
            padding: 0.75rem 1rem;
          }
        }
      `}</style>
    </header>
  );
}

