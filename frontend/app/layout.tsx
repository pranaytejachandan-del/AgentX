import './globals.css';
import React from 'react';
import Link from 'next/link';
import { Bot, LayoutDashboard, ShoppingCart, ShieldAlert, PlusCircle, Server } from 'lucide-react';
import { checkBackendHealth } from '@/lib/api';

export const metadata = {
  title: 'AgentX — Autonomous B2B Procurement Platform',
  description: 'AI-Powered Procurement Dashboard, Multi-Turn Agent Negotiation & Execution Trace Viewer',
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const health = await checkBackendHealth();
  const isOnline = health.status === 'healthy' || health.status === 'connected';

  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 min-h-screen flex flex-col font-sans">
        {/* Top Enterprise Header */}
        <header className="sticky top-0 z-40 bg-slate-900 text-white border-b border-slate-800 shadow-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            {/* Logo & Brand */}
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-blue-600 flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform">
                <Bot className="w-6 h-6 stroke-[2.2]" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-lg font-extrabold tracking-tight text-white">AgentX</span>
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-400/30">
                    B2B Platform
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 font-medium">Autonomous Procurement & Trace Engine</p>
              </div>
            </Link>

            {/* Main Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              <Link
                href="/"
                className="px-3.5 py-2 rounded-lg text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-2"
              >
                <LayoutDashboard className="w-4 h-4 text-sky-400" />
                Dashboard
              </Link>

              <Link
                href="/procurement"
                className="px-3.5 py-2 rounded-lg text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-2"
              >
                <ShoppingCart className="w-4 h-4 text-emerald-400" />
                Procurements
              </Link>

              <Link
                href="/approvals"
                className="px-3.5 py-2 rounded-lg text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-2"
              >
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                Approvals Queue
              </Link>
            </nav>

            {/* Right CTAs */}
            <div className="flex items-center gap-3">
              {/* Backend Status Indicator */}
              <div
                className={`hidden sm:flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full border ${
                  isOnline
                    ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80'
                    : 'bg-rose-950/80 text-rose-300 border-rose-800/80'
                }`}
              >
                <Server className="w-3 h-3" />
                <span>Backend: {isOnline ? 'Online' : 'Connected'}</span>
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                  }`}
                />
              </div>

              <Link
                href="/procurement/new"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs rounded-lg shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-sky-400"
              >
                <PlusCircle className="w-4 h-4" />
                New Procurement
              </Link>
            </div>
          </div>
        </header>

        {/* Main Content Body */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">{children}</main>

        {/* Footer */}
        <footer className="bg-white border-t border-slate-200/80 py-6 mt-12 text-slate-500 text-xs">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900">AgentX</span>
              <span>— Autonomous B2B Purchasing & Agent Execution Trace Viewer</span>
            </div>
            <p className="text-slate-400">Powered by LangGraph, pgvector, FastAPI & Razorpay</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
