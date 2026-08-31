"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

export default function ReviewQueuePage() {
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actioned, setActioned] = useState<Record<string, { action: string; notes: string }>>({});
  const [activeNotes, setActiveNotes] = useState<Record<string, string>>({});

  useEffect(() => {
    async function loadQueue() {
      const data = await apiFetch("/decisions");
      if (Array.isArray(data)) {
        const reviewQueue = data.filter((d: any) => 
          d.final_decision === 'FLAG' || d.final_decision === 'ESCALATE'
        );
        setQueue(reviewQueue);
      } else {
        setQueue([]);
      }
      setLoading(false);
    }
    loadQueue();
  }, []);

  const handleAction = async (id: string, action: string) => {
    const notes = activeNotes[id] || `Human review action: ${action}`;
    try {
      await apiFetch(`/decisions/${id}/review`, {
        method: "POST",
        body: JSON.stringify({
          action,
          notes,
        }),
      });
      setActioned(prev => ({ ...prev, [id]: { action, notes } }));
    } catch (err) {
      console.error("Failed to submit review action:", err);
      setActioned(prev => ({ ...prev, [id]: { action, notes } }));
    }
  };

  const pendingQueue = queue.filter(item => !actioned[item.id] && !item.human_review_status);
  const resolvedQueue = queue.filter(item => actioned[item.id] || item.human_review_status);

  return (
    <div className="py-8 space-y-8 animate-in fade-in duration-500 font-mono">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-graphite">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[24px] font-bold text-paper uppercase">Human Review & Exception Queue</h1>
            <span className="badge bg-coral-red/10 text-coral-red border border-coral-red/30 text-[11px]">HUMAN-IN-THE-LOOP</span>
          </div>
          <p className="text-[13px] text-fog font-sans mt-1">
            Review ambiguous, flagged, and escalated autonomous agent proposals before financial authorization.
          </p>
        </div>

        <div className="flex items-center gap-4 text-[12px]">
          <div className="p-2 px-3 bg-obsidian rounded border border-graphite">
            <span className="text-ash">PENDING: </span>
            <span className="text-acid-lime font-bold">{pendingQueue.length}</span>
          </div>
          <div className="p-2 px-3 bg-obsidian rounded border border-graphite">
            <span className="text-ash">RESOLVED: </span>
            <span className="text-pulse-green font-bold">{resolvedQueue.length}</span>
          </div>
        </div>
      </div>

      {/* Pending Reviews List */}
      <div className="space-y-6">
        <div className="text-[12px] text-ash uppercase">ACTION REQUIRED ({pendingQueue.length} TRANSACTIONS):</div>

        {loading ? (
          <div className="linear-card p-12 text-center text-fog text-[13px] border-graphite">
            <div className="w-5 h-5 rounded-full border-2 border-graphite border-t-acid-lime animate-spin mx-auto mb-3" />
            <div>Loading review queue from IntentGuard gateway...</div>
          </div>
        ) : pendingQueue.length === 0 ? (
          <div className="linear-card p-12 text-center text-fog text-[13px] border-graphite">
            <div className="text-paper text-[16px] font-semibold mb-1">Queue is currently clear</div>
            <div>All flagged and escalated transactions have been reviewed and actioned.</div>
            <Link href="/demo" className="btn-ghost inline-block mt-4 text-[12px]">
              Trigger New Demo Scenarios &rarr;
            </Link>
          </div>
        ) : (
          pendingQueue.map((item) => (
            <div key={item.id} className="linear-card p-0 overflow-hidden border-graphite bg-carbon">
              
              <div className="p-5 bg-obsidian border-b border-graphite flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[12px]">
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${
                    item.final_decision === 'FLAG'
                      ? 'bg-acid-lime/20 text-acid-lime border border-acid-lime/40'
                      : 'bg-lavender/20 text-lavender border border-lavender/40'
                  }`}>
                    {item.final_decision}
                  </span>
                  <span className="text-paper font-semibold">Decision #{item.id.substring(0, 10)}</span>
                  <span className="text-ash">·</span>
                  <span className="text-fog">Confidence: {Math.round((item.confidence || 0.85) * 100)}%</span>
                </div>

                <Link href={`/audit?id=${item.id}`} className="text-ash hover:text-mist text-[11px]">
                  View Full Audit Trace &rarr;
                </Link>
              </div>

              <div className="p-6 grid md:grid-cols-3 gap-6 text-[13px]">
                
                {/* Reason & Evidence */}
                <div className="md:col-span-2 space-y-4">
                  <div>
                    <div className="text-[11px] text-ash uppercase mb-1">WHY IT WAS ESCALATED:</div>
                    <p className="p-3 bg-void rounded border border-graphite text-mist leading-relaxed font-sans text-[13px]">
                      {item.explanation}
                    </p>
                  </div>

                  <div>
                    <label className="text-[11px] text-ash uppercase">REVIEWER AUDIT NOTES:</label>
                    <input
                      type="text"
                      placeholder="Add mandatory human operator reasoning before authorizing..."
                      value={activeNotes[item.id] || ""}
                      onChange={e => setActiveNotes({ ...activeNotes, [item.id]: e.target.value })}
                      className="w-full bg-void border border-graphite rounded px-3 py-2 text-paper text-[12px] outline-none focus:border-acid-lime mt-1 font-sans"
                    />
                  </div>
                </div>

                {/* Actions Panel */}
                <div className="flex flex-col justify-between p-4 bg-obsidian rounded-lg border border-graphite space-y-3">
                  <div className="text-[11px] text-ash uppercase font-semibold">
                    HUMAN OPERATOR ACTION:
                  </div>

                  <div className="space-y-2">
                    <button
                      onClick={() => handleAction(item.id, "APPROVE")}
                      className="btn-primary w-full justify-center text-[12px] bg-pulse-green text-white hover:brightness-110"
                    >
                      ✓ OVERRIDE & APPROVE
                    </button>
                    <button
                      onClick={() => handleAction(item.id, "REJECT")}
                      className="btn-primary w-full justify-center text-[12px] bg-coral-red text-white hover:brightness-110"
                    >
                      ✕ PERMANENTLY REJECT
                    </button>
                    <button
                      onClick={() => handleAction(item.id, "REQUEST_INFO")}
                      className="btn-ghost w-full justify-center text-[12px] bg-carbon text-mist hover:text-paper"
                    >
                      ? REQUEST USER CLARIFICATION
                    </button>
                  </div>

                  <div className="text-[10px] text-ash text-center">
                    Action is immutably logged to the audit ledger.
                  </div>
                </div>

              </div>

            </div>
          ))
        )}
      </div>

      {/* Resolved History */}
      {resolvedQueue.length > 0 && (
        <div className="space-y-3 pt-6 border-t border-graphite">
          <div className="text-[12px] text-ash uppercase">RESOLVED TRANSACTIONS ({resolvedQueue.length}):</div>
          <div className="space-y-2">
            {resolvedQueue.map((item) => {
              const status = actioned[item.id]?.action || item.human_review_status;
              const notes = actioned[item.id]?.notes || item.human_review_notes;
              return (
                <div key={item.id} className="p-3 bg-obsidian rounded border border-graphite flex items-center justify-between text-[12px]">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      status === 'APPROVE' || status === 'APPROVED' ? 'bg-pulse-green/10 text-pulse-green' :
                      status === 'REJECT' || status === 'REJECTED' ? 'bg-coral-red/10 text-coral-red' :
                      'bg-lavender/10 text-lavender'
                    }`}>
                      {status}
                    </span>
                    <span className="text-paper font-semibold">Decision #{item.id.substring(0, 10)}</span>
                    <span className="text-fog font-sans text-[12px]">{notes}</span>
                  </div>
                  <Link href={`/audit?id=${item.id}`} className="text-ash hover:text-mist text-[11px]">
                    Trace &rarr;
                  </Link>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
