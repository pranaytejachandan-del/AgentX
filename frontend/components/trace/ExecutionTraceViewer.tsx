import React, { useState } from 'react';
import { ExecutionTraceEvent } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDate } from '@/lib/utils';
import { Activity, ChevronDown, ChevronUp, Bot, User, ShieldCheck, CreditCard, Webhook, CheckCircle2 } from 'lucide-react';

interface ExecutionTraceViewerProps {
  events?: ExecutionTraceEvent[];
}

export function ExecutionTraceViewer({ events }: ExecutionTraceViewerProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!events || events.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <Activity className="w-5 h-5 text-sky-600" />
            AgentX Execution Trace Timeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 italic">No execution trace events logged yet.</p>
        </CardContent>
      </Card>
    );
  }

  const getActorIcon = (actor: string) => {
    switch (actor) {
      case 'USER':
        return <User className="w-3.5 h-3.5 text-slate-600" />;
      case 'INTENT_AGENT':
      case 'DISCOVERY_AGENT':
      case 'NEGOTIATION_AGENT':
        return <Bot className="w-3.5 h-3.5 text-sky-600" />;
      case 'GUARDRAIL_ENGINE':
        return <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />;
      case 'HUMAN_ADMIN':
        return <User className="w-3.5 h-3.5 text-amber-600" />;
      case 'PAYMENT_SERVICE':
        return <CreditCard className="w-3.5 h-3.5 text-blue-600" />;
      case 'WEBHOOK':
        return <Webhook className="w-3.5 h-3.5 text-purple-600" />;
      default:
        return <CheckCircle2 className="w-3.5 h-3.5 text-slate-600" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Activity className="w-5 h-5 text-sky-600" />
          AgentX Autonomous Decision Execution Trace ({events.length} Events)
        </CardTitle>
        <span className="text-xs text-slate-400 font-medium">Click any step to inspect decision detail</span>
      </CardHeader>

      <CardContent>
        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
          {events.map((event, idx) => {
            const isExpanded = expandedIndex === idx;

            return (
              <div key={idx} className="relative group">
                {/* Node Dot */}
                <div className="absolute left-[-24px] top-1 -translate-x-1/2 w-4 h-4 rounded-full border-2 border-white bg-sky-600 shadow-xs ring-2 ring-sky-100 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-white" />
                </div>

                <div
                  onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                  className="bg-slate-50/60 hover:bg-slate-100/80 border border-slate-200/80 rounded-xl p-4 cursor-pointer transition-all space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900">{event.title}</span>
                      <Badge variant="outline" className="text-[10px] gap-1 px-2">
                        {getActorIcon(event.actor)}
                        {event.actor}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <span>{formatDate(event.timestamp)}</span>
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                  </div>

                  <p className="text-xs text-slate-700 font-medium leading-relaxed">{event.summary}</p>

                  {/* Expanded Decision Rationale Details */}
                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-slate-200 text-xs space-y-2 text-slate-600 bg-white p-3 rounded-lg border border-slate-100 animate-in fade-in duration-150">
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <span className="text-slate-400 font-medium block">Stage Identifier</span>
                          <span className="font-mono font-semibold text-slate-800">{event.stage}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 font-medium block">Decision Actor</span>
                          <span className="font-semibold text-slate-800">{event.actor}</span>
                        </div>
                      </div>

                      <div>
                        <span className="text-slate-400 font-medium block mb-0.5">Execution Summary</span>
                        <p className="text-slate-800 leading-normal">{event.summary}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
