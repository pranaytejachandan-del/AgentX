import React from 'react';
import { ExecutionStage } from '@/lib/types';
import { CheckCircle2, Circle, Clock, AlertTriangle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ExecutionStepperProps {
  currentStage: ExecutionStage;
}

const STAGES: { id: ExecutionStage; label: string; desc: string }[] = [
  { id: 'REQUEST_CREATED', label: 'Created', desc: 'Request initiated' },
  { id: 'PARSING', label: 'Parsing', desc: 'NLP intent parsing' },
  { id: 'DISCOVERING', label: 'Discovery', desc: 'Vendor offer discovery' },
  { id: 'NEGOTIATING', label: 'Negotiation', desc: 'Agent multi-turn negotiation' },
  { id: 'POLICY_CHECK', label: 'Policy Check', desc: 'Financial safety guardrails' },
  { id: 'APPROVAL_REQUIRED', label: 'Approval', desc: 'Human authorization (> ₹100k)' },
  { id: 'READY_FOR_PAYMENT', label: 'Payment Ready', desc: 'Authorized deal' },
  { id: 'PAYMENT_PENDING', label: 'Payment Pending', desc: 'Razorpay checkout' },
  { id: 'PAID', label: 'Paid', desc: 'Webhook verified' },
  { id: 'COMPLETED', label: 'Completed', desc: 'Procurement fulfilled' },
];

export function ExecutionStepper({ currentStage }: ExecutionStepperProps) {
  const isFailed = currentStage === 'FAILED' || currentStage === 'CANCELLED';

  const getStageIndex = (stage: ExecutionStage | string) => {
    if (!stage || stage === 'CREATED' || stage === 'REQUEST_CREATED') return 0;
    if (stage === 'PARSING') return 1;
    if (stage === 'DISCOVERING') return 2;
    if (stage === 'NEGOTIATING') return 3;
    if (stage === 'POLICY_CHECK') return 4;
    if (stage === 'APPROVAL_REQUIRED') return 5;
    if (stage === 'READY_FOR_PAYMENT') return 6;
    if (stage === 'PAYMENT_PENDING') return 7;
    if (stage === 'PAID') return 8;
    if (stage === 'COMPLETED') return 9;
    if (stage === 'FAILED' || stage === 'CANCELLED') return 3; // Default failed stage to Negotiation
    const idx = STAGES.findIndex((s) => s.id === stage);
    return idx >= 0 ? idx : 0;
  };

  const currentIndex = getStageIndex(currentStage);

  return (
    <div className="w-full bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wider text-slate-500">
          AgentX Workflow Progression
        </h3>
        <span className="text-xs text-slate-400 font-medium">Source of truth: Backend API</span>
      </div>

      {/* Desktop Stepper */}
      <div className="hidden lg:flex items-center justify-between relative">
        {/* Connecting Line */}
        <div className="absolute left-6 right-6 top-4 h-0.5 bg-slate-200 -z-0" />

        {STAGES.map((stage, idx) => {
          // Created (idx 0) is always completed for any existing request
          const isDone = idx === 0 ? (currentStage !== 'CREATED' && currentStage !== 'REQUEST_CREATED') : (idx < currentIndex || currentStage === 'COMPLETED' || currentStage === 'PAID');
          const isCurrent = (idx === currentIndex && !isDone && !isFailed) || (idx === 0 && (currentStage === 'CREATED' || currentStage === 'REQUEST_CREATED'));
          const isUpcoming = idx > currentIndex && !isDone && !isCurrent;

          return (
            <div key={stage.id} className="relative z-10 flex flex-col items-center group max-w-[90px]">
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center transition-all border-2 font-semibold text-xs bg-white',
                  isDone && 'border-emerald-500 bg-emerald-500 text-white shadow-xs',
                  isCurrent && 'border-sky-600 bg-sky-50 text-sky-700 ring-4 ring-sky-100 animate-pulse',
                  isUpcoming && 'border-slate-300 text-slate-400 bg-white',
                  isFailed && idx === currentIndex && 'border-rose-500 bg-rose-50 text-rose-700 ring-4 ring-rose-100'
                )}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-white stroke-[2.5]" />
                ) : isFailed && idx === currentIndex ? (
                  <XCircle className="w-4 h-4 text-rose-600" />
                ) : isCurrent ? (
                  <Clock className="w-4 h-4 text-sky-600 animate-spin" />
                ) : (
                  <span>{idx + 1}</span>
                )}
              </div>

              <span
                className={cn(
                  'mt-2 text-xs font-semibold text-center leading-tight truncate w-full',
                  isDone && 'text-slate-900',
                  isCurrent && 'text-sky-700 font-bold',
                  isUpcoming && 'text-slate-400',
                  isFailed && idx === currentIndex && 'text-rose-700 font-bold'
                )}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Mobile/Tablet Vertical Stepper */}
      <div className="lg:hidden space-y-3">
        {STAGES.map((stage, idx) => {
          const isDone = idx === 0 ? (currentStage !== 'CREATED' && currentStage !== 'REQUEST_CREATED') : (idx < currentIndex || currentStage === 'COMPLETED' || currentStage === 'PAID');
          const isCurrent = (idx === currentIndex && !isDone && !isFailed) || (idx === 0 && (currentStage === 'CREATED' || currentStage === 'REQUEST_CREATED'));

          return (
            <div key={stage.id} className="flex items-center gap-3">
              <div
                className={cn(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium border shrink-0',
                  isDone && 'border-emerald-500 bg-emerald-500 text-white',
                  isCurrent && 'border-sky-600 bg-sky-50 text-sky-700 ring-2 ring-sky-100',
                  isFailed && idx === currentIndex && 'border-rose-500 bg-rose-50 text-rose-700 ring-2 ring-rose-100',
                  !isDone && !isCurrent && !isFailed && 'border-slate-300 text-slate-400'
                )}
              >
                {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : isFailed && idx === currentIndex ? <XCircle className="w-3.5 h-3.5 text-rose-600" /> : idx + 1}
              </div>
              <div className="flex-1 min-w-0">
                <p className={cn('text-xs font-medium', isCurrent ? 'text-sky-700 font-semibold' : isFailed && idx === currentIndex ? 'text-rose-700 font-semibold' : 'text-slate-700')}>
                  {stage.label}
                </p>
                <p className="text-[11px] text-slate-400 truncate">{stage.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
