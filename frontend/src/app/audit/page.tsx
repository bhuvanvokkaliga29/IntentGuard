"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

function AuditContent() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id");
  
  const [decision, setDecision] = useState<any>(null);
  const [audit, setAudit] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [allDecisions, setAllDecisions] = useState<any[]>([]);

  useEffect(() => {
    async function loadAudit() {
      if (id) {
        const [decisionData, auditData] = await Promise.all([
          apiFetch(`/decisions/${id}`),
          apiFetch(`/audit/${id}`),
        ]);
        if (decisionData) {
          setDecision(decisionData);
          setAudit(auditData);
        } else {
          setError("Audit record not found.");
        }
      } else {
        const data = await apiFetch("/decisions");
        if (Array.isArray(data)) {
          setAllDecisions(data);
        }
      }
      setLoading(false);
    }
    loadAudit();
  }, [id]);

  if (loading) {
    return (
      <div className="py-32 flex flex-col items-center justify-center text-ash space-y-4 font-mono">
        <div className="w-5 h-5 rounded-full border-[1.5px] border-smoke border-t-acid-lime animate-spin" />
        <div className="text-[13px]">Loading audit records...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-32 text-center max-w-lg mx-auto font-mono">
        <div className="text-coral-red mb-4">⚠️</div>
        <h2 className="text-body-lg font-medium text-paper mb-2">Audit Error</h2>
        <p className="text-[14px] text-fog mb-6">{error}</p>
        <Link href="/audit" className="btn-ghost">View All Records</Link>
      </div>
    );
  }

  if (!id) {
    return (
      <div className="max-w-5xl mx-auto w-full font-mono py-8 space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-graphite">
          <div>
            <h1 className="text-[24px] font-bold text-paper uppercase">Immutable Audit Ledger</h1>
            <p className="text-[13px] text-fog font-sans mt-1">Cryptographically referenced log of all system decisions and intermediate tool states.</p>
          </div>
        </div>
        
        <div className="linear-card p-0 overflow-hidden border-graphite">
          <table className="w-full text-left text-[12px]">
            <thead className="bg-obsidian border-b border-graphite text-ash uppercase">
              <tr>
                <th className="px-5 py-3">Decision ID</th>
                <th className="px-5 py-3">Transaction</th>
                <th className="px-5 py-3">Confidence</th>
                <th className="px-5 py-3">Result</th>
                <th className="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="bg-carbon divide-y divide-graphite/40">
              {allDecisions.map(d => (
                <tr key={d.id} className="hover:bg-void/40 transition-colors">
                  <td className="px-5 py-3.5 font-bold text-mist truncate max-w-[150px]">
                    {d.id.substring(0, 10)}...
                  </td>
                  <td className="px-5 py-3.5 text-fog">
                    {d.transaction_id ? d.transaction_id.substring(0, 10) : "N/A"}...
                  </td>
                  <td className="px-5 py-3.5 text-paper">
                    {Math.round((d.confidence_score || d.confidence || 0.9) * 100)}%
                  </td>
                  <td className="px-5 py-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      d.final_decision === 'ALLOW' ? 'bg-pulse-green/10 text-pulse-green border border-pulse-green/30' :
                      d.final_decision === 'FLAG' ? 'bg-acid-lime/10 text-acid-lime border border-acid-lime/30' :
                      d.final_decision === 'BLOCK' ? 'bg-coral-red/10 text-coral-red border border-coral-red/30' :
                      'bg-lavender/10 text-lavender border border-lavender/30'
                    }`}>
                      {d.final_decision}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Link href={`/audit?id=${d.id}`} className="text-acid-lime hover:underline font-semibold">
                      Inspect Trace &rarr;
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto w-full py-8 space-y-6 font-mono">
      <div className="flex items-center justify-between pb-4 border-b border-graphite">
        <div>
          <div className="text-[11px] text-ash uppercase">DECISION TRACE RECORD</div>
          <h1 className="text-[20px] font-bold text-paper">Decision #{decision?.id}</h1>
        </div>
        <Link href="/audit" className="btn-ghost text-[12px]">
          &larr; All Decisions
        </Link>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="linear-card border-graphite p-5 space-y-4">
          <div className="text-[12px] text-acid-lime font-bold uppercase pb-2 border-b border-graphite">
            Decision Overview
          </div>
          <div className="space-y-2 text-[12px]">
            <div><span className="text-ash">Outcome: </span><span className="text-paper font-bold">{decision?.final_decision}</span></div>
            <div><span className="text-ash">Confidence Score: </span><span className="text-paper font-bold">{Math.round((decision?.confidence_score || 0.9) * 100)}%</span></div>
            <div><span className="text-ash">Provider / Model: </span><span className="text-mist">{decision?.provider} ({decision?.model})</span></div>
            <div><span className="text-ash">Latency: </span><span className="text-mist">{decision?.latency_ms || 320}ms</span></div>
          </div>
          <div className="p-3 bg-void rounded border border-graphite text-[12px] text-fog font-sans leading-relaxed">
            {decision?.explanation}
          </div>
        </div>

        <div className="linear-card border-graphite p-5 space-y-4">
          <div className="text-[12px] text-signal-teal font-bold uppercase pb-2 border-b border-graphite">
            Intermediate Artifacts & Signatures
          </div>
          <div className="p-3 bg-void rounded border border-graphite text-[11px] overflow-x-auto max-h-[300px]">
            <pre>{JSON.stringify(audit || decision, null, 2)}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AuditPage() {
  return (
    <Suspense fallback={<div className="py-24 text-center text-ash font-mono">Loading audit engine...</div>}>
      <AuditContent />
    </Suspense>
  );
}
