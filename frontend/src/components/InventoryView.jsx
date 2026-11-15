import React, { useState, useEffect } from "react";
import { apiJson, apiFetch } from "../api";
import { Package, Camera, AlertTriangle, Check, Sparkles, X } from "lucide-react";

export default function InventoryView({ onDataChanged }) {
  const [inventory, setInventory] = useState([]);
  const [shoppingList, setShoppingList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showItemModal, setShowItemModal] = useState(false);
  const [showShoppingModal, setShowShoppingModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Vision Scan state
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanFile, setScanFile] = useState(null);
  const [scanPreview, setScanPreview] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [reconcileItems, setReconcileItems] = useState([]);
  const [reconciling, setReconciling] = useState(false);
  const [scanSuccessMsg, setScanSuccessMsg] = useState("");

  // Forms
  const [itemForm, setItemForm] = useState({
    name: "",
    category: "cleaning",
    quantity: "2",
    unit: "pack",
    reorder_threshold: "1",
    target_quantity: "3",
    location: "",
    notes: "",
  });

  const [shoppingForm, setShoppingForm] = useState({
    item_name: "",
    quantity: "1",
    unit: "pack",
    estimated_cost: "",
  });

  function handleScanFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("Image file size exceeds 10 MB limit.");
      return;
    }
    setScanFile(file);
    setScanPreview(URL.createObjectURL(file));
    setError("");
  }

  async function handleScanSubmit() {
    if (!scanFile) return;
    setScanning(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", scanFile);
      const res = await apiFetch("/api/inventory/scan", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to scan inventory image.");
      }
      const data = await res.json();
      setScanResult(data);
      const initialReconcile = (data.detected_items || []).map((det) => ({
        name: det.name,
        category: det.category || "general",
        quantity: det.estimated_quantity,
        unit: det.unit || "pcs",
        confidence: det.confidence,
        brand: det.brand,
        notes: det.notes,
        matched_item_id: det.matched_item_id,
        existing_quantity: det.existing_quantity,
        action: det.matched_item_id ? "add" : "new",
        reorder_threshold: 1.0,
      }));
      setReconcileItems(initialReconcile);
    } catch (err) {
      setError(err.message || "Failed to analyze inventory image.");
    } finally {
      setScanning(false);
    }
  }

  function updateReconcileField(idx, field, value) {
    setReconcileItems((prev) => {
      const updated = [...prev];
      updated[idx] = { ...updated[idx], [field]: value };
      return updated;
    });
  }

  function removeReconcileItem(idx) {
    setReconcileItems((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleReconcileSubmit() {
    setReconciling(true);
    setError("");
    try {
      const payload = {
        items: reconcileItems.map((item) => ({
          action: item.action,
          item_id: item.matched_item_id,
          name: item.name,
          quantity: Number(item.quantity) || 0,
          unit: item.unit,
          category: item.category,
          reorder_threshold: Number(item.reorder_threshold) || 1,
        })),
      };
      const resData = await apiJson("/api/inventory/reconcile", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setShowScanModal(false);
      setScanResult(null);
      setScanFile(null);
      setScanPreview(null);
      setScanSuccessMsg(
        `Inventory reconciled successfully! ${resData.updated_items.length} updated, ${resData.created_items.length} created, ${resData.ignored_count} skipped.`
      );
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to reconcile inventory items.");
    } finally {
      setReconciling(false);
    }
  }

  async function loadData() {
    setLoading(true);
    try {
      const [invData, shopData] = await Promise.all([
        apiJson("/api/inventory"),
        apiJson("/api/shopping-list"),
      ]);
      setInventory(invData);
      setShoppingList(shopData);
    } catch (err) {
      setError(err.message || "Failed to load inventory.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleAddItem(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiJson("/api/inventory", {
        method: "POST",
        body: JSON.stringify({
          name: itemForm.name,
          category: itemForm.category,
          quantity: Number(itemForm.quantity),
          unit: itemForm.unit,
          reorder_threshold: Number(itemForm.reorder_threshold),
          target_quantity: itemForm.target_quantity ? Number(itemForm.target_quantity) : null,
          location: itemForm.location || null,
          notes: itemForm.notes || null,
        }),
      });

      setShowItemModal(false);
      setItemForm({
        name: "",
        category: "cleaning",
        quantity: "2",
        unit: "pack",
        reorder_threshold: "1",
        target_quantity: "3",
        location: "",
        notes: "",
      });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to add inventory item.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdateQuantity(item, delta) {
    const newQty = Math.max(0, item.quantity + delta);
    try {
      await apiJson(`/api/inventory/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ quantity: newQty }),
      });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to update item quantity.");
    }
  }

  async function handleDeleteItem(id) {
    if (!window.confirm("Are you sure you want to delete this supply item?")) return;
    try {
      await apiFetch(`/api/inventory/${id}`, { method: "DELETE" });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to delete item.");
    }
  }

  async function handleAddShopping(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiJson("/api/shopping-list", {
        method: "POST",
        body: JSON.stringify({
          item_name: shoppingForm.item_name,
          quantity: Number(shoppingForm.quantity) || 1,
          unit: shoppingForm.unit,
          estimated_cost: shoppingForm.estimated_cost ? Number(shoppingForm.estimated_cost) : null,
        }),
      });

      setShowShoppingModal(false);
      setShoppingForm({
        item_name: "",
        quantity: "1",
        unit: "pack",
        estimated_cost: "",
      });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to add shopping item.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleShoppingPurchased(item) {
    try {
      await apiJson(`/api/shopping-list/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ purchased: !item.purchased }),
      });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to update shopping item.");
    }
  }

  async function handleDeleteShopping(id) {
    try {
      await apiFetch(`/api/shopping-list/${id}`, { method: "DELETE" });
      await loadData();
      if (onDataChanged) onDataChanged();
    } catch (err) {
      setError(err.message || "Failed to delete shopping item.");
    }
  }

  const lowItems = inventory.filter((i) => i.quantity <= i.reorder_threshold);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2.5">
            <Package className="w-6 h-6 text-emerald-500" />
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Inventory Specialist Domain</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Critical household supplies, reorder threshold tracking, and auto-populated shopping lists.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => { setError(""); setShowScanModal(true); setScanResult(null); setScanFile(null); setScanPreview(null); }}
            className="px-3.5 py-2 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-500 text-white shadow-sm transition flex items-center gap-1.5"
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Scan Inventory</span>
          </button>
          <button
            onClick={() => { setError(""); setShowShoppingModal(true); }}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition"
          >
            + Add Shopping Item
          </button>
          <button
            onClick={() => { setError(""); setShowItemModal(true); }}
            className="px-3.5 py-2 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition"
          >
            + Add Supply Item
          </button>
        </div>
      </div>

      {scanSuccessMsg && (
        <div className="rounded-xl bg-emerald-950/50 border border-emerald-700/60 p-4 text-xs text-emerald-300 flex items-center justify-between">
          <span>{scanSuccessMsg}</span>
          <button onClick={() => setScanSuccessMsg("")} className="text-emerald-400 hover:text-emerald-200 font-bold ml-2 p-1" aria-label="Close message"><X className="w-4 h-4" /></button>
        </div>
      )}

      {error && (
        <div className="rounded-xl bg-red-950/50 border border-red-700/60 p-4 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Low stock warning banner */}
      {lowItems.length > 0 && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
            <div>
              <p className="text-xs font-bold text-red-900 dark:text-red-300">
                {lowItems.length} item(s) below reorder threshold
              </p>
              <p className="text-[11px] text-red-700 dark:text-red-400">
                {lowItems.map((i) => `${i.name} (${i.quantity} ${i.unit})`).join(", ")}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              // Add lowest item to shopping list quickly
              if (lowItems[0]) {
                setShoppingForm({
                  item_name: lowItems[0].name,
                  quantity: "2",
                  unit: lowItems[0].unit,
                  estimated_cost: "",
                });
                setShowShoppingModal(true);
              }
            }}
            className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-semibold"
          >
            Add to Shopping List
          </button>
        </div>
      )}

      {/* Supplies Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">
            Household Supplies ({inventory.length})
          </h2>
          <span className="text-xs text-slate-400">Stock level monitored against safety threshold</span>
        </div>

        {inventory.length === 0 ? (
          <div className="p-8 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center text-xs text-slate-400">
            No supplies tracked in this household. Add essential items or seed simulated demo data.
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {inventory.map((item) => {
              const isLow = item.quantity <= item.reorder_threshold;
              return (
                <div
                  key={item.id}
                  className={`p-4 rounded-xl bg-white dark:bg-slate-900 border shadow-sm space-y-3 transition ${
                    isLow
                      ? "border-red-300 dark:border-red-800/80 bg-red-50/20"
                      : "border-slate-200 dark:border-slate-800 hover:border-emerald-500/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-sm text-slate-900 dark:text-white truncate">{item.name}</h3>
                    <div className="flex items-center gap-1.5">
                      {isLow ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300 font-bold">
                          LOW
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-medium">
                          OK
                        </span>
                      )}
                      <button
                        onClick={() => handleDeleteItem(item.id)}
                        className="text-slate-400 hover:text-red-500 text-xs p-1"
                        title="Delete item"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span className="capitalize">{item.category}</span>
                    <span>Threshold: {item.reorder_threshold} {item.unit}</span>
                  </div>

                  {/* Stock adjuster controls */}
                  <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-slate-400 block">Stock on hand</span>
                      <span className="text-base font-extrabold text-slate-900 dark:text-white">
                        {item.quantity} <span className="text-xs font-normal text-slate-400">{item.unit}</span>
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleUpdateQuantity(item, -1)}
                        className="h-7 w-7 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center font-bold text-slate-700 dark:text-slate-200"
                        title="Decrease quantity by 1"
                      >
                        -
                      </button>
                      <button
                        onClick={() => handleUpdateQuantity(item, 1)}
                        className="h-7 w-7 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center font-bold text-slate-700 dark:text-slate-200"
                        title="Increase quantity by 1"
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Shopping List Section */}
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-sm text-slate-900 dark:text-white">Household Shopping List</h2>
            <p className="text-xs text-slate-400">Items flagged by Inventory Specialist or manually scheduled</p>
          </div>
          <span className="text-xs text-slate-400">{shoppingList.length} items</span>
        </div>

        <div className="divide-y divide-slate-100 dark:divide-slate-800">
          {shoppingList.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No items on the shopping list.
            </div>
          ) : (
            shoppingList.map((item) => (
              <div
                key={item.id}
                className="p-4 flex items-center justify-between gap-4 hover:bg-slate-50/50 dark:hover:bg-slate-800/40"
              >
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={item.purchased}
                    onChange={() => handleToggleShoppingPurchased(item)}
                    className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                  />
                  <div>
                    <p
                      className={`text-xs font-semibold ${
                        item.purchased
                          ? "line-through text-slate-400"
                          : "text-slate-900 dark:text-white"
                      }`}
                    >
                      {item.item_name}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      Quantity: {item.quantity} {item.unit || "pack"}
                      {item.estimated_cost && ` · Est. $${item.estimated_cost}`}
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => handleDeleteShopping(item.id)}
                  className="text-slate-400 hover:text-red-500 text-xs px-2 py-1"
                >
                  Delete
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Add Supply Modal */}
      {showItemModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-white">Track Supply Item</h3>
              <button onClick={() => setShowItemModal(false)} className="text-slate-400 hover:text-slate-600 p-1"><X className="w-4 h-4" /></button>
            </div>

            <form onSubmit={handleAddItem} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Item Name</label>
                <input
                  type="text"
                  required
                  value={itemForm.name}
                  onChange={(e) => setItemForm({ ...itemForm, name: e.target.value })}
                  placeholder="e.g. Water Filter Cartridges"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Category</label>
                  <select
                    value={itemForm.category}
                    onChange={(e) => setItemForm({ ...itemForm, category: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  >
                    <option value="cleaning">Cleaning</option>
                    <option value="pantry">Pantry / Food</option>
                    <option value="maintenance">Maintenance</option>
                    <option value="safety">Safety</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Unit</label>
                  <input
                    type="text"
                    required
                    value={itemForm.unit}
                    onChange={(e) => setItemForm({ ...itemForm, unit: e.target.value })}
                    placeholder="pack, box, kg"
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Current Quantity</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={itemForm.quantity}
                    onChange={(e) => setItemForm({ ...itemForm, quantity: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Reorder Threshold</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={itemForm.reorder_threshold}
                    onChange={(e) => setItemForm({ ...itemForm, reorder_threshold: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Location</label>
                <input
                  type="text"
                  value={itemForm.location}
                  onChange={(e) => setItemForm({ ...itemForm, location: e.target.value })}
                  placeholder="e.g. Utility Cabinet"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowItemModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-bold text-white shadow-sm"
                >
                  {submitting ? "Saving..." : "Save Item"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Shopping Item Modal */}
      {showShoppingModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-base text-slate-900 dark:text-white">Add Shopping Item</h3>
              <button onClick={() => setShowShoppingModal(false)} className="text-slate-400 hover:text-slate-600 p-1"><X className="w-4 h-4" /></button>
            </div>

            <form onSubmit={handleAddShopping} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Item Name</label>
                <input
                  type="text"
                  required
                  value={shoppingForm.item_name}
                  onChange={(e) => setShoppingForm({ ...shoppingForm, item_name: e.target.value })}
                  placeholder="e.g. Water Filters"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Quantity</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={shoppingForm.quantity}
                    onChange={(e) => setShoppingForm({ ...shoppingForm, quantity: e.target.value })}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Unit</label>
                  <input
                    type="text"
                    value={shoppingForm.unit}
                    onChange={(e) => setShoppingForm({ ...shoppingForm, unit: e.target.value })}
                    placeholder="pack, pcs"
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Estimated Cost (Optional)</label>
                <input
                  type="number"
                  step="any"
                  value={shoppingForm.estimated_cost}
                  onChange={(e) => setShoppingForm({ ...shoppingForm, estimated_cost: e.target.value })}
                  placeholder="$"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 p-2.5"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowShoppingModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-bold text-white shadow-sm"
                >
                  {submitting ? "Saving..." : "Add to List"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Computer Vision Inventory Scanner Modal */}
      {showScanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-4 overflow-y-auto">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <Camera className="w-6 h-6 text-teal-500" />
                <div>
                  <h3 className="font-bold text-base text-slate-900 dark:text-white">Computer Vision Inventory Scanner</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Upload storage or pantry photos to detect items, count quantities, and reconcile with stock.
                  </p>
                </div>
              </div>
              <button
                onClick={() => { setShowScanModal(false); setScanResult(null); setScanFile(null); }}
                className="text-slate-400 hover:text-slate-600 font-bold p-1"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Step 1: Upload & Scan */}
            {!scanResult && (
              <div className="space-y-4 text-xs">
                <div className="border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-6 text-center space-y-3">
                  {scanPreview ? (
                    <div className="flex flex-col items-center gap-2">
                      <img src={scanPreview} alt="Inventory Scan Preview" className="max-h-56 rounded-lg object-contain border border-slate-200 dark:border-slate-800 shadow-xs" />
                      <p className="font-mono text-[11px] text-slate-400">{scanFile?.name} ({(scanFile?.size / 1024).toFixed(1)} KB)</p>
                      <button
                        type="button"
                        onClick={() => { setScanFile(null); setScanPreview(null); }}
                        className="text-xs text-red-500 hover:underline"
                      >
                        Remove photo & choose another
                      </button>
                    </div>
                  ) : (
                    <div>
                      <Camera className="w-10 h-10 text-teal-500 mx-auto mb-2" />
                      <p className="font-semibold text-slate-700 dark:text-slate-300">Select or drop a photograph of your shelf, fridge, or pantry</p>
                      <p className="text-[11px] text-slate-400 mt-1">Supports JPG, PNG, WEBP (up to 10 MB)</p>
                      <label className="mt-3 inline-block px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-bold cursor-pointer transition shadow-xs">
                        Browse Photo
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          className="hidden"
                          onChange={handleScanFileChange}
                        />
                      </label>
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowScanModal(false)}
                    className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={!scanFile || scanning}
                    onClick={handleScanSubmit}
                    className="px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 font-bold text-white shadow-sm disabled:opacity-50 transition"
                  >
                    {scanning ? "Detecting items with Computer Vision..." : "Scan & Detect Items →"}
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Detections Review & Reconciliation */}
            {scanResult && (
              <div className="space-y-4 text-xs">
                {scanResult.image_summary && (
                  <div className="p-3 bg-teal-50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-800 rounded-xl text-teal-900 dark:text-teal-300">
                    <p className="font-semibold text-[11px] uppercase tracking-wider text-teal-700 dark:text-teal-400 mb-0.5">Vision Summary</p>
                    <p>{scanResult.image_summary}</p>
                  </div>
                )}

                {scanResult.warnings?.length > 0 && (
                  <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl text-amber-900 dark:text-amber-300 space-y-1">
                    <p className="font-semibold text-[11px] uppercase tracking-wider text-amber-700 dark:text-amber-400">Detection Notes / Warnings</p>
                    {scanResult.warnings.map((w, idx) => (
                      <p key={idx} className="flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" /><span>{w}</span></p>
                    ))}
                  </div>
                )}

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-slate-900 dark:text-white">Detected Items ({reconcileItems.length}) & Reconciliation Strategy</h4>
                    <span className="text-[11px] text-slate-400">Choose how each item updates inventory:</span>
                  </div>

                  <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-slate-50 dark:bg-slate-950 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-800">
                          <th className="p-2.5">Item Name</th>
                          <th className="p-2.5">Category</th>
                          <th className="p-2.5 w-24">Detected Qty</th>
                          <th className="p-2.5 w-20">Unit</th>
                          <th className="p-2.5">Match Status</th>
                          <th className="p-2.5">Reconciliation Action</th>
                          <th className="p-2.5 text-right">Remove</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                        {reconcileItems.map((item, idx) => (
                          <tr key={idx} className={item.action === "ignore" ? "opacity-50 bg-slate-50/50 dark:bg-slate-950/50" : ""}>
                            <td className="p-2.5">
                              <input
                                type="text"
                                value={item.name}
                                onChange={(e) => updateReconcileField(idx, "name", e.target.value)}
                                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded px-2 py-1 text-xs"
                              />
                              {item.notes && <p className="text-[10px] text-slate-400 mt-0.5">{item.notes}</p>}
                            </td>
                            <td className="p-2.5">
                              <select
                                value={item.category}
                                onChange={(e) => updateReconcileField(idx, "category", e.target.value)}
                                className="bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded px-2 py-1 text-xs"
                              >
                                <option value="cleaning">Cleaning</option>
                                <option value="food">Food</option>
                                <option value="beverage">Beverage</option>
                                <option value="pantry">Pantry</option>
                                <option value="paper_goods">Paper Goods</option>
                                <option value="personal_care">Personal Care</option>
                                <option value="general">General</option>
                              </select>
                            </td>
                            <td className="p-2.5">
                              <input
                                type="number"
                                step="any"
                                min="0"
                                value={item.quantity}
                                onChange={(e) => updateReconcileField(idx, "quantity", Number(e.target.value))}
                                className="w-20 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded px-2 py-1 text-xs font-mono"
                              />
                            </td>
                            <td className="p-2.5">
                              <input
                                type="text"
                                value={item.unit}
                                onChange={(e) => updateReconcileField(idx, "unit", e.target.value)}
                                className="w-16 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded px-2 py-1 text-xs"
                              />
                            </td>
                            <td className="p-2.5">
                              {item.matched_item_id ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300">
                                  <Check className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                                  <span>Matched (Current: {item.existing_quantity})</span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300">
                                  <Sparkles className="w-3 h-3 text-blue-600 dark:text-blue-400" />
                                  <span>New Item</span>
                                </span>
                              )}
                              {item.confidence && (
                                <span className="block text-[10px] text-slate-400 mt-0.5">
                                  Confidence: {Math.round(item.confidence * 100)}%
                                </span>
                              )}
                            </td>
                            <td className="p-2.5">
                              <select
                                value={item.action}
                                onChange={(e) => updateReconcileField(idx, "action", e.target.value)}
                                className="bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded px-2 py-1 text-xs font-medium"
                              >
                                {item.matched_item_id && <option value="add">Add to Stock (+{item.quantity})</option>}
                                {item.matched_item_id && <option value="replace">Replace Count (Exact: {item.quantity})</option>}
                                <option value="new">Create as New Item</option>
                                <option value="ignore">Ignore / Skip</option>
                              </select>
                            </td>
                            <td className="p-2.5 text-right">
                              <button
                                type="button"
                                onClick={() => removeReconcileItem(idx)}
                                className="text-red-400 hover:text-red-600 font-bold p-1"
                                title="Remove item"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-between border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => { setScanResult(null); }}
                    className="px-3.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold text-xs"
                  >
                    ← Re-scan photo
                  </button>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShowScanModal(false)}
                      className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={reconciling || reconcileItems.length === 0}
                      onClick={handleReconcileSubmit}
                      className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-bold text-white shadow-sm disabled:opacity-50 transition"
                    >
                      {reconciling ? "Reconciling Inventory..." : "Confirm & Save Reconciled Inventory"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
