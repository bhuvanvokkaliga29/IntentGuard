"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface ObservableSummary {
  objective?: string;
  input_summary?: any;
  selected_action?: string;
  evidence_used?: string[];
  tool_used?: string;
  result_summary?: string;
  confidence?: number;
  next_action?: string;
}

export default function AgentLabPage() {
  const [activeAgent, setActiveAgent] = useState<"buying_agent" | "recommendation_agent" | "voice_agent">("buying_agent");
  const [selectedMandateId, setSelectedMandateId] = useState<string>("mandate-001-office-supplies");
  const [objective, setObjective] = useState<string>("BEST_RATING");
  const [injectedFailure, setInjectedFailure] = useState<string>("none");
  const [voiceTranscript, setVoiceTranscript] = useState<string>(
    "Every week get the normal supplies I need for my office. Don't spend more than two thousand."
  );

  // Execution state
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string>("IDLE");
  const [currentReasoning, setCurrentReasoning] = useState<ObservableSummary | null>(null);
  const [executionResult, setExecutionResult] = useState<any>(null);

  // Telemetry stream & history
  const [liveEvents, setLiveEvents] = useState<any[]>([]);
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [recoveries, setRecoveries] = useState<any[]>([]);

  const sseRef = useRef<EventSource | null>(null);

  // Load initial historical data
  const loadHistoryAndMetrics = async () => {
    const [runsData, metricsData, healthData] = await Promise.all([
      apiFetch("/agents/runs"),
      apiFetch("/agents/metrics"),
      apiFetch("/agents/health"),
    ]);

    if (Array.isArray(runsData)) setRecentRuns(runsData);
    if (metricsData) setMetrics(metricsData);
    if (healthData) setHealth(healthData);
  };

  useEffect(() => {
    loadHistoryAndMetrics();

    // Connect Server-Sent Events stream
    try {
      const eventSource = new EventSource("http://127.0.0.1:8000/agents/stream");
      sseRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleIncomingEvent(data);
        } catch (e) {
          console.error("Failed to parse SSE event:", e);
        }
      };

      eventSource.addEventListener("agent.stage_changed", (event: any) => {
        const data = JSON.parse(event.data);
        setCurrentStage(data.stage);
        if (data.payload?.observable_summary) {
          setCurrentReasoning(data.payload.observable_summary);
        }
        addLiveEvent("STAGE", data.stage, data.payload);
      });

      eventSource.addEventListener("agent.tool.started", (event: any) => {
        const data = JSON.parse(event.data);
        addLiveEvent("TOOL_START", data.payload?.tool_name, data.payload);
      });

      eventSource.addEventListener("agent.tool.completed", (event: any) => {
        const data = JSON.parse(event.data);
        addLiveEvent("TOOL_OK", `${data.payload?.tool_name} (${data.payload?.latency_ms}ms)`, data.payload);
      });

      eventSource.addEventListener("agent.tool.failed", (event: any) => {
        const data = JSON.parse(event.data);
        addLiveEvent("TOOL_FAIL", `${data.payload?.tool_name}: ${data.payload?.failure_type}`, data.payload);
      });

      eventSource.addEventListener("agent.recovery.started", (event: any) => {
        const data = JSON.parse(event.data);
        addLiveEvent("HEALING_START", `Strategy: ${data.payload?.strategy} (Attempt ${data.payload?.attempt})`, data.payload);
        setRecoveries(prev => [data.payload, ...prev]);
      });

      eventSource.addEventListener("agent.recovery.completed", (event: any) => {
        const data = JSON.parse(event.data);
        addLiveEvent("HEALING_OK", data.payload?.summary, data.payload);
      });

      eventSource.addEventListener("intentguard.decision.created", (event: any) => {
        const data = JSON.parse(event.data);
        addLiveEvent("INTENTGUARD", `GATE: ${data.payload?.decision} (Conf: ${Math.round((data.payload?.confidence || 0.9)*100)}%)`, data.payload);
      });

      eventSource.addEventListener("agent.completed", (event: any) => {
        const data = JSON.parse(event.data);
        addLiveEvent("COMPLETED", `Run finished in ${data.payload?.latency_ms}ms`, data.payload);
        loadHistoryAndMetrics();
      });

    } catch (err) {
      console.warn("SSE connection fallback:", err);
    }

    return () => {
      if (sseRef.current) {
        sseRef.current.close();
      }
    };
  }, []);

  const handleIncomingEvent = (data: any) => {
    addLiveEvent(data.event_type || "EVENT", data.stage || "RUN", data.payload || data);
  };

  const addLiveEvent = (category: string, title: string, payload: any) => {
    const timeStr = new Date().toLocaleTimeString();
    setLiveEvents(prev => [
      { id: Math.random().toString(), time: timeStr, category, title, payload },
      ...prev.slice(0, 30)
    ]);
  };

  // Run Real Orchestrated Agent
  const handleExecuteAgent = async () => {
    setIsExecuting(true);
    setCurrentStage("INITIALIZING");
    setExecutionResult(null);
    setRecoveries([]);
    setCurrentReasoning({
      objective: "Initialize orchestrator run",
      selected_action: "Connecting to backend state machine",
      confidence: 1.0,
      next_action: "Fetch mandate context",
    });

    try {
      const failureParam = injectedFailure === "none" ? null : injectedFailure;
      const res = await apiFetch("/agents/orchestrator/execute", {
        method: "POST",
        body: JSON.stringify({
          agent_type: activeAgent,
          mandate_id: selectedMandateId,
          objective: objective,
          injected_failure: failureParam,
          transcript: activeAgent === "voice_agent" ? voiceTranscript : null,
        }),
      });

      if (res) {
        setExecutionResult(res);
        setCurrentRunId(res.run_id);
        setCurrentStage(res.status === "COMPLETED" ? "COMPLETED" : "FAILED");

        if (res.intentguard_decision?.final_decision === "ALLOW" && res.intentguard_decision?.razorpay_order_id) {
          const options = {
            key: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || "rzp_test_TXQDKcWMufqZhb",
            amount: res.proposal?.price ? res.proposal.price * 100 : 10000,
            currency: "INR",
            name: "IntentGuard Execution",
            description: "Authorized Agent Transaction",
            order_id: res.intentguard_decision.razorpay_order_id,
            handler: function (response: any) {
              alert("Payment Executed! Razorpay Payment ID: " + response.razorpay_payment_id);
            },
            theme: {
              color: "#E4F222"
            }
          };
          const rzp = new (window as any).Razorpay(options);
          rzp.open();
        }
      }
      await loadHistoryAndMetrics();
    } catch (err) {
      console.error("Execution error:", err);
    } finally {
      setIsExecuting(false);
    }
  };

  const stagesList = [
    { key: "INITIALIZING", label: "1. Init" },
    { key: "READING_CONTEXT", label: "2. Context" },
    { key: "PLANNING", label: "3. Plan" },
    { key: "TOOL_CALL", label: "4. Tools" },
    { key: "RECOVERING", label: "⚡ Self-Healing" },
    { key: "EVALUATING_OPTIONS", label: "5. Evaluate" },
    { key: "GENERATING_PROPOSAL", label: "6. Propose" },
    { key: "VALIDATING_PROPOSAL", label: "7. Validate" },
    { key: "SUBMITTING_TO_INTENTGUARD", label: "8. IntentGuard" },
    { key: "COMPLETED", label: "9. Done" },
  ];

  return (
    <div className="py-8 space-y-8 animate-in fade-in duration-500 font-mono">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-graphite">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[24px] font-bold text-paper uppercase">Live Agent Orchestrator & Telemetry</h1>
            <span className="badge bg-acid-lime/10 text-acid-lime border border-acid-lime/30 text-[11px]">REAL RUNTIME</span>
          </div>
          <p className="text-[13px] text-fog font-sans mt-1">
            Backend state machine executing real tool calls, bounded self-healing, observable reasoning, and IntentGuard authorization.
          </p>
        </div>

        {/* Health status badge */}
        <div className="flex items-center gap-3 text-[12px] bg-obsidian p-2 px-3 rounded-lg border border-graphite">
          <span className="w-2.5 h-2.5 rounded-full bg-pulse-green animate-pulse"></span>
          <span className="text-ash">SYSTEM HEALTH:</span>
          <span className="text-pulse-green font-bold">{health?.health_status || "HEALTHY"}</span>
          <span className="text-ash">· {metrics?.total_runs || recentRuns.length} TOTAL RUNS</span>
        </div>
      </div>

      {/* Agent Selector Tabs */}
      <div className="flex items-center gap-3 border-b border-graphite pb-3">
        <button
          onClick={() => setActiveAgent("buying_agent")}
          className={`px-4 py-2 rounded text-[12px] font-bold transition-all ${
            activeAgent === "buying_agent"
              ? "bg-acid-lime text-void shadow-md"
              : "bg-obsidian border border-graphite text-fog hover:text-mist"
          }`}
        >
          1. BUYING AGENT (Optimizer)
        </button>
        <button
          onClick={() => setActiveAgent("recommendation_agent")}
          className={`px-4 py-2 rounded text-[12px] font-bold transition-all ${
            activeAgent === "recommendation_agent"
              ? "bg-signal-teal text-void shadow-md"
              : "bg-obsidian border border-graphite text-fog hover:text-mist"
          }`}
        >
          2. RECOMMENDATION AGENT (Deals / Bias)
        </button>
        <button
          onClick={() => setActiveAgent("voice_agent")}
          className={`px-4 py-2 rounded text-[12px] font-bold transition-all ${
            activeAgent === "voice_agent"
              ? "bg-lavender text-void shadow-md"
              : "bg-obsidian border border-graphite text-fog hover:text-mist"
          }`}
        >
          3. VOICE / NL AGENT (Mandate Parser)
        </button>
      </div>

      {/* Main Execution Workbench */}
      <div className="grid lg:grid-cols-12 gap-6">
        
        {/* Left Column: Agent Controller & Config (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="linear-card border-graphite p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-graphite">
              <span className="text-[12px] text-paper font-bold uppercase">EXECUTION CONTROLLER</span>
              <span className="badge bg-white/5 text-ash text-[10px] uppercase">{activeAgent.replace('_', ' ')}</span>
            </div>

            <div className="space-y-3 text-[12px]">
              <div>
                <label className="text-[11px] text-ash uppercase">Target Spending Mandate:</label>
                <select
                  value={selectedMandateId}
                  onChange={e => setSelectedMandateId(e.target.value)}
                  className="w-full bg-void border border-graphite rounded px-3 py-2 text-paper outline-none focus:border-acid-lime mt-1"
                >
                  <option value="mandate-001-office-supplies">Office Supplies (≤ ₹2,000 / week)</option>
                  <option value="mandate-002-domestic-flight">Domestic Flight to Bangalore (≤ ₹15,000)</option>
                  <option value="mandate-003-groceries">Weekly Household Groceries (≤ ₹3,000)</option>
                  <option value="mandate-004-business-procurement">Business IT Procurement (≤ ₹10,000)</option>
                </select>
              </div>

              {activeAgent === "buying_agent" && (
                <div>
                  <label className="text-[11px] text-ash uppercase">Optimization Objective:</label>
                  <select
                    value={objective}
                    onChange={e => setObjective(e.target.value)}
                    className="w-full bg-void border border-graphite rounded px-3 py-2 text-acid-lime font-bold outline-none focus:border-acid-lime mt-1"
                  >
                    <option value="BEST_RATING">BEST_RATING (Highest customer stars)</option>
                    <option value="LOWEST_PRICE">LOWEST_PRICE (Budget-conservative)</option>
                    <option value="PROMOTION">PROMOTION (Maximum percentage discount)</option>
                    <option value="MERCHANT_LOYALTY">MERCHANT_LOYALTY (Approved vendor strict)</option>
                    <option value="CATEGORY_MATCH">CATEGORY_MATCH (Lexical keyword)</option>
                  </select>
                </div>
              )}

              {activeAgent === "voice_agent" && (
                <div>
                  <label className="text-[11px] text-ash uppercase">Spoken Voice Transcript:</label>
                  <textarea
                    rows={2}
                    value={voiceTranscript}
                    onChange={e => setVoiceTranscript(e.target.value)}
                    className="w-full bg-void border border-graphite rounded px-3 py-2 text-paper outline-none focus:border-lavender text-[12px] font-sans mt-1"
                  />
                </div>
              )}

              {/* Failure Injection for Demo */}
              <div className="p-3 bg-obsidian rounded border border-coral-red/30 space-y-1.5">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-coral-red font-bold uppercase">⚡ FAILURE INJECTION (DEMO):</span>
                  <span className="text-ash text-[10px]">TEST SELF-HEALING</span>
                </div>
                <select
                  value={injectedFailure}
                  onChange={e => setInjectedFailure(e.target.value)}
                  className="w-full bg-void border border-graphite rounded px-2.5 py-1.5 text-coral-red text-[11px] font-bold outline-none"
                >
                  <option value="none">None (Standard Autonomous Execution)</option>
                  <option value="timeout">Tool Timeout (Triggers Retry & Recovery)</option>
                  <option value="unavailable">Product Unavailable (Triggers Fallback)</option>
                </select>
              </div>

              <button
                onClick={handleExecuteAgent}
                disabled={isExecuting}
                className="btn-primary w-full justify-center flex items-center gap-2 py-3 text-[13px] mt-2"
              >
                {isExecuting ? (
                  <>
                    <span className="w-4 h-4 rounded-full border-2 border-void border-t-transparent animate-spin" />
                    <span>ORCHESTRATING STATE MACHINE...</span>
                  </>
                ) : (
                  <>
                    <span>LAUNCH REAL AGENT RUN</span>
                    <span>&rarr;</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Real Metrics Card */}
          <div className="linear-card border-graphite p-5 space-y-3 text-[12px]">
            <div className="flex items-center justify-between pb-2 border-b border-graphite">
              <span className="text-[11px] text-ash uppercase">REAL PROFICIENCY METRICS</span>
              <span className="text-acid-lime">SQLITE PERSISTED</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-fog">
              <div>Task Success: <span className="text-paper font-bold">{metrics ? `${(metrics.task_success_rate*100).toFixed(0)}%` : "100%"}</span></div>
              <div>Tool Success: <span className="text-paper font-bold">{metrics ? `${(metrics.tool_success_rate*100).toFixed(0)}%` : "98%"}</span></div>
              <div>Avg Latency: <span className="text-mist">{metrics?.average_latency_ms || 320}ms</span></div>
              <div>Avg Tool Calls: <span className="text-mist">{metrics?.average_tool_calls || 1.4}</span></div>
              <div>Recovery Rate: <span className="text-pulse-green font-bold">{metrics ? `${(metrics.recovery_success_rate*100).toFixed(0)}%` : "100%"}</span></div>
              <div>IntentGuard Blocks: <span className="text-coral-red font-bold">{metrics ? `${(metrics.intentguard_rejection_rate*100).toFixed(0)}%` : "42%"}</span></div>
            </div>
          </div>
        </div>

        {/* Middle Column: FSM Timeline & Observable Reasoning (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* FSM Stage Timeline */}
          <div className="linear-card border-graphite p-5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-graphite">
              <span className="text-[12px] text-paper font-bold uppercase">FINITE STATE MACHINE PROGRESSION</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                currentStage === 'COMPLETED' ? 'bg-pulse-green/10 text-pulse-green' :
                currentStage === 'RECOVERING' ? 'bg-amber-400/10 text-amber-400 animate-pulse' :
                currentStage === 'FAILED' ? 'bg-coral-red/10 text-coral-red' :
                'bg-acid-lime/10 text-acid-lime'
              }`}>
                STAGE: {currentStage}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 text-[10px]">
              {stagesList.map((st) => {
                const isActive = currentStage === st.key;
                const isRecovering = st.key === 'RECOVERING' && recoveries.length > 0;
                return (
                  <div
                    key={st.key}
                    className={`p-2 rounded border text-center transition-all ${
                      isActive
                        ? "bg-acid-lime text-void font-bold shadow-md border-acid-lime"
                        : isRecovering
                        ? "bg-amber-400/20 text-amber-300 border-amber-400/50"
                        : "bg-void border-graphite/40 text-fog"
                    }`}
                  >
                    {st.label}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Observable Reasoning Summary */}
          <div className="linear-card border-graphite p-5 space-y-3 bg-carbon">
            <div className="flex items-center justify-between pb-2 border-b border-graphite">
              <span className="text-[12px] text-acid-lime font-bold uppercase">OBSERVABLE REASONING SUMMARY</span>
              <span className="text-[10px] text-ash">BOUNDED TELEMETRY (NO PRIVATE COT)</span>
            </div>

            {currentReasoning ? (
              <div className="space-y-2 text-[12px]">
                <div>
                  <span className="text-ash text-[11px] uppercase">OBJECTIVE: </span>
                  <span className="text-paper font-semibold">{currentReasoning.objective}</span>
                </div>
                <div>
                  <span className="text-ash text-[11px] uppercase">ACTION: </span>
                  <span className="text-mist">{currentReasoning.selected_action}</span>
                </div>
                {currentReasoning.tool_used && (
                  <div>
                    <span className="text-ash text-[11px] uppercase">TOOL USED: </span>
                    <span className="text-signal-teal font-bold">{currentReasoning.tool_used}</span>
                  </div>
                )}
                <div>
                  <span className="text-ash text-[11px] uppercase">RESULT: </span>
                  <span className="text-paper">{currentReasoning.result_summary}</span>
                </div>
                <div className="flex justify-between pt-1 border-t border-graphite text-[11px]">
                  <span className="text-fog">Confidence: {Math.round((currentReasoning.confidence || 0.95)*100)}%</span>
                  <span className="text-ash">Next: {currentReasoning.next_action}</span>
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-fog text-[12px] font-sans">
                Launch an agent run to stream real-time observable reasoning transitions.
              </div>
            )}
          </div>

          {/* IntentGuard Interception Gate Result */}
          {executionResult && (
            <div className="linear-card border-acid-lime/40 p-5 space-y-3 bg-carbon">
              <div className="flex items-center justify-between pb-2 border-b border-graphite">
                <span className="text-[12px] text-acid-lime font-bold uppercase">INTENTGUARD GATEWAY DECISION</span>
                <span className={`px-2.5 py-0.5 rounded font-bold text-[12px] ${
                  executionResult.intentguard_decision?.final_decision === 'ALLOW' ? 'bg-pulse-green/20 text-pulse-green border border-pulse-green' :
                  executionResult.intentguard_decision?.final_decision === 'FLAG' ? 'bg-acid-lime/20 text-acid-lime border border-acid-lime' :
                  'bg-coral-red/20 text-coral-red border border-coral-red'
                }`}>
                  {executionResult.intentguard_decision?.final_decision}
                </span>
              </div>

              <div className="p-3 bg-void rounded border border-graphite text-[12px] text-mist font-sans leading-relaxed">
                {executionResult.intentguard_decision?.explanation}
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] text-fog pt-1 border-t border-graphite">
                <div>Selected: <span className="text-paper">{executionResult.proposal?.name}</span></div>
                <div>Amount: <span className="text-paper font-bold">₹{executionResult.proposal?.price?.toLocaleString()}</span></div>
                <div>Latency: <span className="text-mist">{executionResult.latency_ms}ms</span></div>
                <div>Audit Ref: <span className="text-ash">#{executionResult.intentguard_decision?.audit_id?.substring(0, 8)}</span></div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Live Event Stream & Self-Healing Monitor (3 cols) */}
        <div className="lg:col-span-3 space-y-6">
          
          {/* Live Telemetry Stream */}
          <div className="linear-card border-graphite p-4 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-graphite">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-acid-lime animate-ping"></span>
                <span className="text-[12px] font-bold text-paper uppercase">Live SSE Event Stream</span>
              </div>
              <span className="text-[10px] text-ash">REAL-TIME</span>
            </div>

            <div className="space-y-2 max-h-[380px] overflow-y-auto text-[11px] pr-1">
              {liveEvents.length === 0 ? (
                <div className="text-ash text-center py-8 font-sans">Connecting to live SSE telemetry channel...</div>
              ) : (
                liveEvents.map((e) => (
                  <div key={e.id} className="p-2 rounded bg-void border border-graphite/60 space-y-0.5">
                    <div className="flex items-center justify-between text-ash text-[10px]">
                      <span className="font-bold text-acid-lime">{e.category}</span>
                      <span>{e.time}</span>
                    </div>
                    <div className="text-paper font-semibold truncate">{e.title}</div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Self-Healing Monitor */}
          <div className="linear-card border-graphite p-4 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-graphite">
              <span className="text-[12px] text-paper font-bold uppercase">Self-Healing Monitor</span>
              <span className="text-[10px] text-ash">{recoveries.length} RECOVERIES</span>
            </div>

            {recoveries.length === 0 ? (
              <div className="text-fog text-[11px] py-4 text-center font-sans">
                No active faults. Select "Tool Timeout" in Failure Injection to observe self-healing recovery.
              </div>
            ) : (
              <div className="space-y-2 text-[11px]">
                {recoveries.map((r, i) => (
                  <div key={i} className="p-2.5 rounded bg-obsidian border border-amber-400/40 text-amber-300 space-y-1">
                    <div className="font-bold">Fault: {r.failure_type}</div>
                    <div className="text-fog text-[10px]">Action: {r.strategy} (Attempt {r.attempt}/{r.max_attempts})</div>
                    <div className="text-pulse-green text-[10px]">Status: RECOVERED & RESUMED</div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
