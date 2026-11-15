import React, { useState, useEffect } from "react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import { apiJson, apiFetch } from "../api";
import { Zap, FileText, Upload, FileSpreadsheet, Download, AlertTriangle, Info, X } from "lucide-react";

export default function EnergyView({ onDataChanged }) {
  const [readings, setReadings] = useState([]);
  const [bills, setBills] = useState([]);
  const [billAnalysis, setBillAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showBillModal, setShowBillModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Bill Digitization State
  const [billFile, setBillFile] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [extractedBill, setExtractedBill] = useState(null);
  const [confirmingBill, setConfirmingBill] = useState(false);
  const [billSuccessMsg, setBillSuccessMsg] = useState("");

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

  async function loadData() {
    setLoading(true);
    try {
      const [readingsData, billsData, analysisData] = await Promise.all([
        apiJson("/api/readings?type=electricity"),
        apiJson("/api/bills?utility_type=electricity").catch(() => []),
        apiJson("/api/bills/analysis?utility_type=electricity").catch(() => null),
      ]);
      setReadings(readingsData);
      setBills(billsData || []);
      setBillAnalysis(analysisData);
    } catch (err) {
      setError(err.message || "Failed to load energy data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function handleBillFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("Bill file size exceeds 10 MB limit.");
      return;
    }
    setBillFile(file);
    setError("");
  }

  async function handleExtractBill() {
    if (!billFile) return;
    setExtracting(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", billFile);
      formData.append("utility_type", "electricity");

      const res = await apiFetch("/api/bills/extract", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to extract electricity bill.");
      }
      const data = await res.json();
      setExtractedBill({
        ...data,
        sync_reading: true,
      });
    } catch (err) {
      setError(err.message || "Failed to process bill.");
    } finally {
      setExtracting(false);
    }
  }

  async function handleConfirmBill(e) {
    e.preventDefault();
    if (!extractedBill) return;
    setConfirmingBill(true);
    setError("");
    try {
      const payload = {
        utility_type: "electricity",
        provider_name: extractedBill.provider_name || null,
        account_number: extractedBill.account_number || null,
        bill_number: extractedBill.bill_number || null,
        bill_date: extractedBill.bill_date || null,
        due_date: extractedBill.due_date || null,
        period_start: extractedBill.period_start || null,
        period_end: extractedBill.period_end || null,
        period_days: Number(extractedBill.period_days) || 30,
        previous_reading: extractedBill.previous_reading !== null && extractedBill.previous_reading !== "" ? Number(extractedBill.previous_reading) : null,
        current_reading: extractedBill.current_reading !== null && extractedBill.current_reading !== "" ? Number(extractedBill.current_reading) : null,
        consumption: Number(extractedBill.consumption) || 0,
        consumption_unit: extractedBill.consumption_unit || "kWh",
        total_amount: extractedBill.total_amount !== null && extractedBill.total_amount !== "" ? Number(extractedBill.total_amount) : null,
        currency: extractedBill.currency || "USD",
        fixed_charges: extractedBill.fixed_charges !== null && extractedBill.fixed_charges !== "" ? Number(extractedBill.fixed_charges) : null,
        variable_charges: extractedBill.variable_charges !== null && extractedBill.variable_charges !== "" ? Number(extractedBill.variable_charges) : null,
        taxes: extractedBill.taxes !== null && extractedBill.taxes !== "" ? Number(extractedBill.taxes) : null,
        other_charges: extractedBill.other_charges !== null && extractedBill.other_charges !== "" ? Number(extractedBill.other_charges) : null,
        source_filename: extractedBill.source_filename || billFile?.name || "bill.pdf",
        sync_reading: Boolean(extractedBill.sync_reading),
      };

      await apiJson("/api/bills/confirm", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setShowBillModal(false);
      setBillFile(null);
      setExtractedBill(null);
      setBillSuccessMsg("Electricity bill digitized and confirmed successfully!");
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to confirm bill.");
    } finally {
      setConfirmingBill(false);
    }
  }

  async function handleDownloadBillCsv(billId, billNumber) {
    try {
      const res = await apiFetch(`/api/bills/${billId}/csv`);
      if (!res.ok) throw new Error("Failed to download bill CSV.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bill-electricity-${billNumber || billId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err.message || "Failed to download bill CSV.");
    }
  }

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
      await loadData();
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
      await loadData();
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
      await loadData();
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
          <div className="flex items-center gap-2.5">
            <Zap className="w-6 h-6 text-amber-500" />
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Energy Specialist Domain</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Electricity consumption telemetry, bill digitization, and automated anomaly detection.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => { setError(""); setShowBillModal(true); setExtractedBill(null); setBillFile(null); }}
            className="px-3.5 py-2 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Upload Bill</span>
          </button>
          <button
            onClick={() => { setError(""); setShowImportModal(true); }}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition flex items-center gap-1.5"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import CSV</span>
          </button>
          <button
            onClick={() => { setError(""); setShowAddModal(true); }}
            className="px-3.5 py-2 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition"
          >
            + Add Meter Reading
          </button>
        </div>
      </div>

      {billSuccessMsg && (
        <div className="rounded-xl bg-emerald-950/50 border border-emerald-700/60 p-4 text-xs text-emerald-300 flex items-center justify-between">
          <span>{billSuccessMsg}</span>
          <button onClick={() => setBillSuccessMsg("")} className="text-emerald-400 hover:text-emerald-200 font-bold ml-2 p-1" aria-label="Close message"><X className="w-4 h-4" /></button>
        </div>
      )}

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

      {/* Digitized Bills & Trend Analytics Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-amber-500" />
              <span>Digitized Electricity Bills & Trend Analytics</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Parsed utility statements, normalized billing cycles, and automated cost-per-kWh analytics.
            </p>
          </div>
          <button
            onClick={() => { setError(""); setShowBillModal(true); setExtractedBill(null); setBillFile(null); }}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-xs transition w-fit"
          >
            + Upload New Bill
          </button>
        </div>

        {billAnalysis && billAnalysis.warnings?.length > 0 && (
          <div className="p-3.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl text-xs text-amber-900 dark:text-amber-300 space-y-1">
            <p className="font-semibold uppercase tracking-wider text-[11px] text-amber-700 dark:text-amber-400">Analysis Note</p>
            {billAnalysis.warnings.map((w, idx) => (
              <p key={idx} className="flex items-center gap-1.5"><Info className="w-3.5 h-3.5 text-blue-500 shrink-0" /><span>{w}</span></p>
            ))}
          </div>
        )}

        {billAnalysis && billAnalysis.anomalies?.length > 0 && (
          <div className="p-3.5 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl text-xs text-red-900 dark:text-red-300 space-y-1">
            <p className="font-semibold uppercase tracking-wider text-[11px] text-red-700 dark:text-red-400">Consumption Anomaly Detected</p>
            {billAnalysis.anomalies.map((a, idx) => (
              <p key={idx} className="flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" /><span>Period {a.period} exceeded baseline daily consumption by +{a.spike_pct}% ({a.daily_rate} kWh/day vs avg {a.baseline_daily_rate} kWh/day).</span></p>
            ))}
          </div>
        )}

        {/* Bill Analysis KPI Cards */}
        {billAnalysis && billAnalysis.total_bills > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
              <p className="text-[11px] text-slate-500">Digitized Bills</p>
              <p className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">{billAnalysis.total_bills}</p>
            </div>
            <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
              <p className="text-[11px] text-slate-500">Period Trend</p>
              <p className="text-xl font-bold mt-0.5">
                {billAnalysis.consumption_trend_pct !== null ? (
                  <span className={billAnalysis.consumption_trend_pct > 0 ? "text-red-500" : "text-emerald-500"}>
                    {billAnalysis.consumption_trend_pct > 0 ? `+${billAnalysis.consumption_trend_pct}%` : `${billAnalysis.consumption_trend_pct}%`}
                  </span>
                ) : (
                  <span className="text-slate-400 text-sm">Need 2+ bills</span>
                )}
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
              <p className="text-[11px] text-slate-500">Total Billed Spend</p>
              <p className="text-xl font-bold text-slate-900 dark:text-white mt-0.5">
                ${billAnalysis.total_spend?.toFixed(2) || "0.00"}
              </p>
            </div>
            <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
              <p className="text-[11px] text-slate-500">Cost per kWh</p>
              <p className="text-xl font-bold text-indigo-600 dark:text-indigo-400 mt-0.5">
                {billAnalysis.cost_per_unit !== null ? `$${billAnalysis.cost_per_unit.toFixed(3)}` : "—"}
              </p>
            </div>
          </div>
        )}

        {/* Confirmed Bills Table */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-950 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <th className="py-2.5 px-4">Billing Period</th>
                  <th className="py-2.5 px-4">Provider</th>
                  <th className="py-2.5 px-4">Bill #</th>
                  <th className="py-2.5 px-4 text-right">Consumption</th>
                  <th className="py-2.5 px-4 text-right">Total Amount</th>
                  <th className="py-2.5 px-4 text-right">Standardized CSV</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {bills.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400">
                      No electricity bills digitized yet. Click "Upload Bill" to extract and analyze statements.
                    </td>
                  </tr>
                ) : (
                  bills.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="py-2.5 px-4 font-mono">
                        {b.period_start || "—"} to {b.period_end || "—"}
                        <span className="text-[10px] text-slate-400 block">({b.period_days} days)</span>
                      </td>
                      <td className="py-2.5 px-4 font-medium">{b.provider_name || "Unknown Provider"}</td>
                      <td className="py-2.5 px-4 font-mono text-slate-500">{b.bill_number || "—"}</td>
                      <td className="py-2.5 px-4 text-right font-mono font-semibold">
                        {b.consumption} {b.consumption_unit}
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                        {b.total_amount !== null ? `$${b.total_amount.toFixed(2)}` : "—"}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <button
                          onClick={() => handleDownloadBillCsv(b.id, b.bill_number)}
                          className="px-2.5 py-1 text-[11px] rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold transition inline-flex items-center gap-1.5"
                        >
                          <Download className="w-3 h-3 text-slate-500 dark:text-slate-400" />
                          <span>Download CSV</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-white">Add Electricity Reading</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600 p-1"><X className="w-4 h-4" /></button>
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
              <button onClick={() => setShowImportModal(false)} className="text-slate-400 hover:text-slate-600 p-1"><X className="w-4 h-4" /></button>
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

      {/* Upload & Digitize Electricity Bill Modal */}
      {showBillModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <FileText className="w-6 h-6 text-indigo-500" />
                <div>
                  <h3 className="font-bold text-base text-slate-900 dark:text-white">Digitize Electricity Bill</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Upload PDF statement or photo to automatically extract consumption, tariff, and charges.
                  </p>
                </div>
              </div>
              <button
                onClick={() => { setShowBillModal(false); setExtractedBill(null); setBillFile(null); }}
                className="text-slate-400 hover:text-slate-600 font-bold p-1"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Step 1: Select File & Extract */}
            {!extractedBill && (
              <div className="space-y-4 text-xs">
                <div className="border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center space-y-3">
                  {billFile ? (
                    <div className="space-y-2">
                      <FileText className="w-10 h-10 text-indigo-500 mx-auto" />
                      <p className="font-bold text-slate-900 dark:text-white">{billFile.name}</p>
                      <p className="text-[11px] text-slate-400 font-mono">{(billFile.size / 1024).toFixed(1)} KB</p>
                      <button
                        type="button"
                        onClick={() => setBillFile(null)}
                        className="text-xs text-red-500 hover:underline block mx-auto"
                      >
                        Choose a different file
                      </button>
                    </div>
                  ) : (
                    <div>
                      <FileSpreadsheet className="w-10 h-10 text-indigo-400 mx-auto mb-2" />
                      <p className="font-semibold text-slate-700 dark:text-slate-300">Select or drop your electricity bill</p>
                      <p className="text-[11px] text-slate-400 mt-1">Supports PDF, JPG, JPEG, PNG, WEBP (up to 10 MB)</p>
                      <label className="mt-3 inline-block px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold cursor-pointer transition shadow-xs">
                        Browse File
                        <input
                          type="file"
                          accept=".pdf,image/jpeg,image/png,image/webp"
                          className="hidden"
                          onChange={handleBillFileChange}
                        />
                      </label>
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowBillModal(false)}
                    className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={!billFile || extracting}
                    onClick={handleExtractBill}
                    className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-bold text-white shadow-sm disabled:opacity-50 transition"
                  >
                    {extracting ? "Extracting bill data with AI..." : "Extract & Digitize Bill →"}
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Review and Confirm Extracted Bill Data */}
            {extractedBill && (
              <form onSubmit={handleConfirmBill} className="space-y-4 text-xs">
                <div className="flex items-center justify-between p-3 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 rounded-xl">
                  <div>
                    <span className="font-bold text-indigo-900 dark:text-indigo-300">Extraction Complete</span>
                    <span className="text-[11px] text-indigo-700 dark:text-indigo-400 block">
                      Review and correct any extracted values before persisting to database.
                    </span>
                  </div>
                  {extractedBill.confidence_score && (
                    <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200">
                      {Math.round(extractedBill.confidence_score * 100)}% Confidence
                    </span>
                  )}
                </div>

                {extractedBill.warnings?.length > 0 && (
                  <div className="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl text-amber-900 dark:text-amber-300 space-y-1">
                    {extractedBill.warnings.map((w, idx) => (
                      <p key={idx} className="flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" /><span>{w}</span></p>
                    ))}
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Provider Name</label>
                    <input
                      type="text"
                      value={extractedBill.provider_name || ""}
                      onChange={(e) => setExtractedBill({ ...extractedBill, provider_name: e.target.value })}
                      placeholder="e.g. Pacific Electric"
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Account Number</label>
                    <input
                      type="text"
                      value={extractedBill.account_number || ""}
                      onChange={(e) => setExtractedBill({ ...extractedBill, account_number: e.target.value })}
                      placeholder="e.g. ACC-192840"
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Bill / Invoice Number</label>
                    <input
                      type="text"
                      value={extractedBill.bill_number || ""}
                      onChange={(e) => setExtractedBill({ ...extractedBill, bill_number: e.target.value })}
                      placeholder="e.g. INV-2026-9481"
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Bill Date</label>
                    <input
                      type="date"
                      value={extractedBill.bill_date || ""}
                      onChange={(e) => setExtractedBill({ ...extractedBill, bill_date: e.target.value })}
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Period Start</label>
                    <input
                      type="date"
                      value={extractedBill.period_start || ""}
                      onChange={(e) => setExtractedBill({ ...extractedBill, period_start: e.target.value })}
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Period End</label>
                    <input
                      type="date"
                      value={extractedBill.period_end || ""}
                      onChange={(e) => setExtractedBill({ ...extractedBill, period_end: e.target.value })}
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Period Days</label>
                    <input
                      type="number"
                      value={extractedBill.period_days || 30}
                      onChange={(e) => setExtractedBill({ ...extractedBill, period_days: Number(e.target.value) })}
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Consumption (kWh) *</label>
                    <input
                      type="number"
                      step="any"
                      required
                      value={extractedBill.consumption}
                      onChange={(e) => setExtractedBill({ ...extractedBill, consumption: Number(e.target.value) })}
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2 font-mono font-bold"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Total Bill Amount ($)</label>
                    <input
                      type="number"
                      step="any"
                      value={extractedBill.total_amount ?? ""}
                      onChange={(e) => setExtractedBill({ ...extractedBill, total_amount: e.target.value })}
                      placeholder="e.g. 85.50"
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2 font-mono font-bold text-emerald-600 dark:text-emerald-400"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Due Date</label>
                    <input
                      type="date"
                      value={extractedBill.due_date || ""}
                      onChange={(e) => setExtractedBill({ ...extractedBill, due_date: e.target.value })}
                      className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2"
                    />
                  </div>
                </div>

                <div className="pt-2">
                  <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={Boolean(extractedBill.sync_reading)}
                      onChange={(e) => setExtractedBill({ ...extractedBill, sync_reading: e.target.checked })}
                      className="rounded text-indigo-600"
                    />
                    <span>Automatically synchronize this bill's consumption to Energy Readings</span>
                  </label>
                </div>

                <div className="pt-2 flex items-center justify-between border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setExtractedBill(null)}
                    className="px-3.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                  >
                    ← Re-upload statement
                  </button>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShowBillModal(false)}
                      className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={confirmingBill}
                      className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-bold text-white shadow-sm disabled:opacity-50 transition"
                    >
                      {confirmingBill ? "Persisting Bill & CSV..." : "Confirm & Save Bill"}
                    </button>
                  </div>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
