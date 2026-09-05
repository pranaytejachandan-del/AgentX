'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchProcurementRequests } from '@/lib/api';
import { ProcurementListResponse } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatINR, formatDate, getStageLabel, getStageBadgeColor } from '@/lib/utils';
import {
  Activity,
  Clock,
  ShieldAlert,
  CreditCard,
  CheckCircle2,
  XCircle,
  PlusCircle,
  ArrowRight,
  RefreshCw,
  Search,
  Filter,
} from 'lucide-react';

export default function DashboardPage() {
  const [data, setData] = useState<ProcurementListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchProcurementRequests();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to AgentX backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const metrics = data?.metrics || {
    total: 0,
    active: 0,
    awaiting_approval: 0,
    payment_pending: 0,
    completed: 0,
    failed: 0,
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Dashboard Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 rounded-2xl text-white shadow-lg border border-slate-800">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">AgentX Procurement Command Center</h1>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl">
            Autonomous B2B purchasing agents, multi-turn AI negotiation, deterministic financial safety guardrails, and real-time execution trace viewer.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={loadData} isLoading={loading} icon={<RefreshCw className="w-4 h-4" />}>
            Refresh
          </Button>

          <Link href="/procurement/new">
            <Button variant="primary" size="sm" icon={<PlusCircle className="w-4 h-4" />}>
              Start AgentX
            </Button>
          </Link>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Active Requests */}
        <Card className="border-l-4 border-l-sky-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Requests</span>
              <Clock className="w-4 h-4 text-sky-500" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 mt-2">{metrics.active}</p>
            <p className="text-[11px] text-slate-400 mt-1">In parsing, discovery or negotiation</p>
          </CardContent>
        </Card>

        {/* Awaiting Approval */}
        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Awaiting Approval</span>
              <ShieldAlert className="w-4 h-4 text-amber-500" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 mt-2">{metrics.awaiting_approval}</p>
            <p className="text-[11px] text-slate-400 mt-1">&gt; ₹100,000 threshold requirement</p>
          </CardContent>
        </Card>

        {/* Payment Pending */}
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Payment Pending</span>
              <CreditCard className="w-4 h-4 text-blue-500" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 mt-2">{metrics.payment_pending}</p>
            <p className="text-[11px] text-slate-400 mt-1">Authorized Razorpay links</p>
          </CardContent>
        </Card>

        {/* Completed */}
        <Card className="border-l-4 border-l-emerald-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Completed</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 mt-2">{metrics.completed}</p>
            <p className="text-[11px] text-slate-400 mt-1">Paid and fulfilled orders</p>
          </CardContent>
        </Card>

        {/* Failed */}
        <Card className="border-l-4 border-l-rose-500">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Failed / Cancelled</span>
              <XCircle className="w-4 h-4 text-rose-500" />
            </div>
            <p className="text-2xl font-extrabold text-slate-900 mt-2">{metrics.failed}</p>
            <p className="text-[11px] text-slate-400 mt-1">Policy violations or rejected</p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Procurement Requests Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            <Activity className="w-5 h-5 text-sky-600" />
            Recent Procurement Requests
          </CardTitle>

          <Link href="/procurement">
            <Button variant="ghost" size="sm" icon={<ArrowRight className="w-4 h-4" />}>
              View All Procurements
            </Button>
          </Link>
        </CardHeader>

        <CardContent className="p-0">
          {error && (
            <div className="p-6 text-center">
              <p className="text-sm text-rose-600 font-medium">{error}</p>
              <Button variant="outline" size="sm" onClick={loadData} className="mt-3">
                Retry Connection
              </Button>
            </div>
          )}

          {loading && !data && (
            <div className="p-8 text-center text-slate-400 text-sm animate-pulse">
              Loading procurement requests...
            </div>
          )}

          {data && data.items.length === 0 && (
            <div className="p-12 text-center space-y-3">
              <Activity className="w-8 h-8 text-slate-300 mx-auto" />
              <h3 className="text-base font-semibold text-slate-700">No Procurement Requests Found</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Create a procurement request using natural language to launch AgentX autonomous purchasing agents.
              </p>
              <Link href="/procurement/new">
                <Button variant="primary" size="sm" icon={<PlusCircle className="w-4 h-4" />}>
                  Create First Request
                </Button>
              </Link>
            </div>
          )}

          {data && data.items.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-y border-slate-200 text-slate-500 uppercase font-semibold text-[11px] tracking-wider">
                  <tr>
                    <th className="px-6 py-3">Req ID</th>
                    <th className="px-6 py-3">Description / Product</th>
                    <th className="px-6 py-3">Status Stage</th>
                    <th className="px-6 py-3">Vendor</th>
                    <th className="px-6 py-3">Amount</th>
                    <th className="px-6 py-3">Created Date</th>
                    <th className="px-6 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.slice(0, 10).map((req) => (
                    <tr key={req.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-slate-900">#{req.id}</td>
                      <td className="px-6 py-4 max-w-xs">
                        <p className="font-semibold text-slate-900 truncate">
                          {req.extracted_constraints?.item_description || req.raw_prompt}
                        </p>
                        <p className="text-[11px] text-slate-400 line-clamp-1 italic mt-0.5">
                          "{req.raw_prompt}"
                        </p>
                      </td>
                      <td className="px-6 py-4">
                        <Badge className={getStageBadgeColor(req.execution_status)}>
                          {getStageLabel(req.execution_status)}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-slate-800 font-medium">
                        {req.order?.vendor_name || '—'}
                      </td>
                      <td className="px-6 py-4 font-bold text-slate-900">
                        {req.order?.total_amount
                          ? formatINR(req.order.total_amount)
                          : req.max_budget
                          ? formatINR(req.max_budget)
                          : '—'}
                      </td>
                      <td className="px-6 py-4 text-slate-500">{formatDate(req.created_at)}</td>
                      <td className="px-6 py-4 text-right">
                        <Link href={`/procurement/${req.id}`}>
                          <Button variant="outline" size="sm" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                            View Execution
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
