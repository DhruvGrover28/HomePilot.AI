import React, { useState, useEffect, useRef } from "react";
import { apiJson, apiFetch } from "../api";
import { MessageSquare, Cpu } from "lucide-react";

export default function AssistantView({ onInspectRun }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [triggerInvestigation, setTriggerInvestigation] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);

  const samplePrompts = [
    "What are my household's top operational priorities right now?",
    "Check our electricity consumption and see if any appliance is spiking.",
    "Are we experiencing any continuous water flow or leak patterns?",
    "Which household supplies are running low and need reordering?",
  ];

  async function loadHistory() {
    setLoadingHistory(true);
    try {
      const data = await apiJson("/api/assistant/history");
      setMessages(data);
    } catch (err) {
      setError(err.message || "Failed to load conversation history.");
    } finally {
      setLoadingHistory(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function handleSend(e) {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);
    setError("");

    try {
      const result = await apiJson("/api/assistant/chat", {
        method: "POST",
        body: JSON.stringify({
          message: trimmed,
          trigger_investigation: triggerInvestigation,
        }),
      });

      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: result.reply,
        metadata: result.investigation_run ? { run: result.investigation_run } : null,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message || "Failed to send message to assistant.");
    } finally {
      setSending(false);
    }
  }

  async function handleClearHistory() {
    if (!window.confirm("Are you sure you want to clear your conversation history?")) return;
    try {
      await apiFetch("/api/assistant/history", { method: "DELETE" });
      setMessages([]);
    } catch (err) {
      setError(err.message || "Failed to clear history.");
    }
  }

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-600 dark:text-teal-300 font-bold text-sm">
            AI
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              HomePilot Assistant
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-300">
                Grounding Active
              </span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Conversational operational AI grounded in your household telemetry and agent traces.
            </p>
          </div>
        </div>

        <button
          onClick={handleClearHistory}
          disabled={messages.length === 0}
          className="text-xs text-slate-400 hover:text-red-500 disabled:opacity-30 transition px-2 py-1"
        >
          Clear History
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-950/50 border border-red-700/60 p-3 text-xs text-red-300 shrink-0">
          {error}
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        {loadingHistory ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-400">
            Loading assistant conversation...
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
            <div className="h-12 w-12 rounded-2xl bg-teal-500/10 text-teal-600 dark:text-teal-400 flex items-center justify-center">
              <MessageSquare className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
                Ask HomePilot About Your Household
              </h3>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Your assistant queries deterministic consumption models, appliance health, and monitoring issues directly.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-2 max-w-lg w-full pt-2">
              {samplePrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => { setInput(prompt); }}
                  className="p-3 text-left rounded-xl bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 transition"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => {
            const isUser = m.role === "user";
            return (
              <div
                key={m.id}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl p-4 text-xs leading-relaxed space-y-2 ${
                    isUser
                      ? "bg-teal-600 text-white rounded-br-xs"
                      : "bg-slate-100 dark:bg-slate-950 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800 rounded-bl-xs"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>

                  {/* If assistant attached an investigation run */}
                  {m.metadata?.run && onInspectRun && (
                    <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
                      <button
                        onClick={() => onInspectRun(m.metadata.run)}
                        className="text-[11px] font-bold text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1.5"
                      >
                        <Cpu className="w-3.5 h-3.5" />
                        <span>Inspect Linked Agent Run (#{m.metadata.run.id}) →</span>
                      </button>
                    </div>
                  )}

                  <span className={`block text-[9px] ${isUser ? "text-teal-200" : "text-slate-400"}`}>
                    {m.created_at?.slice(11, 16)}
                  </span>
                </div>
              </div>
            );
          })
        )}

        {sending && (
          <div className="flex justify-start">
            <div className="p-4 rounded-2xl bg-slate-100 dark:bg-slate-950 text-slate-500 text-xs border border-slate-200 dark:border-slate-800 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-teal-500 animate-ping" />
              <span>HomePilot is querying household data...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <form
        onSubmit={handleSend}
        className="p-3 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm shrink-0 space-y-2"
      >
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about electricity, leaks, appliances, or low supplies..."
            className="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-4 py-2.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-teal-400"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs disabled:opacity-40 transition"
          >
            Send
          </button>
        </div>

        <div className="flex items-center justify-between text-[11px] px-1 text-slate-500">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={triggerInvestigation}
              onChange={(e) => setTriggerInvestigation(e.target.checked)}
              className="rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
            />
            <span>Trigger LangGraph supervisor investigation if needed</span>
          </label>
          <span>Powered by HomePilot AI Provider Failover</span>
        </div>
      </form>
    </div>
  );
}
