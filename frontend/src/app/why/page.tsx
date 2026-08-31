import Link from "next/link";

export default function WhyPage() {
  return (
    <div className="py-24 animate-in fade-in duration-500 max-w-5xl mx-auto px-6">
      <div className="mb-16 text-center max-w-3xl mx-auto">
        <h1 className="text-display mb-6">Why Structural Rules Are Not Enough</h1>
        <p className="text-body-lg text-fog text-balance">
          Delegating money to an AI agent requires more than just budget limits. 
          When an agent operates within a boundary, it can still violate your actual intent.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8 mb-24">
        {/* Left: Traditional */}
        <div className="linear-card bg-carbon/30 border-graphite">
          <div className="text-[14px] text-ash font-mono mb-8 uppercase tracking-widest border-b border-graphite pb-4">Current Standard</div>
          
          <ul className="space-y-6">
            <li className="flex items-center gap-4 text-mist">
              <div className="w-6 h-6 rounded bg-graphite flex items-center justify-center text-[12px]">✓</div>
              Amount limits
            </li>
            <li className="flex items-center gap-4 text-mist">
              <div className="w-6 h-6 rounded bg-graphite flex items-center justify-center text-[12px]">✓</div>
              Merchant allowlist
            </li>
            <li className="flex items-center gap-4 text-mist">
              <div className="w-6 h-6 rounded bg-graphite flex items-center justify-center text-[12px]">✓</div>
              Category restrictions
            </li>
            <li className="flex items-center gap-4 text-mist">
              <div className="w-6 h-6 rounded bg-graphite flex items-center justify-center text-[12px]">✓</div>
              Recurrence limits
            </li>
          </ul>
          
          <div className="mt-12 p-6 bg-void border border-graphite rounded-lg relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-coral-red/5 blur-3xl rounded-full" />
            <div className="text-[12px] text-coral-red font-mono mb-2 uppercase">The Blind Spot</div>
            <p className="text-[14px] text-fog leading-relaxed">
              If an agent is authorized to spend ₹2,000 at a stationery store for "office supplies", existing controls will gladly allow the purchase of a ₹1,950 premium box of imported chocolates from that exact store.
            </p>
          </div>
        </div>
        
        {/* Right: IntentGuard */}
        <div className="linear-card bg-obsidian border-graphite relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-acid-lime/5 blur-3xl rounded-full -z-10" />
          
          <div className="text-[14px] text-mist font-mono mb-8 uppercase tracking-widest border-b border-graphite pb-4 flex items-center justify-between">
            <span>IntentGuard</span>
            <div className="w-2 h-2 rounded-full bg-acid-lime animate-pulse" />
          </div>
          
          <ul className="space-y-6">
            <li className="flex items-center gap-4 text-paper">
              <div className="w-6 h-6 rounded bg-acid-lime/20 border border-acid-lime/50 text-acid-lime flex items-center justify-center text-[12px]">+</div>
              Semantic purpose matching
            </li>
            <li className="flex items-center gap-4 text-paper">
              <div className="w-6 h-6 rounded bg-acid-lime/20 border border-acid-lime/50 text-acid-lime flex items-center justify-center text-[12px]">+</div>
              Context extraction
            </li>
            <li className="flex items-center gap-4 text-paper">
              <div className="w-6 h-6 rounded bg-acid-lime/20 border border-acid-lime/50 text-acid-lime flex items-center justify-center text-[12px]">+</div>
              Ambiguity detection
            </li>
            <li className="flex items-center gap-4 text-paper">
              <div className="w-6 h-6 rounded bg-acid-lime/20 border border-acid-lime/50 text-acid-lime flex items-center justify-center text-[12px]">+</div>
              Human escalation queue
            </li>
          </ul>
          
          <div className="mt-12 p-6 bg-void border border-acid-lime/30 rounded-lg relative z-10">
            <div className="text-[12px] text-acid-lime font-mono mb-2 uppercase">The Solution</div>
            <p className="text-[14px] text-mist leading-relaxed">
              IntentGuard extracts the item facts ("premium chocolate"), compares it against the user's declared semantic intent ("office supplies"), and deterministically flags the transaction for review before any money moves.
            </p>
          </div>
        </div>
      </div>

      <div className="text-center mt-16">
        <Link href="/demo" className="btn-primary inline-flex items-center gap-2">
          See It In Action
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="group-hover:translate-x-0.5 transition-transform"><path d="M6 12L10 8L6 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </Link>
      </div>

    </div>
  );
}
