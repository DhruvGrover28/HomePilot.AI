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

  async function seedDemo() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/demo/seed`, { method: "POST" });
      if (!response.ok) throw new Error("Unable to seed demo data.");
      await loadSummary();
    } catch (seedError) {
      setError(seedError.message);
    }
  }

  useEffect(() => { loadSummary(); }, []);

  if (loading) return <main className="p-8">Loading HomePilot...</main>;
  return (
    <main className="mx-auto min-h-screen max-w-7xl space-y-6 p-6 md:p-10">
      <header className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-teal-700">Household operations</p>
          <h1 className="mt-1 text-3xl font-semibold">HomePilot AI</h1>
          <p className="mt-2 text-slate-600">Monitor consumption, maintenance and supplies from one place.</p>
        </div>
        <button onClick={seedDemo} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white">Seed simulated demo</button>
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
            <h2 className="text-lg font-semibold">Household records</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {summary.appliances.map((appliance) => (
                <div key={appliance.id} className="rounded-lg border border-slate-100 p-3">
                  <strong>{appliance.name}</strong>{appliance.is_simulated && <SimulatedBadge />}<p className="mt-1 text-sm text-slate-500">{appliance.category}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
