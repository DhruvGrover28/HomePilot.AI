import React from "react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import { Zap, Droplets, Wrench, Package, Brain, Activity, Check, X } from "lucide-react";

export default function DashboardView({
  summary,
  monitoringIssues,
  intelligence,
  onNavigate,
  onRunMonitoring,
  onRunAnalysis,
  workingAction,
  onUpdateRecommendationStatus,
}) {
  const electricityData = (summary?.electricity || []).map((row) => ({
    date: row.reading_date,
    rate: Number((row.consumption / (row.period_days || 1)).toFixed(2)),
  }));

  const waterData = (summary?.water || []).map((row) => ({
    date: row.reading_date,
    rate: Number((row.consumption / (row.period_days || 1)).toFixed(2)),
  }));

  const lowInventoryCount = (summary?.inventory || []).filter(
    (item) => item.quantity <= item.reorder_threshold
  ).length;

  return (
    <div className="space-y-6">
      {/* Top Welcome & Quick Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-teal-600 dark:text-teal-400">
            Operations Center
          </span>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
            Household Operations Dashboard
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time telemetry, deterministic monitoring, and agentic intelligence across your home.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={onRunMonitoring}
            disabled={workingAction}
            className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition flex items-center gap-1.5"
          >
            <Activity className="w-3.5 h-3.5 text-teal-500" />
            <span>{workingAction === "monitoring" ? "Checking..." : "Run Monitoring Check"}</span>
          </button>
          <button
            onClick={() => onRunAnalysis()}
            disabled={workingAction}
            className="px-4 py-2 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition flex items-center gap-1.5"
          >
            <Brain className="w-3.5 h-3.5" />
            <span>{workingAction === "analysis" ? "Analyzing..." : "Run Full Agent Analysis"}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Electricity */}
        <div
          onClick={() => onNavigate("energy")}
          className="cursor-pointer p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-teal-500/50 transition"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Electricity Readings</span>
            <Zap className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {summary?.electricity?.length || 0}
            </span>
            <span className="text-xs text-slate-400">periods logged</span>
          </div>
          <p className="mt-2 text-xs text-teal-600 dark:text-teal-400 font-medium">View consumption →</p>
        </div>

        {/* Water */}
        <div
          onClick={() => onNavigate("water")}
          className="cursor-pointer p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-blue-500/50 transition"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Water Readings</span>
            <Droplets className="w-4 h-4 text-cyan-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {summary?.water?.length || 0}
            </span>
            <span className="text-xs text-slate-400">periods logged</span>
          </div>
          <p className="mt-2 text-xs text-blue-600 dark:text-blue-400 font-medium">View water flow →</p>
        </div>

        {/* Appliances & Tasks */}
        <div
          onClick={() => onNavigate("maintenance")}
          className="cursor-pointer p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-amber-500/50 transition"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Appliances & Tasks</span>
            <Wrench className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {summary?.appliances?.length || 0}
            </span>
            <span className="text-xs text-amber-600 font-medium">
              ({summary?.tasks_open || 0} open tasks)
            </span>
          </div>
          <p className="mt-2 text-xs text-amber-600 dark:text-amber-400 font-medium">View maintenance →</p>
        </div>

        {/* Inventory */}
        <div
          onClick={() => onNavigate("inventory")}
          className="cursor-pointer p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-emerald-500/50 transition"
        >
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Supplies & Inventory</span>
            <Package className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {summary?.inventory?.length || 0}
            </span>
            {lowInventoryCount > 0 ? (
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300">
                {lowInventoryCount} low
              </span>
            ) : (
              <span className="text-xs text-slate-400">items stocked</span>
            )}
          </div>
          <p className="mt-2 text-xs text-emerald-600 dark:text-emerald-400 font-medium">View supplies →</p>
        </div>
      </div>

      {/* Consumption Charts Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Electricity chart */}
        <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-bold text-sm text-slate-900 dark:text-white">Electricity Daily Rate</h2>
              <p className="text-xs text-slate-500">Historical consumption rate (kWh / day)</p>
            </div>
            <span className="text-xs font-semibold px-2 py-1 rounded bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300">
              Energy Domain
            </span>
          </div>
          <div className="h-56 pt-2">
            {electricityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={electricityData}>
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="rate" stroke="#0d9488" strokeWidth={2.5} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No electricity readings recorded yet.
              </div>
            )}
          </div>
        </div>

        {/* Water chart */}
        <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-bold text-sm text-slate-900 dark:text-white">Water Daily Rate</h2>
              <p className="text-xs text-slate-500">Historical consumption rate (Litres / day)</p>
            </div>
            <span className="text-xs font-semibold px-2 py-1 rounded bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
              Water Domain
            </span>
          </div>
          <div className="h-56 pt-2">
            {waterData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={waterData}>
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="rate" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No water readings recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Intelligence & Recommendations Section */}
      {intelligence && (
        <div className="p-6 rounded-2xl bg-gradient-to-br from-indigo-50/50 to-teal-50/30 dark:from-slate-900 dark:to-slate-900 border border-indigo-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                Deterministic Intelligence
              </span>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                Prioritized Issues & Recommendations
              </h2>
            </div>
            <button
              onClick={() => onNavigate("investigations")}
              className="text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
            >
              Inspect Agent Traces →
            </button>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {/* Priority Issues */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Ranked Open Issues ({intelligence.open_issues?.length || 0})
              </h3>
              {intelligence.open_issues?.length === 0 ? (
                <div className="p-4 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-500">
                  No open issues detected across household domains.
                </div>
              ) : (
                (intelligence.open_issues || []).slice(0, 4).map((issue) => (
                  <div
                    key={issue.id}
                    className="p-3.5 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-xs flex items-center justify-between"
                  >
                    <div>
                      <p className="font-semibold text-xs text-slate-900 dark:text-white">{issue.title}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Domain: <span className="font-medium text-slate-700 dark:text-slate-300">{issue.domain}</span> · Severity: {issue.priority_factors?.severity || "standard"}
                      </p>
                    </div>
                    <span className="text-[11px] uppercase tracking-wider px-2 py-0.5 rounded font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                      {issue.investigation?.status || "open"}
                    </span>
                  </div>
                ))
              )}
            </div>

            {/* Recommendations */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Evidence-Led Actions ({intelligence.recommendations?.length || 0})
              </h3>
              {intelligence.recommendations?.length === 0 ? (
                <div className="p-4 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-500">
                  Run an agent investigation to generate evidence-backed recommendations.
                </div>
              ) : (
                (intelligence.recommendations || []).slice(0, 4).map((rec) => (
                  <div
                    key={rec.id}
                    className="p-3.5 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-xs space-y-1.5"
                  >
                    <p className="font-semibold text-xs text-slate-900 dark:text-white">
                      {rec.recommendation?.suggested_action}
                    </p>
                    <p className="text-[11px] text-teal-700 dark:text-teal-400">
                      Support: {rec.priority_factors?.evidence_support || "medium"} · Feasibility: {rec.priority_factors?.feasibility || "high"}
                    </p>
                    <div className="flex items-center justify-between pt-1 text-[10px] border-t border-slate-100 dark:border-slate-800">
                      <span className={`px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                        rec.recommendation?.status === "completed"
                          ? "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300"
                          : rec.recommendation?.status === "deferred"
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                          : rec.recommendation?.status === "dismissed"
                          ? "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-400"
                          : "bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300"
                      }`}>
                        {rec.recommendation?.status || "active"}
                      </span>
                      {onUpdateRecommendationStatus && (
                        <div className="flex items-center gap-1.5">
                          {rec.recommendation?.status !== "completed" && (
                            <button
                              onClick={() => onUpdateRecommendationStatus(rec.id, "completed")}
                              className="px-2 py-0.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium flex items-center gap-1"
                              title="Mark completed"
                            >
                              <Check className="w-3 h-3" />
                              <span>Complete</span>
                            </button>
                          )}
                          {rec.recommendation?.status !== "deferred" && rec.recommendation?.status !== "completed" && (
                            <button
                              onClick={() => onUpdateRecommendationStatus(rec.id, "deferred")}
                              className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300"
                              title="Defer action"
                            >
                              Defer
                            </button>
                          )}
                          {rec.recommendation?.status !== "dismissed" && rec.recommendation?.status !== "completed" && (
                            <button
                              onClick={() => onUpdateRecommendationStatus(rec.id, "dismissed")}
                              className="p-1 rounded text-slate-400 hover:text-red-500"
                              title="Dismiss recommendation"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {rec.recommendation?.status && rec.recommendation?.status !== "active" && (
                            <button
                              onClick={() => onUpdateRecommendationStatus(rec.id, "active")}
                              className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300"
                              title="Reactivate recommendation"
                            >
                              Reopen
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Monitoring alerts banner */}
      <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-sm text-slate-900 dark:text-white">
            Monitoring Engine Activity
          </h2>
          <button
            onClick={() => onNavigate("monitoring")}
            className="text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
          >
            View All ({monitoringIssues.length}) →
          </button>
        </div>

        {monitoringIssues.length === 0 ? (
          <p className="text-xs text-slate-500">All household telemetry parameters are within normal baseline thresholds.</p>
        ) : (
          <div className="space-y-2">
            {monitoringIssues.slice(0, 3).map((issue) => (
              <div
                key={issue.id}
                className="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-bold text-slate-800 dark:text-slate-200">{issue.title}</span>
                  <span className="ml-2 text-slate-500">({issue.domain})</span>
                </div>
                <span className="font-mono text-slate-400">Occurrences: {issue.occurrence_count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
