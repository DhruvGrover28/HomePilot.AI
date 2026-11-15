import React, { useState, useEffect } from "react";
import { apiJson, apiFetch } from "./api";
import Navigation from "./components/Navigation";
import PublicLanding from "./components/PublicLanding";
import OnboardingWizard from "./components/OnboardingWizard";
import DashboardView from "./components/DashboardView";
import EnergyView from "./components/EnergyView";
import WaterView from "./components/WaterView";
import MaintenanceView from "./components/MaintenanceView";
import InventoryView from "./components/InventoryView";
import MonitoringView from "./components/MonitoringView";
import InvestigationsView from "./components/InvestigationsView";
import AssistantView from "./components/AssistantView";
import SettingsView from "./components/SettingsView";

export default function App() {
  const [authUser, setAuthUser] = useState(null);
  const [household, setHousehold] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  const [currentView, setCurrentView] = useState("dashboard");
  const [summary, setSummary] = useState(null);
  const [monitoringIssues, setMonitoringIssues] = useState([]);
  const [intelligence, setIntelligence] = useState(null);
  const [selectedAgentRun, setSelectedAgentRun] = useState(null);

  const [globalLoading, setGlobalLoading] = useState(true);
  const [workingAction, setWorkingAction] = useState("");
  const [bannerError, setBannerError] = useState("");

  // Theme application
  useEffect(() => {
    const theme = authUser?.theme_preference || "system";
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else if (theme === "light") {
      root.classList.remove("dark");
    } else {
      // system
      if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        root.classList.add("dark");
      } else {
        root.classList.remove("dark");
      }
    }
  }, [authUser?.theme_preference]);

  // Load user & household on mount
  async function checkAuth() {
    try {
      const userRes = await apiFetch("/api/auth/me");
      if (userRes.ok) {
        const user = await userRes.json();
        // Fetch household details
        let hhData = null;
        try {
          hhData = await apiJson("/api/auth/household");
        } catch (err) {
          if (err.status === 401) {
            setAuthUser(null);
            setHousehold(null);
            return;
          }
          if (err.status === 404 || err.status === 409) {
            hhData = null;
          } else {
            setBannerError(err.message || "Failed to load household configuration.");
          }
        }
        setAuthUser(user);
        setHousehold(hhData);
        await loadHouseholdData();
      } else {
        setAuthUser(null);
        setHousehold(null);
      }
    } catch {
      setAuthUser(null);
      setHousehold(null);
    } finally {
      setAuthChecked(true);
      setGlobalLoading(false);
    }
  }

  async function loadHouseholdData() {
    try {
      const [sumData, monData, intData] = await Promise.allSettled([
        apiJson("/api/dashboard/summary"),
        apiJson("/api/monitoring/issues"),
        apiJson("/api/intelligence/summary"),
      ]);

      const authErr = [sumData, monData, intData].find(
        (r) => r.status === "rejected" && r.reason?.status === 401
      );
      if (authErr) {
        setAuthUser(null);
        setHousehold(null);
        return;
      }

      if (sumData.status === "fulfilled") setSummary(sumData.value);
      if (monData.status === "fulfilled") setMonitoringIssues(monData.value);
      if (intData.status === "fulfilled") setIntelligence(intData.value);
    } catch (err) {
      if (err.status === 401) {
        setAuthUser(null);
        setHousehold(null);
        return;
      }
      setBannerError(err.message || "Failed to load household operations data.");
    }
  }

  useEffect(() => {
    checkAuth();
  }, []);

  async function handleLogout() {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } finally {
      setAuthUser(null);
      setHousehold(null);
      setCurrentView("dashboard");
    }
  }

  async function handleQuickRunMonitoring() {
    setWorkingAction("monitoring");
    setBannerError("");
    try {
      const issues = await apiJson("/api/monitoring/check", {
        method: "POST",
        body: JSON.stringify({}),
      });
      setMonitoringIssues(issues);
      // reload intelligence
      try {
        const intData = await apiJson("/api/intelligence/summary");
        setIntelligence(intData);
      } catch {
        // ignore
      }
    } catch (err) {
      setBannerError(err.message || "Failed to run monitoring sweep.");
    } finally {
      setWorkingAction("");
    }
  }

  async function handleRunFullAnalysis() {
    setWorkingAction("analysis");
    setBannerError("");
    try {
      const run = await apiJson("/api/agents/runs", {
        method: "POST",
        body: JSON.stringify({
          goal: "Review energy, water, maintenance and inventory priorities.",
        }),
      });
      setSelectedAgentRun(run);
      setCurrentView("investigations");
      await loadHouseholdData();
    } catch (err) {
      setBannerError(err.message || "Failed to run household analysis.");
    } finally {
      setWorkingAction("");
    }
  }

  async function handleSeedDemoData() {
    setBannerError("");
    try {
      await apiJson("/api/demo/seed", { method: "POST" });
      await loadHouseholdData();
    } catch (err) {
      setBannerError(err.message || "Failed to seed demo data.");
      throw err;
    }
  }

  async function handleUpdateRecommendationStatus(recId, status) {
    try {
      await apiJson(`/api/recommendations/${recId}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      await loadHouseholdData();
    } catch (err) {
      setBannerError(err.message || "Failed to update recommendation status.");
    }
  }

  function handleInspectRun(run) {
    setSelectedAgentRun(run);
    setCurrentView("investigations");
  }

  // 1. Initial Loading Screen
  if (globalLoading) {
    return (
      <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100 p-6 space-y-4">
        <div className="h-10 w-10 rounded-xl bg-teal-500/20 border border-teal-400/40 flex items-center justify-center text-teal-300 font-bold text-xl animate-pulse">
          HP
        </div>
        <p className="text-xs text-slate-400 font-mono tracking-wider uppercase">
          Initializing HomePilot AI Operations...
        </p>
      </main>
    );
  }

  // 2. Unauthenticated -> Public Landing & Auth Modal
  if (!authChecked || !authUser) {
    return (
      <PublicLanding
        onAuthenticated={async () => {
          const userRes = await apiFetch("/api/auth/me");
          if (!userRes.ok) {
            setAuthUser(null);
            setHousehold(null);
            throw new Error("Session verification failed. Please check browser cookie settings.");
          }
          const verifiedUser = await userRes.json();
          let hh = null;
          try {
            hh = await apiJson("/api/auth/household");
          } catch (err) {
            if (err.status === 401) {
              setAuthUser(null);
              setHousehold(null);
              throw new Error("Session authentication failed while retrieving household.");
            }
            if (err.status === 404 || err.status === 409) {
              hh = null;
            } else {
              setAuthUser(null);
              setHousehold(null);
              throw err;
            }
          }
          setHousehold(hh);
          setAuthUser(verifiedUser);
          await loadHouseholdData();
        }}
      />
    );
  }

  // 3. Authenticated but Onboarding Incomplete -> Wizard
  if (household && !household.onboarding_completed) {
    return (
      <OnboardingWizard
        household={household}
        onComplete={async () => {
          try {
            const hh = await apiJson("/api/auth/household");
            setHousehold(hh);
            await loadHouseholdData();
          } catch (err) {
            if (err.status === 401) {
              setAuthUser(null);
              setHousehold(null);
              return;
            }
            setBannerError(err.message || "Failed to update household settings.");
          }
        }}
        onSeedDemo={handleSeedDemoData}
      />
    );
  }

  // 4. Authenticated SaaS App Shell
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col md:flex-row font-sans selection:bg-teal-500 selection:text-white">
      {/* Sidebar Navigation */}
      <Navigation
        currentView={currentView}
        setCurrentView={setCurrentView}
        user={authUser}
        household={household}
        onLogout={handleLogout}
        onQuickRunMonitoring={handleQuickRunMonitoring}
        monitoringCount={monitoringIssues.length}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto max-h-screen">
        {/* Global Alert Banner */}
        {bannerError && (
          <div className="m-6 mb-0 p-4 rounded-xl bg-red-950/60 border border-red-700/60 text-xs text-red-300 flex items-center justify-between">
            <span>{bannerError}</span>
            <button onClick={() => setBannerError("")} className="text-red-400 hover:text-white text-xs">
              ✕
            </button>
          </div>
        )}

        {/* View Routing */}
        <div className="p-6 md:p-8 space-y-6">
          {currentView === "dashboard" && (
            <DashboardView
              summary={summary}
              monitoringIssues={monitoringIssues}
              intelligence={intelligence}
              onNavigate={(v) => setCurrentView(v)}
              onRunMonitoring={handleQuickRunMonitoring}
              onRunAnalysis={handleRunFullAnalysis}
              workingAction={workingAction}
              onUpdateRecommendationStatus={handleUpdateRecommendationStatus}
            />
          )}

          {currentView === "energy" && (
            <EnergyView onDataChanged={loadHouseholdData} />
          )}

          {currentView === "water" && (
            <WaterView onDataChanged={loadHouseholdData} />
          )}

          {currentView === "maintenance" && (
            <MaintenanceView onDataChanged={loadHouseholdData} />
          )}

          {currentView === "inventory" && (
            <InventoryView onDataChanged={loadHouseholdData} />
          )}

          {currentView === "monitoring" && (
            <MonitoringView
              monitoringIssues={monitoringIssues}
              onRunMonitoring={handleQuickRunMonitoring}
              onInspectRun={handleInspectRun}
              working={workingAction === "monitoring"}
            />
          )}

          {currentView === "investigations" && (
            <InvestigationsView
              activeRun={selectedAgentRun}
              onSelectRun={(r) => setSelectedAgentRun(r)}
            />
          )}

          {currentView === "assistant" && (
            <AssistantView onInspectRun={handleInspectRun} />
          )}

          {currentView === "settings" && (
            <SettingsView
              user={authUser}
              household={household}
              onUserUpdated={(u) => setAuthUser(u)}
              onHouseholdUpdated={(h) => setHousehold(h)}
              onSeedDemo={handleSeedDemoData}
              onLogout={handleLogout}
            />
          )}
        </div>
      </main>
    </div>
  );
}
