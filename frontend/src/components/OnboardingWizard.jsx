import React, { useState } from "react";
import { apiJson } from "../api";
import { BrandSymbol } from "./BrandLogo";

export default function OnboardingWizard({ household, onComplete, onSeedDemo }) {
  const [step, setStep] = useState(1);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  const [householdForm, setHouseholdForm] = useState({
    name: household?.name || "My Home",
    timezone: household?.timezone || "UTC",
    preferred_units: household?.preferred_units || "metric",
  });

  const [initialAppliance, setInitialAppliance] = useState({
    name: "Main Refrigerator",
    category: "kitchen",
    power_rating_watts: 150,
  });

  const [initialSupply, setInitialSupply] = useState({
    name: "Dishwasher Salt / Pods",
    category: "cleaning",
    quantity: 1,
    unit: "pack",
    reorder_threshold: 1,
  });

  async function handleFinish(withDemo = false) {
    setWorking(true);
    setError("");
    try {
      // 1. Update household details and mark onboarding_completed: true
      await apiJson("/api/auth/household", {
        method: "PATCH",
        body: JSON.stringify({
          name: householdForm.name,
          timezone: householdFormFormTimezone(),
          preferred_units: householdForm.preferred_units,
          onboarding_completed: true,
        }),
      });

      if (withDemo) {
        // User chose to seed demonstration household data
        await onSeedDemo();
      } else {
        // Add sample initial appliance & supply if provided
        if (initialAppliance.name.trim()) {
          try {
            await apiJson("/api/appliances", {
              method: "POST",
              body: JSON.stringify({
                name: initialAppliance.name,
                category: initialAppliance.category,
                power_rating_watts: Number(initialAppliance.power_rating_watts) || null,
              }),
            });
          } catch {
            // ignore item creation non-fatal error
          }
        }
        if (initialSupply.name.trim()) {
          try {
            await apiJson("/api/inventory", {
              method: "POST",
              body: JSON.stringify({
                name: initialSupply.name,
                category: initialSupply.category,
                quantity: Number(initialSupply.quantity) || 1,
                unit: initialSupply.unit,
                reorder_threshold: Number(initialSupply.reorder_threshold) || 1,
              }),
            });
          } catch {
            // ignore item creation non-fatal error
          }
        }
      }

      onComplete();
    } catch (err) {
      setError(err.message || "Failed to complete onboarding.");
    } finally {
      setWorking(false);
    }
  }

  function householdFormFormTimezone() {
    return householdForm.timezone || "UTC";
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl space-y-6">
        {/* Progress indicator */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <BrandSymbol size="sm" />
            <span className="text-xs uppercase tracking-widest text-slate-400 font-semibold">
              Household Setup · Step {step} of 4
            </span>
          </div>
          <div className="flex gap-1.5">
            {[1, 2, 3, 4].map((s) => (
              <span
                key={s}
                className={`h-2 w-6 rounded-full transition-colors ${
                  s === step ? "bg-teal-400" : s < step ? "bg-teal-700" : "bg-slate-800"
                }`}
              />
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded-lg bg-red-950/50 border border-red-700/60 p-3 text-xs text-red-300">
            {error}
          </div>
        )}

        {/* Step 1: Welcome & Household Name */}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-white">Welcome to HomePilot AI</h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              Let's configure your isolated household environment. Your telemetry, appliances, and investigations remain strictly private to your account.
            </p>
            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Household Name</label>
                <input
                  type="text"
                  value={householdForm.name}
                  onChange={(e) => setHouseholdForm({ ...householdForm, name: e.target.value })}
                  placeholder="e.g. Maple Residence or Apt 4B"
                  className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Timezone</label>
                  <select
                    value={householdForm.timezone}
                    onChange={(e) => setHouseholdForm({ ...householdForm, timezone: e.target.value })}
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  >
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">US Eastern (UTC-5)</option>
                    <option value="America/Chicago">US Central (UTC-6)</option>
                    <option value="America/Los_Angeles">US Pacific (UTC-8)</option>
                    <option value="Europe/London">Europe / London</option>
                    <option value="Asia/Kolkata">Asia / Kolkata (IST)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Units System</label>
                  <select
                    value={householdForm.preferred_units}
                    onChange={(e) => setHouseholdForm({ ...householdForm, preferred_units: e.target.value })}
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  >
                    <option value="metric">Metric (kWh, Litres)</option>
                    <option value="imperial">Imperial (kWh, Gallons)</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="pt-4 flex justify-end">
              <button
                onClick={() => setStep(2)}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-sm transition"
              >
                Next: Appliances →
              </button>
            </div>
          </div>
        )}

        {/* Step 2: First Appliance */}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-white">Add Your First Monitored Appliance</h2>
            <p className="text-xs text-slate-400">
              The Maintenance Specialist tracks power consumption, age, and maintenance tasks. You can add more later.
            </p>
            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Appliance Name</label>
                <input
                  type="text"
                  value={initialAppliance.name}
                  onChange={(e) => setInitialAppliance({ ...initialAppliance, name: e.target.value })}
                  placeholder="e.g. Heat Pump, Refrigerator, Dishwasher"
                  className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Category</label>
                  <select
                    value={initialAppliance.category}
                    onChange={(e) => setInitialAppliance({ ...initialAppliance, category: e.target.value })}
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  >
                    <option value="kitchen">Kitchen</option>
                    <option value="hvac">HVAC / Heating</option>
                    <option value="laundry">Laundry</option>
                    <option value="water">Water Heating</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Power Rating (Watts)</label>
                  <input
                    type="number"
                    value={initialAppliance.power_rating_watts}
                    onChange={(e) => setInitialAppliance({ ...initialAppliance, power_rating_watts: e.target.value })}
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  />
                </div>
              </div>
            </div>
            <div className="pt-4 flex justify-between">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white"
              >
                ← Back
              </button>
              <button
                onClick={() => setStep(3)}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-sm transition"
              >
                Next: Supplies →
              </button>
            </div>
          </div>
        )}

        {/* Step 3: First Inventory Item */}
        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-white">Track Key Consumables</h2>
            <p className="text-xs text-slate-400">
              The Inventory Specialist automatically flags supplies falling below safety thresholds and prepares shopping recommendations.
            </p>
            <div className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Supply Name</label>
                <input
                  type="text"
                  value={initialSupply.name}
                  onChange={(e) => setInitialSupply({ ...initialSupply, name: e.target.value })}
                  placeholder="e.g. Water Filters, Salt, Pods"
                  className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Current Qty</label>
                  <input
                    type="number"
                    value={initialSupply.quantity}
                    onChange={(e) => setInitialSupply({ ...initialSupply, quantity: e.target.value })}
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Unit</label>
                  <input
                    type="text"
                    value={initialSupply.unit}
                    onChange={(e) => setInitialSupply({ ...initialSupply, unit: e.target.value })}
                    placeholder="pack, pcs"
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Threshold</label>
                  <input
                    type="number"
                    value={initialSupply.reorder_threshold}
                    onChange={(e) => setInitialSupply({ ...initialSupply, reorder_threshold: e.target.value })}
                    className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-400"
                  />
                </div>
              </div>
            </div>
            <div className="pt-4 flex justify-between">
              <button
                onClick={() => setStep(2)}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white"
              >
                ← Back
              </button>
              <button
                onClick={() => setStep(4)}
                className="px-5 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-sm transition"
              >
                Next: Launch Options →
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Choose Launch Mode */}
        {step === 4 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-white">Choose Your Starting Point</h2>
            <p className="text-xs text-slate-300">
              You can start with a clean slate or populate your household with demonstration telemetry to evaluate the agentic monitoring system immediately.
            </p>
            <div className="grid gap-3 pt-2">
              <div
                onClick={() => !working && handleFinish(true)}
                className="cursor-pointer p-4 rounded-xl border border-teal-500/50 bg-teal-950/30 hover:bg-teal-950/50 transition space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-teal-300 text-sm">Recommended: Populate Demonstration Telemetry</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-teal-400 text-slate-950 font-bold">Fast-Track</span>
                </div>
                <p className="text-xs text-slate-400">
                  Pre-loads 30 days of electricity readings, water usage spikes, appliances, and supply thresholds strictly in your isolated household account.
                </p>
              </div>

              <div
                onClick={() => !working && handleFinish(false)}
                className="cursor-pointer p-4 rounded-xl border border-slate-800 bg-slate-950/60 hover:bg-slate-850 transition space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200 text-sm">Start Empty & Enter Readings Manually</span>
                </div>
                <p className="text-xs text-slate-400">
                  Starts with only the items you entered above. You can import readings via CSV anytime.
                </p>
              </div>
            </div>

            <div className="pt-4 flex justify-between items-center">
              <button
                onClick={() => setStep(3)}
                disabled={working}
                className="px-4 py-2 text-sm text-slate-400 hover:text-white"
              >
                ← Back
              </button>
              {working && <span className="text-xs text-teal-400 animate-pulse">Configuring household...</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
