'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { fetchProcurementRequestDetail } from '@/lib/api';
import { ProcurementDetailResponse } from '@/lib/types';
import { ExecutionStepper } from '@/components/procurement/ExecutionStepper';
import { RequirementsCard } from '@/components/procurement/RequirementsCard';
import { OfferRankingList } from '@/components/offers/OfferRankingList';
import { NegotiationViewer } from '@/components/negotiation/NegotiationViewer';
import { GuardrailPanel } from '@/components/approval/GuardrailPanel';
import { HumanApprovalCard } from '@/components/approval/HumanApprovalCard';
import { PaymentPanel } from '@/components/payment/PaymentPanel';
import { ExecutionTraceViewer } from '@/components/trace/ExecutionTraceViewer';
import { AuditEventLog } from '@/components/trace/AuditEventLog';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { formatINR, formatDate, getStageLabel, getStageBadgeColor } from '@/lib/utils';
import { ArrowLeft, RefreshCw, Bot, ShoppingCart, Clock, CheckCircle2 } from 'lucide-react';

// Stages where we should auto-poll the backend for status updates
const ACTIVE_STAGES = new Set([
  'CREATED', 'PARSING', 'DISCOVERING', 'NEGOTIATING', 'POLICY_CHECK',
]);

// Stages considered terminal (no further polling needed)
const TERMINAL_STAGES = new Set([
  'APPROVAL_REQUIRED', 'READY_FOR_PAYMENT', 'PAYMENT_PENDING', 'PAID', 'COMPLETED', 'FAILED', 'CANCELLED',
]);

export default function RequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const requestId = Number(params?.id);

  const [data, setData] = useState<ProcurementDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const loadDetail = useCallback(async () => {
    if (!requestId || isNaN(requestId)) return;
    setError(null);
    try {
      const res = await fetchProcurementRequestDetail(requestId);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load procurement request details.');
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  // Auto-polling: refresh every 4 seconds while the workflow is still in-flight
  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    if (!data) return;
    const stage = data.request?.execution_status;

    // Clear any existing poll
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    // Start polling for active (non-terminal, non-approval-wait) stages
    if (ACTIVE_STAGES.has(stage)) {
      pollingRef.current = setInterval(() => {
        loadDetail();
      }, 4000);
    }

    // Also poll PAYMENT_PENDING to catch webhook updates
    if (stage === 'PAYMENT_PENDING') {
      pollingRef.current = setInterval(() => {
        loadDetail();
      }, 5000);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [data?.request?.execution_status, loadDetail]);

  if (loading && !data) {
    return (
      <div className="p-12 text-center text-slate-400 text-sm animate-pulse space-y-3">
        <Bot className="w-8 h-8 text-sky-500 mx-auto animate-bounce" />
        <p>Loading AgentX Execution Trace &amp; Request Data...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-2xl mx-auto p-8 bg-rose-50 border border-rose-200 rounded-2xl text-center space-y-4">
        <h3 className="text-lg font-bold text-rose-900">Procurement Request Not Found</h3>
        <p className="text-xs text-rose-700">{error || `Request #${requestId} could not be loaded.`}</p>
        <div className="flex items-center justify-center gap-3">
          <Button variant="outline" size="sm" onClick={() => router.push('/procurement')}>
            Back to Procurements
          </Button>
          <Button variant="primary" size="sm" onClick={loadDetail}>
            Retry Loading
          </Button>
        </div>
      </div>
    );
  }

  const { request, order, discovered_offers, negotiation_traces, negotiation_summary, guardrail_result, execution_trace, audit_events } = data;

  // Show Approve Deal whenever status is APPROVAL_REQUIRED, even if order is temporarily null
  const showApprovalCard = request.execution_status === 'APPROVAL_REQUIRED' && order?.approval_status === 'PENDING';

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* 1. Header & Stage Action Bar */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <Link
              href="/procurement"
              className="text-xs text-slate-400 hover:text-slate-700 transition-colors flex items-center gap-1 font-medium"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </Link>

            <h1 className="text-xl font-extrabold text-slate-900 font-mono">
              Procurement Request #{request.id}
            </h1>

            <Badge className={getStageBadgeColor(request.execution_status)}>
              {getStageLabel(request.execution_status)}
            </Badge>

            {ACTIVE_STAGES.has(request.execution_status) && (
              <span className="text-[10px] text-sky-600 font-semibold animate-pulse flex items-center gap-1">
                <Clock className="w-3 h-3" /> Auto-refreshing…
              </span>
            )}
          </div>

          <p className="text-xs text-slate-500 mt-1 max-w-2xl line-clamp-1">
            &quot;{request.raw_prompt}&quot;
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button variant="outline" size="sm" onClick={loadDetail} icon={<RefreshCw className="w-3.5 h-3.5" />}>
            Refresh State
          </Button>
        </div>
      </div>

      {/* 2. Execution Progress Stepper */}
      <ExecutionStepper currentStage={request.execution_status} />

      {/* 3. Human Approval UI — shown whenever APPROVAL_REQUIRED + order.approval_status PENDING */}
      {showApprovalCard && order && (
        <HumanApprovalCard requestId={request.id} order={order} onRefresh={loadDetail} />
      )}

      {/* 4. Request Requirements Card */}
      <RequirementsCard
        constraints={request.extracted_constraints}
        rawPrompt={request.raw_prompt}
        maxBudget={request.max_budget}
      />

      {/* 5. Ranked Offers UI */}
      <OfferRankingList offers={discovered_offers} />

      {/* 6. Multi-Turn Negotiation Viewer */}
      <NegotiationViewer traces={negotiation_traces} summary={negotiation_summary} />

      {/* 7. Financial Guardrails Panel */}
      <GuardrailPanel guardrailResult={guardrail_result} />

      {/* 8. Razorpay Payment Panel */}
      <PaymentPanel
        requestId={request.id}
        order={order}
        executionStatus={request.execution_status}
        onRefresh={loadDetail}
      />

      {/* 9. Agent Execution Trace Viewer */}
      <ExecutionTraceViewer events={execution_trace} />

      {/* 10. Immutable Audit Log */}
      <AuditEventLog events={audit_events} />
    </div>
  );
}


