import React, { useState, useEffect } from "react";
import { apiJson } from "../api";

export default function InvestigationsView({ activeRun, onSelectRun }) {
  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(activeRun || null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);

  // Form for triggering a new investigation
  const [goal, setGoal] = useState("Investigate unusual energy consumption and correlate with appliance maintenance status.");
  const [mode, setMode] = useState("live");

  const sampleGoals = [
    "Investigate unusual energy consumption and correlate with appliance maintenance status.",
    "Inspect water flow telemetry for potential leak signatures and check plumbing fixtures.",
    "Review low inventory items and cross-check with maintenance task schedules.",
    "Comprehensive cross-domain operational audit across all four household domains.",
  ];

  async function loadRuns() {
    setLoading(true);
    try {
      const data = await apiJson("/api/agents/runs");
      setRuns(data);
      if (!selectedRun && data.length > 0) {
        setSelectedRun(data[0]);
      }
    } catch (err) {
      setError(err.message || "Failed to load agent runs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
  }, []);

  useEffect(() => {
    if (activeRun) {
      setSelectedRun(activeRun);
    }
  }, [activeRun]);

  async function handleLaunchRun(e) {
    if (e) e.preventDefault();
    setRunning(true);
    setError("");
    try {
      const run = await apiJson("/api/agents/runs", {
        method: "POST",
        body: JSON.stringify({
          goal,
          mode,
        }),
      });
      setSelectedRun(run);
      await loadRuns();
      if (onSelectRun) onSelectRun(run);
    } catch (err) {
      setError(err.message || "Failed to run agent investigation.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🧠</span>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Agentic Investigations</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Dynamic LangGraph Supervisor coordination, deterministic tool executions, and transparent evidence traces.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">
            {runs.length} runs recorded
          </span>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-red-950/50 border border-red-700/60 p-4 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Launch New Investigation Form */}
      <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <h2 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
          <span>⚡</span> Launch New Agentic Investigation
        </h2>

        <form onSubmit={handleLaunchRun} className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Investigation Objective / Goal
            </label>
            <input
              type="text"
              required
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g. Investigate recent consumption anomalies and check appliance health"
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 px-3.5 py-2.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-teal-400"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-slate-400 font-medium">Quick Prompts:</span>
            {sampleGoals.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setGoal(sample)}
                className="text-[11px] px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-750 text-slate-700 dark:text-slate-300 truncate max-w-xs transition"
              >
                {sample}
              </button>
            ))}
          </div>

          <div className="pt-2 flex items-center justify-between">
            <div className="flex items-center gap-3 text-xs">
              <span className="font-semibold text-slate-600 dark:text-slate-400">Execution Mode:</span>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="live"
                  checked={mode === "live"}
                  onChange={() => setMode("live")}
                  className="text-teal-600"
                />
                <span className="text-slate-700 dark:text-slate-300">Live (LLM + Tools)</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="mock"
                  checked={mode === "mock"}
                  onChange={() => setMode("mock")}
                  className="text-teal-600"
                />
                <span className="text-slate-700 dark:text-slate-300">Mock (Deterministic Verification)</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={running}
              className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs shadow-md shadow-teal-600/20 disabled:opacity-50 transition"
            >
              {running ? "Supervisor Investigating..." : "Launch Investigation →"}
            </button>
          </div>
        </form>
      </div>

      {/* Investigation Runs Explorer Grid */}
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Past Runs Sidebar */}
        <div className="lg:col-span-4 space-y-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 px-1">
            Run History ({runs.length})
          </h2>

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {runs.length === 0 ? (
              <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-400 text-center">
                No past runs recorded.
              </div>
            ) : (
              runs.map((r) => {
                const isSelected = selectedRun?.id === r.id;
                return (
                  <div
                    key={r.id}
                    onClick={() => setSelectedRun(r)}
                    className={`cursor-pointer p-3.5 rounded-xl border bg-white dark:bg-slate-900 shadow-xs transition space-y-1.5 ${
                      isSelected
                        ? "border-teal-500 ring-1 ring-teal-500"
                        : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-mono text-slate-400">#{r.id}</span>
                      <span className="uppercase text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {r.mode}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-slate-900 dark:text-white line-clamp-2">
                      {r.goal}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                      <span>{r.findings?.length || 0} findings</span>
                      <span>{r.recommendations?.length || 0} recommendations</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Run Deep Inspection */}
        <div className="lg:col-span-8">
          {selectedRun ? (
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
              {/* Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300">
                    Run #{selectedRun.id} · {selectedRun.mode} mode
                  </span>
                  <h2 className="text-base font-bold text-slate-900 dark:text-white mt-1">
                    {selectedRun.goal}
                  </h2>
                </div>
                <div className="text-right text-[11px] text-slate-400 font-mono">
                  {selectedRun.created_at?.slice(0, 19)}
                </div>
              </div>

              {/* Dynamic Supervisor Execution Timeline */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  LangGraph Supervisor Decision Timeline
                </h3>

                <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
                  {selectedRun.trace && selectedRun.trace.length > 0 ? (
                    selectedRun.trace.map((step, idx) => (
                      <div key={idx} className="relative group">
                        <span className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full bg-teal-500 ring-4 ring-white dark:ring-slate-900" />
                        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs text-slate-800 dark:text-slate-200 font-mono">
                              {step.node || step.kind || `Step ${idx + 1}`}
                            </span>
                            {step.selected && (
                              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300">
                                Selected: {step.selected}
                              </span>
                            )}
                          </div>
                          {step.rationale && (
                            <p className="text-xs text-slate-600 dark:text-slate-400">{step.rationale}</p>
                          )}
                          {step.candidates && (
                            <p className="text-[11px] text-slate-500">
                              Candidates evaluated: {step.candidates.join(", ")}
                            </p>
                          )}
                          {step.tool && (
                            <p className="text-[11px] font-mono text-teal-700 dark:text-teal-400">
                              Tool: {step.tool}(household_id)
                            </p>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-slate-400">Trace data unavailable.</div>
                  )}
                </div>
              </div>

              {/* Findings */}
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Evidence-Led Findings ({selectedRun.findings?.length || 0})
                </h3>

                <div className="grid gap-3">
                  {(selectedRun.findings || []).map((f) => (
                    <div
                      key={f.id}
                      className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-slate-900 dark:text-white">
                          {f.subject}
                        </span>
                        <span
                          className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                            f.severity === "high" || f.severity === "critical"
                              ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
                              : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                          }`}
                        >
                          {f.severity}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                        {f.summary}
                      </p>
                      {f.evidence_ids && f.evidence_ids.length > 0 && (
                        <p className="text-[11px] font-mono text-slate-400 pt-1">
                          Evidence citations: {f.evidence_ids.join(", ")}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommendations */}
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Scored Recommendations ({selectedRun.recommendations?.length || 0})
                </h3>

                <div className="grid sm:grid-cols-2 gap-3">
                  {(selectedRun.recommendations || []).map((r, i) => (
                    <div
                      key={i}
                      className="p-4 rounded-xl bg-teal-50/50 dark:bg-teal-950/20 border border-teal-200 dark:border-teal-800/60 space-y-2 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-teal-900 dark:text-teal-200">
                            {r.subject}
                          </span>
                          <span className="font-mono text-xs font-bold text-teal-700 dark:text-teal-300">
                            Score {r.score?.toFixed(1)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-700 dark:text-slate-300 mt-1 font-medium">
                          {r.suggested_action}
                        </p>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                          {r.summary}
                        </p>
                      </div>
                      <span className="text-[10px] uppercase font-bold text-teal-700 dark:text-teal-400 tracking-wider">
                        Category: {r.category}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center text-xs text-slate-400">
              Select an investigation run to view the decision timeline and evidence traces.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
