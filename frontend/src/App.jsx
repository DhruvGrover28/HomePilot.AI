import { useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const anomalyRows = useMemo(() => {
    if (!result?.transactions) {
      return [];
    }
    return result.transactions.filter((txn) => txn.anomaly_type);
  }, [result]);

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      setError("Please select a CSV file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/expenses/upload`, {
        method: "POST",
        body: formData,
      });

      const json = await response.json();
      if (!response.ok) {
        throw new Error(json.detail || "Upload failed");
      }
      setResult(json);
    } catch (uploadError) {
      setError(uploadError.message || "Unexpected error during upload.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen p-6 md:p-10">
      <section className="mx-auto w-full max-w-6xl space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold text-slate-900">HomePilot AI</h1>
          <p className="text-sm text-slate-600">
            Upload a sample bank statement CSV to categorize transactions and surface expense anomalies.
          </p>
        </header>

        <form onSubmit={handleUpload} className="space-y-3 rounded-lg border border-slate-200 p-4">
          <label className="block text-sm font-medium text-slate-700" htmlFor="csv-upload">
            Bank statement CSV
          </label>
          <input
            id="csv-upload"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="block w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {loading ? "Analyzing..." : "Upload and Analyze"}
          </button>
        </form>

        {error && (
          <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}

        {result && (
          <>
            <section className="rounded-lg border border-slate-200 p-4">
              <h2 className="text-lg font-semibold text-slate-900">Summary</h2>
              <p className="mt-2 text-sm text-slate-700">Upload ID: {result.upload_id}</p>
              <p className="text-sm text-slate-700">Transactions: {result.transactions.length}</p>
              <p className="text-sm text-slate-700">Anomalies: {result.anomalies_count}</p>
            </section>

            <section className="overflow-hidden rounded-lg border border-slate-200">
              <h2 className="border-b border-slate-200 px-4 py-3 text-lg font-semibold text-slate-900">
                Categorized Transactions
              </h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50 text-left text-slate-700">
                    <tr>
                      <th className="px-4 py-2">Date</th>
                      <th className="px-4 py-2">Description</th>
                      <th className="px-4 py-2">Merchant</th>
                      <th className="px-4 py-2">Amount</th>
                      <th className="px-4 py-2">Category</th>
                      <th className="px-4 py-2">Anomaly</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {result.transactions.map((txn, index) => (
                      <tr key={`${txn.description}-${index}`}>
                        <td className="px-4 py-2">{txn.txn_date}</td>
                        <td className="px-4 py-2">{txn.description}</td>
                        <td className="px-4 py-2">{txn.merchant || "-"}</td>
                        <td className="px-4 py-2">{formatCurrency(txn.amount)}</td>
                        <td className="px-4 py-2">{txn.category}</td>
                        <td className="px-4 py-2">
                          {txn.anomaly_type ? (
                            <span className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-800">
                              {txn.anomaly_type}
                            </span>
                          ) : (
                            <span className="text-slate-400">None</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 p-4">
              <h2 className="text-lg font-semibold text-slate-900">Flagged Anomalies</h2>
              {anomalyRows.length === 0 ? (
                <p className="mt-2 text-sm text-slate-600">No anomalies detected.</p>
              ) : (
                <ul className="mt-3 space-y-2 text-sm text-slate-700">
                  {anomalyRows.map((txn, idx) => (
                    <li key={`${txn.description}-${idx}`} className="rounded bg-amber-50 p-2">
                      <strong>{txn.anomaly_type}</strong>: {txn.description} ({formatCurrency(txn.amount)})
                      <div>{txn.anomaly_reason}</div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </section>
    </main>
  );
}
