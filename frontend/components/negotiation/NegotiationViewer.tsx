import React from 'react';
import { NegotiationTrace, NegotiationSummary } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatINR } from '@/lib/utils';
import { MessageSquare, Bot, Building2, TrendingDown, CheckCircle2, ArrowRight } from 'lucide-react';

interface NegotiationViewerProps {
  traces?: NegotiationTrace[];
  summary?: NegotiationSummary | null;
}

export function NegotiationViewer({ traces, summary }: NegotiationViewerProps) {
  if (!traces || traces.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <MessageSquare className="w-5 h-5 text-sky-600" />
            Agent Multi-Turn Negotiation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 italic">
            No negotiation turns recorded yet. AgentX will negotiate with the selected vendor.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <MessageSquare className="w-5 h-5 text-sky-600" />
          Autonomous Multi-Turn Buyer & Supplier Negotiation ({traces.length} Turns)
        </CardTitle>
        {summary && (
          <Badge variant="success" className="text-xs">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            {summary.status || 'DEAL AGREED'}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Savings Summary Banner */}
        {summary && (
          <div className="bg-gradient-to-r from-emerald-50 via-teal-50 to-sky-50 border border-emerald-200/80 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                <TrendingDown className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">Negotiated Deal Savings Summary</h4>
                <p className="text-xs text-slate-600">
                  Initial Listed Price: <span className="font-semibold text-slate-900">{formatINR(summary.initial_price)}</span>
                  {' → '}
                  Final Agreed Price: <span className="font-bold text-emerald-700">{formatINR(summary.final_price)}</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-right">
              <div className="bg-white/80 px-3.5 py-1.5 rounded-lg border border-emerald-200/60">
                <span className="text-[11px] text-slate-500 font-medium block uppercase tracking-wider">Unit Savings</span>
                <span className="text-sm font-bold text-emerald-700">{formatINR(summary.unit_savings)} / unit</span>
              </div>
              <div className="bg-emerald-600 text-white px-3.5 py-1.5 rounded-lg shadow-xs">
                <span className="text-[11px] text-emerald-100 font-medium block uppercase tracking-wider">Total Savings</span>
                <span className="text-sm font-extrabold">{formatINR(summary.total_savings)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Multi-Turn Dialogue Transcript */}
        <div className="space-y-4 relative before:absolute before:left-4 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
          {traces.map((trace) => (
            <div key={trace.id} className="relative pl-10 space-y-3">
              {/* Turn Indicator */}
              <div className="absolute left-2.5 top-1.5 -translate-x-1/2 w-4 h-4 rounded-full bg-sky-600 text-white flex items-center justify-center text-[10px] font-bold ring-4 ring-white">
                {trace.turn_number}
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Turn #{trace.turn_number}</span>
                <Badge
                  variant={
                    trace.negotiation_status === 'ACCEPTED'
                      ? 'success'
                      : trace.negotiation_status === 'COUNTER_OFFER'
                      ? 'info'
                      : 'default'
                  }
                >
                  {trace.negotiation_status}
                </Badge>
              </div>

              {/* Buyer Agent Message */}
              {trace.buyer_agent_message && (
                <div className="bg-sky-50/80 border border-sky-100 p-3.5 rounded-xl text-xs text-slate-800">
                  <div className="flex items-center gap-1.5 text-sky-800 font-semibold mb-1">
                    <Bot className="w-4 h-4 text-sky-600" />
                    AgentX Buyer Agent
                    {trace.proposed_price && (
                      <span className="ml-auto font-bold text-sky-700 bg-white px-2 py-0.5 rounded border border-sky-200">
                        Proposed: {formatINR(trace.proposed_price)}
                      </span>
                    )}
                  </div>
                  <p className="leading-relaxed font-sans">{trace.buyer_agent_message}</p>
                </div>
              )}

              {/* Supplier Simulator Response */}
              {trace.supplier_agent_message && (
                <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl text-xs text-slate-800">
                  <div className="flex items-center gap-1.5 text-slate-800 font-semibold mb-1">
                    <Building2 className="w-4 h-4 text-slate-600" />
                    Supplier Simulator
                    {trace.counter_price && (
                      <span className="ml-auto font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200">
                        Counter: {formatINR(trace.counter_price)}
                      </span>
                    )}
                  </div>
                  <p className="leading-relaxed font-sans">{trace.supplier_agent_message}</p>
                </div>
              )}

              {/* Decision Summary */}
              {trace.decision_summary && (
                <div className="text-xs bg-amber-50/60 border border-amber-200/80 text-amber-900 p-2.5 rounded-lg flex items-center gap-2">
                  <ArrowRight className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  <span className="font-semibold text-amber-800">Agent Decision Rationale:</span>
                  <span>{trace.decision_summary}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
