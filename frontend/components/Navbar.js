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
                <span className="brand-text-crime">Crime</span>
                <span className="brand-text-lens">Lens<span className="brand-optic-dot"></span></span>
              </span>
              <span className="system-subtitle">FORENSIC INTELLIGENCE</span>
            </div>
          </Link>
        </div>

        {/* USER PROFILE & LOGOUT */}
        <div className="header-actions-group">
          <div className="user-profile-card">
            <div className="user-avatar-indicator" title="Officer Active Session">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
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
            title="Sign out of CrimeLens"
            aria-label="Logout"
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
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
          background-color: #ffffff;
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border-bottom: 1px solid #e2e8f0;
          position: sticky;
          top: 0;
          z-index: 50;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
          transition: all 0.2s ease;
        }

        .header-container {
          max-width: 1440px;
          margin: 0 auto;
          padding: 0.75rem clamp(1.25rem, 3.5vw, 2.5rem);
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
          width: 38px;
          height: 38px;
          border-radius: 11px;
          background: #0f172a;
          box-shadow: 0 2px 6px rgba(15, 23, 42, 0.2);
        }

        .header-titles {
          display: flex;
          flex-direction: column;
          justify-content: center;
          gap: 1.5px;
        }

        .brand-name {
          font-family: 'Plus Jakarta Sans', var(--font-sans);
          font-size: 1.40rem;
          font-weight: 850;
          letter-spacing: -0.04em;
          display: inline-flex;
          align-items: baseline;
          line-height: 1.15;
          user-select: none;
          position: relative;
        }

        .brand-text-crime {
          color: #0b0f19;
          font-weight: 850;
          letter-spacing: -0.04em;
          transition: color 0.2s ease;
        }

        .brand-text-lens {
          position: relative;
          font-weight: 850;
          letter-spacing: -0.04em;
          background: linear-gradient(135deg, #1e293b 0%, #1e40af 40%, #2563eb 72%, #0284c7 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          display: inline-flex;
          align-items: baseline;
          margin-left: 0.5px;
          transition: all 0.25s ease;
        }

        .brand-optic-dot {
          display: inline-block;
          width: 4.5px;
          height: 4.5px;
          border-radius: 50%;
          background: #0284c7;
          margin-left: 2.5px;
          transform: translateY(-3px);
          box-shadow: 0 0 7px rgba(2, 132, 199, 0.7);
        }

        .header-logo-link:hover .brand-text-lens {
          background: linear-gradient(135deg, #0f172a 0%, #2563eb 42%, #38bdf8 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .header-logo-link:hover .brand-optic-dot {
          background: #38bdf8;
          box-shadow: 0 0 9px rgba(56, 189, 248, 0.9);
        }

        .system-subtitle {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.58rem;
          font-weight: 700;
          letter-spacing: 0.16em;
          text-transform: uppercase;
          color: #64748b;
          line-height: 1.2;
          user-select: none;
          margin-top: 1px;
        }

        .header-actions-group {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .user-profile-card {
          display: flex;
          align-items: center;
          gap: 0.85rem;
          padding: 0.42rem 1.05rem 0.42rem 0.55rem;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
          transition: all 0.2s ease;
        }

        .user-profile-card:hover {
          border-color: #cbd5e1;
          box-shadow: 0 3px 8px rgba(0, 0, 0, 0.06);
          background: #fbfcfe;
        }

        .user-avatar-indicator {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          background: #0f172a;
          color: #ffffff;
          border: 1px solid rgba(53, 167, 255, 0.32);
          border-radius: 10px;
          flex-shrink: 0;
          box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15);
        }

        .user-status-dot {
          position: absolute;
          bottom: -1px;
          right: -1px;
          width: 8.5px;
          height: 8.5px;
          border-radius: 50%;
          background: #10b981;
          border: 2px solid #ffffff;
          box-shadow: 0 0 5px rgba(16, 185, 129, 0.7);
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
          gap: 2px;
          line-height: 1.15;
        }

        .user-name {
          font-family: 'Plus Jakarta Sans', var(--font-sans);
          font-size: 0.90rem;
          font-weight: 750;
          color: #0b0f19;
          letter-spacing: -0.015em;
          line-height: 1.2;
          margin: 0;
          padding: 0;
        }

        .role-badge {
          display: block;
          font-family: 'Plus Jakarta Sans', var(--font-sans);
          font-size: 0.73rem;
          font-weight: 500;
          letter-spacing: 0.01em;
          color: #64748b;
          background: transparent;
          border: none;
          border-radius: 0;
          padding: 0;
          margin: 0;
          line-height: 1.2;
          text-transform: capitalize;
        }

        .logout-button {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          padding: 0;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          color: #475569;
          cursor: pointer;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
          cursor: pointer;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .logout-button:hover {
          background: #fef2f2;
          border-color: #fecaca;
          color: #dc2626;
          box-shadow: 0 3px 10px rgba(220, 38, 38, 0.15);
          transform: translateY(-1px);
        }

        .logout-button:hover .logout-icon {
          transform: translateX(2px);
        }

        .logout-button:active {
          transform: translateY(1px);
          box-shadow: none;
        }

        .logout-icon {
          flex-shrink: 0;
          transition: transform 0.2s ease;
        }

        @media (max-width: 640px) {
          .system-subtitle {
            display: none;
          }
          .user-details {
            display: none;
          }
          .header-container {
            padding: 0.65rem 1rem;
          }
        }
      `}</style>
    </header>
  );
}

