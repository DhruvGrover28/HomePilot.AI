import React, { useState } from "react";
import { apiJson, apiFetch } from "../api";
import { Settings, Database } from "lucide-react";

export default function SettingsView({
  user,
  household,
  onUserUpdated,
  onHouseholdUpdated,
  onSeedDemo,
}) {
  // Profile state
  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name || "",
    theme_preference: user?.theme_preference || "system",
  });
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState("");

  // Household state
  const [householdForm, setHouseholdForm] = useState({
    name: household?.name || "",
    timezone: household?.timezone || "UTC",
    preferred_units: household?.preferred_units || "metric",
  });
  const [householdSaving, setHouseholdSaving] = useState(false);
  const [householdMsg, setHouseholdMsg] = useState("");

  // Change password state
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordMsg, setPasswordMsg] = useState("");
  const [passwordError, setPasswordError] = useState("");

  // Demo seeding state
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState("");

  async function handleSaveProfile(e) {
    e.preventDefault();
    setProfileSaving(true);
    setProfileMsg("");
    try {
      const updated = await apiJson("/api/auth/me", {
        method: "PATCH",
        body: JSON.stringify(profileForm),
      });
      setProfileMsg("Profile updated successfully.");
      onUserUpdated(updated);
    } catch (err) {
      setProfileMsg(`Error: ${err.message}`);
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleSaveHousehold(e) {
    e.preventDefault();
    setHouseholdSaving(true);
    setHouseholdMsg("");
    try {
      const updated = await apiJson("/api/auth/household", {
        method: "PATCH",
        body: JSON.stringify(householdForm),
      });
      setHouseholdMsg("Household settings updated successfully.");
      onHouseholdUpdated(updated);
    } catch (err) {
      setHouseholdMsg(`Error: ${err.message}`);
    } finally {
      setHouseholdSaving(false);
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    setPasswordSaving(true);
    setPasswordMsg("");
    setPasswordError("");

    if (passwordForm.new_password.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      setPasswordSaving(false);
      return;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError("New passwords do not match.");
      setPasswordSaving(false);
      return;
    }

    try {
      await apiJson("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify(passwordForm),
      });
      setPasswordMsg("Password changed successfully.");
      setPasswordForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch (err) {
      setPasswordError(err.message || "Failed to update password.");
    } finally {
      setPasswordSaving(false);
    }
  }

  async function handleTriggerSeedDemo() {
    if (!window.confirm("This will populate demonstration telemetry, appliances, and supplies strictly in your isolated household. Proceed?")) return;
    setSeeding(true);
    setSeedMsg("");
    try {
      await onSeedDemo();
      setSeedMsg("Demonstration telemetry successfully seeded in your household.");
    } catch (err) {
      setSeedMsg(`Error: ${err.message}`);
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-2.5">
          <Settings className="w-6 h-6 text-slate-400" />
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">Account & Household Settings</h1>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Manage your personal profile, household configuration, security credentials, and demo data.
        </p>
      </div>

      {/* Profile Settings */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-slate-900 dark:text-white">User Profile</h2>
        {profileMsg && (
          <p className="text-xs font-semibold text-teal-600 dark:text-teal-400">{profileMsg}</p>
        )}

        <form onSubmit={handleSaveProfile} className="space-y-3 text-xs max-w-md">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Full Name</label>
            <input
              type="text"
              required
              value={profileForm.full_name}
              onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Email Address (Account ID)</label>
            <input
              type="email"
              disabled
              value={user?.email || ""}
              className="w-full rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-300 dark:border-slate-700 p-2.5 cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Theme Preference</label>
            <select
              value={profileForm.theme_preference}
              onChange={(e) => setProfileForm({ ...profileForm, theme_preference: e.target.value })}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
            >
              <option value="system">System Default</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={profileSaving}
            className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 font-bold text-white shadow-sm transition disabled:opacity-50"
          >
            {profileSaving ? "Saving..." : "Save Profile"}
          </button>
        </form>
      </div>

      {/* Household Configuration */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-slate-900 dark:text-white">Household Configuration</h2>
        {householdMsg && (
          <p className="text-xs font-semibold text-teal-600 dark:text-teal-400">{householdMsg}</p>
        )}

        <form onSubmit={handleSaveHousehold} className="space-y-3 text-xs max-w-md">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Household Name</label>
            <input
              type="text"
              required
              value={householdForm.name}
              onChange={(e) => setHouseholdForm({ ...householdForm, name: e.target.value })}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Timezone</label>
              <select
                value={householdForm.timezone}
                onChange={(e) => setHouseholdForm({ ...householdForm, timezone: e.target.value })}
                className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
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
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Preferred Units</label>
              <select
                value={householdForm.preferred_units}
                onChange={(e) => setHouseholdForm({ ...householdForm, preferred_units: e.target.value })}
                className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
              >
                <option value="metric">Metric (kWh, Litres)</option>
                <option value="imperial">Imperial (kWh, Gallons)</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={householdSaving}
            className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 font-bold text-white shadow-sm transition disabled:opacity-50"
          >
            {householdSaving ? "Saving..." : "Save Household Settings"}
          </button>
        </form>
      </div>

      {/* Change Password */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-slate-900 dark:text-white">Change Password</h2>
        {passwordMsg && <p className="text-xs font-semibold text-green-600">{passwordMsg}</p>}
        {passwordError && <p className="text-xs font-semibold text-red-600">{passwordError}</p>}

        <form onSubmit={handleChangePassword} className="space-y-3 text-xs max-w-md">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Current Password</label>
            <input
              type="password"
              required
              value={passwordForm.current_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">New Password (8+ chars)</label>
            <input
              type="password"
              required
              minLength={8}
              value={passwordForm.new_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Confirm New Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={passwordForm.confirm_password}
              onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
              className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
            />
          </div>

          <button
            type="submit"
            disabled={passwordSaving}
            className="px-4 py-2 rounded-lg bg-slate-900 dark:bg-slate-100 hover:bg-slate-800 text-white dark:text-slate-900 font-bold shadow-sm transition disabled:opacity-50"
          >
            {passwordSaving ? "Updating..." : "Update Password"}
          </button>
        </form>
      </div>

      {/* Demonstration Environment */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
        <h2 className="text-sm font-bold text-slate-900 dark:text-white">Demonstration Environment</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Populate realistic multi-domain household telemetry (30 days of electricity readings with an anomaly, water usage with a continuous flow pattern, kitchen & HVAC appliances, and supply inventory) strictly inside your current household account.
        </p>

        {seedMsg && <p className="text-xs font-semibold text-teal-600 dark:text-teal-400">{seedMsg}</p>}

        <button
          onClick={handleTriggerSeedDemo}
          disabled={seeding}
          className="px-4 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 font-bold text-xs text-white shadow-sm transition disabled:opacity-50 flex items-center gap-1.5"
        >
          <Database className="w-3.5 h-3.5" />
          <span>{seeding ? "Populating Demo Data..." : "Seed Demonstration Telemetry"}</span>
        </button>
      </div>

      {/* Danger Zone: Account Deletion */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-red-200 dark:border-red-900/60 shadow-sm space-y-3">
        <h2 className="text-sm font-bold text-red-600 dark:text-red-400">Danger Zone</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Permanently delete your account and revoke all active sessions. This action cannot be undone.
        </p>

        <button
          onClick={async () => {
            if (!window.confirm("Are you sure you want to delete your account? This action cannot be undone.")) return;
            try {
              await apiFetch("/api/auth/me", { method: "DELETE" });
              if (onLogout) onLogout();
            } catch (err) {
              alert(`Failed to delete account: ${err.message}`);
            }
          }}
          className="px-4 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 font-bold text-xs text-white shadow-sm transition"
        >
          Delete Account
        </button>
      </div>
    </div>
  );
}
