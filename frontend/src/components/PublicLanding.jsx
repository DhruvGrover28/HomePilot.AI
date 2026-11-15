import React, { useState } from "react";
import { apiJson } from "../api";

export default function PublicLanding({ onAuthenticated }) {
  const [authMode, setAuthMode] = useState(""); // "" | "login" | "register"
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (authMode === "register") {
      if (form.password.length < 8) {
        setError("Password must be at least 8 characters.");
        return;
      }
      if (form.password !== form.confirm_password) {
        setError("Passwords do not match.");
        return;
      }
    }

    setWorking(true);
    try {
      const endpoint = authMode === "register" ? "/api/auth/register" : "/api/auth/login";
      const payload =
        authMode === "register"
          ? {
              full_name: form.full_name,
              email: form.email,
              password: form.password,
              confirm_password: form.confirm_password,
            }
          : {
              email: form.email,
              password: form.password,
            };

      const result = await apiJson(endpoint, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      await onAuthenticated(result.user);
    } catch (err) {
      setError(err.message || "Authentication failed. Please verify credentials.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-white">
      {/* Top Navbar */}
      <nav className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-teal-500/20 border border-teal-400/40 flex items-center justify-center text-teal-300 font-bold text-lg">
              HP
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              HomePilot <span className="text-teal-400 font-normal">AI</span>
            </span>
          </div>

          <div className="hidden md:flex items-center gap-8 text-sm text-slate-300 font-medium">
            <a href="#architecture" className="hover:text-teal-300 transition">Agentic Architecture</a>
            <a href="#domains" className="hover:text-teal-300 transition">4 Specialist Domains</a>
            <a href="#features" className="hover:text-teal-300 transition">Features</a>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => { setError(""); setAuthMode("login"); }}
              className="px-4 py-2 text-sm font-medium text-slate-200 hover:text-white rounded-lg hover:bg-slate-800 transition"
            >
              Sign In
            </button>
            <button
              onClick={() => { setError(""); setAuthMode("register"); }}
              className="px-4 py-2 text-sm font-semibold bg-teal-500 text-slate-950 hover:bg-teal-400 rounded-lg shadow-sm shadow-teal-500/20 transition"
            >
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-24 px-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(20,184,166,0.12),transparent_50%)] pointer-events-none" />
        <div className="mx-auto max-w-7xl grid gap-12 lg:grid-cols-12 lg:items-center">
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-950/80 border border-teal-700/60 text-teal-300 text-xs font-semibold uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
              Autonomous Household Operations System
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
              Evidence-Led Intelligence for Modern Households.
            </h1>
            <p className="text-lg text-slate-300 max-w-2xl leading-relaxed">
              HomePilot AI coordinates specialist AI agents using real household data and deterministic tools. It detects anomalies, investigates cross-domain issues, and delivers transparent, actionable recommendations.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <button
                onClick={() => { setError(""); setAuthMode("register"); }}
                className="px-6 py-3.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-base shadow-lg shadow-teal-500/25 transition"
              >
                Launch Your Household
              </button>
              <a
                href="#architecture"
                className="px-6 py-3.5 rounded-xl border border-slate-700 bg-slate-900/60 hover:bg-slate-800 text-slate-200 font-semibold text-base transition"
              >
                See How It Works
              </a>
            </div>

            <div className="pt-6 grid grid-cols-3 gap-6 border-t border-slate-800/80 max-w-lg">
              <div>
                <p className="text-2xl font-bold text-teal-400">100%</p>
                <p className="text-xs text-slate-400 font-medium">Household Isolated</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-teal-400">4</p>
                <p className="text-xs text-slate-400 font-medium">Specialist Domains</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-teal-400">Bounded</p>
                <p className="text-xs text-slate-400 font-medium">Execution Budgets</p>
              </div>
            </div>
          </div>

          {/* Interactive Agentic Architecture Preview Card */}
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl p-6 backdrop-blur space-y-5">
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-teal-400" />
                  <span className="text-sm font-semibold text-slate-200">LangGraph Supervisor</span>
                </div>
                <span className="text-xs px-2.5 py-1 rounded bg-teal-500/10 text-teal-300 font-mono border border-teal-500/20">
                  Dynamic Coordination
                </span>
              </div>

              {/* Dynamic Dispatch visualization */}
              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
                  <span className="text-teal-400 font-semibold">1. Trigger:</span> Water consumption spiked by 48% vs baseline
                </div>
                <div className="flex justify-center">
                  <span className="text-slate-500">↓ Supervisor selects domain</span>
                </div>
                <div className="p-3 rounded-lg bg-blue-950/40 border border-blue-800/50 text-blue-200">
                  <span className="text-blue-400 font-semibold">2. Water Specialist:</span> Confirms continuous flow rate signature
                </div>
                <div className="flex justify-center">
                  <span className="text-slate-500">↓ Dynamic follow-up handoff</span>
                </div>
                <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-200">
                  <span className="text-amber-400 font-semibold">3. Maintenance Specialist:</span> Correlates with Dishwasher age & check-valve wear
                </div>
                <div className="flex justify-center">
                  <span className="text-slate-500">↓ Supervisor finalizes plan</span>
                </div>
                <div className="p-3 rounded-lg bg-teal-950/50 border border-teal-700/60 text-teal-200">
                  <span className="text-teal-300 font-semibold">4. Actionable Finding:</span> Inspect inlet valve before replacing entire unit
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Specialist Domains Section */}
      <section id="domains" className="py-20 px-6 bg-slate-900/50 border-t border-b border-slate-800/80">
        <div className="mx-auto max-w-7xl space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <h2 className="text-xs font-semibold text-teal-400 uppercase tracking-widest">Core Capabilities</h2>
            <p className="text-3xl font-bold text-white tracking-tight">Four Dedicated Specialist Domains</p>
            <p className="text-sm text-slate-400">
              Each specialist operates with isolated deterministic Python tools and real database telemetry.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 hover:border-teal-500/40 transition space-y-3">
              <div className="text-3xl">⚡</div>
              <h3 className="font-bold text-lg text-white">Energy Specialist</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Monitors daily electricity consumption rates (kWh/day), identifies anomalies vs 30-day baseline, and spots unseasonal spikes.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 hover:border-blue-500/40 transition space-y-3">
              <div className="text-3xl">💧</div>
              <h3 className="font-bold text-lg text-white">Water Specialist</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Tracks daily water consumption (litres/day), runs leak signature heuristics, and flags sustained high usage.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 hover:border-amber-500/40 transition space-y-3">
              <div className="text-3xl">🔧</div>
              <h3 className="font-bold text-lg text-white">Maintenance Specialist</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Tracks household appliances, warranties, operating age, and scheduled maintenance tasks to prevent breakdowns.
              </p>
            </div>

            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 hover:border-emerald-500/40 transition space-y-3">
              <div className="text-3xl">📦</div>
              <h3 className="font-bold text-lg text-white">Inventory Specialist</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Tracks critical consumables (filters, salt, bulbs), detects low stock below safety thresholds, and auto-generates shopping items.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture Highlights */}
      <section id="architecture" className="py-20 px-6">
        <div className="mx-auto max-w-7xl grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <span className="text-xs font-semibold text-teal-400 uppercase tracking-widest">Built For Rigor</span>
            <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
              True Agentic Behavior, Not Just a Chatbot.
            </h2>
            <div className="space-y-4 text-sm text-slate-300">
              <div className="flex items-start gap-3">
                <span className="p-1 rounded bg-teal-500/20 text-teal-400 font-bold">✓</span>
                <p><strong className="text-white">Dynamic LangGraph Coordination:</strong> The supervisor chooses specialists based on evidence and objective, with full multi-turn follow-up.</p>
              </div>
              <div className="flex items-start gap-3">
                <span className="p-1 rounded bg-teal-500/20 text-teal-400 font-bold">✓</span>
                <p><strong className="text-white">Strict Household Isolation:</strong> Database queries, agent tools, and monitoring run strictly within authenticated household boundaries.</p>
              </div>
              <div className="flex items-start gap-3">
                <span className="p-1 rounded bg-teal-500/20 text-teal-400 font-bold">✓</span>
                <p><strong className="text-white">Provider Failover:</strong> Staggered provider racing ensures system resilience across Gemini, OpenRouter, and Ollama.</p>
              </div>
              <div className="flex items-start gap-3">
                <span className="p-1 rounded bg-teal-500/20 text-teal-400 font-bold">✓</span>
                <p><strong className="text-white">Deterministic Verification:</strong> LLMs do not invent math; deterministic Python tools compute statistical consumption and bounds.</p>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-4">
            <h3 className="font-bold text-white text-base">Key Architecture Attributes</h3>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <p className="font-semibold text-teal-300">Background Engine</p>
                <p className="mt-1 text-slate-400">APScheduler checks energy, water, maintenance and inventory continuously.</p>
              </div>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <p className="font-semibold text-teal-300">Explainable Traces</p>
                <p className="mt-1 text-slate-400">Every decision, tool query, and candidate evaluation is fully recorded.</p>
              </div>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <p className="font-semibold text-teal-300">Bounded Budgets</p>
                <p className="mt-1 text-slate-400">Prevents runaway agent loops with strict iteration and specialist budgets.</p>
              </div>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                <p className="font-semibold text-teal-300">Hybrid Persistence</p>
                <p className="mt-1 text-slate-400">Seamless support for local SQLite and production PostgreSQL.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-800 py-8 px-6 text-center text-xs text-slate-500">
        <p>HomePilot AI — Agentic AI Household Operations System.</p>
        <p className="mt-1">IBM SkillsBuild Agentic AI Internship Capstone Project.</p>
      </footer>

      {/* Auth Modal (Login / Register) */}
      {authMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-8 shadow-2xl text-slate-100">
            <button
              onClick={() => { setAuthMode(""); setError(""); }}
              className="absolute top-5 right-5 text-slate-400 hover:text-white"
            >
              ✕
            </button>

            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white">
                {authMode === "login" ? "Sign In to HomePilot" : "Create Your Household Account"}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {authMode === "login"
                  ? "Access your isolated household operations dashboard."
                  : "Begin your setup with isolated household data."}
              </p>
            </div>

            {error && (
              <div className="mb-4 rounded-lg bg-red-950/50 border border-red-700/60 p-3 text-xs text-red-300">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {authMode === "register" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                    placeholder="e.g. Alex Morgan"
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="alex@example.com"
                  className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                />
              </div>

              {authMode === "register" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Confirm Password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={form.confirm_password}
                    onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}
                    placeholder="••••••••"
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={working}
                className="w-full mt-2 py-3 px-4 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-bold text-sm shadow-md transition"
              >
                {working
                  ? "Please wait..."
                  : authMode === "login"
                  ? "Sign In"
                  : "Create Household Account"}
              </button>
            </form>

            <div className="mt-5 text-center text-xs text-slate-400">
              {authMode === "login" ? (
                <span>
                  Don't have an account?{" "}
                  <button
                    onClick={() => { setError(""); setAuthMode("register"); }}
                    className="text-teal-400 font-semibold hover:underline"
                  >
                    Register here
                  </button>
                </span>
              ) : (
                <span>
                  Already have an account?{" "}
                  <button
                    onClick={() => { setError(""); setAuthMode("login"); }}
                    className="text-teal-400 font-semibold hover:underline"
                  >
                    Sign in
                  </button>
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
