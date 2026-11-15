import React, { useState } from "react";
import BrandLogo from "./BrandLogo";
import {
  LayoutDashboard,
  Zap,
  Droplets,
  Wrench,
  Package,
  Bell,
  Cpu,
  MessageSquare,
  Settings,
  Menu,
  X,
  LogOut,
  Activity
} from "lucide-react";

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
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "energy", label: "Energy", icon: Zap },
    { id: "water", label: "Water", icon: Droplets },
    { id: "maintenance", label: "Maintenance", icon: Wrench },
    { id: "inventory", label: "Inventory", icon: Package },
    { id: "monitoring", label: "Monitoring", icon: Bell, badge: monitoringCount > 0 ? monitoringCount : null },
    { id: "investigations", label: "Investigations", icon: Cpu },
    { id: "assistant", label: "Assistant", icon: MessageSquare },
    { id: "settings", label: "Settings", icon: Settings },
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
          <BrandLogo subtitle={household?.name || "My Household"} size="md" />

          {/* Mobile Hamburger Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation links - Desktop always visible, Mobile toggled */}
        <nav className={`p-3 space-y-1 ${mobileMenuOpen ? "block" : "hidden md:block"}`}>
          {navItems.map((item) => {
            const isActive = currentView === item.id;
            const IconComponent = item.icon;
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
                  <IconComponent className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
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
          <Activity className="w-3.5 h-3.5 text-teal-400" />
          <span>Check Monitoring</span>
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
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
