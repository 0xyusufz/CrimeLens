"use client";

import React from "react";

export function CrimeLensStar({
  size = 24,
  color = "currentColor",
  strokeWidth = 3.5,
  className = "",
  style = {},
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={style}
    >
      <path
        d="M12 2.5V21.5M2.5 12H21.5M5.28 5.28L18.72 18.72M5.28 18.72L18.72 5.28"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function CrimeLensLogo({
  size = 32,
  iconSize = null,
  withBadge = true,
  className = "",
}) {
  const calculatedIconSize = iconSize || Math.round(size * 0.58);

  if (!withBadge) {
    return (
      <CrimeLensStar
        size={size}
        color="#2563eb"
        className={className}
      />
    );
  }

  return (
    <div
      className={`crimelens-brand-logo ${className}`}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: `${Math.round(size * 0.28)}px`,
        background: "linear-gradient(135deg, #38bdf8 0%, #0284c7 45%, #2563eb 100%)",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 2px 10px rgba(2, 132, 199, 0.35)",
        flexShrink: 0,
      }}
    >
      <CrimeLensStar size={calculatedIconSize} color="#ffffff" strokeWidth={3.5} />
    </div>
  );
}
