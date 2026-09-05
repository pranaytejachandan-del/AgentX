'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchProcurementRequests, approveProcurement, rejectProcurement } from '@/lib/api';
import { ProcurementListResponse, ProcurementRequestSummary } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatINR, formatDate } from '@/lib/utils';
import { ShieldAlert, CheckCircle, XCircle, ArrowRight, RefreshCw, AlertCircle } from 'lucide-react';

export default function ApprovalsPage() {
  const [data, setData] = useState<ProcurementListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionReqId, setActionReqId] = useState<number | null>(null);
  const [actionNotes, setActionNotes] = useState<Record<number, string>>({});

  const loadPending = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchProcurementRequests('APPROVAL_REQUIRED');
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load approval queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPending();
  }, []);

  const handleApprove = async (reqId: number) => {
    setActionReqId(reqId);
    try {
      await approveProcurement(reqId, actionNotes[reqId] || 'Approved via Approvals Queue');
      await loadPending();
    } catch (err: any) {
      alert(err.message || 'Approval failed.');
    } finally {
      setActionReqId(null);
    }
  };

  const handleReject = async (reqId: number) => {
    setActionReqId(reqId);
    try {
      await rejectProcurement(reqId, actionNotes[reqId] || 'Rejected via Approvals Queue');
      await loadPending();
    } catch (err: any) {
      alert(err.message || 'Rejection failed.');
    } finally {
      setActionReqId(null);
    }
  };

  const pendingItems = data?.items || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-amber-600" />
            Human Approvals Queue
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Review and authorize high-value transactions that exceed the ₹100,000 financial threshold.
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={loadPending} isLoading={loading} icon={<RefreshCw className="w-3.5 h-3.5" />}>
          Refresh Queue
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && !data && (
        <div className="p-8 text-center text-slate-400 text-sm animate-pulse">
          Checking pending approval requests...
        </div>
      )}

      {data && pendingItems.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="p-12 text-center space-y-3">
            <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" />
            <h3 className="text-base font-bold text-slate-800">Approvals Queue is Clear</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              There are currently no transactions awaiting human authorization.
            </p>
          </CardContent>
        </Card>
      )}

      {pendingItems.map((req) => {
        const order = req.order;

        return (
          <Card key={req.id} className="border-amber-300 shadow-md">
            <CardHeader className="bg-amber-50/60 border-b border-amber-200">
              <CardTitle className="text-slate-900 font-mono">
                Procurement Request #{req.id}
              </CardTitle>
              <Badge variant="warning" className="text-xs">
                THRESHOLD &gt; ₹100,000
              </Badge>
            </CardHeader>

            <CardContent className="space-y-4 pt-5">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-400 font-medium block">Item Description</span>
                  <span className="font-bold text-slate-900">
                    {req.extracted_constraints?.item_description || req.raw_prompt}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 font-medium block">Vendor</span>
                  <span className="font-bold text-slate-900">{order?.vendor_name || '—'}</span>
                </div>

                <div>
                  <span className="text-slate-400 font-medium block">Quantity / Agreed Unit Price</span>
                  <span className="font-bold text-slate-900">
                    {order?.quantity} units @ {formatINR(order?.negotiated_unit_price)}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 font-medium block">Total Value</span>
                  <span className="font-extrabold text-amber-900 text-base">
                    {formatINR(order?.total_amount)}
                  </span>
                </div>
              </div>

              {/* Notes Input */}
              <div className="flex flex-col sm:flex-row items-center gap-3">
                <input
                  type="text"
                  placeholder="Optional approval/rejection audit note..."
                  value={actionNotes[req.id] || ''}
                  onChange={(e) => setActionNotes({ ...actionNotes, [req.id]: e.target.value })}
                  className="flex-1 text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                />

                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleReject(req.id)}
                    isLoading={actionReqId === req.id}
                    icon={<XCircle className="w-4 h-4" />}
                  >
                    Reject
                  </Button>

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleApprove(req.id)}
                    isLoading={actionReqId === req.id}
                    icon={<CheckCircle className="w-4 h-4" />}
                    className="bg-emerald-600 hover:bg-emerald-700"
                  >
                    Approve
                  </Button>

                  <Link href={`/procurement/${req.id}`}>
                    <Button variant="outline" size="sm" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                      Details
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
