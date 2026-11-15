import React, { useState } from "react";
import { apiJson } from "../api";
import BrandLogo from "./BrandLogo";
import {
  Zap,
  Droplets,
  Wrench,
  Package,
  Camera,
  FileSpreadsheet,
  Activity,
  Shield,
  Cpu,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  X,
  Sparkles,
  BarChart3,
  Layers,
  Clock,
  Lock,
  Compass
} from "lucide-react";

export default function PublicLanding({ onAuthenticated }) {
  const [authMode, setAuthMode] = useState(""); // "" | "login" | "register"
  const [showArchDeepDive, setShowArchDeepDive] = useState(false);
  const [activePreviewTab, setActivePreviewTab] = useState("vision");
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-white relative overflow-x-hidden">
      {/* Background Ambient Glow Elements */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none animate-pulse-glow" />
      <div className="absolute top-1/3 right-10 w-[30rem] h-[30rem] bg-cyan-600/10 rounded-full blur-3xl pointer-events-none animate-pulse-glow" />
      <div className="absolute bottom-1/4 left-10 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Navbar */}
      <nav className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <BrandLogo subtitle="Household Autopilot" size="lg" />

          <div className="hidden md:flex items-center gap-8 text-sm text-slate-300 font-medium">
            <a href="#features" className="hover:text-teal-300 transition-colors">Features</a>
            <a href="#preview" className="hover:text-teal-300 transition-colors">Live Showcase</a>
            <a href="#domains" className="hover:text-teal-300 transition-colors">Specialist Domains</a>
            <button
              onClick={() => {
                setShowArchDeepDive(true);
                const el = document.getElementById("architecture");
                if (el) el.scrollIntoView({ behavior: "smooth" });
              }}
              className="text-slate-400 hover:text-teal-300 transition-colors flex items-center gap-1"
            >
              <span>Architecture</span>
              <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">Deep Dive</span>
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => { setError(""); setAuthMode("login"); }}
              className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white rounded-lg hover:bg-slate-900 border border-transparent hover:border-slate-800 transition"
            >
              Sign In
            </button>
            <button
              onClick={() => { setError(""); setAuthMode("register"); }}
              className="px-5 py-2 text-sm font-semibold bg-gradient-to-r from-teal-400 to-teal-500 text-slate-950 hover:from-teal-300 hover:to-teal-400 rounded-lg shadow-md shadow-teal-500/20 transition transform active:scale-95"
            >
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-20 pb-20 px-6">
        <div className="mx-auto max-w-7xl grid gap-12 lg:grid-cols-12 lg:items-center">
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-slate-900/90 border border-teal-500/30 text-teal-300 text-xs font-semibold shadow-inner">
              <Sparkles className="w-3.5 h-3.5 text-teal-400 animate-pulse" />
              <span>Next-Gen Autonomous Household Intelligence</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.12]">
              Effortless Home Operations. <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-300 via-cyan-300 to-blue-400">
                Powered by Multi-Agent AI.
              </span>
            </h1>

            <p className="text-lg text-slate-300 max-w-2xl leading-relaxed">
              Stop guessing utility spikes, manual pantry counts, and forgotten appliance maintenance. HomePilot AI watches over your home with computer vision, bill digitization, and autonomous specialist agents.
            </p>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={() => { setError(""); setAuthMode("register"); }}
                className="px-7 py-3.5 rounded-xl bg-gradient-to-r from-teal-400 to-cyan-500 hover:from-teal-300 hover:to-cyan-400 text-slate-950 font-bold text-base shadow-xl shadow-teal-500/25 transition transform hover:-translate-y-0.5 active:translate-y-0 flex items-center gap-2"
              >
                <span>Launch Your Household</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <a
                href="#preview"
                className="px-6 py-3.5 rounded-xl border border-slate-700/80 bg-slate-900/60 hover:bg-slate-800 text-slate-200 font-semibold text-base transition flex items-center gap-2"
              >
                <Activity className="w-4 h-4 text-teal-400" />
                <span>Explore Features</span>
              </a>
            </div>

            {/* Quick Metrics Bar */}
            <div className="pt-6 grid grid-cols-3 gap-6 border-t border-slate-800/80 max-w-lg">
              <div>
                <p className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-cyan-300">
                  100%
                </p>
                <p className="text-xs text-slate-400 font-medium mt-0.5">Private Household Isolation</p>
              </div>
              <div>
                <p className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-cyan-300">
                  4 AI Agents
                </p>
                <p className="text-xs text-slate-400 font-medium mt-0.5">Energy, Water, Care, Pantry</p>
              </div>
              <div>
                <p className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-cyan-300">
                  Real-Time
                </p>
                <p className="text-xs text-slate-400 font-medium mt-0.5">Telemetry & Anomaly Alerts</p>
              </div>
            </div>
          </div>

          {/* Flashy Hero Interactive Card */}
          <div className="lg:col-span-5">
            <div className="relative rounded-2xl border border-slate-800/80 bg-gradient-to-b from-slate-900/95 to-slate-950/95 shadow-2xl p-6 backdrop-blur-xl space-y-5 animate-float">
              {/* Card Header */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                  <div>
                    <h2 className="text-sm font-semibold text-slate-100">Live Household Sentinel</h2>
                    <p className="text-[11px] text-slate-400">Autonomous Home Telemetry Active</p>
                  </div>
                </div>
                <span className="text-[11px] px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-300 font-medium border border-teal-500/20 flex items-center gap-1.5">
                  <Shield className="w-3 h-3 text-teal-400" />
                  Protected
                </span>
              </div>

              {/* Dynamic Live Cards Simulation */}
              <div className="space-y-3">
                <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
                      <Zap className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-200">Electricity Baseline</p>
                      <p className="text-[11px] text-slate-400">14.2 kWh/day • Normal Pace</p>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-emerald-400">-6% this week</span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                      <Droplets className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-slate-200">Water Flow Guard</p>
                      <p className="text-[11px] text-slate-400">Zero continuous leak signatures</p>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-teal-400">Healthy</span>
                </div>

                <div className="p-3.5 rounded-xl bg-gradient-to-r from-teal-950/40 to-slate-950 border border-teal-600/30">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-semibold text-teal-300 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-teal-400" />
                      Autonomous Specialist Action
                    </span>
                    <span className="text-[10px] text-slate-400">2 min ago</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-snug">
                    Water Specialist correlated dishwasher intake with recent cycle telemetry. Recommendation: Clean inlet screen to prevent valve strain.
                  </p>
                </div>
              </div>

              {/* Call to Action Inside Card */}
              <button
                onClick={() => { setError(""); setAuthMode("register"); }}
                className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700/80 text-teal-300 border border-slate-700 text-xs font-semibold flex items-center justify-center gap-2 transition"
              >
                <span>Experience Real-Time Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Feature Showcase Section */}
      <section id="preview" className="py-20 px-6 bg-slate-900/40 border-t border-b border-slate-800/80">
        <div className="mx-auto max-w-7xl space-y-12">
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <span className="text-xs font-semibold text-teal-400 uppercase tracking-widest">
              Live Capabilities
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Powerful Home Operations Made Intuitive
            </h2>
            <p className="text-sm text-slate-400">
              Explore how HomePilot AI automates the tedious parts of managing your household.
            </p>
          </div>

          {/* Interactive Feature Tabs */}
          <div className="flex flex-wrap justify-center gap-2 max-w-2xl mx-auto">
            <button
              onClick={() => setActivePreviewTab("vision")}
              className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition flex items-center gap-2 border ${
                activePreviewTab === "vision"
                  ? "bg-teal-500/20 border-teal-500/60 text-teal-300 shadow-md shadow-teal-500/10"
                  : "bg-slate-900/80 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              <Camera className="w-4 h-4" />
              <span>Vision Inventory</span>
            </button>

            <button
              onClick={() => setActivePreviewTab("bills")}
              className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition flex items-center gap-2 border ${
                activePreviewTab === "bills"
                  ? "bg-teal-500/20 border-teal-500/60 text-teal-300 shadow-md shadow-teal-500/10"
                  : "bg-slate-900/80 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Bill Digitization</span>
            </button>

            <button
              onClick={() => setActivePreviewTab("telemetry")}
              className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition flex items-center gap-2 border ${
                activePreviewTab === "telemetry"
                  ? "bg-teal-500/20 border-teal-500/60 text-teal-300 shadow-md shadow-teal-500/10"
                  : "bg-slate-900/80 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Leak & Anomaly Defense</span>
            </button>

            <button
              onClick={() => setActivePreviewTab("agents")}
              className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition flex items-center gap-2 border ${
                activePreviewTab === "agents"
                  ? "bg-teal-500/20 border-teal-500/60 text-teal-300 shadow-md shadow-teal-500/10"
                  : "bg-slate-900/80 border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              <Cpu className="w-4 h-4" />
              <span>Multi-Agent Supervisor</span>
            </button>
          </div>

          {/* Interactive Showcase Display */}
          <div className="max-w-4xl mx-auto rounded-2xl border border-slate-800 bg-slate-900/80 p-6 md:p-8 shadow-2xl backdrop-blur">
            {activePreviewTab === "vision" && (
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div className="space-y-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold border border-emerald-500/20">
                    <Camera className="w-3.5 h-3.5" />
                    <span>Computer Vision OCR & Multimodal Detection</span>
                  </div>
                  <h3 className="text-2xl font-bold text-white">Snap a Photo of Pantry or Fridge</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    No more manual grocery entry. Our multimodal AI scans your shelves, estimates item quantities, pre-matches against your catalog, and updates your shopping list with a single click.
                  </p>
                  <ul className="space-y-2 text-xs text-slate-300">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Automatic matching against existing stock</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Add to stock, replace count, or create new item</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Permanent visual scan audit logs</span>
                    </li>
                  </ul>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono text-xs">
                  <div className="text-[11px] text-slate-400 pb-2 border-b border-slate-800 flex justify-between">
                    <span>Vision Scan Result</span>
                    <span className="text-emerald-400">3 Items Detected</span>
                  </div>
                  <div className="flex justify-between items-center bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <div>
                      <p className="text-slate-200 font-semibold">Oat Milk</p>
                      <p className="text-[10px] text-slate-400">2 cartons (Matched)</p>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">Action: Add (+2)</span>
                  </div>
                  <div className="flex justify-between items-center bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <div>
                      <p className="text-slate-200 font-semibold">Greek Yogurt</p>
                      <p className="text-[10px] text-slate-400">1 tub (Low Stock Alert)</p>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">Action: Replace</span>
                  </div>
                  <div className="flex justify-between items-center bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                    <div>
                      <p className="text-slate-200 font-semibold">Ground Coffee</p>
                      <p className="text-[10px] text-slate-400">340 g (New Brand)</p>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-teal-500/20 text-teal-300">Action: New</span>
                  </div>
                </div>
              </div>
            )}

            {activePreviewTab === "bills" && (
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div className="space-y-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-semibold border border-cyan-500/20">
                    <FileSpreadsheet className="w-3.5 h-3.5" />
                    <span>PDF & Image Bill Extraction</span>
                  </div>
                  <h3 className="text-2xl font-bold text-white">Turn Any Bill Into Actionable Analytics</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    Upload electricity or water bills in PDF or image format. We extract key metrics, charges, and readings, convert them into durable CSV records, and spot unseasonal cost spikes.
                  </p>
                  <ul className="space-y-2 text-xs text-slate-300">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Automatic PDF and multimodal image parsing</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>One-click RFC 4180 CSV export and PostgreSQL persistence</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Synchronizes telemetry readings to update trends</span>
                    </li>
                  </ul>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono text-xs">
                  <div className="text-[11px] text-slate-400 pb-2 border-b border-slate-800 flex justify-between">
                    <span>Extracted Bill Preview</span>
                    <span className="text-teal-400">Verified</span>
                  </div>
                  <div className="space-y-2 text-[11px]">
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Billing Period:</span>
                      <span className="text-slate-200">Oct 01 - Oct 31 (31 days)</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Total Consumption:</span>
                      <span className="text-slate-200">412.00 kWh</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Total Amount:</span>
                      <span className="text-teal-300 font-bold">$78.28</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-900">
                      <span className="text-slate-400">Cost per kWh:</span>
                      <span className="text-slate-200">$0.190 / kWh</span>
                    </div>
                  </div>
                  <div className="pt-2 flex gap-2">
                    <span className="w-full text-center py-1.5 rounded bg-teal-500/10 border border-teal-500/20 text-teal-300 text-[10px]">
                      Durable CSV Generated & Saved
                    </span>
                  </div>
                </div>
              </div>
            )}

            {activePreviewTab === "telemetry" && (
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div className="space-y-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 text-xs font-semibold border border-amber-500/20">
                    <Activity className="w-3.5 h-3.5" />
                    <span>24/7 Continuous Surveillance</span>
                  </div>
                  <h3 className="text-2xl font-bold text-white">Catch Hidden Leaks Before Disasters</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    Background monitors continuously test consumption rates against historical 30-day baselines. When a toilet flapper leaks or HVAC struggles, you get instant root-cause alerts.
                  </p>
                  <ul className="space-y-2 text-xs text-slate-300">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Continuous flow signature leak detection</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Phantom electrical load identification</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Instant severity rating with estimated cost impact</span>
                    </li>
                  </ul>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono text-xs">
                  <div className="text-[11px] text-slate-400 pb-2 border-b border-slate-800 flex justify-between">
                    <span>Active Telemetry Monitor</span>
                    <span className="text-amber-400">1 Finding Detected</span>
                  </div>
                  <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-200 space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-amber-300">Continuous Water Flow</span>
                      <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded">High Severity</span>
                    </div>
                    <p className="text-[11px] text-slate-300">
                      Sustained 0.4 L/min flow between 2:00 AM and 5:00 AM. Probable cause: Guest bathroom toilet flapper seal.
                    </p>
                    <p className="text-[10px] text-amber-400 pt-1 font-semibold">Estimated Monthly Waste: ~$42.00</p>
                  </div>
                </div>
              </div>
            )}

            {activePreviewTab === "agents" && (
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div className="space-y-4">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-semibold border border-indigo-500/20">
                    <Cpu className="w-3.5 h-3.5" />
                    <span>LangGraph Multi-Agent Architecture</span>
                  </div>
                  <h3 className="text-2xl font-bold text-white">Autonomous Agents That Collaborate</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    Unlike standard chatbots that guess, HomePilot coordinates specialized agents (Energy, Water, Maintenance, Inventory) that query real database tools to investigate problems with mathematical rigor.
                  </p>
                  <ul className="space-y-2 text-xs text-slate-300">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Deterministic Python tools (no hallucinated math)</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Multi-turn supervisor dynamic dispatch</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
                      <span>Transparent, step-by-step reasoning logs</span>
                    </li>
                  </ul>
                </div>
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 font-mono text-xs">
                  <div className="text-[11px] text-slate-400 pb-2 border-b border-slate-800 flex justify-between">
                    <span>Supervisor Dispatch Trace</span>
                    <span className="text-teal-400">Complete</span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-[11px]">
                    <span className="text-teal-400 font-semibold">1. Goal:</span> Investigate 32% spike in upstairs power draw
                  </div>
                  <div className="p-2 rounded bg-amber-950/30 border border-amber-800/40 text-[11px]">
                    <span className="text-amber-400 font-semibold">2. Energy Tool:</span> Peak draws correlate with 2pm-6pm heat waves
                  </div>
                  <div className="p-2 rounded bg-blue-950/30 border border-blue-800/40 text-[11px]">
                    <span className="text-blue-400 font-semibold">3. Maintenance Tool:</span> AC filter last replaced 114 days ago
                  </div>
                  <div className="p-2 rounded bg-teal-950/40 border border-teal-700/50 text-[11px]">
                    <span className="text-teal-300 font-semibold">4. Resolution:</span> Order 20x25x1 MERV 11 filter; schedule swap
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Core Specialist Domains */}
      <section id="domains" className="py-20 px-6">
        <div className="mx-auto max-w-7xl space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-semibold text-teal-400 uppercase tracking-widest">Four Dedicated Domains</span>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">Meet Your Household Specialists</h2>
            <p className="text-sm text-slate-400">
              Each specialist runs deterministic tools against real telemetry to protect your home and wallet.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-amber-500/40 transition-all duration-300 space-y-3 hover:shadow-lg hover:shadow-amber-500/5 group">
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 group-hover:scale-105 transition-transform">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-lg text-white">Energy Specialist</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Tracks daily kWh rates, identifies off-peak savings, digitizes electric bills, and flags phantom appliance drain.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 transition-all duration-300 space-y-3 hover:shadow-lg hover:shadow-cyan-500/5 group">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform">
                <Droplets className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-lg text-white">Water Specialist</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Calculates daily litres, runs continuous flow heuristics to catch silent leaks, and parses water utility bills.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-blue-500/40 transition-all duration-300 space-y-3 hover:shadow-lg hover:shadow-blue-500/5 group">
              <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 group-hover:scale-105 transition-transform">
                <Wrench className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-lg text-white">Maintenance Specialist</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Manages appliances, warranty dates, filter lifespans, and schedules preventive care to prevent catastrophic equipment breakdowns.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-emerald-500/40 transition-all duration-300 space-y-3 hover:shadow-lg hover:shadow-emerald-500/5 group">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition-transform">
                <Package className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-lg text-white">Inventory Specialist</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Uses computer vision to scan pantry and fridge photos, monitors consumables, and auto-compiles smart grocery lists.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Value Grid */}
      <section id="features" className="py-20 px-6 bg-slate-900/30 border-t border-slate-800/80">
        <div className="mx-auto max-w-7xl space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-semibold text-teal-400 uppercase tracking-widest">Built For Homeowners</span>
            <h2 className="text-3xl font-extrabold text-white tracking-tight">Everything You Need for Peace of Mind</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-3">
              <div className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 w-fit">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-base text-white">100% Private & Isolated</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Every household operates in a strictly isolated data sandbox. No cross-household leakage, no telemetry sharing, full session authentication.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-3">
              <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 w-fit">
                <BarChart3 className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-base text-white">Deterministic Verification</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                AI agents do not guess or fabricate numbers. All statistics, spike variances, and bill comparisons are calculated using verified Python code.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-3">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 w-fit">
                <Layers className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-base text-white">Multi-Provider Failover</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Resilient agent execution with automatic racing across Google Gemini, OpenRouter, and local models to ensure 24/7 uptime.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Technical Architecture Deep Dive (Collapsible & Expandable for interested users/engineers) */}
      <section id="architecture" className="py-16 px-6 border-t border-slate-800/80">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 md:p-8 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold text-teal-400 uppercase tracking-widest">
                  Technical Architecture & Under-the-Hood
                </span>
                <h3 className="text-xl sm:text-2xl font-bold text-white mt-1">
                  Engineered with LangGraph Multi-Agent Rigor
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Deterministic tools, bounded execution budgets, and verifiable evidence traces.
                </p>
              </div>

              <button
                onClick={() => setShowArchDeepDive(!showArchDeepDive)}
                className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-teal-300 border border-slate-700 text-xs font-semibold flex items-center gap-2 self-start sm:self-auto transition"
              >
                <span>{showArchDeepDive ? "Collapse Technical Architecture" : "Explore Technical Architecture"}</span>
                {showArchDeepDive ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </div>

            {/* Expandable Technical Details */}
            {showArchDeepDive && (
              <div className="pt-6 border-t border-slate-800 space-y-8 animate-fadeIn">
                <div className="grid md:grid-cols-2 gap-8 items-start">
                  <div className="space-y-4">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider text-teal-300">
                      Dynamic LangGraph Supervisor
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      Rather than a static script or hallucinating single LLM prompt, HomePilot employs an orchestrator that dynamically inspects goals, queries real database state, dispatches to domain specialists with isolated execution contexts, and terminates cleanly when evidence is sufficient.
                    </p>

                    <div className="space-y-3 font-mono text-xs">
                      <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
                        <span className="text-teal-400 font-semibold">1. Trigger:</span> Water consumption spiked +48% vs 30-day baseline
                      </div>
                      <div className="text-center text-slate-500 text-[10px]">↓ Supervisor selects domain specialist</div>
                      <div className="p-3 rounded-lg bg-blue-950/40 border border-blue-800/50 text-blue-200">
                        <span className="text-blue-400 font-semibold">2. Water Specialist:</span> Confirms continuous flow rate signature (0.3 L/min)
                      </div>
                      <div className="text-center text-slate-500 text-[10px]">↓ Multi-turn cross-domain handoff</div>
                      <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 text-amber-200">
                        <span className="text-amber-400 font-semibold">3. Maintenance Specialist:</span> Cross-checks Dishwasher inlet age (5.8 years)
                      </div>
                      <div className="text-center text-slate-500 text-[10px]">↓ Synthesizes verifiable resolution</div>
                      <div className="p-3 rounded-lg bg-teal-950/50 border border-teal-700/60 text-teal-200">
                        <span className="text-teal-300 font-semibold">4. Finding:</span> Inspect inlet seal before scheduling full pump replacement
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider text-teal-300">
                      Core System Guarantees
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                        <p className="font-semibold text-teal-300">Background Engine</p>
                        <p className="mt-1 text-slate-400 text-[11px]">APScheduler checks telemetry, bills, and maintenance continuously.</p>
                      </div>
                      <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                        <p className="font-semibold text-teal-300">Explainable Traces</p>
                        <p className="mt-1 text-slate-400 text-[11px]">Every tool call, candidate reasoning, and parameter is auditable.</p>
                      </div>
                      <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                        <p className="font-semibold text-teal-300">Bounded Budgets</p>
                        <p className="mt-1 text-slate-400 text-[11px]">Hard execution bounds prevent runaway LLM agent loops.</p>
                      </div>
                      <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                        <p className="font-semibold text-teal-300">Dual Persistence</p>
                        <p className="mt-1 text-slate-400 text-[11px]">Seamless compatibility across local SQLite and production Neon PostgreSQL.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* CTA Bottom Banner */}
      <section className="py-20 px-6 bg-gradient-to-b from-slate-950 to-slate-900 border-t border-slate-800/80 text-center">
        <div className="mx-auto max-w-4xl space-y-6">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Ready for a Smarter, Proactive Household?
          </h2>
          <p className="text-sm text-slate-300 max-w-xl mx-auto">
            Take full control of your utility costs, pantry inventory, and appliance longevity today.
          </p>
          <div className="pt-2">
            <button
              onClick={() => { setError(""); setAuthMode("register"); }}
              className="px-8 py-4 rounded-xl bg-gradient-to-r from-teal-400 to-cyan-500 hover:from-teal-300 hover:to-cyan-400 text-slate-950 font-bold text-base shadow-xl shadow-teal-500/25 transition transform hover:-translate-y-0.5 active:translate-y-0"
            >
              Get Started in Minutes
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-800/80 py-8 px-6 text-center text-xs text-slate-500">
        <p className="font-medium text-slate-400">HomePilot AI — Autonomous Multi-Agent Household Operations System</p>
        <p className="mt-1">IBM SkillsBuild Agentic AI Internship Capstone Project</p>
      </footer>

      {/* Auth Modal (Login / Register) */}
      {authMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-8 shadow-2xl text-slate-100">
            <button
              onClick={() => { setAuthMode(""); setError(""); }}
              className="absolute top-5 right-5 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
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
                className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-teal-400 to-cyan-500 hover:from-teal-300 hover:to-cyan-400 disabled:opacity-50 text-slate-950 font-bold text-sm shadow-md transition"
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
