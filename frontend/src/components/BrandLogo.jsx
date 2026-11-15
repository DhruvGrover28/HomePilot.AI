import React from "react";

export function BrandSymbol({ size = "md", className = "", animate = false }) {
  const sizeClasses = {
    xs: "w-6 h-6",
    sm: "w-7 h-7",
    md: "w-9 h-9",
    lg: "w-10 h-10",
    xl: "w-12 h-12",
  };
  const sizeClass = sizeClasses[size] || size;

  return (
    <svg
      viewBox="0 0 100 100"
      className={`${sizeClass} ${animate ? "animate-pulse" : ""} ${className} shrink-0`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="HomePilot AI Symbol"
    >
      <defs>
        <linearGradient id="hpBg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0B0F19" />
          <stop offset="100%" stopColor="#0F172A" />
        </linearGradient>
        <linearGradient id="hpTeal" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#22D3EE" />
          <stop offset="100%" stopColor="#14B8A6" />
        </linearGradient>
        <linearGradient id="hpPilot" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38BDF8" />
          <stop offset="50%" stopColor="#2DD4BF" />
          <stop offset="100%" stopColor="#34D399" />
        </linearGradient>
      </defs>

      {/* Container Base (Midnight Navy Squircle) */}
      <rect x="4" y="4" width="92" height="92" rx="22" fill="url(#hpBg)" stroke="#1E293B" strokeWidth="1.5" />

      {/* Outer Geometric House Contour */}
      <path
        d="M 50 16 L 81 38 L 81 77 A 5 5 0 0 1 76 82 L 24 82 A 5 5 0 0 1 19 77 L 19 38 Z"
        stroke="url(#hpTeal)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="#0D1527"
        fillOpacity="0.6"
      />

      {/* Subtle Apex Beacon Line */}
      <line x1="50" y1="21" x2="50" y2="44" stroke="#06B6D4" strokeWidth="1.8" strokeDasharray="2 2" strokeOpacity="0.8" />

      {/* Interconnected 4-Agent Circuit Grid */}
      <line x1="33" y1="46" x2="67" y2="46" stroke="#334155" strokeWidth="1.8" />
      <line x1="33" y1="68" x2="67" y2="68" stroke="#334155" strokeWidth="1.8" />
      <line x1="33" y1="46" x2="33" y2="68" stroke="#334155" strokeWidth="1.8" />
      <line x1="67" y1="46" x2="67" y2="68" stroke="#334155" strokeWidth="1.8" />

      {/* Diagonal Agent-to-Pilot Telemetry Links */}
      <line x1="33" y1="46" x2="50" y2="57" stroke="#0D9488" strokeWidth="1.4" strokeOpacity="0.7" />
      <line x1="67" y1="46" x2="50" y2="57" stroke="#0D9488" strokeWidth="1.4" strokeOpacity="0.7" />
      <line x1="33" y1="68" x2="50" y2="57" stroke="#0D9488" strokeWidth="1.4" strokeOpacity="0.7" />
      <line x1="67" y1="68" x2="50" y2="57" stroke="#0D9488" strokeWidth="1.4" strokeOpacity="0.7" />

      {/* The Four Specialist Agent Nodes */}
      <circle cx="33" cy="46" r="4.5" fill="#38BDF8" stroke="#0B0F19" strokeWidth="1.5" />
      <circle cx="33" cy="46" r="1.8" fill="#FFFFFF" />

      <circle cx="67" cy="46" r="4.5" fill="#22D3EE" stroke="#0B0F19" strokeWidth="1.5" />
      <circle cx="67" cy="46" r="1.8" fill="#FFFFFF" />

      <circle cx="33" cy="68" r="4.5" fill="#34D399" stroke="#0B0F19" strokeWidth="1.5" />
      <circle cx="33" cy="68" r="1.8" fill="#FFFFFF" />

      <circle cx="67" cy="68" r="4.5" fill="#2DD4BF" stroke="#0B0F19" strokeWidth="1.5" />
      <circle cx="67" cy="68" r="1.8" fill="#FFFFFF" />

      {/* Central Pilot Navigation Diamond */}
      <path
        d="M 50 46 L 54.5 54.5 L 63 57 L 54.5 59.5 L 50 68 L 45.5 59.5 L 37 57 L 45.5 54.5 Z"
        fill="url(#hpPilot)"
      />
      <circle cx="50" cy="57" r="2" fill="#FFFFFF" />
    </svg>
  );
}

export default function BrandLogo({
  variant = "wordmark", // "symbol" | "wordmark"
  size = "md",
  subtitle = null,
  animate = false,
  className = "",
  theme = "dark",
}) {
  if (variant === "symbol") {
    return <BrandSymbol size={size} animate={animate} className={className} />;
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <BrandSymbol size={size} animate={animate} />
      <div className="flex flex-col">
        <div className="flex items-center gap-1.5 leading-tight">
          <span className={`font-bold tracking-tight text-base sm:text-lg ${theme === "light" ? "text-slate-900" : "text-white"}`}>
            HomePilot
          </span>
          <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-teal-400 text-slate-950 shadow-xs">
            AI
          </span>
        </div>
        {subtitle && (
          <p className="text-[10px] font-medium text-slate-400 tracking-wide uppercase truncate max-w-[150px] mt-0.5">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
