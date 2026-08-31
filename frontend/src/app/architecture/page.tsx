"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Node {
  id: string;
  label: string;
  type: string;
  description: string;
}

interface Edge {
  source: string;
  target: string;
  condition?: string;
}

interface ArchData {
  nodes: Node[];
  edges: Edge[];
}

export default function ArchitecturePage() {
  const [data, setData] = useState<ArchData | null>(null);
  const [activeNode, setActiveNode] = useState<Node | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadArch() {
      const d = await apiFetch("/architecture");
      if (d && d.nodes) {
        setData(d);
        setActiveNode(d.nodes.find((n: Node) => n.id === "intentguard") || d.nodes[0]);
      } else {
        // Fallback architecture definition
        const fallbackNodes: Node[] = [
          { id: "user", label: "User", type: "external", description: "Defines spending mandate" },
          { id: "agent", label: "Autonomous Proposer Agent", type: "external", description: "Proposes transactions" },
          { id: "mandate", label: "Mandate", type: "data", description: "Structured spending policy" },
          { id: "intentguard", label: "IntentGuard Gateway", type: "system", description: "Central authorization gate" },
          { id: "structural", label: "Structural Policy Engine", type: "engine", description: "Deterministic boundary" },
          { id: "extraction", label: "Fact Extraction", type: "llm", description: "Parses untrusted descriptions" },
          { id: "semantic", label: "Semantic Verification", type: "llm", description: "Self-consistency entailment" },
          { id: "confidence", label: "Confidence Engine", type: "engine", description: "Derives mathematical score" },
          { id: "decision", label: "Deterministic Policy", type: "decision", description: "ALLOW / FLAG / BLOCK / ESCALATE" },
          { id: "review", label: "Human Review Queue", type: "human", description: "Operator exception interface" },
          { id: "audit", label: "Immutable Audit Ledger", type: "storage", description: "Full trace storage" }
        ];
        setData({ nodes: fallbackNodes, edges: [] });
        setActiveNode(fallbackNodes[3]);
      }
      setLoading(false);
    }
    loadArch();
  }, []);

  if (loading) {
    return (
      <div className="py-32 flex flex-col items-center justify-center text-ash space-y-4 font-mono">
        <div className="w-5 h-5 rounded-full border-[1.5px] border-smoke border-t-acid-lime animate-spin" />
        <div className="text-[13px]">Loading architecture map...</div>
      </div>
    );
  }

  const nodes = data?.nodes || [];

  return (
    <div className="py-8 max-w-6xl mx-auto space-y-8 font-mono animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-graphite">
        <div>
          <h1 className="text-[24px] font-bold text-paper uppercase">System Architecture & Boundaries</h1>
          <p className="text-[13px] text-fog font-sans mt-1">Interactive map of LLM isolation, deterministic control gates, and human review boundaries.</p>
        </div>
        <Link href="/trace" className="btn-primary text-[12px] py-1.5 px-3">
          Interactive Node Trace &rarr;
        </Link>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 linear-card p-6 bg-void border-graphite space-y-4">
          <div className="text-[11px] text-ash uppercase pb-2 border-b border-graphite">
            ARCHITECTURAL COMPONENTS (CLICK TO INSPECT):
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            {nodes.map(n => (
              <button
                key={n.id}
                onClick={() => setActiveNode(n)}
                className={`p-3.5 rounded border text-left transition-all ${
                  activeNode?.id === n.id
                    ? "bg-carbon border-acid-lime text-paper shadow-md"
                    : "bg-obsidian border-graphite text-fog hover:border-smoke hover:text-mist"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] font-bold text-paper">{n.label}</span>
                  <span className="text-[10px] text-ash uppercase px-1.5 py-0.5 rounded bg-void border border-graphite">
                    {n.type}
                  </span>
                </div>
                <div className="text-[11px] text-fog font-sans truncate">{n.description}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="linear-card border-graphite p-6 space-y-4 sticky top-24 bg-carbon">
          <div className="pb-3 border-b border-graphite">
            <span className="text-[11px] text-ash uppercase">COMPONENT DETAILS</span>
            <h2 className="text-[18px] font-bold text-paper mt-1">{activeNode?.label}</h2>
            <span className="badge bg-acid-lime/10 text-acid-lime border border-acid-lime/30 text-[10px] mt-2 inline-block">
              {activeNode?.type.toUpperCase()} BOUNDARY
            </span>
          </div>

          <p className="text-[13px] text-mist font-sans leading-relaxed">
            {activeNode?.description}
          </p>

          <div className="p-3 bg-void rounded border border-graphite text-[11px] text-fog space-y-1">
            <div><span className="text-ash">Security Role: </span>Isolation & Enforcement</div>
            <div><span className="text-ash">Execution Authority: </span>Bounded / Non-financial</div>
          </div>
        </div>
      </div>
    </div>
  );
}
