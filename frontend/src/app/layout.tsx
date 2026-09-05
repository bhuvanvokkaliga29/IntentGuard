import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import Script from "next/script";

export const metadata: Metadata = {
  title: "IntentGuard — Semantic Spending Guard for Autonomous Agents",
  description: "Verify what an autonomous AI agent proposes to buy against what the user actually meant.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased min-h-screen flex flex-col bg-void text-mist selection:bg-acid-lime/30 selection:text-void font-sans">
        <Script src="https://checkout.razorpay.com/v1/checkout.js" strategy="beforeInteractive" />
        {/* Navigation - Dark Console Top Bar */}
        <header className="sticky top-0 z-50 w-full bg-void/90 backdrop-blur-md border-b border-graphite/60">
          <div className="w-full max-w-[1760px] mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center gap-2.5 group">
                <div className="w-5 h-5 bg-acid-lime rounded-sm flex items-center justify-center text-void font-mono font-bold text-[11px] shadow-[0_0_10px_rgba(228,242,34,0.3)]">
                  IG
                </div>
                <div className="flex flex-col">
                  <span className="font-mono font-semibold text-[15px] text-paper tracking-wider uppercase">IntentGuard</span>
                  <span className="text-[10px] text-ash font-mono -mt-1 tracking-tight">AGENTIC PAYMENT CONTROL</span>
                </div>
              </Link>

              <nav className="hidden lg:flex items-center gap-1 pl-4 border-l border-graphite">
                <Link href="/" className="text-[13px] font-mono px-2.5 py-1.5 text-mist hover:text-paper hover:bg-carbon rounded transition-colors">
                  Overview
                </Link>
                <Link href="/demo" className="text-[13px] font-mono px-2.5 py-1.5 text-mist hover:text-paper hover:bg-carbon rounded transition-colors">
                  Live Demo
                </Link>
                <Link href="/lab" className="text-[13px] font-mono px-2.5 py-1.5 text-acid-lime bg-acid-lime/5 border border-acid-lime/20 hover:bg-acid-lime/10 rounded transition-colors">
                  ⚡ Agent Lab
                </Link>
                <Link href="/trace" className="text-[13px] font-mono px-2.5 py-1.5 text-mist hover:text-paper hover:bg-carbon rounded transition-colors">
                  Decision Trace
                </Link>
                <Link href="/evaluation" className="text-[13px] font-mono px-2.5 py-1.5 text-mist hover:text-paper hover:bg-carbon rounded transition-colors">
                  Evaluation
                </Link>
                <Link href="/review" className="text-[13px] font-mono px-2.5 py-1.5 text-coral-red bg-coral-red/5 border border-coral-red/20 hover:bg-coral-red/10 rounded transition-colors">
                  Review Queue
                </Link>
                <Link href="/architecture" className="text-[13px] font-mono px-2.5 py-1.5 text-mist hover:text-paper hover:bg-carbon rounded transition-colors">
                  Architecture
                </Link>
                <Link href="/audit" className="text-[13px] font-mono px-2.5 py-1.5 text-mist hover:text-paper hover:bg-carbon rounded transition-colors">
                  Audit
                </Link>
                <Link href="/dataset" className="text-[13px] font-mono px-2.5 py-1.5 text-mist hover:text-paper hover:bg-carbon rounded transition-colors">
                  Dataset
                </Link>
              </nav>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded bg-carbon border border-graphite text-[11px] font-mono text-ash">
                <span className="w-2 h-2 rounded-full bg-pulse-green animate-pulse"></span>
                <span>GATEWAY ACTIVE</span>
              </div>
              <Link href="/demo" className="btn-primary text-[12px] font-mono py-1.5 px-3">
                RUN FAILURE DEMO &rarr;
              </Link>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 w-full max-w-[1760px] mx-auto px-6 lg:px-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="w-full border-t border-graphite mt-24 bg-carbon/40">
          <div className="w-full max-w-[1760px] mx-auto px-6 lg:px-8 py-8 flex flex-col md:flex-row justify-between items-center text-[12px] text-ash font-mono">
            <div className="flex items-center gap-4 mb-4 md:mb-0">
              <span>Razorpay AI Buildathon 2026</span>
              <span>·</span>
              <span>Track 5: Open Track</span>
              <span>·</span>
              <span className="text-mist">Deterministic Control Layer</span>
            </div>
            <div className="flex gap-6">
              <Link href="/architecture" className="hover:text-mist transition-colors">Security Boundaries</Link>
              <Link href="/evaluation" className="hover:text-mist transition-colors">Benchmark Metrics</Link>
              <Link href="/audit" className="hover:text-mist transition-colors">Audit Integrity</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
