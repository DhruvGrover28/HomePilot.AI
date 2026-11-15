import React, { useState, useEffect } from "react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import { apiJson, apiFetch } from "../api";

export default function EnergyView({ onDataChanged }) {
  const [readings, setReadings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form states
  const [readingForm, setReadingForm] = useState({
    reading_date: new Date().toISOString().split("T")[0],
    meter_value: "",
    consumption: "",
    period_days: "30",
    cost: "",
    notes: "",
  });

  const [importFile, setImportFile] = useState(null);

  async function loadReadings() {
    setLoading(true);
    try {
      const data = await apiJson("/api/readings?type=electricity");
      setReadings(data);
    } catch (err) {
      setError(err.message || "Failed to load energy readings.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReadings();
  }, []);

  async function handleAddReading(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiJson("/api/readings", {
        method: "POST",
        body: JSON.stringify({
          type: "electricity",
          reading_date: readingForm.reading_date,
          meter_value: readingForm.meter_value ? Number(readingForm.meter_value) : null,
          consumption: Number(readingForm.consumption),
          period_days: Number(readingForm.period_days) || 30,
          cost: readingForm.cost ? Number(readingForm.cost) : null,
          unit: "kWh",
          source: "manual",
          notes: readingForm.notes || null,
        }),
      });

      setShowAddModal(false);
      setReadingForm({
        reading_date: new Date().toISOString().split("T")[0],
        meter_value: "",
        consumption: "",
        period_days: "30",
        cost: "",
        notes: "",
      });
      await loadReadings();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to save reading.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleImportCSV(e) {
    e.preventDefault();
    if (!importFile) return;
    setSubmitting(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const res = await apiFetch("/api/readings/import", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail?.errors?.join(", ") || "Failed to import CSV.");
      }

      setShowImportModal(false);
      setImportFile(null);
      await loadReadings();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to import readings.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteReading(id) {
    if (!window.confirm("Are you sure you want to delete this reading?")) return;
    try {
      await apiFetch(`/api/readings/${id}`, { method: "DELETE" });
      await loadReadings();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to delete reading.");
    }
  }

  const chartData = readings.map((r) => ({
    date: r.reading_date,
    rate: Number((r.consumption / (r.period_days || 1)).toFixed(2)),
  }));

  const totalConsumption = readings.reduce((acc, r) => acc + (r.consumption || 0), 0);
  const avgDailyRate =
    readings.length > 0
      ? (
          readings.reduce((acc, r) => acc + r.consumption / (r.period_days || 1), 0) /
          readings.length
        ).toFixed(2)
      : "0.00";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">⚡</span>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Energy Specialist Domain</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Electricity consumption telemetry, daily burn rates, and automated anomaly detection.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => { setError(""); setShowImportModal(true); }}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition"
          >
            📂 Import CSV
          </button>
          <button
            onClick={() => { setError(""); setShowAddModal(true); }}
            className="px-3.5 py-2 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition"
          >
            + Add Meter Reading
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-red-950/50 border border-red-700/60 p-4 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Analytics stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <p className="text-xs text-slate-500">Average Daily Rate</p>
          <p className="text-2xl font-bold text-teal-600 dark:text-teal-400 mt-1">{avgDailyRate} <span className="text-xs font-normal text-slate-400">kWh/day</span></p>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <p className="text-xs text-slate-500">Total Tracked Usage</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{totalConsumption.toFixed(1)} <span className="text-xs font-normal text-slate-400">kWh</span></p>
        </div>
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <p className="text-xs text-slate-500">Telemetry Periods</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{readings.length} <span className="text-xs font-normal text-slate-400">billing periods</span></p>
        </div>
      </div>

      {/* Chart */}
      <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
        <h2 className="text-sm font-bold text-slate-900 dark:text-white">Electricity Rate History (kWh/day)</h2>
        <div className="h-60 pt-2">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="rate" stroke="#0d9488" strokeWidth={2.5} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              No historical electricity readings. Add one or seed demo data.
            </div>
          )}
        </div>
      </div>

      {/* Readings Table */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <h2 className="font-bold text-sm text-slate-900 dark:text-white">Logged Meter Readings</h2>
          <span className="text-xs text-slate-400">{readings.length} entries</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-950/70 border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Meter Value</th>
                <th className="py-3 px-4">Period (Days)</th>
                <th className="py-3 px-4">Total (kWh)</th>
                <th className="py-3 px-4">Daily Rate</th>
                <th className="py-3 px-4">Origin</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {readings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No electricity readings logged yet.
                  </td>
                </tr>
              ) : (
                readings.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-medium text-slate-900 dark:text-slate-100">{row.reading_date}</td>
                    <td className="py-3 px-4 font-mono text-slate-600 dark:text-slate-300">{row.meter_value ?? "—"}</td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-300">{row.period_days} days</td>
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">{row.consumption} kWh</td>
                    <td className="py-3 px-4 font-bold text-teal-600 dark:text-teal-400">
                      {(row.consumption / (row.period_days || 1)).toFixed(2)} kWh/d
                    </td>
                    <td className="py-3 px-4">
                      {row.is_simulated ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 font-medium">
                          Simulated
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300 font-medium">
                          Manual
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDeleteReading(row.id)}
                        className="text-red-500 hover:text-red-700 font-medium hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-white">Add Electricity Reading</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <form onSubmit={handleAddReading} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Reading Date</label>
                <input
                  type="date"
                  required
                  value={readingForm.reading_date}
                  onChange={(e) => setReadingForm({ ...readingForm, reading_date: e.target.value })}
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Consumption (kWh)</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={readingForm.consumption}
                    onChange={(e) => setReadingForm({ ...readingForm, consumption: e.target.value })}
                    placeholder="e.g. 450"
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Period (Days)</label>
                  <input
                    type="number"
                    required
                    value={readingForm.period_days}
                    onChange={(e) => setReadingForm({ ...readingForm, period_days: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Meter Value (Optional)</label>
                  <input
                    type="number"
                    step="any"
                    value={readingForm.meter_value}
                    onChange={(e) => setReadingForm({ ...readingForm, meter_value: e.target.value })}
                    placeholder="e.g. 12845.5"
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Cost (Optional)</label>
                  <input
                    type="number"
                    step="any"
                    value={readingForm.cost}
                    onChange={(e) => setReadingForm({ ...readingForm, cost: e.target.value })}
                    placeholder="$ amount"
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Notes</label>
                <input
                  type="text"
                  value={readingForm.notes}
                  onChange={(e) => setReadingForm({ ...readingForm, notes: e.target.value })}
                  placeholder="e.g. AC running continuously during heatwave"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 font-bold text-white shadow-sm"
                >
                  {submitting ? "Saving..." : "Save Reading"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CSV Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-white">Import Readings from CSV</h3>
              <button onClick={() => setShowImportModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400">
              Upload a CSV file containing columns: <code className="font-mono text-teal-600">type, reading_date, meter_value, consumption, period_days</code>.
            </p>

            <form onSubmit={handleImportCSV} className="space-y-4 text-xs">
              <input
                type="file"
                accept=".csv"
                required
                onChange={(e) => setImportFile(e.target.files[0])}
                className="w-full p-2 border border-dashed rounded-lg border-slate-300 dark:border-slate-700"
              />

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !importFile}
                  className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 font-bold text-white shadow-sm disabled:opacity-50"
                >
                  {submitting ? "Importing..." : "Upload & Parse CSV"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
