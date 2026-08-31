"use client";

import { useState } from "react";
import Link from "next/link";

interface TraceNode {
  id: string;
  name: string;
  type: "input" | "proposer" | "gateway" | "structural" | "ai" | "deterministic" | "gate" | "audit";
  description: string;
  payload: any;
}

export default function TraceGraphPage() {
  const [selectedNodeId, setSelectedNodeId] = useState<string>("structural");

  const nodes: TraceNode[] = [
    {
      id: "mandate",
      name: "1. USER MANDATE",
      type: "input",
      description: "User declares spending policy with natural language purpose context, structural limits, and approved vendors.",
      payload: {
        mandate_id: "mandate-001-office-supplies",
        intent_text: "Buy my regular office supplies up to ₹2,000 per week from our usual stationery suppliers.",
        max_amount_per_txn: 2000.0,
        budget_cap: 8000.0,
        allowed_categories: ["office_supplies", "stationery", "writing_instruments", "paper_products"],
        allowed_merchants: ["Stationery Mart", "Office Depot India", "Pen Paper Store"],
        frequency: "weekly",
        exclusions: ["electronics", "furniture", "food", "beverages", "personal_items"],
        location_constraint: "domestic",
        purpose_context: "Routine restocking of office consumables — paper, pens, sticky notes."
      }
    },
    {
      id: "proposer",
      name: "2. PROPOSER AGENT",
      type: "proposer",
      description: "Autonomous purchasing system optimizes across synthetic merchant catalogs (e.g. optimizing for BEST_RATING).",
      payload: {
        agent_type: "buying_agent",
        optimization_objective: "BEST_RATING",
        catalog_items_scanned: 18,
        eligible_candidates: 12,
        selection_heuristic: "max(rating, -price)",
        selected_sku: "prod-stat-chocolates",
        selection_reason: "Selected highest rated product (4.95 stars) from approved merchant Stationery Mart."
      }
    },
    {
      id: "proposal",
      name: "3. TRANSACTION PROPOSAL",
      type: "input",
      description: "Structured transaction proposal emitted by proposer agent before any financial movement.",
      payload: {
        proposal_id: "prop-buy-8a91f0b2",
        mandate_id: "mandate-001-office-supplies",
        amount: 1950.0,
        currency: "INR",
        merchant_name: "Stationery Mart",
        merchant_category: "stationery",
        item_description: "premium imported chocolates gift box",
        created_at: "2026-08-30T18:30:00Z"
      }
    },
    {
      id: "gateway",
      name: "4. INTENTGUARD GATEWAY",
      type: "gateway",
      description: "Central security boundary that intercepts all agent proposals. Proposer agents cannot bypass this gate.",
      payload: {
        intercept_status: "INTERCEPTED",
        security_token_verified: true,
        ground_truth_isolated: true,
        untrusted_data_sanitized: true,
        routed_to: ["structural_engine", "fact_extraction_pipeline"]
      }
    },
    {
      id: "structural",
      name: "5. STRUCTURAL POLICY ENGINE",
      type: "structural",
      description: "Pure deterministic Python checks for amount limit, cumulative cap, merchant allowlist, and exclusions.",
      payload: {
        overall_pass: true,
        checks: [
          { constraint: "max_amount_per_txn", value: "₹1,950.00", limit: "₹2,000.00", passed: true },
          { constraint: "budget_cap", value: "₹1,950.00", limit: "₹8,000.00", passed: true },
          { constraint: "merchant_allowed", value: "Stationery Mart", allowed_list: ["Stationery Mart", "Office Depot India"], passed: true },
          { constraint: "category_allowed", value: "stationery", allowed_categories: ["office_supplies", "stationery"], passed: true },
          { constraint: "exclusions", value: "premium imported chocolates", detected_exclusions: [], passed: true }
        ],
        failure_reasons: []
      }
    },
    {
      id: "extraction",
      name: "6. FACT EXTRACTION",
      type: "ai",
      description: "Extracts normalized categorical facts from unstructured item descriptions as untrusted transaction data.",
      payload: {
        normalized_category: "food_and_confectionery",
        primary_item_type: "chocolate_truffles_gift_box",
        is_office_supply: false,
        is_luxury_gift: true,
        target_domain: "gourmet_food",
        extraction_confidence: 0.96
      }
    },
    {
      id: "semantic",
      name: "7. SEMANTIC VERIFICATION",
      type: "ai",
      description: "Evaluates natural language purpose entailment with multi-sample self-consistency.",
      payload: {
        mandate_intent_purpose: "Office consumables and desk stationery restocking",
        transaction_item_fact: "Luxury confectionery / chocolates gift box",
        samples: [
          { sample_id: 1, verdict: "no_fit", rationale: "Chocolates are food confectionery, not office stationery supplies." },
          { sample_id: 2, verdict: "no_fit", rationale: "Item violates office supplies purpose despite merchant categorization." },
          { sample_id: 3, verdict: "no_fit", rationale: "Food gift item does not satisfy workplace stationery mandate." }
        ],
        majority_verdict: "no_fit",
        agreement_rate: 1.0
      }
    },
    {
      id: "confidence",
      name: "8. CONFIDENCE ENGINE",
      type: "deterministic",
      description: "Calculates mathematical confidence from sample agreement, evidence completeness, and structural clarity.",
      payload: {
        confidence_score: 0.92,
        agreement_rate: 1.0,
        evidence_completeness: 0.95,
        mandate_specificity: 0.90,
        confidence_tier: "HIGH"
      }
    },
    {
      id: "decision",
      name: "9. DETERMINISTIC POLICY",
      type: "deterministic",
      description: "Deterministic state machine maps structural results, semantic verdicts, and confidence to final outcome.",
      payload: {
        final_decision: "FLAG",
        decision_path: "structural_pass + semantic_no_fit + high_confidence → FLAG/BLOCK",
        reason: "The transaction satisfies budget and merchant constraints, but the purchased item does not match the stated office-supplies purpose.",
        requires_human_review: true,
        financial_action_permitted: false
      }
    },
    {
      id: "execution_gate",
      name: "10. FINANCIAL EXECUTION GATE",
      type: "gate",
      description: "Payment execution is blocked. The proposal is halted and routed to the Human Review Queue.",
      payload: {
        execution_status: "BLOCKED_FROM_EXECUTION",
        dispatched_to: "HUMAN_REVIEW_QUEUE",
        real_money_moved: "₹0.00",
        audit_trail_persisted: true
      }
    }
  ];

  const selectedNode = nodes.find(n => n.id === selectedNodeId) || nodes[0];

  return (
    <div className="py-8 space-y-8 animate-in fade-in duration-500 font-mono">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-graphite">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[24px] font-bold text-paper uppercase">Interactive Decision Trace & Graph</h1>
            <span className="badge bg-acid-lime/10 text-acid-lime border border-acid-lime/30 text-[11px]">END-TO-END PIPELINE</span>
          </div>
          <p className="text-[13px] text-fog font-sans mt-1">
            Click any node in the execution pipeline to inspect its exact structured schema, intermediate states, and data payloads.
          </p>
        </div>

        <Link href="/demo" className="btn-primary text-[12px] py-1.5 px-3">
          RUN NEW CASE &rarr;
        </Link>
      </div>

      {/* Interactive Graph Layout: Pipeline Stream on Left, Payload Inspector on Right */}
      <div className="grid lg:grid-cols-12 gap-6">
        
        {/* Left Column: Graph Flow (5 cols) */}
        <div className="lg:col-span-5 space-y-2.5">
          <div className="text-[12px] text-ash uppercase mb-2">PIPELINE EXECUTION NODES:</div>
          
          {nodes.map((node, index) => {
            const isSelected = node.id === selectedNodeId;
            return (
              <div key={node.id} className="relative">
                <button
                  onClick={() => setSelectedNodeId(node.id)}
                  className={`w-full p-3.5 rounded-lg border text-left transition-all flex items-center justify-between ${
                    isSelected
                      ? "bg-carbon border-acid-lime text-paper shadow-[0_0_12px_rgba(228,242,34,0.15)]"
                      : "bg-obsidian border-graphite text-fog hover:border-smoke hover:text-mist"
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="text-[13px] font-bold text-paper">{node.name}</div>
                    <div className="text-[11px] text-fog font-sans truncate max-w-[280px]">
                      {node.description}
                    </div>
                  </div>

                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    node.type === 'structural' || node.type === 'deterministic' ? 'bg-pulse-green/10 text-pulse-green' :
                    node.type === 'ai' ? 'bg-acid-lime/10 text-acid-lime' :
                    node.type === 'proposer' ? 'bg-signal-teal/10 text-signal-teal' :
                    node.type === 'gate' ? 'bg-coral-red/10 text-coral-red' :
                    'bg-white/5 text-ash'
                  }`}>
                    {node.type}
                  </span>
                </button>

                {index < nodes.length - 1 && (
                  <div className="w-[1px] h-2.5 bg-graphite mx-auto my-0.5" />
                )}
              </div>
            );
          })}
        </div>

        {/* Right Column: Node Payload Inspector (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="linear-card border-graphite p-6 space-y-4 sticky top-24">
            <div className="flex items-center justify-between pb-3 border-b border-graphite">
              <div>
                <span className="text-[11px] text-ash uppercase">INSPECTING NODE</span>
                <h2 className="text-[18px] font-bold text-paper">{selectedNode.name}</h2>
              </div>
              <span className={`px-2.5 py-1 rounded text-[11px] font-bold uppercase ${
                selectedNode.type === 'structural' || selectedNode.type === 'deterministic' ? 'bg-pulse-green/10 text-pulse-green border border-pulse-green/30' :
                selectedNode.type === 'ai' ? 'bg-acid-lime/10 text-acid-lime border border-acid-lime/30' :
                selectedNode.type === 'proposer' ? 'bg-signal-teal/10 text-signal-teal border border-signal-teal/30' :
                selectedNode.type === 'gate' ? 'bg-coral-red/10 text-coral-red border border-coral-red/30' :
                'bg-white/5 text-ash border border-graphite'
              }`}>
                {selectedNode.type}
              </span>
            </div>

            <p className="text-[13px] text-mist font-sans leading-relaxed">
              {selectedNode.description}
            </p>

            <div className="space-y-1.5">
              <div className="text-[11px] text-ash uppercase flex items-center justify-between">
                <span>STRUCTURED PAYLOAD / TRACE RECORD:</span>
                <span className="text-acid-lime">JSON SCHEMA</span>
              </div>
              <div className="bg-void p-4 rounded-lg border border-graphite overflow-x-auto text-[12px] text-paper max-h-[460px]">
                <pre>{JSON.stringify(selectedNode.payload, null, 2)}</pre>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between text-[12px] text-fog border-t border-graphite">
              <span>Deterministic Gate Guarantee: Pass through all 10 nodes</span>
              <Link href="/audit" className="text-acid-lime hover:underline">
                View Immutable Audit Log &rarr;
              </Link>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
