"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setToken, setUser } from "../../lib/auth";
import { apiClient } from "../../lib/apiClient";
import CrimeLensLogo, { CrimeLensStar } from "../../components/CrimeLensLogo";
import "./login.css";

// Eye toggle icon
function EyeIcon({ show }) {
  if (show) {
    return (
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    );
  }
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("dev@crimelens.local");
  const [password, setPassword] = useState("password");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!email.trim() || !password.trim() || loading) return;

    setError(null);
    setLoading(true);

    try {
      const data = await apiClient("/api/auth/login", {
        method: "POST",
        body: { email: email.trim(), password: password.trim() },
      });
      setToken(data.access_token);
      if (data.user) {
        setUser(data.user);
      }
      router.push("/");
    } catch (err) {
      setError(err.message || "Authentication failed. Please verify credentials.");
    } finally {
      setLoading(false);
    }
  };

  // Quick Demo Autofill
  const handleQuickFill = (demoEmail, demoPass) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="aurora-login-viewport">
      {/* Centered Floating Master Card */}
      <div className="aurora-master-card">
        {/* 1. LEFT HERO ART PANEL */}
        <div className="aurora-left-hero">
          {/* Subtle Background Forensic Network Graph */}
          <div className="hero-network-overlay" aria-hidden="true">
            <svg
              className="hero-network-svg"
              viewBox="0 0 400 640"
              preserveAspectRatio="xMidYMid slice"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                {/* Micro Dot Matrix Grid */}
                <pattern id="tacticalGrid" width="28" height="28" patternUnits="userSpaceOnUse">
                  <circle cx="14" cy="14" r="0.8" fill="rgba(255, 255, 255, 0.08)" />
                </pattern>

                {/* Gradients for Edges */}
                <linearGradient id="edgeGradMain" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.45" />
                  <stop offset="50%" stopColor="#818cf8" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#c084fc" stopOpacity="0.25" />
                </linearGradient>

                <linearGradient id="edgeGradSubtle" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#bae6fd" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="#e9d5ff" stopOpacity="0.15" />
                </linearGradient>

                <filter id="nodeGlowEnhanced" x="-60%" y="-60%" width="220%" height="220%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Background Tactical Matrix Grid */}
              <rect width="100%" height="100%" fill="url(#tacticalGrid)" opacity="0.85" />

              {/* Connecting Edges Between 6 Nodes */}
              <g className="network-edges" stroke="url(#edgeGradMain)" strokeWidth="1.2">
                <line x1="310" y1="95" x2="170" y2="180" />
                <line x1="310" y1="95" x2="335" y2="255" />
                <line x1="170" y1="180" x2="335" y2="255" />
                <line x1="170" y1="180" x2="75" y2="340" />
                <line x1="335" y1="255" x2="225" y2="400" />
                <line x1="75" y1="340" x2="225" y2="400" />
                <line x1="225" y1="400" x2="335" y2="495" />
                <line x1="335" y1="255" x2="335" y2="495" />
              </g>

              {/* Secondary Cross-link with Subtle Dash */}
              <g stroke="url(#edgeGradSubtle)" strokeWidth="0.9" strokeDasharray="3 4">
                <line x1="75" y1="340" x2="310" y2="95" />
                <line x1="170" y1="180" x2="335" y2="495" />
              </g>

              {/* Live Animated Data Flow Packets (Smooth SVG Motion) */}
              <circle r="2.2" fill="#67e8f9" filter="url(#nodeGlowEnhanced)">
                <animateMotion
                  path="M 75 340 L 170 180 L 310 95"
                  dur="6s"
                  repeatCount="indefinite"
                />
              </circle>
              <circle r="2" fill="#c084fc" filter="url(#nodeGlowEnhanced)">
                <animateMotion
                  path="M 310 95 L 335 255 L 225 400 L 335 495"
                  dur="7s"
                  repeatCount="indefinite"
                />
              </circle>

              {/* 6 HIGH-TECH FORENSIC NODES */}

              {/* Node 1: Top Right (Entry Record) */}
              <g className="network-node" transform="translate(310, 95)">
                <circle r="14" fill="#38bdf8" fillOpacity="0.12" className="node-halo" />
                <circle r="7.5" stroke="rgba(125, 211, 252, 0.45)" strokeWidth="0.8" />
                <circle r="3.5" fill="#ffffff" filter="url(#nodeGlowEnhanced)" />
                <text x="12" y="3" className="node-tech-tag">REC-01</text>
              </g>

              {/* Node 2: Upper Center Hub (Syndicate Analysis Center) */}
              <g className="network-node" transform="translate(170, 180)">
                <circle r="18" fill="#818cf8" fillOpacity="0.16" className="node-halo node-halo-pulse" />
                {/* Animated Expanding Radar Ping */}
                <circle r="12" stroke="rgba(147, 197, 253, 0.6)" strokeWidth="0.9" fill="none" className="node-radar-ping" />
                {/* Rotating Reticle */}
                <circle r="9" stroke="rgba(255, 255, 255, 0.45)" strokeWidth="0.9" strokeDasharray="2 2" className="node-reticle-spin" />
                {/* Crosshairs */}
                <line x1="-11" y1="0" x2="-7" y2="0" stroke="rgba(186, 230, 253, 0.6)" strokeWidth="0.9" />
                <line x1="7" y1="0" x2="11" y2="0" stroke="rgba(186, 230, 253, 0.6)" strokeWidth="0.9" />
                <line x1="0" y1="-11" x2="0" y2="-7" stroke="rgba(186, 230, 253, 0.6)" strokeWidth="0.9" />
                <line x1="0" y1="7" x2="0" y2="11" stroke="rgba(186, 230, 253, 0.6)" strokeWidth="0.9" />
                <circle r="4.5" fill="#ffffff" filter="url(#nodeGlowEnhanced)" />
                <text x="14" y="-4" className="node-tech-tag">SYN-HUB</text>
              </g>

              {/* Node 3: Mid Right (Evidentiary Marker) */}
              <g className="network-node" transform="translate(335, 255)">
                <circle r="15" fill="#c084fc" fillOpacity="0.14" className="node-halo" />
                <circle r="8" stroke="rgba(216, 180, 254, 0.4)" strokeWidth="0.8" />
                <circle r="3.8" fill="#ffffff" filter="url(#nodeGlowEnhanced)" />
                <text x="12" y="3" className="node-tech-tag">EV-04</text>
              </g>

              {/* Node 4: Mid Left (Source Link) */}
              <g className="network-node" transform="translate(75, 340)">
                <circle r="15" fill="#38bdf8" fillOpacity="0.14" className="node-halo" />
                <circle r="7.5" stroke="rgba(125, 211, 252, 0.4)" strokeWidth="0.8" />
                <circle r="3.5" fill="#e0f2fe" filter="url(#nodeGlowEnhanced)" />
              </g>

              {/* Node 5: Central Lower Hub (AI Graph & Association Engine) */}
              <g className="network-node" transform="translate(225, 400)">
                <circle r="20" fill="#38bdf8" fillOpacity="0.18" className="node-halo node-halo-pulse-delayed" />
                {/* Radar Ping */}
                <circle r="13" stroke="rgba(103, 232, 249, 0.6)" strokeWidth="0.9" fill="none" className="node-radar-ping-delayed" />
                {/* Concentric Target Ring */}
                <circle r="10" stroke="rgba(255, 255, 255, 0.5)" strokeWidth="0.9" strokeDasharray="3 2" className="node-reticle-spin" />
                {/* Crosshairs */}
                <line x1="-12" y1="0" x2="-8" y2="0" stroke="rgba(147, 197, 253, 0.65)" strokeWidth="0.9" />
                <line x1="8" y1="0" x2="12" y2="0" stroke="rgba(147, 197, 253, 0.65)" strokeWidth="0.9" />
                <line x1="0" y1="-12" x2="0" y2="-8" stroke="rgba(147, 197, 253, 0.65)" strokeWidth="0.9" />
                <line x1="0" y1="8" x2="0" y2="12" stroke="rgba(147, 197, 253, 0.65)" strokeWidth="0.9" />
                <circle r="5" fill="#ffffff" filter="url(#nodeGlowEnhanced)" />
                <text x="16" y="4" className="node-tech-tag">LINK // AI</text>
              </g>

              {/* Node 6: Lower Right (Closure Marker) */}
              <g className="network-node" transform="translate(335, 495)">
                <circle r="15" fill="#c084fc" fillOpacity="0.14" className="node-halo" />
                <circle r="8" stroke="rgba(216, 180, 254, 0.45)" strokeWidth="0.8" />
                <circle r="3.8" fill="#ffffff" filter="url(#nodeGlowEnhanced)" />
              </g>
            </svg>
          </div>

          <div className="hero-top-badge-row">
            <div className="hero-top-badge">
              <div className="hero-star-wrapper">
                <CrimeLensStar size={32} color="#ffffff" strokeWidth={3.5} />
              </div>
              <span className="hero-brand-name">
                <span className="hero-brand-crime">Crime</span>
                <span className="hero-brand-lens">Lens</span>
              </span>
            </div>
          </div>

          <div className="hero-bottom-content">
            <span className="hero-kicker">INVESTIGATION PLATFORM</span>
            <h1 className="hero-main-title">
              Connect evidence, track suspects, and solve cases faster.
            </h1>
            <p className="hero-desc">
              A secure workspace for detectives and forensic teams to link critical evidence, map crime networks, and close active investigations.
            </p>
            <div className="hero-features-list">
              <div className="hero-feature-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#67e8f9" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Automated Entity Resolution & Deduplication</span>
              </div>
              <div className="hero-feature-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#67e8f9" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Interactive Crime Network & Path Analysis</span>
              </div>
              <div className="hero-feature-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#67e8f9" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Chain-of-Custody & Evidentiary Audit Trail</span>
              </div>
            </div>
          </div>
        </div>

        {/* 2. RIGHT SIGN IN FORM PANEL */}
        <div className="aurora-right-form">
          <div className="form-brand-mark">
            <CrimeLensLogo size={34} iconSize={20} withBadge={true} />
            <span className="form-brand-name">
              <span className="form-brand-crime">Crime</span>
              <span className="form-brand-lens">Lens</span>
            </span>
          </div>

          <div className="form-heading-group">
            <h2 className="form-title">Investigator Portal</h2>
            <p className="form-subtitle">
              Sign in with your authorized department clearance to access active case dossiers, forensic intelligence, and linked evidence records.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="auth-inputs-form">
            {error && (
              <div className="auth-error-banner" role="alert">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            {/* Email Field */}
            <div className="auth-field-group">
              <label htmlFor="login-email" className="auth-label">
                Your email
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="investigator@crimelens.local"
                required
                disabled={loading}
                autoComplete="email"
                className="auth-text-input"
              />
            </div>

            {/* Password Field */}
            <div className="auth-field-group">
              <label htmlFor="login-password" className="auth-label">
                Password
              </label>
              <div className="password-input-wrapper">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  disabled={loading}
                  autoComplete="current-password"
                  className="auth-text-input password-field"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="password-eye-btn"
                  title={showPassword ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  <EyeIcon show={showPassword} />
                </button>
              </div>
            </div>

            {/* Submit Action Button */}
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="auth-action-submit-btn"
            >
              {loading ? "Authenticating Clearance…" : "Sign In to Console"}
            </button>

            {/* Quick Demo Clearance Header */}
            <div className="auth-clearance-header">
              <span className="clearance-label">QUICK CLEARANCE PROFILES</span>
            </div>

            {/* Quick Demo Clearance Pills */}
            <div className="quick-demo-pills-row">
              <button
                type="button"
                className="quick-demo-pill"
                onClick={() => handleQuickFill("dev@crimelens.local", "password")}
                title="Sign in as Administrator"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <span>Admin</span>
              </button>

              <button
                type="button"
                className="quick-demo-pill"
                onClick={() => handleQuickFill("officer@crimelens.local", "password")}
                title="Sign in as Investigator"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <span>Investigator</span>
              </button>

              <button
                type="button"
                className="quick-demo-pill"
                onClick={() => handleQuickFill("analyst@crimelens.local", "password")}
                title="Sign in as Forensic Analyst"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M10 2v7.31L4.15 20.3A2 2 0 0 0 5.89 23h12.22a2 2 0 0 0 1.74-2.7L14 9.31V2" />
                  <line x1="8.5" y1="2" x2="15.5" y2="2" />
                </svg>
                <span>Forensic</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
