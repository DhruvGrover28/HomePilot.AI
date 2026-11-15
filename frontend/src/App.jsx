import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function SimulatedBadge() {
  return <span className="ml-2 rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-800">simulated</span>;
}

function ConsumptionChart({ title, rows, color }) {
  const data = rows.map((row) => ({ date: row.reading_date, rate: row.consumption / row.period_days }));
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="rate" stroke={color} strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default function App() {
  const [summary, setSummary] = useState(null);
  const [agentRun, setAgentRun] = useState(null);
  const [monitoringIssues, setMonitoringIssues] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadSummary() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/summary`);
      if (!response.ok) throw new Error("Unable to load household data.");
      setSummary(await response.json());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadMonitoring() {
    const response = await fetch(`${API_BASE_URL}/api/monitoring/issues`);
    if (!response.ok) throw new Error("Unable to load monitoring activity.");
    setMonitoringIssues(await response.json());
  }

  async function seedDemo() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/demo/seed`, { method: "POST" });
      if (!response.ok) throw new Error("Unable to seed demo data.");
      await loadSummary();
      await loadMonitoring();
    } catch (seedError) {
      setError(seedError.message);
    }

  }

  async function runMonitoring() {
    try {
      setError("");
      const response = await fetch(`${API_BASE_URL}/api/monitoring/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!response.ok) throw new Error("Unable to run monitoring.");
      setMonitoringIssues(await response.json());
    } catch (monitoringError) {
      setError(monitoringError.message);
    }
  }

  async function runAnalysis() {
    try {
      setError("");
      const response = await fetch(`${API_BASE_URL}/api/agents/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: "Review energy, water, maintenance and inventory priorities." }),
      });
      if (!response.ok) throw new Error("Unable to run household analysis.");
      setAgentRun(await response.json());
    } catch (runError) {
      setError(runError.message);
    }
  }

  useEffect(() => {
    Promise.all([loadSummary(), loadMonitoring()]).catch((loadError) => setError(loadError.message));
  }, []);

  if (loading) return <main className="p-8">Loading HomePilot...</main>;
  return (
    <main className="mx-auto min-h-screen max-w-7xl space-y-6 p-6 md:p-10">
      <header className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-teal-700">Household operations</p>
          <h1 className="mt-1 text-3xl font-semibold">HomePilot AI</h1>
          <p className="mt-2 text-slate-600">Monitor consumption, maintenance and supplies from one place.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={runMonitoring} className="rounded-lg border border-teal-700 px-4 py-2 text-sm font-medium text-teal-800">Check monitoring</button>
          <button onClick={runAnalysis} className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white">Run household analysis</button>
          <button onClick={seedDemo} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">Seed simulated demo</button>
        </div>
      </header>
      {error && <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-700">{error}</div>}
      {summary && (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl bg-teal-700 p-5 text-white"><p className="text-sm opacity-80">Electricity periods</p><p className="mt-2 text-3xl font-semibold">{summary.electricity.length}</p></div>
            <div className="rounded-xl bg-blue-700 p-5 text-white"><p className="text-sm opacity-80">Water periods</p><p className="mt-2 text-3xl font-semibold">{summary.water.length}</p></div>
            <div className="rounded-xl bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Open tasks</p><p className="mt-2 text-3xl font-semibold">{summary.tasks_open}</p></div>
            <div className="rounded-xl bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Appliances</p><p className="mt-2 text-3xl font-semibold">{summary.appliances.length}</p></div>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <ConsumptionChart title="Electricity daily rate (kWh)" rows={summary.electricity} color="#0f766e" />
            <ConsumptionChart title="Water daily rate (litres)" rows={summary.water} color="#1d4ed8" />
          </div>
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-lg font-semibold">Monitoring activity</h2>
              <span className="text-xs text-slate-500">{monitoringIssues.length} detected records</span>
            </div>
            {monitoringIssues.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No monitoring issues detected.</p>
            ) : (
              <div className="mt-4 space-y-3">
                {monitoringIssues.map((issue) => (
                  <article key={issue.id} className="rounded-lg border border-slate-100 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="font-semibold">{issue.title}</h3>
                      <div className="flex gap-2 text-xs uppercase tracking-wide">
                        <span className={issue.issue_status === "open" ? "text-amber-700" : "text-green-700"}>{issue.issue_status}</span>
                        <span className="text-slate-500">{issue.investigation_status}</span>
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {issue.domain}{issue.entity_id ? ` #${issue.entity_id}` : ""} · First: {issue.first_trigger_source} · Latest: {issue.last_trigger_source} · Occurrences: {issue.occurrence_count}
                    </p>
                    {issue.latest_evidence_id && (
                      <p className="mt-1 text-xs text-slate-500">Latest evidence reading: {issue.latest_evidence_id}</p>
                    )}
                    {issue.latest_run?.findings?.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {issue.latest_run.findings.map((finding) => (
                          <p key={finding.id} className="text-sm text-slate-600">{finding.summary}</p>
                        ))}
                      </div>
                    )}
                    {issue.latest_run?.recommendations?.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {issue.latest_run.recommendations.map((recommendation) => (
                          <p key={`${recommendation.category}-${recommendation.subject}`} className="text-sm text-teal-800">
                            Recommendation: {recommendation.suggested_action}
                          </p>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Household records</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {summary.appliances.map((appliance) => (
                <div key={appliance.id} className="rounded-lg border border-slate-100 p-3">
                  <strong>{appliance.name}</strong>{appliance.is_simulated && <SimulatedBadge />}<p className="mt-1 text-sm text-slate-500">{appliance.category}</p>
                </div>
              ))}
            </div>
          </section>
          {agentRun && (
            <section className="rounded-xl border border-teal-200 bg-teal-50 p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-lg font-semibold">Household analysis</h2>
                <span className="text-xs uppercase tracking-wide text-teal-800">{agentRun.mode} mode</span>
              </div>
              <p className="mt-1 text-sm text-slate-600">{agentRun.goal}</p>
              <div className="mt-4 space-y-2">
                {agentRun.findings.map((finding) => (
                  <article key={finding.id} className="rounded-lg bg-white p-3 shadow-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="font-semibold">{finding.subject}</h3>
                      <span className="text-xs uppercase tracking-wide text-slate-500">{finding.severity}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{finding.summary}</p>
                  </article>
                ))}
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                {agentRun.recommendations.map((recommendation) => (
                  <article key={`${recommendation.category}-${recommendation.subject}`} className="rounded-lg bg-white p-4 shadow-sm">
                    <h3 className="font-semibold">{recommendation.subject}</h3>
                    <p className="mt-1 text-sm text-slate-600">{recommendation.summary}</p>
                    <p className="mt-3 text-sm text-slate-800">{recommendation.suggested_action}</p>
                    <p className="mt-2 text-xs text-slate-500">Score: {recommendation.score.toFixed(1)}</p>
                  </article>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-500">
                Trace: {agentRun.trace.map((step) => step.node || step.kind).join(" -> ")}
              </p>
            </section>
          )}
        </>
      )}
    </main>
  );
}
