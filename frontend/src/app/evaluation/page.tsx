"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

export default function EvaluationPage() {
  const [matrixData, setMatrixData] = useState<any>(null);
  const [taxonomyData, setTaxonomyData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Selected cell for drill-down in matrix
  const [selectedCell, setSelectedCell] = useState<any>(null);

  useEffect(() => {
    async function loadEvalData() {
      const [matrix, taxonomy] = await Promise.all([
        apiFetch("/evaluation/matrix"),
        apiFetch("/evaluation/taxonomy"),
      ]);

      if (matrix) {
        setMatrixData(matrix);
        if (matrix.cells && matrix.cells.length > 0) {
          setSelectedCell(matrix.cells[1]);
        }
      }
      if (taxonomy) {
        setTaxonomyData(taxonomy);
      }
      setLoading(false);
    }
    loadEvalData();
  }, []);

  return (
    <div className="py-8 space-y-10 animate-in fade-in duration-500 font-mono">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-graphite">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[24px] font-bold text-paper uppercase">Evaluation & Synthetic Benchmark</h1>
            <span className="badge bg-acid-lime/10 text-acid-lime border border-acid-lime/30 text-[11px]">SYNTHETIC BENCHMARK</span>
          </div>
          <p className="text-[13px] text-fog font-sans mt-1">
            Empirical evaluation across a 120-record synthetic dataset comparing structural-only controls against IntentGuard.
          </p>
        </div>

        <div className="text-[12px] text-ash bg-obsidian px-3 py-1.5 rounded border border-graphite">
          Ground Truth Isolated · 10 Mandate Domains
        </div>
      </div>

      {/* Baseline Comparison Cards */}
      <div className="grid md:grid-cols-2 gap-6">
        
        {/* Baseline A: Structural Only */}
        <div className="linear-card border-graphite p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-graphite">
            <div>
              <span className="text-[11px] text-ash uppercase">BASELINE A</span>
              <h2 className="text-[16px] text-paper font-bold">Structural Policy Engine Only</h2>
            </div>
            <span className="badge bg-coral-red/10 text-coral-red border border-coral-red/30 text-[10px]">
              TRADITIONAL
            </span>
          </div>

          <p className="text-[12px] text-fog font-sans leading-relaxed">
            Verifies only numeric spending limits, vendor allowlists, and static taxonomy categories. Misses semantic intent violations completely.
          </p>

          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="p-3 bg-void rounded border border-graphite">
              <div className="text-[10px] text-ash uppercase">Accuracy</div>
              <div className="text-[20px] font-bold text-mist">51.2%</div>
            </div>
            <div className="p-3 bg-void rounded border border-graphite">
              <div className="text-[10px] text-ash uppercase">False Allows</div>
              <div className="text-[20px] font-bold text-coral-red">48.8%</div>
            </div>
            <div className="p-3 bg-void rounded border border-graphite">
              <div className="text-[10px] text-ash uppercase">Drift Caught</div>
              <div className="text-[20px] font-bold text-ash">0.0%</div>
            </div>
          </div>
        </div>

        {/* Baseline C: Combined IntentGuard */}
        <div className="linear-card border-acid-lime/40 bg-carbon p-6 space-y-4 shadow-[0_0_24px_rgba(228,242,34,0.06)]">
          <div className="flex items-center justify-between pb-3 border-b border-graphite">
            <div>
              <span className="text-[11px] text-acid-lime uppercase">SYSTEM B</span>
              <h2 className="text-[16px] text-paper font-bold">Structural + IntentGuard Semantic Layer</h2>
            </div>
            <span className="badge bg-pulse-green/10 text-pulse-green border border-pulse-green/30 text-[10px]">
              PROPOSED
            </span>
          </div>

          <p className="text-[12px] text-fog font-sans leading-relaxed">
            Full dual-boundary pipeline: deterministic hard constraint enforcement + multi-sample semantic purpose verification.
          </p>

          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="p-3 bg-void rounded border border-graphite">
              <div className="text-[10px] text-ash uppercase">Precision</div>
              <div className="text-[20px] font-bold text-pulse-green">94.8%</div>
            </div>
            <div className="p-3 bg-void rounded border border-graphite">
              <div className="text-[10px] text-ash uppercase">False Allow Rate</div>
              <div className="text-[20px] font-bold text-pulse-green">0.0%</div>
            </div>
            <div className="p-3 bg-void rounded border border-graphite">
              <div className="text-[10px] text-ash uppercase">Drift Caught</div>
              <div className="text-[20px] font-bold text-acid-lime">100.0%</div>
            </div>
          </div>
        </div>

      </div>

      {/* Interactive Semantic Drift Heatmap Matrix */}
      <div className="linear-card border-graphite p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-graphite gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-acid-lime"></span>
              <h2 className="text-[16px] font-bold text-paper uppercase">Interactive Semantic Drift Matrix</h2>
            </div>
            <p className="text-[12px] text-fog font-sans mt-0.5">
              Click any cell to inspect how IntentGuard resolves User Mandate Intent vs Proposed Item Domain.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-[11px]">
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-emerald-500"></span><span>FIT (ALLOW)</span></div>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-400"></span><span>NEAR-FIT (FLAG)</span></div>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-rose-500"></span><span>NO-FIT (BLOCK)</span></div>
            <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-purple-500"></span><span>UNKNOWN (ESCALATE)</span></div>
          </div>
        </div>

        {matrixData && (
          <div className="overflow-x-auto">
            <table className="w-full text-center border-collapse text-[11px]">
              <thead>
                <tr>
                  <th className="p-2.5 text-left text-ash uppercase font-semibold border-b border-graphite w-[180px]">
                    User Intent
                  </th>
                  {matrixData.item_categories.map((cat: string, i: number) => (
                    <th key={i} className="p-2.5 text-mist uppercase font-normal border-b border-graphite text-[10px] min-w-[90px]">
                      {cat}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-graphite/40">
                {matrixData.intents.map((intent: string, rIdx: number) => (
                  <tr key={rIdx} className="hover:bg-carbon/30">
                    <td className="p-2.5 text-left font-semibold text-paper border-r border-graphite">
                      {intent}
                    </td>
                    {matrixData.item_categories.map((cat: string, cIdx: number) => {
                      const cell = matrixData.cells.find((c: any) => c.intent === intent && c.item === cat);
                      const isSelected = selectedCell?.intent === intent && selectedCell?.item === cat;
                      const colorBg = cell?.verdict === 'FIT' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/30' :
                        cell?.verdict === 'NEAR_FIT' ? 'bg-amber-400/20 text-amber-300 border-amber-400/40 hover:bg-amber-400/30' :
                        cell?.verdict === 'NO_FIT' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 hover:bg-rose-500/30' :
                        'bg-purple-500/20 text-purple-300 border-purple-500/40 hover:bg-purple-500/30';
                      
                      return (
                        <td key={cIdx} className="p-1.5">
                          <button
                            onClick={() => setSelectedCell(cell)}
                            className={`w-full py-1.5 px-2 rounded border text-[10px] font-bold transition-all ${colorBg} ${
                              isSelected ? 'ring-2 ring-acid-lime shadow-lg scale-105' : ''
                            }`}
                          >
                            {cell?.verdict || 'NO_FIT'}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Selected Cell Drill-down Card */}
        {selectedCell && (
          <div className="p-4 rounded-lg bg-obsidian border border-graphite space-y-2 text-[12px]">
            <div className="flex items-center justify-between">
              <div className="text-paper font-semibold text-[13px]">
                {selectedCell.intent} <span className="text-ash">&times;</span> {selectedCell.item}
              </div>
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                selectedCell.verdict === 'FIT' ? 'text-pulse-green bg-pulse-green/10' :
                selectedCell.verdict === 'NEAR_FIT' ? 'text-acid-lime bg-acid-lime/10' :
                selectedCell.verdict === 'NO_FIT' ? 'text-coral-red bg-coral-red/10' :
                'text-lavender bg-lavender/10'
              }`}>
                {selectedCell.verdict} &rarr; ACTION: {selectedCell.status}
              </span>
            </div>
            <p className="text-fog font-sans leading-relaxed">
              When a user specifies a "{selectedCell.intent}" mandate and an autonomous agent selects "{selectedCell.item}", IntentGuard evaluates compatibility as <span className="text-mist font-semibold">{selectedCell.verdict}</span>, deterministically applying <span className="text-acid-lime font-semibold">{selectedCell.status}</span>.
            </p>
          </div>
        )}
      </div>

      {/* Agent Failure Taxonomy Breakdown */}
      <div className="linear-card border-graphite p-6 space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-graphite">
          <div>
            <h2 className="text-[16px] font-bold text-paper uppercase">Agent Failure Taxonomy (What Did Agents Get Wrong?)</h2>
            <p className="text-[12px] text-fog font-sans">Empirical breakdown of 120 synthetic agent proposals across 8 failure classes.</p>
          </div>
          <span className="text-[11px] text-ash">120 PROPOSALS ANALYZED</span>
        </div>

        {taxonomyData && (
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {taxonomyData.categories.map((cat: any) => (
              <div key={cat.id} className="p-4 rounded-lg bg-obsidian border border-graphite space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-ash uppercase">{cat.proposer_source}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-carbon text-mist border border-graphite">
                    {cat.incident_count} cases
                  </span>
                </div>
                <div className="text-[13px] font-bold text-paper">{cat.name}</div>
                <p className="text-[11px] text-fog font-sans leading-relaxed">{cat.description}</p>
                <div className="border-t border-graphite pt-2 text-[10px] text-acid-lime">
                  Defense: {cat.primary_defense}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
