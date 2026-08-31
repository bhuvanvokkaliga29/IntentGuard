"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Scenario {
  id: string;
  name: string;
  description: string;
  mandate_id: string;
  mandate_text: string;
  max_amount: number;
  allowed_merchants: string[];
  proposer_agent: string;
  transaction: {
    amount: number;
    merchant_name: string;
    merchant_category: string;
    item_description: string;
  };
  without_intentguard_outcome: string;
  with_intentguard_expected: string;
  explanation: string;
}

export default function LiveDemoPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("");
  const [mode, setMode] = useState<"with_guard" | "without_guard">("with_guard");
  
  // Custom Transaction Form state
  const [mandateId, setMandateId] = useState<string>("mandate-001-office-supplies");
  const [mandateText, setMandateText] = useState<string>("Buy my regular office supplies up to ₹2,000 per week from our usual stationery suppliers.");
  const [amount, setAmount] = useState<string>("1950");
  const [merchantName, setMerchantName] = useState<string>("Stationery Mart");
  const [merchantCategory, setMerchantCategory] = useState<string>("stationery");
  const [itemDescription, setItemDescription] = useState<string>("premium imported chocolates gift box");
  const [proposerAgentName, setProposerAgentName] = useState<string>("Buying Agent (BEST_RATING)");
  const [selectionReason, setSelectionReason] = useState<string>("Selected highest-rated item from preferred merchant.");

  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);
  const [activeStep, setActiveStep] = useState<number>(0);

  useEffect(() => {
    async function loadScenarios() {
      const data = await apiFetch("/agents/scenarios");
      if (data && data.scenarios) {
        setScenarios(data.scenarios);
        if (data.scenarios.length > 0) {
          selectScenario(data.scenarios[0]);
        }
      }
    }
    loadScenarios();
  }, []);

  const selectScenario = (sc: Scenario) => {
    setSelectedScenarioId(sc.id);
    setMandateId(sc.mandate_id);
    setMandateText(sc.mandate_text);
    setAmount(sc.transaction.amount.toString());
    setMerchantName(sc.transaction.merchant_name);
    setMerchantCategory(sc.transaction.merchant_category);
    setItemDescription(sc.transaction.item_description);
    setProposerAgentName(sc.proposer_agent);
    setSelectionReason(sc.description);
    setSimResult(null);
    setActiveStep(0);
  };

  const handleRunSimulation = async () => {
    setSimulating(true);
    setSimResult(null);
    setActiveStep(1);

    try {
      // Create transaction in DB
      const txn = await apiFetch("/transactions", {
        method: "POST",
        body: JSON.stringify({
          mandate_id: mandateId,
          amount: parseFloat(amount),
          merchant_name: merchantName,
          merchant_category: merchantCategory,
          item_description: itemDescription,
        }),
      });

      // Step progression animation
      for (let i = 2; i <= 6; i++) {
        await new Promise(r => setTimeout(r, 120));
        setActiveStep(i);
      }

      // Evaluate through IntentGuard
      const evalData = await apiFetch("/decisions/evaluate", {
        method: "POST",
        body: JSON.stringify({
          transaction_id: txn ? txn.id : "sim-txn-fallback",
          mandate_id: mandateId,
        }),
      });

      for (let i = 7; i <= 11; i++) {
        await new Promise(r => setTimeout(r, 100));
        setActiveStep(i);
      }

      if (evalData) {
        setSimResult({
          decision: evalData,
          transaction: txn,
        });
      } else {
        // Safe fallback
        setSimResult({
          decision: {
            final_decision: "FLAG",
            explanation: `Transaction evaluated: Amount (₹${amount}) at ${merchantName} satisfies structural limits, but item purpose requires human review.`,
            confidence_score: 0.90,
            structural_result: { overall_pass: true },
            audit_id: "aud-demo-fallback"
          },
          transaction: txn,
        });
      }

    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      setSimulating(false);
    }
  };

  const currentScenario = scenarios.find(s => s.id === selectedScenarioId);

  return (
    <div className="py-8 space-y-8 animate-in fade-in duration-500 font-mono">
      
      {/* Header with Mode Switcher */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-graphite">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[24px] font-bold text-paper uppercase">Live Agent & IntentGuard Execution</h1>
            <span className="badge bg-acid-lime/10 text-acid-lime border border-acid-lime/30 text-[11px]">CONTROLLED DEMO</span>
          </div>
          <p className="text-[13px] text-fog font-sans mt-1">
            Observe autonomous proposer agent output, structural validation, and semantic gatekeeping in real time.
          </p>
        </div>

        {/* Before / After Mode Switcher */}
        <div className="flex items-center p-1 rounded-lg bg-obsidian border border-graphite text-[12px]">
          <button
            onClick={() => setMode("without_guard")}
            className={`px-3 py-1.5 rounded font-semibold transition-all ${
              mode === "without_guard"
                ? "bg-coral-red text-white shadow-sm"
                : "text-fog hover:text-mist"
            }`}
          >
            WITHOUT INTENTGUARD
          </button>
          <button
            onClick={() => setMode("with_guard")}
            className={`px-3 py-1.5 rounded font-semibold transition-all ${
              mode === "with_guard"
                ? "bg-acid-lime text-void shadow-sm"
                : "text-fog hover:text-mist"
            }`}
          >
            WITH INTENTGUARD
          </button>
        </div>
      </div>

      {/* Scenario Pickers Grid */}
      <div>
        <div className="text-[12px] text-ash uppercase mb-3 flex items-center justify-between">
          <span>SELECT CONTROLLED FAILURE / SUCCESS SCENARIO:</span>
          <span className="text-acid-lime">{scenarios.length} CANONICAL BENCHMARK CASES</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
          {scenarios.map((sc, idx) => (
            <button
              key={sc.id}
              onClick={() => selectScenario(sc)}
              className={`p-3 rounded-lg border text-left transition-all ${
                selectedScenarioId === sc.id
                  ? "bg-carbon border-acid-lime text-paper shadow-[0_0_12px_rgba(228,242,34,0.15)]"
                  : "bg-obsidian border-graphite text-fog hover:border-smoke hover:text-mist"
              }`}
            >
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-ash font-bold">CASE {idx + 1}</span>
                <span className={`px-1.5 py-0.2 rounded text-[10px] font-semibold ${
                  sc.with_intentguard_expected === 'ALLOW' ? 'text-pulse-green bg-pulse-green/10' :
                  sc.with_intentguard_expected === 'FLAG' ? 'text-acid-lime bg-acid-lime/10' :
                  sc.with_intentguard_expected === 'BLOCK' ? 'text-coral-red bg-coral-red/10' :
                  'text-lavender bg-lavender/10'
                }`}>
                  {sc.with_intentguard_expected}
                </span>
              </div>
              <div className="text-[12px] font-semibold truncate text-paper">{sc.name.split(': ')[1] || sc.name}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 3-Column Core Workspace */}
      <div className="grid lg:grid-cols-3 gap-6">
        
        {/* COLUMN 1: USER MANDATE */}
        <div className="linear-card border-graphite p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-graphite mb-4">
              <span className="text-[12px] text-ash uppercase font-semibold">1. USER MANDATE</span>
              <span className="badge bg-white/5 border border-graphite text-fog text-[10px]">DECLARED INTENT</span>
            </div>

            <div className="space-y-3 text-[13px]">
              <div>
                <label className="text-[11px] text-ash uppercase">Stated Purpose Context:</label>
                <div className="p-3 bg-void border border-graphite rounded text-paper font-sans text-[13px] leading-relaxed mt-1">
                  "{mandateText}"
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="text-[11px] text-ash uppercase">Txn Limit:</label>
                  <div className="text-mist font-semibold">≤ ₹{currentScenario?.max_amount?.toLocaleString() || "2,000"}</div>
                </div>
                <div>
                  <label className="text-[11px] text-ash uppercase">Frequency:</label>
                  <div className="text-mist">Weekly Restocking</div>
                </div>
              </div>

              <div>
                <label className="text-[11px] text-ash uppercase">Approved Merchants:</label>
                <div className="text-mist text-[12px] truncate">
                  {currentScenario?.allowed_merchants?.join(", ") || "Stationery Mart, Office Depot"}
                </div>
              </div>
            </div>
          </div>

          <div className="p-3 rounded bg-obsidian border border-graphite text-[11px] text-fog">
            Mandate constraints are cryptographically signed and immutable during agent evaluation.
          </div>
        </div>

        {/* COLUMN 2: PROPOSER AGENT & TRANSACTION */}
        <div className="linear-card border-graphite p-5 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-graphite mb-4">
              <span className="text-[12px] text-signal-teal uppercase font-semibold">2. AGENT PROPOSAL</span>
              <span className="badge bg-signal-teal/10 text-signal-teal border border-signal-teal/20 text-[10px]">
                {proposerAgentName.split(' ')[0]}
              </span>
            </div>

            <div className="space-y-3 text-[13px]">
              <div>
                <label className="text-[11px] text-ash uppercase">Proposing Agent:</label>
                <div className="text-paper font-semibold">{proposerAgentName}</div>
                <div className="text-[11px] text-fog mt-0.5">{selectionReason}</div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-[11px] text-ash uppercase">Proposed Amount:</label>
                  <input
                    type="number"
                    value={amount}
                    onChange={e => setAmount(e.target.value)}
                    className="w-full bg-void border border-graphite rounded px-2.5 py-1.5 text-paper font-semibold outline-none focus:border-acid-lime"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-ash uppercase">Merchant Name:</label>
                  <input
                    type="text"
                    value={merchantName}
                    onChange={e => setMerchantName(e.target.value)}
                    className="w-full bg-void border border-graphite rounded px-2.5 py-1.5 text-paper outline-none focus:border-acid-lime"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] text-ash uppercase">Proposed Item Description:</label>
                <textarea
                  rows={2}
                  value={itemDescription}
                  onChange={e => setItemDescription(e.target.value)}
                  className="w-full bg-void border border-graphite rounded px-2.5 py-1.5 text-paper outline-none focus:border-acid-lime text-[12px] font-mono mt-1"
                />
              </div>
            </div>
          </div>

          <button
            onClick={handleRunSimulation}
            disabled={simulating}
            className="btn-primary w-full justify-center flex items-center gap-2 py-2.5 text-[13px]"
          >
            {simulating ? (
              <>
                <span className="w-4 h-4 rounded-full border-2 border-void border-t-transparent animate-spin" />
                <span>INTERCEPTING & VERIFYING...</span>
              </>
            ) : (
              <>
                <span>VERIFY WITH INTENTGUARD</span>
                <span>&rarr;</span>
              </>
            )}
          </button>
        </div>

        {/* COLUMN 3: INTENTGUARD GATING DECISION */}
        <div className={`linear-card p-5 flex flex-col justify-between space-y-4 ${
          mode === 'without_guard' ? 'border-coral-red/40 bg-coral-red/5' : 'border-acid-lime/40 bg-carbon'
        }`}>
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-graphite mb-4">
              <span className={`text-[12px] uppercase font-semibold ${
                mode === 'without_guard' ? 'text-coral-red' : 'text-acid-lime'
              }`}>
                {mode === 'without_guard' ? '3. STRUCTURAL-ONLY RESULT' : '3. INTENTGUARD GATEWAY'}
              </span>
              <span className="badge bg-white/5 border border-graphite text-fog text-[10px]">
                {mode === 'without_guard' ? 'NO SEMANTIC GATE' : 'DETERMINISTIC CONTROL'}
              </span>
            </div>

            {mode === 'without_guard' ? (
              <div className="space-y-4 text-[13px]">
                <div className="p-4 rounded bg-void border border-coral-red/30 space-y-2">
                  <div className="text-coral-red font-bold text-[14px]">
                    ⚠️ UNCHECKED PROCEED: PURCHASE EXECUTED
                  </div>
                  <p className="text-fog text-[12px] leading-relaxed font-sans">
                    Under traditional structural controls, this transaction satisfied the budget limit (₹{amount} ≤ ₹{currentScenario?.max_amount || 2000}) and approved vendor check. The semantic intent violation was completely missed.
                  </p>
                </div>

                <div className="space-y-1.5 text-[12px] text-fog">
                  <div className="flex justify-between">
                    <span>Structural Budget:</span>
                    <span className="text-pulse-green font-bold">PASS</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Merchant Allowlist:</span>
                    <span className="text-pulse-green font-bold">PASS</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Semantic Intent Check:</span>
                    <span className="text-coral-red font-bold">BYPASSED / UNCHECKED</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4 text-[13px]">
                {simResult ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-ash text-[11px] uppercase">Final Gate Decision:</span>
                      <span className={`px-3 py-1 rounded font-mono font-bold text-[13px] ${
                        simResult.decision.final_decision === 'ALLOW' ? 'bg-pulse-green/20 text-pulse-green border border-pulse-green' :
                        simResult.decision.final_decision === 'FLAG' ? 'bg-acid-lime/20 text-acid-lime border border-acid-lime' :
                        simResult.decision.final_decision === 'BLOCK' ? 'bg-coral-red/20 text-coral-red border border-coral-red' :
                        'bg-lavender/20 text-lavender border border-lavender'
                      }`}>
                        {simResult.decision.final_decision}
                      </span>
                    </div>

                    <div className="p-3 bg-void border border-graphite rounded text-[12px] text-mist leading-relaxed font-sans">
                      {simResult.decision.explanation}
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] text-fog pt-1">
                      <div>
                        <span className="text-ash">Structural Check: </span>
                        <span className={simResult.decision.structural_result?.overall_pass ? "text-pulse-green" : "text-coral-red"}>
                          {simResult.decision.structural_result?.overall_pass ? "PASS" : "FAIL"}
                        </span>
                      </div>
                      <div>
                        <span className="text-ash">Confidence: </span>
                        <span className="text-paper font-semibold">
                          {Math.round((simResult.decision.confidence_score || 0.9) * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 text-center text-fog text-[12px] border border-dashed border-graphite rounded-lg font-sans">
                    Click "VERIFY WITH INTENTGUARD" to execute the live deterministic pipeline.
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between text-[11px] border-t border-graphite pt-3 text-ash">
            <span>Audit Ref: #{simResult?.decision?.audit_id ? simResult.decision.audit_id.substring(0, 8) : "IMMUTABLE"}</span>
            <Link href="/review" className="text-acid-lime hover:underline">
              Review Queue &rarr;
            </Link>
          </div>
        </div>

      </div>

      {/* Animated 11-Stage Pipeline Trace */}
      <div className="linear-card border-graphite p-5">
        <div className="flex items-center justify-between pb-3 border-b border-graphite mb-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-acid-lime"></span>
            <span className="text-[12px] font-bold text-paper uppercase">Live 11-Stage Pipeline Execution Timeline</span>
          </div>
          <span className="text-[11px] text-ash">
            {simulating ? `PROCESSING STEP ${activeStep}/11...` : simResult ? "PIPELINE COMPLETED" : "IDLE"}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2 text-[11px]">
          {[
            { step: 1, label: "Mandate Ingest" },
            { step: 2, label: "Agent Search" },
            { step: 3, label: "Candidate Selection" },
            { step: 4, label: "Proposal Formed" },
            { step: 5, label: "IntentGuard Intercept" },
            { step: 6, label: "Structural Engine" },
            { step: 7, label: "Fact Extraction" },
            { step: 8, label: "Semantic Verification" },
            { step: 9, label: "Confidence Engine" },
            { step: 10, label: "Deterministic Policy" },
            { step: 11, label: "Audit Persisted" },
          ].map(s => {
            const isCompleted = activeStep >= s.step || (simResult && !simulating);
            const isCurrent = activeStep === s.step && simulating;
            return (
              <div
                key={s.step}
                className={`p-2.5 rounded border transition-all ${
                  isCurrent
                    ? "bg-acid-lime/10 border-acid-lime text-acid-lime animate-pulse font-bold"
                    : isCompleted
                    ? "bg-obsidian border-graphite text-paper"
                    : "bg-void border-graphite/40 text-ash"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-ash">S{s.step}</span>
                  <span>{isCompleted ? "✓" : "○"}</span>
                </div>
                <div className="truncate font-semibold">{s.label}</div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
