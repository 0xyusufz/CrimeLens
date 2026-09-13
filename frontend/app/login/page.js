"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setToken, setUser } from "../../lib/auth";
import { apiClient } from "../../lib/apiClient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password || loading) return;

    setError(null);
    setLoading(true);

    try {
      const data = await apiClient("/api/auth/login", {
        method: "POST",
        body: { email, password },
      });
      setToken(data.access_token);
      if (data.user) {
        setUser(data.user);
      }
      router.push("/");
    } catch (err) {
      setError(err.message || "Authentication failed. Please verify your investigator credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-viewport">
      <div className="login-wrapper">
        {/* LEFT PANEL: BRANDING & INTELLIGENCE NETWORK */}
        <div className="brand-panel">
          <div className="brand-panel-glow" aria-hidden="true" />

          {/* Header & Logo */}
          <div className="brand-header">
            <div className="brand-logo-container">
              <svg
                width="34"
                height="34"
                viewBox="0 0 32 32"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="brand-logo-svg"
                aria-hidden="true"
              >
                <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.4" />
                <circle cx="16" cy="16" r="9" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />
                <circle cx="16" cy="16" r="4" fill="currentColor" />
                <line x1="16" y1="2" x2="16" y2="7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="16" y1="25" x2="16" y2="30" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="2" y1="16" x2="7" y2="16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <line x1="25" y1="16" x2="30" y2="16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              <div className="brand-title-group">
                <span className="brand-title">CrimeLens</span>
                <span className="brand-badge">INTELLIGENCE SUITE</span>
              </div>
            </div>
          </div>

          {/* Core Headlines */}
          <div className="brand-headline-block">
            <h1 className="brand-headline">
              Evidence-backed investigative intelligence
            </h1>
            <p className="brand-subtext">
              Connect fragmented evidence. Discover relationships. Verify the intelligence.
            </p>
          </div>

          {/* Abstract Criminal-Network Graph Motif (SVG/CSS Only) */}
          <div className="network-motif-wrapper" aria-hidden="true">
            <svg
              className="network-graph-svg"
              viewBox="0 0 460 210"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <linearGradient id="edgeGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0ea5e9" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.15" />
                </linearGradient>
                <linearGradient id="edgeGrad2" x1="0%" y1="100%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#0284c7" stopOpacity="0.5" />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.2" />
                </linearGradient>
                <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
                </radialGradient>
              </defs>

              {/* Radar Grid / Scanlines */}
              <circle cx="230" cy="105" r="95" stroke="#1e293b" strokeWidth="1" strokeDasharray="4 4" opacity="0.6" />
              <circle cx="230" cy="105" r="55" stroke="#1e293b" strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />
              <line x1="230" y1="10" x2="230" y2="200" stroke="#1e293b" strokeWidth="1" strokeDasharray="2 4" opacity="0.4" />
              <line x1="50" y1="105" x2="410" y2="105" stroke="#1e293b" strokeWidth="1" strokeDasharray="2 4" opacity="0.4" />

              {/* Connection Edges */}
              <line x1="85" y1="65" x2="210" y2="55" stroke="url(#edgeGrad1)" strokeWidth="1.5" />
              <line x1="210" y1="55" x2="355" y2="85" stroke="url(#edgeGrad1)" strokeWidth="1.5" />
              <line x1="85" y1="65" x2="155" y2="155" stroke="url(#edgeGrad2)" strokeWidth="1.5" />
              <line x1="155" y1="155" x2="295" y2="165" stroke="url(#edgeGrad1)" strokeWidth="1.5" strokeDasharray="4 3" />
              <line x1="210" y1="55" x2="295" y2="165" stroke="url(#edgeGrad2)" strokeWidth="1.5" />
              <line x1="355" y1="85" x2="295" y2="165" stroke="url(#edgeGrad1)" strokeWidth="1.5" />

              {/* Node 1: Person Nexus */}
              <g className="graph-node-group">
                <circle cx="85" cy="65" r="16" fill="url(#nodeGlow)" />
                <circle cx="85" cy="65" r="6" fill="#0ea5e9" className="pulse-dot" />
                <circle cx="85" cy="65" r="10" stroke="#38bdf8" strokeWidth="1.5" opacity="0.8" />
                <text x="85" y="44" textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="monospace" fontWeight="600">
                  PERSON: SUSPECT_A
                </text>
              </g>

              {/* Node 2: Corporate Entity */}
              <g className="graph-node-group">
                <circle cx="210" cy="55" r="18" fill="url(#nodeGlow)" />
                <circle cx="210" cy="55" r="7" fill="#38bdf8" />
                <circle cx="210" cy="55" r="12" stroke="#0ea5e9" strokeWidth="1.5" opacity="0.9" />
                <text x="210" y="33" textAnchor="middle" fill="#38bdf8" fontSize="9.5" fontFamily="monospace" fontWeight="700">
                  ENTITY: HOLDINGS_LTD
                </text>
              </g>

              {/* Node 3: Account / Transaction */}
              <g className="graph-node-group">
                <circle cx="355" cy="85" r="14" fill="url(#nodeGlow)" />
                <circle cx="355" cy="85" r="5" fill="#06b6d4" className="pulse-dot" />
                <circle cx="355" cy="85" r="9" stroke="#06b6d4" strokeWidth="1.5" opacity="0.8" />
                <text x="355" y="108" textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="monospace" fontWeight="600">
                  ACC: WIRE_TRANS
                </text>
              </g>

              {/* Node 4: Evidence Document */}
              <g className="graph-node-group">
                <circle cx="155" cy="155" r="14" fill="url(#nodeGlow)" />
                <circle cx="155" cy="155" r="5" fill="#10b981" />
                <circle cx="155" cy="155" r="9" stroke="#10b981" strokeWidth="1.5" opacity="0.8" />
                <text x="155" y="179" textAnchor="middle" fill="#10b981" fontSize="9" fontFamily="monospace" fontWeight="600">
                  EVIDENCE: DOC_82F
                </text>
              </g>

              {/* Node 5: Location Nexus */}
              <g className="graph-node-group">
                <circle cx="295" cy="165" r="14" fill="url(#nodeGlow)" />
                <circle cx="295" cy="165" r="5" fill="#f59e0b" />
                <circle cx="295" cy="165" r="9" stroke="#f59e0b" strokeWidth="1.5" opacity="0.8" />
                <text x="295" y="190" textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="monospace" fontWeight="600">
                  LOC: FACILITY_4
                </text>
              </g>
            </svg>
            <div className="network-status-bar">
              <span className="status-indicator-dot" />
              <span>LIVE EVIDENCE GRAPH PROJECTION</span>
              <span className="status-separator">•</span>
              <span>VERIFIED RELATIONSHIPS</span>
            </div>
          </div>

          {/* 4 Pillars Sequence */}
          <div className="brand-steps-container">
            <div className="step-card">
              <div className="step-index">1</div>
              <div className="step-content">
                <span className="step-action">AI discovers</span>
                <span className="step-description">Autonomous entity extraction and pattern detection across evidentiary records.</span>
              </div>
            </div>

            <div className="step-card">
              <div className="step-index">2</div>
              <div className="step-content">
                <span className="step-action">Graph connects</span>
                <span className="step-description">Multi-hop relationship mapping reveals concealed criminal networks.</span>
              </div>
            </div>

            <div className="step-card">
              <div className="step-index">3</div>
              <div className="step-content">
                <span className="step-action">Evidence supports</span>
                <span className="step-description">Cryptographic SHA-256 chain maintains strict evidentiary integrity.</span>
              </div>
            </div>

            <div className="step-card step-card-highlight">
              <div className="step-index">4</div>
              <div className="step-content">
                <span className="step-action">Investigator decides</span>
                <span className="step-description">Human-in-the-loop validation ensures actionable, courtroom-ready verdicts.</span>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT PANEL: AUTHENTICATION FORM */}
        <div className="auth-panel">
          <div className="auth-panel-glow" aria-hidden="true" />
          <div className="auth-card">
            {/* Header */}
            <div className="auth-header">
              <div className="auth-icon-badge" aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <h2 className="auth-title">CrimeLens Access</h2>
              <p className="auth-subtitle">Sign in to your investigator account</p>
            </div>

            {/* Error Notification */}
            {error && (
              <div className="auth-error-banner" role="alert" aria-live="polite">
                <svg
                  className="auth-error-icon"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <div className="auth-error-text">
                  <span className="auth-error-title">Authentication Failed</span>
                  <span className="auth-error-desc">{error}</span>
                </div>
              </div>
            )}

            {/* Form */}
            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              {/* Email Field */}
              <div className="input-group">
                <label className="input-label" htmlFor="email">
                  Email
                </label>
                <div className="input-field-wrapper">
                  <svg
                    className="input-icon"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    className="auth-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    placeholder="investigator@agency.gov"
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="input-group">
                <div className="password-label-row">
                  <label className="input-label" htmlFor="password">
                    Password
                  </label>
                </div>
                <div className="input-field-wrapper">
                  <svg
                    className="input-icon"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    className="auth-input password-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="••••••••••••"
                    disabled={loading}
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    tabIndex={0}
                  >
                    {showPassword ? (
                      /* Eye Off SVG */
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      /* Eye SVG */
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="auth-submit-btn"
                disabled={loading || !email || !password}
              >
                {loading ? (
                  <span className="submit-spinner-wrapper">
                    <span className="submit-spinner" aria-hidden="true" />
                    <span>Authenticating...</span>
                  </span>
                ) : (
                  <span className="submit-content">
                    <span>Authenticate</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </span>
                )}
              </button>
            </form>

            {/* Security Notice */}
            <div className="auth-security-notice">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="security-icon">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <span>Restricted investigator portal. All sessions and queries are cryptographically logged to the audit ledger.</span>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .login-viewport {
          min-height: 100vh;
          width: 100%;
          background-color: #080b11;
          background-image:
            radial-gradient(at 15% 15%, rgba(14, 165, 233, 0.08) 0px, transparent 50%),
            radial-gradient(at 85% 85%, rgba(2, 132, 199, 0.06) 0px, transparent 50%),
            linear-gradient(180deg, #090d15 0%, #05070a 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2.5rem 1.5rem;
          box-sizing: border-box;
          color: #f1f5f9;
        }

        .login-wrapper {
          width: 100%;
          max-width: 1180px;
          min-height: 640px;
          display: grid;
          grid-template-columns: 1.15fr 0.85fr;
          gap: 2rem;
          align-items: stretch;
        }

        /* LEFT BRAND PANEL */
        .brand-panel {
          position: relative;
          background: linear-gradient(165deg, rgba(17, 24, 39, 0.85) 0%, rgba(11, 16, 27, 0.95) 100%);
          border: 1px solid rgba(56, 189, 248, 0.16);
          border-radius: 20px;
          padding: 3rem;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          overflow: hidden;
          box-shadow:
            0 20px 45px -10px rgba(0, 0, 0, 0.6),
            inset 0 1px 0 rgba(255, 255, 255, 0.06);
          backdrop-filter: blur(16px);
        }

        .brand-panel-glow {
          position: absolute;
          top: -120px;
          left: -120px;
          width: 320px;
          height: 320px;
          background: radial-gradient(circle, rgba(14, 165, 233, 0.15) 0%, rgba(14, 165, 233, 0) 70%);
          pointer-events: none;
          z-index: 0;
        }

        .brand-header {
          position: relative;
          z-index: 1;
          margin-bottom: 2rem;
        }

        .brand-logo-container {
          display: flex;
          align-items: center;
          gap: 0.85rem;
        }

        .brand-logo-svg {
          color: #38bdf8;
          filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.45));
        }

        .brand-title-group {
          display: flex;
          flex-direction: column;
        }

        .brand-title {
          font-size: 1.35rem;
          font-weight: 700;
          letter-spacing: -0.02em;
          color: #f8fafc;
        }

        .brand-badge {
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.12em;
          color: #38bdf8;
          font-family: monospace;
        }

        .brand-headline-block {
          position: relative;
          z-index: 1;
          margin-bottom: 1.5rem;
        }

        .brand-headline {
          font-size: 2rem;
          font-weight: 800;
          line-height: 1.25;
          letter-spacing: -0.025em;
          color: #f8fafc;
          margin-bottom: 0.75rem;
        }

        .brand-subtext {
          font-size: 0.95rem;
          line-height: 1.6;
          color: #94a3b8;
          max-width: 480px;
        }

        /* SVG NETWORK MOTIF */
        .network-motif-wrapper {
          position: relative;
          z-index: 1;
          background: rgba(10, 15, 25, 0.6);
          border: 1px solid rgba(56, 189, 248, 0.12);
          border-radius: 12px;
          padding: 1rem 1.25rem 0.75rem;
          margin-bottom: 1.75rem;
        }

        .network-graph-svg {
          width: 100%;
          height: auto;
          display: block;
          filter: drop-shadow(0 0 8px rgba(14, 165, 233, 0.15));
        }

        .pulse-dot {
          animation: pulseNode 3s ease-in-out infinite;
        }

        @keyframes pulseNode {
          0%, 100% {
            opacity: 0.75;
            transform: scale(1);
          }
          50% {
            opacity: 1;
            transform: scale(1.15);
            filter: drop-shadow(0 0 6px #38bdf8);
          }
        }

        .network-status-bar {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-top: 0.5rem;
          font-size: 0.68rem;
          font-family: monospace;
          color: #64748b;
          letter-spacing: 0.06em;
        }

        .status-indicator-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #10b981;
          box-shadow: 0 0 8px #10b981;
          display: inline-block;
        }

        .status-separator {
          color: #334155;
        }

        /* 4 PILLARS SEQUENCE (CARDS) */
        .brand-steps-container {
          position: relative;
          z-index: 1;
          display: flex;
          flex-direction: column;
          gap: 0.65rem;
        }

        .step-card {
          display: flex;
          align-items: center;
          gap: 0.85rem;
          padding: 0.7rem 0.95rem;
          background: rgba(15, 23, 42, 0.55);
          border: 1px solid rgba(56, 189, 248, 0.08);
          border-radius: 10px;
          transition: all 0.2s ease;
        }

        .step-card:hover {
          background: rgba(15, 23, 42, 0.8);
          border-color: rgba(56, 189, 248, 0.22);
          transform: translateX(3px);
        }

        .step-card-highlight {
          border-color: rgba(56, 189, 248, 0.18);
          background: rgba(14, 165, 233, 0.06);
        }

        .step-index {
          width: 24px;
          height: 24px;
          min-width: 24px;
          border-radius: 6px;
          background: rgba(56, 189, 248, 0.12);
          border: 1px solid rgba(56, 189, 248, 0.25);
          color: #38bdf8;
          font-size: 0.72rem;
          font-weight: 700;
          font-family: monospace;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .step-content {
          display: flex;
          flex-direction: column;
        }

        .step-action {
          font-size: 0.85rem;
          font-weight: 700;
          color: #f1f5f9;
          letter-spacing: -0.01em;
        }

        .step-description {
          font-size: 0.75rem;
          color: #94a3b8;
          line-height: 1.35;
        }

        /* RIGHT AUTH PANEL */
        .auth-panel {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .auth-panel-glow {
          position: absolute;
          bottom: -100px;
          right: -100px;
          width: 300px;
          height: 300px;
          background: radial-gradient(circle, rgba(2, 132, 199, 0.12) 0%, rgba(2, 132, 199, 0) 70%);
          pointer-events: none;
          z-index: 0;
        }

        .auth-card {
          position: relative;
          z-index: 1;
          width: 100%;
          background: linear-gradient(165deg, rgba(17, 24, 39, 0.9) 0%, rgba(13, 18, 30, 0.95) 100%);
          border: 1px solid rgba(56, 189, 248, 0.15);
          border-radius: 20px;
          padding: 3rem 2.75rem;
          box-shadow:
            0 25px 50px -12px rgba(0, 0, 0, 0.65),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(16px);
        }

        .auth-header {
          text-align: center;
          margin-bottom: 2rem;
        }

        .auth-icon-badge {
          width: 48px;
          height: 48px;
          margin: 0 auto 1.25rem;
          border-radius: 12px;
          background: rgba(14, 165, 233, 0.1);
          border: 1px solid rgba(56, 189, 248, 0.25);
          color: #38bdf8;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 0 20px rgba(14, 165, 233, 0.15);
        }

        .auth-title {
          font-size: 1.65rem;
          font-weight: 700;
          letter-spacing: -0.02em;
          color: #f8fafc;
          margin-bottom: 0.4rem;
        }

        .auth-subtitle {
          font-size: 0.9rem;
          color: #94a3b8;
        }

        /* ERROR BANNER */
        .auth-error-banner {
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 10px;
          padding: 0.85rem 1rem;
          margin-bottom: 1.5rem;
          animation: slideDown 0.2s ease-out;
        }

        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-6px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .auth-error-icon {
          color: #ef4444;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .auth-error-text {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .auth-error-title {
          font-size: 0.82rem;
          font-weight: 700;
          color: #fca5a5;
        }

        .auth-error-desc {
          font-size: 0.8rem;
          color: #f87171;
          line-height: 1.35;
        }

        /* FORM CONTROLS */
        .auth-form {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }

        .input-group {
          display: flex;
          flex-direction: column;
          gap: 0.45rem;
        }

        .input-label {
          font-size: 0.82rem;
          font-weight: 600;
          color: #cbd5e1;
          letter-spacing: 0.01em;
        }

        .password-label-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .input-field-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }

        .input-icon {
          position: absolute;
          left: 1rem;
          color: #64748b;
          pointer-events: none;
          transition: color 0.2s;
        }

        .auth-input {
          width: 100%;
          height: 3rem;
          padding: 0 1rem 0 2.75rem;
          background: #090d15;
          border: 1px solid #1e293b;
          border-radius: 10px;
          color: #f8fafc;
          font-size: 0.92rem;
          font-family: inherit;
          transition: all 0.2s ease;
          box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4);
        }

        .auth-input::placeholder {
          color: #475569;
        }

        .auth-input:focus {
          outline: none;
          border-color: #38bdf8;
          box-shadow:
            0 0 0 3px rgba(56, 189, 248, 0.15),
            inset 0 1px 2px rgba(0, 0, 0, 0.3);
        }

        .auth-input:focus + .input-icon,
        .input-field-wrapper:focus-within .input-icon {
          color: #38bdf8;
        }

        .password-input {
          padding-right: 3rem;
        }

        .password-toggle-btn {
          position: absolute;
          right: 0.75rem;
          background: transparent;
          border: none;
          color: #64748b;
          padding: 0.4rem;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: color 0.2s, background-color 0.2s;
        }

        .password-toggle-btn:hover {
          color: #cbd5e1;
          background-color: rgba(255, 255, 255, 0.05);
        }

        .password-toggle-btn:focus {
          outline: none;
          color: #38bdf8;
          background-color: rgba(56, 189, 248, 0.1);
        }

        /* PRIMARY CTA BUTTON */
        .auth-submit-btn {
          margin-top: 0.75rem;
          height: 3.15rem;
          width: 100%;
          background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
          border: 1px solid rgba(56, 189, 248, 0.3);
          border-radius: 10px;
          color: #ffffff;
          font-size: 0.95rem;
          font-weight: 600;
          letter-spacing: 0.01em;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow:
            0 4px 18px -2px rgba(14, 165, 233, 0.45),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }

        .auth-submit-btn:hover:not(:disabled) {
          background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
          box-shadow:
            0 6px 24px -2px rgba(14, 165, 233, 0.65),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
          transform: translateY(-1px);
        }

        .auth-submit-btn:active:not(:disabled) {
          transform: translateY(0);
          box-shadow: 0 2px 10px -2px rgba(14, 165, 233, 0.4);
        }

        .auth-submit-btn:focus {
          outline: none;
          box-shadow:
            0 0 0 3px rgba(56, 189, 248, 0.35),
            0 4px 18px -2px rgba(14, 165, 233, 0.45);
        }

        .auth-submit-btn:disabled {
          opacity: 0.55;
          cursor: not-allowed;
          box-shadow: none;
        }

        .submit-content {
          display: flex;
          align-items: center;
          gap: 0.65rem;
        }

        .submit-spinner-wrapper {
          display: flex;
          align-items: center;
          gap: 0.65rem;
        }

        .submit-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: #ffffff;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        /* SECURITY FOOTER */
        .auth-security-notice {
          margin-top: 2rem;
          padding-top: 1.5rem;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
          display: flex;
          align-items: flex-start;
          gap: 0.65rem;
          font-size: 0.72rem;
          line-height: 1.45;
          color: #64748b;
        }

        .security-icon {
          color: #0ea5e9;
          flex-shrink: 0;
          margin-top: 2px;
        }

        /* RESPONSIVENESS: STACK BRANDING ON MOBILE */
        @media (max-width: 960px) {
          .login-viewport {
            padding: 1.5rem 1rem;
          }

          .login-wrapper {
            grid-template-columns: 1fr;
            gap: 1.5rem;
          }

          .brand-panel {
            padding: 2rem 1.5rem;
          }

          .brand-headline {
            font-size: 1.6rem;
          }

          .auth-card {
            padding: 2rem 1.5rem;
          }
        }

        @media (max-width: 480px) {
          .brand-headline {
            font-size: 1.4rem;
          }

          .step-card {
            padding: 0.6rem 0.75rem;
          }

          .auth-title {
            font-size: 1.4rem;
          }
        }
      `}</style>
    </div>
  );
}
