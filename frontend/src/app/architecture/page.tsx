"use client";

import { useState, useEffect, useRef } from "react";
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

  // Zoom & Pan state for mouse-wheel interaction
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadArch() {
      const d = await apiFetch("/architecture");
      if (d && d.nodes) {
        setData(d);
        setActiveNode(d.nodes.find((n: Node) => n.id === "intentguard") || d.nodes[0]);
      } else {
        const fallbackNodes: Node[] = [
          { id: "user", label: "User Client", type: "external", description: "Defines natural-language spending mandate." },
          { id: "proposers", label: "Untrusted Proposer Agents", type: "agent", description: "Buying, Recommendation & Voice agents formulate transaction proposals." },
          { id: "normalizer", label: "Mandate Normalizer", type: "service", description: "Converts natural language into structured versioned policy." },
          { id: "structural", label: "Structural Policy Engine", type: "engine", description: "Zero-LLM deterministic budget, limit & MCC checks (<1ms)." },
          { id: "semantic", label: "Semantic Verifier", type: "llm", description: "3x multi-sample entailment consensus reasoning." },
          { id: "evidence", label: "Evidence Engine", type: "engine", description: "Unifies structural and semantic facts into decision context." },
          { id: "confidence", label: "Uncertainty / Confidence", type: "engine", description: "Derives mathematical confidence score (0.0 to 1.0)." },
          { id: "decision", label: "Deterministic Decision Engine", type: "decision", description: "Pure Python authority producing ALLOW, FLAG, BLOCK, ESCALATE." },
          { id: "execution", label: "Financial Execution Gateway", type: "gateway", description: "Razorpay payment boundary - only executes on validated ALLOW." },
          { id: "review", label: "Human Review Service", type: "human", description: "Operational queue for flagged or escalated exceptions." },
          { id: "audit", label: "Immutable Audit Ledger", type: "storage", description: "Tamper-proof cryptographic record of every proposal & decision." }
        ];
        setData({ nodes: fallbackNodes, edges: [] });
        setActiveNode(fallbackNodes[3]);
      }
      setLoading(false);
    }
    loadArch();
  }, []);

  // Mouse wheel zoom in / zoom out
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
    setScale(prev => Math.min(Math.max(0.5, prev * zoomFactor), 4.0));
  };

  // Mouse drag pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Left click only
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleResetZoom = () => {
    setScale(1);
    setPan({ x: 0, y: 0 });
  };

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
    <div className="py-8 max-w-7xl mx-auto space-y-8 font-mono animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-graphite">
        <div>
          <h1 className="text-[24px] font-bold text-paper uppercase">System Architecture & Interactive Canvas</h1>
          <p className="text-[13px] text-fog font-sans mt-1">
            Explore the 7 security zones, LLM isolation layers, and deterministic authorization boundaries.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/trace" className="btn-secondary text-[12px] py-1.5 px-3">
            Execution Trace &rarr;
          </Link>
          <Link href="/demo" className="btn-primary text-[12px] py-1.5 px-3">
            Live Demo &rarr;
          </Link>
        </div>
      </div>

      {/* Interactive Mouse-Wheel Zoom & Pan Viewer */}
      <div className="linear-card p-4 bg-void border-graphite space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2 text-[11px] text-ash pb-2 border-b border-graphite">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-acid-lime animate-pulse" />
            <span className="text-paper font-bold uppercase">Interactive Diagram Canvas</span>
            <span className="text-fog hidden sm:inline">(Scroll mouse wheel to Zoom • Click & Drag to Pan)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-fog">Zoom: {Math.round(scale * 100)}%</span>
            <button
              onClick={() => setScale(s => Math.min(4.0, s * 1.2))}
              className="px-2 py-1 bg-obsidian hover:bg-carbon border border-graphite rounded text-mist text-[11px]"
              title="Zoom In"
            >
              +
            </button>
            <button
              onClick={() => setScale(s => Math.max(0.5, s * 0.8))}
              className="px-2 py-1 bg-obsidian hover:bg-carbon border border-graphite rounded text-mist text-[11px]"
              title="Zoom Out"
            >
              -
            </button>
            <button
              onClick={handleResetZoom}
              className="px-2.5 py-1 bg-obsidian hover:bg-carbon border border-graphite rounded text-acid-lime text-[11px]"
              title="Reset View"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Viewport container */}
        <div
          ref={canvasRef}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className="relative h-[520px] w-full overflow-hidden rounded-lg bg-[#0a0d14] border border-graphite cursor-grab active:cursor-grabbing select-none flex items-center justify-center"
        >
          {/* Background grid dots */}
          <div
            className="absolute inset-0 opacity-15 pointer-events-none"
            style={{
              backgroundImage: "radial-gradient(#4ade80 1px, transparent 1px)",
              backgroundSize: "24px 24px"
            }}
          />

          {/* Transformed image layer */}
          <div
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
              transformOrigin: "center center",
              transition: isDragging ? "none" : "transform 0.08s ease-out",
            }}
            className="relative flex items-center justify-center pointer-events-none"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/architecture_diagram.png"
              alt="IntentGuard Master Architecture Diagram"
              className="max-w-none w-[1100px] h-auto rounded-lg shadow-2xl border border-graphite/40"
              draggable={false}
            />
          </div>

          {/* Floating Canvas Helper Overlay */}
          <div className="absolute bottom-3 right-3 bg-obsidian/90 backdrop-blur border border-graphite/80 px-3 py-1.5 rounded text-[11px] text-fog pointer-events-none flex items-center gap-2">
            <span>🖱️ Mouse Wheel: <b>Zoom In/Out</b></span>
            <span>•</span>
            <span>✋ Drag: <b>Pan</b></span>
          </div>
        </div>
      </div>

      {/* Node Inspector Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 linear-card p-6 bg-void border-graphite space-y-4">
          <div className="text-[11px] text-ash uppercase pb-2 border-b border-graphite flex items-center justify-between">
            <span>ARCHITECTURAL SUBSYSTEMS & SECURITY GATES</span>
            <span className="text-fog">Click to inspect boundary rules</span>
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            {nodes.map(n => (
              <button
                key={n.id}
                onClick={() => setActiveNode(n)}
                className={`p-3.5 rounded border text-left transition-all ${
                  activeNode?.id === n.id
                    ? "bg-carbon border-acid-lime text-paper shadow-md scale-[1.01]"
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

        {/* Selected Component Card */}
        <div className="linear-card border-graphite p-6 space-y-4 bg-carbon h-fit sticky top-24">
          <div className="pb-3 border-b border-graphite">
            <span className="text-[11px] text-ash uppercase">SECURITY BOUNDARY INSPECTION</span>
            <h2 className="text-[18px] font-bold text-paper mt-1">{activeNode?.label}</h2>
            <span className="badge bg-acid-lime/10 text-acid-lime border border-acid-lime/30 text-[10px] mt-2 inline-block">
              {activeNode?.type.toUpperCase()} BOUNDARY
            </span>
          </div>

          <p className="text-[13px] text-mist font-sans leading-relaxed">
            {activeNode?.description}
          </p>

          <div className="p-3 bg-void rounded border border-graphite text-[11px] text-fog space-y-1.5">
            <div><span className="text-ash">Isolation: </span>Proposal-Only Sandbox</div>
            <div><span className="text-ash">Settlement Access: </span>Zero Direct Payment Tokens</div>
            <div><span className="text-ash">Enforcement: </span>Deterministic Python Matrix</div>
          </div>
        </div>
      </div>
    </div>
  );
}
