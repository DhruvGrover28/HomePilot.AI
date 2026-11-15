import React, { useState, useEffect } from "react";
import { apiJson, apiFetch } from "../api";

export default function InventoryView({ onDataChanged }) {
  const [inventory, setInventory] = useState([]);
  const [shoppingList, setShoppingList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showItemModal, setShowItemModal] = useState(false);
  const [showShoppingModal, setShowShoppingModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

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
          <div className="flex items-center gap-2">
            <span className="text-xl">📦</span>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">Inventory Specialist Domain</h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Critical household supplies, reorder threshold tracking, and auto-populated shopping lists.
          </p>
        </div>

        <div className="flex items-center gap-2">
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

      {error && (
        <div className="rounded-xl bg-red-950/50 border border-red-700/60 p-4 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Low stock warning banner */}
      {lowItems.length > 0 && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-base">⚠️</span>
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
                        className="text-slate-400 hover:text-red-500 text-xs px-1"
                        title="Delete item"
                      >
                        ✕
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
              <button onClick={() => setShowItemModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
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
              <button onClick={() => setShowShoppingModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
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
    </div>
  );
}
