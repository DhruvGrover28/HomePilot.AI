import React, { useState, useEffect } from "react";
import { apiJson, apiFetch } from "../api";

export default function MaintenanceView({ onDataChanged }) {
  const [appliances, setAppliances] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showApplianceModal, setShowApplianceModal] = useState(false);
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Forms
  const [applianceForm, setApplianceForm] = useState({
    name: "",
    category: "kitchen",
    location: "",
    power_rating_watts: "",
    warranty_expires: "",
    notes: "",
  });

  const [taskForm, setTaskForm] = useState({
    title: "",
    description: "",
    domain: "maintenance",
    priority: "medium",
    due_date: "",
    entity_id: "",
  });

  async function loadData() {
    setLoading(true);
    try {
      const [appData, taskData] = await Promise.all([
        apiJson("/api/appliances"),
        apiJson("/api/tasks"),
      ]);
      setAppliances(appData);
      setTasks(taskData);
    } catch (err) {
      setError(err.message || "Failed to load maintenance records.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleAddAppliance(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiJson("/api/appliances", {
        method: "POST",
        body: JSON.stringify({
          name: applianceForm.name,
          category: applianceForm.category,
          location: applianceForm.location || null,
          power_rating_watts: applianceForm.power_rating_watts ? Number(applianceForm.power_rating_watts) : null,
          warranty_expires: applianceForm.warranty_expires || null,
          notes: applianceForm.notes || null,
        }),
      });

      setShowApplianceModal(false);
      setApplianceForm({
        name: "",
        category: "kitchen",
        location: "",
        power_rating_watts: "",
        warranty_expires: "",
        notes: "",
      });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to add appliance.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteAppliance(id) {
    if (!window.confirm("Are you sure you want to delete this appliance?")) return;
    try {
      await apiFetch(`/api/appliances/${id}`, { method: "DELETE" });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to delete appliance.");
    }
  }

  async function handleAddTask(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiJson("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: taskForm.title,
          description: taskForm.description || null,
          domain: taskForm.domain,
          priority: taskForm.priority,
          due_date: taskForm.due_date || null,
          entity_id: taskForm.entity_id ? Number(taskForm.entity_id) : null,
        }),
      });

      setShowTaskModal(false);
      setTaskForm({
        title: "",
        description: "",
        domain: "maintenance",
        priority: "medium",
        due_date: "",
        entity_id: "",
      });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to create task.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleTaskStatus(task) {
    const nextStatus = task.status === "completed" ? "pending" : "completed";
    try {
      await apiJson(`/api/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to update task.");
    }
  }

  async function handleDeleteTask(id) {
    try {
      await apiFetch(`/api/tasks/${id}`, { method: "DELETE" });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to delete task.");
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🔧</span>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Maintenance Specialist Domain</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Household appliance inventory, operational degradation tracking, and preventive tasks.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => { setError(""); setShowTaskModal(true); }}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition"
          >
            + New Task
          </button>
          <button
            onClick={() => { setError(""); setShowApplianceModal(true); }}
            className="px-3.5 py-2 text-xs font-bold rounded-lg bg-amber-600 hover:bg-amber-500 text-white shadow-sm transition"
          >
            + Add Appliance
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-red-950/50 border border-red-700/60 p-4 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Appliances Directory Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">
            Monitored Appliances ({appliances.length})
          </h2>
          <span className="text-xs text-slate-400">Tracked by Maintenance Specialist</span>
        </div>

        {appliances.length === 0 ? (
          <div className="p-8 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center text-xs text-slate-400">
            No appliances registered in this household. Add your first appliance or seed simulated demo data.
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {appliances.map((app) => (
              <div
                key={app.id}
                className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-2 hover:border-amber-500/40 transition"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-sm text-slate-900 dark:text-white truncate">{app.name}</h3>
                  <div className="flex items-center gap-1.5">
                    {app.is_simulated && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                        simulated
                      </span>
                    )}
                    <button
                      onClick={() => handleDeleteAppliance(app.id)}
                      className="text-slate-400 hover:text-red-500 text-xs px-1"
                      title="Delete appliance"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="uppercase tracking-wider font-semibold text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    {app.category}
                  </span>
                  {app.location && <span>· {app.location}</span>}
                </div>

                <div className="pt-1 text-xs text-slate-600 dark:text-slate-300 grid grid-cols-2 gap-1 border-t border-slate-100 dark:border-slate-800">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Rating</span>
                    <span className="font-medium">{app.power_rating_watts ? `${app.power_rating_watts} W` : "Unknown"}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Warranty</span>
                    <span className="font-medium">{app.warranty_expires || "None"}</span>
                  </div>
                </div>

                {app.notes && (
                  <p className="text-[11px] text-slate-400 italic pt-1 truncate">{app.notes}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Maintenance Tasks Checklist */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-sm text-slate-900 dark:text-white">Maintenance Tasks Checklist</h2>
            <p className="text-xs text-slate-400">Scheduled checks, filter replacements, and technician calls</p>
          </div>
          <span className="text-xs text-slate-400">{tasks.length} tasks</span>
        </div>

        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {tasks.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No tasks currently pending. Create one or let agent investigations generate actionable tasks.
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                className="p-4 flex items-center justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-800/40"
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={task.status === "completed"}
                    onChange={() => handleToggleTaskStatus(task)}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                  />
                  <div>
                    <p
                      className={`text-xs font-semibold ${
                        task.status === "completed"
                          ? "line-through text-slate-400"
                          : "text-slate-900 dark:text-white"
                      }`}
                    >
                      {task.title}
                    </p>
                    {task.description && (
                      <p className="text-[11px] text-slate-500 mt-0.5">{task.description}</p>
                    )}
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400">
                      <span className="uppercase font-semibold tracking-wider">{task.domain}</span>
                      {task.due_date && <span>· Due: {task.due_date}</span>}
                      <span>· Priority: {task.priority}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleDeleteTask(task.id)}
                  className="text-slate-400 hover:text-red-500 text-xs px-2 py-1"
                >
                  Delete
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Add Appliance Modal */}
      {showApplianceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-white">Register Household Appliance</h3>
              <button onClick={() => setShowApplianceModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <form onSubmit={handleAddAppliance} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Appliance Name</label>
                <input
                  type="text"
                  required
                  value={applianceForm.name}
                  onChange={(e) => setApplianceForm({ ...applianceForm, name: e.target.value })}
                  placeholder="e.g. Bosch Dishwasher 800 Series"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Category</label>
                  <select
                    value={applianceForm.category}
                    onChange={(e) => setApplianceForm({ ...applianceForm, category: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  >
                    <option value="kitchen">Kitchen</option>
                    <option value="hvac">HVAC / Heating</option>
                    <option value="laundry">Laundry</option>
                    <option value="water">Water Heating</option>
                    <option value="plumbing">Plumbing</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Location</label>
                  <input
                    type="text"
                    value={applianceForm.location}
                    onChange={(e) => setApplianceForm({ ...applianceForm, location: e.target.value })}
                    placeholder="e.g. Kitchen, Utility Room"
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Power Rating (Watts)</label>
                  <input
                    type="number"
                    value={applianceForm.power_rating_watts}
                    onChange={(e) => setApplianceForm({ ...applianceForm, power_rating_watts: e.target.value })}
                    placeholder="e.g. 1800"
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Warranty Expiry</label>
                  <input
                    type="date"
                    value={applianceForm.warranty_expires}
                    onChange={(e) => setApplianceForm({ ...applianceForm, warranty_expires: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Notes</label>
                <input
                  type="text"
                  value={applianceForm.notes}
                  onChange={(e) => setApplianceForm({ ...applianceForm, notes: e.target.value })}
                  placeholder="e.g. Cleaned filter last month"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowApplianceModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 font-bold text-white shadow-sm"
                >
                  {submitting ? "Saving..." : "Add Appliance"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Task Modal */}
      {showTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-white">Create Maintenance Task</h3>
              <button onClick={() => setShowTaskModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <form onSubmit={handleAddTask} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Task Title</label>
                <input
                  type="text"
                  required
                  value={taskForm.title}
                  onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })}
                  placeholder="e.g. Inspect HVAC intake filters"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  value={taskForm.description}
                  onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
                  placeholder="Details or steps required"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Domain</label>
                  <select
                    value={taskForm.domain}
                    onChange={(e) => setTaskForm({ ...taskForm, domain: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  >
                    <option value="maintenance">Maintenance</option>
                    <option value="energy">Energy</option>
                    <option value="water">Water</option>
                    <option value="inventory">Inventory</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Priority</label>
                  <select
                    value={taskForm.priority}
                    onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Due Date</label>
                <input
                  type="date"
                  value={taskForm.due_date}
                  onChange={(e) => setTaskForm({ ...taskForm, due_date: e.target.value })}
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowTaskModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 font-bold text-white shadow-sm"
                >
                  {submitting ? "Saving..." : "Create Task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
