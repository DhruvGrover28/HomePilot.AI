import React, { useState } from "react";
import { Bell, Activity, X } from "lucide-react";

export default function MonitoringView({
  monitoringIssues,
  onRunMonitoring,
  onInspectRun,
  working,
}) {
  const [activeTab, setActiveTab] = useState("alerts"); // "alerts" | "timeline"
  const [filterDomain, setFilterDomain] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [selectedIssue, setSelectedIssue] = useState(null);

  const filtered = monitoringIssues.filter((issue) => {
    if (filterDomain !== "all" && issue.domain !== filterDomain) return false;
    if (filterStatus !== "all" && issue.issue_status !== filterStatus) return false;
    return true;
  });

  const timelineSorted = [...monitoringIssues].sort(
    (a, b) => new Date(b.last_detected_at || 0) - new Date(a.last_detected_at || 0)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2.5">
            <Bell className="w-6 h-6 text-purple-500" />
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Activity & Notification Centre</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time telemetry monitoring, automated trigger provenance, and anomaly event stream.
          </p>
        </div>

        <button
          onClick={onRunMonitoring}
          disabled={working}
          className="px-4 py-2.5 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition disabled:opacity-50 flex items-center gap-1.5"
        >
          <Activity className="w-3.5 h-3.5" />
          <span>{working ? "Running Sweep..." : "Run Monitoring Sweep"}</span>
        </button>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-4 text-xs font-semibold">
        <button
          onClick={() => setActiveTab("alerts")}
          className={`pb-2.5 px-1 border-b-2 transition ${
            activeTab === "alerts"
              ? "border-teal-500 text-teal-600 dark:text-teal-400 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          }`}
        >
          Active Notifications ({monitoringIssues.filter((i) => i.issue_status === "open").length})
        </button>
        <button
          onClick={() => setActiveTab("timeline")}
          className={`pb-2.5 px-1 border-b-2 transition ${
            activeTab === "timeline"
              ? "border-teal-500 text-teal-600 dark:text-teal-400 font-bold"
              : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          }`}
        >
          Activity Timeline Feed ({monitoringIssues.length} events)
        </button>
      </div>

      {activeTab === "alerts" ? (
        <>
          {/* Filter Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-500 dark:text-slate-400">Domain:</span>
              {["all", "energy", "water", "maintenance", "inventory"].map((domain) => (
                <button
                  key={domain}
                  onClick={() => setFilterDomain(domain)}
                  className={`px-3 py-1.5 rounded-lg capitalize font-medium transition ${
                    filterDomain === domain
                      ? "bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900"
                      : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800"
                  }`}
                >
                  {domain}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-500 dark:text-slate-400">Status:</span>
              {["all", "open", "investigated", "resolved"].map((status) => (
                <button
                  key={status}
                  onClick={() => setFilterStatus(status)}
                  className={`px-3 py-1.5 rounded-lg capitalize font-medium transition ${
                    filterStatus === status
                      ? "bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900"
                      : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800"
                  }`}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>

          {/* Issues Grid / List */}
          <div className="grid lg:grid-cols-12 gap-6">
            <div className={selectedIssue ? "lg:col-span-7 space-y-3" : "lg:col-span-12 space-y-3"}>
              {filtered.length === 0 ? (
                <div className="p-8 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center text-xs text-slate-400">
                  No monitoring issues matching the selected filters.
                </div>
              ) : (
            filtered.map((issue) => {
              const isSelected = selectedIssue?.id === issue.id;
              return (
                <div
                  key={issue.id}
                  onClick={() => setSelectedIssue(issue)}
                  className={`cursor-pointer p-4 rounded-xl border bg-white dark:bg-slate-900 shadow-sm transition space-y-2 ${
                    isSelected
                      ? "border-teal-500 ring-1 ring-teal-500"
                      : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {issue.domain}
                      </span>
                      <h2 className="font-bold text-sm text-slate-900 dark:text-white mt-1">
                        {issue.title}
                      </h2>
                    </div>

                    <div className="flex flex-col items-end gap-1">
                      <span
                        className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full ${
                          issue.issue_status === "open"
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                            : "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300"
                        }`}
                      >
                        {issue.issue_status}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {issue.occurrence_count} occurrences
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-slate-500 dark:text-slate-400 flex flex-wrap gap-x-4 gap-y-1 pt-1 border-t border-slate-100 dark:border-slate-800">
                    <span>Provenance: <strong className="text-slate-700 dark:text-slate-300">{issue.last_trigger_source || "system"}</strong></span>
                    {issue.latest_evidence_id && <span>Evidence ID: #{issue.latest_evidence_id}</span>}
                    <span>Investigation: <strong className="capitalize text-slate-700 dark:text-slate-300">{issue.investigation_status}</strong></span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Issue Detail Drawer */}
        {selectedIssue && (
          <div className="lg:col-span-5 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div>
                <span className="text-[10px] uppercase tracking-wider font-bold text-teal-600 dark:text-teal-400">
                  Issue Detail #{selectedIssue.id}
                </span>
                <h3 className="font-bold text-base text-slate-900 dark:text-white mt-0.5">
                  {selectedIssue.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedIssue(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800">
                <div>
                  <span className="text-[10px] text-slate-400 block">Domain</span>
                  <span className="font-semibold capitalize text-slate-800 dark:text-slate-200">{selectedIssue.domain}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Status</span>
                  <span className="font-semibold uppercase text-amber-600">{selectedIssue.issue_status}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">First Detected</span>
                  <span className="font-mono text-slate-600 dark:text-slate-300">{selectedIssue.first_detected_at?.slice(0, 19)}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Last Detected</span>
                  <span className="font-mono text-slate-600 dark:text-slate-300">{selectedIssue.last_detected_at?.slice(0, 19)}</span>
                </div>
              </div>

              {/* Linked Run Findings & Recommendations */}
              {selectedIssue.latest_run ? (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 dark:text-white">Agent Investigation</span>
                    {onInspectRun && (
                      <button
                        onClick={() => onInspectRun(selectedIssue.latest_run)}
                        className="text-teal-600 dark:text-teal-400 text-xs font-semibold hover:underline"
                      >
                        Inspect Full Trace →
                      </button>
                    )}
                  </div>

                  {selectedIssue.latest_run.findings?.map((f) => (
                    <div key={f.id} className="p-3 rounded-lg bg-teal-50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-800/60">
                      <p className="font-semibold text-teal-900 dark:text-teal-200">{f.subject}</p>
                      <p className="text-[11px] text-teal-800 dark:text-teal-300 mt-1">{f.summary}</p>
                    </div>
                  ))}

                  {selectedIssue.latest_run.recommendations?.map((r, i) => (
                    <div key={i} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                      <p className="font-semibold text-slate-800 dark:text-slate-200">{r.suggested_action}</p>
                      <p className="text-[11px] text-slate-500 mt-1">{r.summary}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-500 text-center">
                  No automated investigation run attached yet. Run household analysis to investigate.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  ) : (
    /* Activity Timeline Feed */
    <div className="space-y-4">
      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
        {timelineSorted.length === 0 ? (
          <div className="p-8 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center text-xs text-slate-400">
            No activity events recorded yet.
          </div>
        ) : (
          timelineSorted.map((item) => (
            <div key={item.id} className="relative group">
              <div className="absolute -left-[19px] top-1.5 h-3 w-3 rounded-full bg-teal-500 ring-4 ring-white dark:ring-slate-950" />
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300">
                      {item.domain}
                    </span>
                    <span className="font-bold text-sm text-slate-900 dark:text-white">
                      {item.title}
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    {item.last_detected_at ? new Date(item.last_detected_at).toLocaleString() : "Unknown"}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-100 dark:border-slate-800">
                  <span>Provenance: <strong className="text-slate-700 dark:text-slate-300 capitalize">{item.last_trigger_source || "system"}</strong></span>
                  <span>Occurrences: <strong className="text-slate-700 dark:text-slate-300">{item.occurrence_count}</strong></span>
                  <span>Status: <strong className="uppercase text-amber-600">{item.issue_status}</strong></span>
                  {item.latest_run && (
                    <button
                      onClick={() => onInspectRun && onInspectRun(item.latest_run)}
                      className="text-teal-600 dark:text-teal-400 font-semibold hover:underline ml-auto"
                    >
                      Inspect Investigation Run →
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )}
</div>
  );
}
