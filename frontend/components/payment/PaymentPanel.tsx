import React, { useState, useEffect } from 'react';
import { OrderSummary, ExecutionStage } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { formatINR, getPaymentBadgeColor } from '@/lib/utils';
import { createPaymentLink } from '@/lib/api';
import { CreditCard, ExternalLink, RefreshCw, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

interface PaymentPanelProps {
  requestId: number;
  order?: OrderSummary | null;
  executionStatus: ExecutionStage;
  onRefresh: () => void;
}

export function PaymentPanel({ requestId, order, executionStatus, onRefresh }: PaymentPanelProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isReadyForPayment = executionStatus === 'READY_FOR_PAYMENT';
  const isPaymentPending = executionStatus === 'PAYMENT_PENDING' || order?.payment_status === 'PAYMENT_PENDING';
  const isPaid = executionStatus === 'PAID' || order?.payment_status === 'PAID';

  // Auto-polling when payment is pending
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isPaymentPending && !isPaid) {
      timer = setInterval(() => {
        onRefresh();
      }, 5000); // refresh every 5 seconds
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPaymentPending, isPaid, onRefresh]);

  const handleCreatePayment = async () => {
    setIsCreating(true);
    setErrorMsg(null);
    try {
      await createPaymentLink(requestId);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Payment link creation failed.');
    } finally {
      setIsCreating(false);
    }
  };

  if (!order && !isReadyForPayment) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <CreditCard className="w-5 h-5 text-sky-600" />
            Razorpay Payment Execution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 italic">
            Payment flow will unlock once the deal passes financial guardrails and human approval.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={isPaid ? 'border-emerald-300 bg-emerald-50/20' : undefined}>
      <CardHeader>
        <CardTitle>
          <CreditCard className="w-5 h-5 text-sky-600" />
          Razorpay Payment Execution & Webhook Status
        </CardTitle>

        {order?.payment_status && (
          <Badge className={getPaymentBadgeColor(order.payment_status)}>
            {order.payment_status === 'PAID' && <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />}
            {order.payment_status === 'PAYMENT_PENDING' && <Clock className="w-3.5 h-3.5 mr-1 animate-spin text-blue-600" />}
            Payment Status: {order.payment_status}
          </Badge>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {errorMsg && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* State 1: Ready to Create Payment */}
        {isReadyForPayment && !order?.razorpay_payment_link_url && (
          <div className="p-4 bg-sky-50 border border-sky-200 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <h4 className="text-sm font-bold text-slate-900">Deal Authorized for Payment</h4>
              <p className="text-xs text-slate-600 mt-0.5">
                Total Authorized Amount: <span className="font-bold text-sky-900">{formatINR(order?.total_amount)}</span>
              </p>
            </div>

            <Button
              variant="primary"
              onClick={handleCreatePayment}
              isLoading={isCreating}
              icon={<CreditCard className="w-4 h-4" />}
            >
              Generate Razorpay Payment Link
            </Button>
          </div>
        )}

        {/* State 2: Payment Link Created */}
        {order?.razorpay_payment_link_url && (
          <div className="space-y-4">
            <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium">Razorpay Link ID</span>
                <span className="font-mono font-semibold text-slate-800">
                  {order.razorpay_payment_link_id || 'N/A'}
                </span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium">Authorized Amount</span>
                <span className="font-extrabold text-base text-slate-900">
                  {formatINR(order.total_amount)}
                </span>
              </div>

              {order.razorpay_payment_id && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Razorpay Payment ID</span>
                  <span className="font-mono font-semibold text-emerald-700">
                    {order.razorpay_payment_id}
                  </span>
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {!isPaid && (
                <a
                  href={order.razorpay_payment_link_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm rounded-lg shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <CreditCard className="w-4 h-4" />
                  Pay with Razorpay
                  <ExternalLink className="w-4 h-4 ml-1" />
                </a>
              )}

              <Button variant="outline" size="md" onClick={onRefresh} icon={<RefreshCw className="w-4 h-4" />}>
                Refresh Status
              </Button>
            </div>

            {isPaymentPending && (
              <p className="text-xs text-blue-600 font-medium flex items-center gap-1.5 animate-pulse">
                <Clock className="w-3.5 h-3.5" />
                Waiting for Razorpay webhook confirmation... Page auto-refreshes every 5 seconds.
              </p>
            )}

            {isPaid && (
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 flex items-center gap-2.5">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <div>
                  <p className="font-bold text-emerald-950">Payment Successfully Confirmed</p>
                  <p className="text-[11px] text-emerald-700">
                    Razorpay HMAC-SHA256 signature verified via server webhook.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
