import React, { useState } from 'react';
import { OrderSummary } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { formatINR } from '@/lib/utils';
import { approveProcurement, rejectProcurement } from '@/lib/api';
import { ShieldAlert, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface HumanApprovalCardProps {
  requestId: number;
  order: OrderSummary;
  onRefresh: () => void;
}

export function HumanApprovalCard({ requestId, order, onRefresh }: HumanApprovalCardProps) {
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [notes, setNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isPending = order.approval_status === 'PENDING';

  if (!isPending) {
    return (
      <Card className="border-l-4 border-l-emerald-500">
        <CardContent className="py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <h4 className="text-sm font-semibold text-slate-900">
                Human Approval Decision: {order.approval_status}
              </h4>
              <p className="text-xs text-slate-500">
                Transaction value {formatINR(order.total_amount)}
              </p>
            </div>
          </div>
          <Badge variant={order.approval_status === 'APPROVED' ? 'success' : 'danger'}>
            {order.approval_status}
          </Badge>
        </CardContent>
      </Card>
    );
  }

  const handleApprove = async () => {
    setIsApproving(true);
    setErrorMsg(null);
    try {
      await approveProcurement(requestId, notes);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Approval failed.');
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    setIsRejecting(true);
    setErrorMsg(null);
    try {
      await rejectProcurement(requestId, notes);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Rejection failed.');
    } finally {
      setIsRejecting(false);
    }
  };

  return (
    <Card className="border-2 border-amber-300 bg-amber-50/20 shadow-md">
      <CardHeader className="bg-amber-100/60 border-b border-amber-200">
        <CardTitle className="text-amber-950 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-700 animate-pulse" />
          Human Approval Required
        </CardTitle>
        <Badge variant="warning" className="text-xs">
          PENDING APPROVAL
        </Badge>
      </CardHeader>

      <CardContent className="space-y-4 pt-5">
        <p className="text-xs text-slate-700 leading-relaxed">
          This transaction total <span className="font-bold text-slate-900">{formatINR(order.total_amount)}</span> exceeds the mandatory human approval threshold of <span className="font-bold text-slate-900">₹100,000</span>. Review the negotiated deal terms below and authorize execution.
        </p>

        {errorMsg && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Validated Deal Summary Table */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-white p-3.5 rounded-xl border border-slate-200 text-xs">
          <div>
            <span className="text-slate-400 font-medium block">Vendor Name</span>
            <span className="font-bold text-slate-900">{order.vendor_name || `Vendor #${order.vendor_id}`}</span>
          </div>
          <div>
            <span className="text-slate-400 font-medium block">Product</span>
            <span className="font-bold text-slate-900">{order.product_title || `Product #${order.product_id}`}</span>
          </div>
          <div>
            <span className="text-slate-400 font-medium block">Quantity / Unit Price</span>
            <span className="font-bold text-slate-900">
              {order.quantity} units @ {formatINR(order.negotiated_unit_price)}
            </span>
          </div>
          <div>
            <span className="text-slate-400 font-medium block">Total Value</span>
            <span className="font-extrabold text-amber-800 text-sm">{formatINR(order.total_amount)}</span>
          </div>
        </div>

        {/* Optional Notes Input */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Approval / Rejection Audit Notes (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. Approved under Q3 Office Procurement Budget..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            variant="danger"
            onClick={handleReject}
            isLoading={isRejecting}
            disabled={isApproving}
            icon={<XCircle className="w-4 h-4" />}
          >
            Reject Deal
          </Button>

          <Button
            variant="primary"
            onClick={handleApprove}
            isLoading={isApproving}
            disabled={isRejecting}
            icon={<CheckCircle className="w-4 h-4" />}
            className="bg-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500"
          >
            Approve Deal
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
