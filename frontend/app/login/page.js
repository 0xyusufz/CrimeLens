"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setToken, setUser } from "../../lib/auth";
import { apiClient } from "../../lib/apiClient";
import { CrimeLensStar } from "../../components/CrimeLensLogo";
import "./login.css";

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

  const handleQuickFill = (demoEmail, demoPass) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="centered-login-viewport">
      <div className="centered-login-card">
        {/* Brand Header */}
        <div className="login-brand-header">
          <div className="login-star-badge">
            <CrimeLensStar size={32} color="#ffffff" strokeWidth={3.5} />
          </div>
          <div className="login-brand-name">
            <span className="brand-crime">Crime</span>
            <span className="brand-lens">Lens<span className="brand-optic-dot"></span></span>
          </div>
          <span className="login-brand-subtitle">FORENSIC INTELLIGENCE</span>
          <div className="login-header-divider"></div>
        </div>

        {/* Title & Subtitle */}
        <div className="login-title-group">
          <h1 className="login-main-title">Authorized Sign In</h1>
          <p className="login-subtitle">
            Enter your departmental credentials to access case dossiers, forensic intelligence, and evidence records.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="login-form-body">
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
              Department Email
            </label>
            <div className="auth-input-wrapper">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" className="input-prefix-icon">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@crimelens.local"
                required
                disabled={loading}
                autoComplete="email"
                className="auth-text-input with-prefix"
              />
            </div>
          </div>

          {/* Password Field */}
          <div className="auth-field-group">
            <label htmlFor="login-password" className="auth-label">
              Clearance Password
            </label>
            <div className="auth-input-wrapper">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" className="input-prefix-icon">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                disabled={loading}
                autoComplete="current-password"
                className="auth-text-input with-prefix with-suffix"
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
            {loading ? "Authenticating Clearance…" : "Sign In to Workspace"}
          </button>

          {/* Quick Demo Clearance Header */}
          <div className="auth-clearance-header">
            <span className="clearance-label">DEMO PROFILES</span>
          </div>

          {/* Quick Demo Clearance Buttons */}
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
              title="Sign in as Lead Investigator"
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
              <span>Analyst</span>
            </button>
          </div>
        </form>

        {/* Footer info */}
        <div className="login-card-footer">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span>Encrypted Clearance System // CJIS & ISO-27001 Compliant</span>
        </div>
      </div>
    </div>
  );
}
