import React, { useState } from "react";

export default function Navigation({
  currentView,
  setCurrentView,
  user,
  household,
  onLogout,
  onQuickRunMonitoring,
  monitoringCount = 0,
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "energy", label: "Energy", icon: "⚡" },
    { id: "water", label: "Water", icon: "💧" },
    { id: "maintenance", label: "Maintenance", icon: "🔧" },
    { id: "inventory", label: "Inventory", icon: "📦" },
    { id: "monitoring", label: "Monitoring", icon: "🔔", badge: monitoringCount > 0 ? monitoringCount : null },
    { id: "investigations", label: "Investigations", icon: "🧠" },
    { id: "assistant", label: "Assistant", icon: "💬" },
    { id: "settings", label: "Settings", icon: "⚙️" },
  ];

  const handleSelectView = (viewId) => {
    setCurrentView(viewId);
    setMobileMenuOpen(false);
  };

  return (
    <aside className="w-full md:w-64 bg-slate-900 text-slate-100 flex flex-col justify-between border-r border-slate-800 shrink-0">
      <div>
        {/* Brand header / Mobile Topbar */}
        <div className="p-4 md:p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-teal-500/20 border border-teal-400/40 flex items-center justify-center text-teal-300 font-bold text-lg">
              HP
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                HomePilot <span className="text-xs font-semibold px-1.5 py-0.5 rounded bg-teal-400 text-slate-950">AI</span>
              </h1>
              <p className="text-xs text-slate-400 truncate max-w-[140px]">
                {household?.name || "My Household"}
              </p>
            </div>
          </div>

          {/* Mobile Hamburger Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? "✕" : "☰"}
          </button>
        </div>

        {/* Navigation links - Desktop always visible, Mobile toggled */}
        <nav className={`p-3 space-y-1 ${mobileMenuOpen ? "block" : "hidden md:block"}`}>
          {navItems.map((item) => {
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleSelectView(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-teal-600 text-white shadow-sm"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-base">{item.icon}</span>
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                    isActive ? "bg-white text-teal-800" : "bg-amber-500 text-slate-950"
                  }`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer controls & user info */}
      <div className={`p-4 border-t border-slate-800 space-y-3 ${mobileMenuOpen ? "block" : "hidden md:block"}`}>
        <button
          onClick={onQuickRunMonitoring}
          className="w-full py-2 px-3 bg-slate-800 hover:bg-slate-700 text-teal-300 border border-slate-700 rounded-lg text-xs font-medium flex items-center justify-center gap-2 transition"
        >
          <span>⚡ Check Monitoring</span>
        </button>

        <div className="flex items-center justify-between pt-2 text-xs">
          <div className="truncate mr-2">
            <p className="font-medium text-slate-200 truncate">{user?.full_name}</p>
            <p className="text-slate-400 truncate">{user?.email}</p>
          </div>
          <button
            onClick={onLogout}
            title="Log out"
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-red-400 transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
