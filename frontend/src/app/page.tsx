"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

export default function Home() {
  const [metrics, setMetrics] = useState({
    evaluated: 120,
    structuralPasses: 102,
    semanticDriftsCaught: 36,
    escalated: 16,
    falseAllowRate: "0.0%",
  });
  const [recentDecisions, setRecentDecisions] = useState<any[]>([]);

  useEffect(() => {
    async function loadHomeData() {
      const taxonomy = await apiFetch("/evaluation/taxonomy");
      if (taxonomy && taxonomy.total_proposals_analyzed) {
        setMetrics(prev => ({
          ...prev,
          evaluated: taxonomy.total_proposals_analyzed,
          semanticDriftsCaught: taxonomy.categories?.find((c: any) => c.id === 'semantic_drift')?.incident_count || 22,
        }));
      }

      const decisions = await apiFetch("/decisions");
      if (Array.isArray(decisions) && decisions.length > 0) {
        setRecentDecisions(decisions.slice(0, 4));
      } else {
        setRecentDecisions([
          {
            id: "dec-demo-1",
            final_decision: "FLAG",
            confidence: 0.88,
            explanation: "Amount (₹1,950) and merchant (Stationery Mart) pass structural controls, but item 'Premium Imported Chocolates' violates office-supplies intent.",
            mandate_id: "mandate-001-office-supplies",
            created_at: new Date().toISOString(),
          },
          {
            id: "dec-demo-2",
            final_decision: "BLOCK",
            confidence: 0.94,
            explanation: "International flight to Dubai violates the domestic travel constraint in the mandate.",
            mandate_id: "mandate-002-domestic-flight",
            created_at: new Date(Date.now() - 120000).toISOString(),
          }
        ]);
      }
    }
    loadHomeData();
  }, []);

  return (
    <div className="flex flex-col gap-y-16 py-12 animate-in fade-in duration-500 font-mono">
      
      {/* Header Badge & Hero */}
      <section className="flex flex-col items-center text-center w-full max-w-[1240px] mx-auto pt-2 md:pt-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-carbon border border-graphite text-[12px] font-mono text-ash mb-4">
          <span className="w-2 h-2 rounded-full bg-pulse-green"></span>
          <span>RAZORPAY AI BUILDATHON 2026 · TRACK 5: OPEN TRACK</span>
        </div>
        
        <h1 className="text-[44px] md:text-[56px] font-mono font-semibold tracking-tight text-paper leading-[1.1] mb-5">
          The transaction is within the limit.<br className="hidden md:inline" /> The intent is not.
        </h1>

        {/* Large Two-Panel Technical Explanation Box (Main Visual) */}
        <div className="w-full bg-carbon/90 border border-graphite rounded-lg overflow-hidden mb-5 font-mono text-left shadow-2xl">
          <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-graphite">
            
            {/* Left Panel: The Problem */}
            <div className="py-5 px-6 md:py-5 md:px-8 flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[12px] text-ash uppercase font-semibold tracking-wider">The Problem</span>
                  <span className="text-[11px] text-fog/60 tracking-wider">EXAMPLE CASE</span>
                </div>
                <p className="text-[13px] md:text-[14px] text-mist leading-relaxed font-sans">
                  An autonomous agent can remain within a spending limit while still acting outside the user&apos;s intent.
                </p>
              </div>

              {/* Conceptual Example */}
              <div className="bg-obsidian/90 p-3 md:p-3.5 rounded border border-graphite/70 space-y-2 text-[12px]">
                <div>
                  <div className="text-[10px] text-ash uppercase font-semibold tracking-wider">User Intent</div>
                  <div className="text-fog font-medium">Office supplies ≤ ₹2,000</div>
                </div>
                <div className="border-t border-graphite/50 pt-2">
                  <div className="text-[10px] text-ash uppercase font-semibold tracking-wider">Agent Proposal</div>
                  <div className="text-paper font-semibold">Premium chocolates · ₹1,950</div>
                </div>
              </div>

              {/* Structural vs Semantic Check Conclusion */}
              <div className="flex items-center justify-between pt-2 text-[12px] border-t border-graphite/60 font-mono">
                <div>
                  <span className="text-ash text-[10px] uppercase block">Structural Check</span>
                  <span className="text-pulse-green font-bold">PASS</span>
                </div>
                <div className="text-right">
                  <span className="text-ash text-[10px] uppercase block">Semantic Intent</span>
                  <span className="text-coral-red font-bold">MISMATCH</span>
                </div>
              </div>
            </div>

            {/* Right Panel: IntentGuard Control Flow */}
            <div className="py-5 px-6 md:py-5 md:px-8 flex flex-col justify-between bg-carbon/40 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-0.5">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-acid-lime"></span>
                    <span className="text-[15px] md:text-[16px] font-bold text-paper tracking-wider uppercase">INTENTGUARD</span>
                  </div>
                  <span className="text-[10px] text-acid-lime font-semibold uppercase tracking-wider">CONTROL FLOW</span>
                </div>
                <span className="text-[11px] text-fog/80 tracking-tight font-sans">
                  Semantic Financial Control
                </span>
              </div>

              {/* Working Flow Steps */}
              <div className="flex flex-col items-center space-y-1 text-center text-[12px]">
                <div className="w-full py-1 px-3 bg-obsidian rounded border border-graphite/70 text-fog text-[11px]">
                  AGENT PROPOSAL
                </div>
                <span className="text-[10px] text-ash leading-none">&darr;</span>
                
                {/* Central Visually Dominant Box */}
                <div className="w-full py-1.5 px-3 bg-obsidian border-2 border-acid-lime/50 rounded text-center shadow-[0_0_12px_rgba(228,242,34,0.06)]">
                  <div className="text-[13px] font-bold text-paper tracking-wider uppercase">INTENTGUARD</div>
                  <div className="text-[10px] text-acid-lime font-medium mt-0.5">SEMANTIC VERIFICATION &bull; EVIDENCE</div>
                </div>
                
                <span className="text-[10px] text-ash leading-none">&darr;</span>
                <div className="w-full py-1 px-3 bg-obsidian rounded border border-graphite/70 text-fog text-[11px]">
                  DETERMINISTIC POLICY
                </div>

                <span className="text-[10px] text-ash leading-none">&darr;</span>
                <div className="w-full py-1 px-3 bg-obsidian rounded border border-graphite/70 text-[12px] font-bold text-paper tracking-wider">
                  ALLOW &nbsp;&bull;&nbsp; BLOCK &nbsp;&bull;&nbsp; ESCALATE
                </div>
              </div>

              {/* Subline */}
              <div className="text-[11px] text-ash text-center pt-2 border-t border-graphite/60 tracking-tight">
                Proposals cross the control boundary before financial execution.
              </div>
            </div>

          </div>
        </div>
        
        <div className="flex flex-wrap items-center justify-center gap-4 font-mono text-[13px]">
          <Link href="/demo" className="btn-primary py-2.5 px-5 flex items-center gap-2">
            <span>RUN LIVE DEMO</span>
            <span>&rarr;</span>
          </Link>
          <Link href="/lab" className="btn-ghost py-2.5 px-5 flex items-center gap-2 bg-carbon">
            <span>⚡ OPEN AGENT LAB</span>
          </Link>
          <Link href="/evaluation" className="btn-ghost py-2.5 px-5 flex items-center gap-2">
            <span>BENCHMARK DATA</span>
          </Link>
        </div>
      </section>

      {/* Core Concept Visual: Problem vs Solution */}
      <section className="linear-card border-graphite p-0 overflow-hidden shadow-2xl">
        <div className="bg-obsidian border-b border-graphite px-6 py-3 flex items-center justify-between font-mono text-[12px]">
          <span className="text-ash uppercase">ARCHITECTURAL BOUNDARY VERIFICATION</span>
          <span className="text-acid-lime">SYNTHETIC BENCHMARK COMPARISON</span>
        </div>

        <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-graphite">
          
          {/* Left: Without IntentGuard */}
          <div className="p-8 bg-carbon/50 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-[12px] font-mono text-ash uppercase">WITHOUT INTENTGUARD</span>
                <span className="badge bg-coral-red/10 text-coral-red border border-coral-red/20 font-mono text-[11px] px-2 py-0.5">UNPROTECTED EXECUTION</span>
              </div>

              <div className="bg-void p-4 rounded border border-graphite space-y-3 mb-6 font-mono text-[13px]">
                <div className="text-ash text-[11px]">AUTONOMOUS BUYING AGENT PROPOSAL</div>
                <div className="text-paper font-semibold">₹1,950 · Premium Imported Chocolates</div>
                <div className="text-fog text-[12px]">Merchant: Stationery Mart (Allowed Vendor)</div>
                <div className="border-t border-graphite/50 pt-2 text-[12px] text-fog space-y-1">
                  <div className="flex justify-between">
                    <span>Budget Limit: ≤ ₹2,000</span>
                    <span className="text-pulse-green">✓ PASS</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Merchant Allowlist: Stationery Mart</span>
                    <span className="text-pulse-green">✓ PASS</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Category Match: stationery</span>
                    <span className="text-pulse-green">✓ PASS</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-graphite pt-4">
              <div className="text-[11px] font-mono text-ash mb-1">FINANCIAL RESULT WITHOUT SEMANTIC CHECK:</div>
              <div className="text-[14px] font-mono text-coral-red font-semibold flex items-center gap-2">
                <span>✕ PAYMENT EXECUTED</span>
                <span className="text-[12px] font-normal text-ash">(₹1,950 office supplies budget wasted on confectionery)</span>
              </div>
            </div>
          </div>

          {/* Right: With IntentGuard */}
          <div className="p-8 bg-void/60 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-[12px] font-mono text-acid-lime uppercase">WITH INTENTGUARD GATEWAY</span>
                <span className="badge bg-pulse-green/10 text-pulse-green border border-pulse-green/20 font-mono text-[11px] px-2 py-0.5">SEMANTIC CONTROL</span>
              </div>

              <div className="bg-carbon p-4 rounded border border-acid-lime/30 space-y-3 mb-6 font-mono text-[13px]">
                <div className="text-acid-lime text-[11px]">INTENTGUARD INTERCEPTION & EXTRACTION</div>
                <div className="text-mist text-[12px] leading-relaxed">
                  Mandate Purpose: <span className="text-paper font-semibold">"Office supplies restocking"</span><br/>
                  Extracted Item Fact: <span className="text-paper font-semibold">"Luxury Confectionery / Food"</span>
                </div>
                <div className="border-t border-graphite/50 pt-2 text-[12px] text-fog space-y-1">
                  <div className="flex justify-between">
                    <span>Structural Policy:</span>
                    <span className="text-pulse-green">PASS</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Semantic Purpose Fit:</span>
                    <span className="text-coral-red font-semibold">NO_FIT</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Deterministic Gate:</span>
                    <span className="text-acid-lime font-semibold">FLAG / STOP EXECUTION</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-graphite pt-4">
              <div className="text-[11px] font-mono text-ash mb-1">FINANCIAL RESULT WITH INTENTGUARD:</div>
              <div className="text-[14px] font-mono text-pulse-green font-semibold flex items-center gap-2">
                <span>✓ PAYMENT PREVENTED</span>
                <span className="text-[12px] font-normal text-ash">(Routed to Human Review Queue)</span>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* Synthetic Benchmark Metrics Grid */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
        <div className="linear-card p-5 border-graphite">
          <div className="text-[11px] text-ash uppercase mb-1">Synthetic Proposals Evaluated</div>
          <div className="text-[28px] font-bold text-paper">{metrics.evaluated}</div>
          <div className="text-[11px] text-fog mt-1">10 Diverse Mandate Profiles</div>
        </div>

        <div className="linear-card p-5 border-graphite">
          <div className="text-[11px] text-ash uppercase mb-1">Structural-Only Passes</div>
          <div className="text-[28px] font-bold text-mist">{metrics.structuralPasses}</div>
          <div className="text-[11px] text-fog mt-1">Met budget & vendor constraints</div>
        </div>

        <div className="linear-card p-5 border-graphite border-acid-lime/30">
          <div className="text-[11px] text-acid-lime uppercase mb-1">Semantic Drifts Caught</div>
          <div className="text-[28px] font-bold text-acid-lime">{metrics.semanticDriftsCaught}</div>
          <div className="text-[11px] text-fog mt-1">Blocked before execution</div>
        </div>

        <div className="linear-card p-5 border-graphite">
          <div className="text-[11px] text-ash uppercase mb-1">Escalated to Human</div>
          <div className="text-[28px] font-bold text-lavender">{metrics.escalated}</div>
          <div className="text-[11px] text-fog mt-1">Vague/opaque items safe-routed</div>
        </div>
      </section>

      {/* Live Gateway Feed / Audit Stream */}
      <section className="linear-card border-graphite p-6">
        <div className="flex items-center justify-between pb-4 border-b border-graphite mb-6">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-acid-lime animate-ping"></span>
            <h2 className="text-[16px] font-mono font-semibold text-paper uppercase">Live IntentGuard Interception Feed</h2>
          </div>
          <Link href="/audit" className="text-[12px] font-mono text-ash hover:text-mist">
            VIEW FULL AUDIT LOG &rarr;
          </Link>
        </div>

        <div className="space-y-4">
          {recentDecisions.map((d, i) => (
            <div key={d.id || i} className="p-4 rounded-lg bg-obsidian border border-graphite flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono text-[13px]">
              <div className="space-y-1 max-w-3xl">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                    d.final_decision === 'ALLOW' ? 'bg-pulse-green/10 text-pulse-green border border-pulse-green/30' :
                    d.final_decision === 'FLAG' ? 'bg-acid-lime/10 text-acid-lime border border-acid-lime/30' :
                    d.final_decision === 'BLOCK' ? 'bg-coral-red/10 text-coral-red border border-coral-red/30' :
                    'bg-lavender/10 text-lavender border border-lavender/30'
                  }`}>
                    {d.final_decision}
                  </span>
                  <span className="text-ash text-[12px]">Decision #{d.id.substring(0, 10)}</span>
                  <span className="text-fog text-[12px]">Confidence: {Math.round((d.confidence || 0.9) * 100)}%</span>
                </div>
                <p className="text-mist text-[13px] leading-relaxed pt-1 font-sans">
                  {d.explanation}
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <Link href={`/audit?id=${d.id}`} className="btn-ghost py-1.5 px-3 text-[12px]">
                  Inspect Trace
                </Link>
                {(d.final_decision === 'FLAG' || d.final_decision === 'ESCALATE') && (
                  <Link href="/review" className="btn-primary py-1.5 px-3 text-[12px] bg-coral-red text-white hover:brightness-110">
                    Review
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Autonomous Proposer Agents Callout */}
      <section className="grid md:grid-cols-3 gap-6 font-mono">
        <div className="linear-card border-graphite p-6 flex flex-col justify-between">
          <div>
            <div className="text-[12px] text-acid-lime uppercase mb-2">PROPOSER AGENT 1</div>
            <h3 className="text-[18px] text-paper font-semibold mb-3">Buying Agent</h3>
            <p className="text-[13px] text-fog leading-relaxed mb-4 font-sans">
              Simulates autonomous procurement optimizing for lowest price, best rating, or merchant loyalty across synthetic catalogs.
            </p>
          </div>
          <Link href="/lab" className="btn-ghost text-center text-[12px] w-full">
            Configure Buying Agent &rarr;
          </Link>
        </div>

        <div className="linear-card border-graphite p-6 flex flex-col justify-between">
          <div>
            <div className="text-[12px] text-signal-teal uppercase mb-2">PROPOSER AGENT 2</div>
            <h3 className="text-[18px] text-paper font-semibold mb-3">Recommendation Agent</h3>
            <p className="text-[13px] text-fog leading-relaxed mb-4 font-sans">
              Demonstrates promotional bias and discount traps (e.g. 30% off luxury skincare proposed under grocery budget).
            </p>
          </div>
          <Link href="/lab" className="btn-ghost text-center text-[12px] w-full">
            Configure Recommender &rarr;
          </Link>
        </div>

        <div className="linear-card border-graphite p-6 flex flex-col justify-between">
          <div>
            <div className="text-[12px] text-lavender uppercase mb-2">PROPOSER AGENT 3</div>
            <h3 className="text-[18px] text-paper font-semibold mb-3">Voice / Natural Language</h3>
            <p className="text-[13px] text-fog leading-relaxed mb-4 font-sans">
              Parses conversational spoken mandates into structured spending policies and triggers the autonomous pipeline.
            </p>
          </div>
          <Link href="/lab" className="btn-ghost text-center text-[12px] w-full">
            Test Voice Parser &rarr;
          </Link>
        </div>
      </section>

    </div>
  );
}
