'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchProcurementRequests } from '@/lib/api';
import { ProcurementListResponse, ExecutionStage } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatINR, formatDate, getStageLabel, getStageBadgeColor } from '@/lib/utils';
import { ShoppingCart, PlusCircle, Search, ArrowRight, RefreshCw, Filter } from 'lucide-react';

const FILTER_STAGES: { id: string; label: string }[] = [
  { id: 'ALL', label: 'All Requests' },
  { id: 'PARSING', label: 'Parsing' },
  { id: 'DISCOVERING', label: 'Discovering' },
  { id: 'NEGOTIATING', label: 'Negotiating' },
  { id: 'POLICY_CHECK', label: 'Policy Check' },
  { id: 'APPROVAL_REQUIRED', label: 'Awaiting Approval' },
  { id: 'READY_FOR_PAYMENT', label: 'Payment Ready' },
  { id: 'PAYMENT_PENDING', label: 'Payment Pending' },
  { id: 'PAID', label: 'Paid' },
  { id: 'COMPLETED', label: 'Completed' },
];

export default function ProcurementListPage() {
  const [data, setData] = useState<ProcurementListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const loadRequests = async (filter?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchProcurementRequests(filter || activeFilter);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load procurement requests.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests(activeFilter);
  }, [activeFilter]);

  const filteredItems = (data?.items || []).filter((req) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const prompt = (req.raw_prompt || '').toLowerCase();
    const itemDesc = (req.extracted_constraints?.item_description || '').toLowerCase();
    const vendor = (req.order?.vendor_name || '').toLowerCase();
    return prompt.includes(query) || itemDesc.includes(query) || vendor.includes(query);
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <ShoppingCart className="w-6 h-6 text-sky-600" />
            Procurement Requests Management
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Monitor and manage all AgentX B2B purchasing transactions across execution stages.
          </p>
        </div>

        <Link href="/procurement/new">
          <Button variant="primary" icon={<PlusCircle className="w-4 h-4" />}>
            New Procurement Request
          </Button>
        </Link>
      </div>

      {/* Filter Tabs & Search Bar */}
      <Card>
        <CardContent className="p-4 space-y-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Search Input */}
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search prompt, product, or vendor..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-xs pl-9 pr-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => loadRequests(activeFilter)}
              isLoading={loading}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Refresh List
            </Button>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100">
            <Filter className="w-3.5 h-3.5 text-slate-400 mr-1" />
            {FILTER_STAGES.map((filter) => (
              <button
                key={filter.id}
                onClick={() => setActiveFilter(filter.id)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                  activeFilter === filter.id
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Procurement Table / Cards */}
      <Card>
        <CardContent className="p-0">
          {error && (
            <div className="p-6 text-center text-xs text-rose-600 font-medium">
              {error}
            </div>
          )}

          {loading && (
            <div className="p-8 text-center text-slate-400 text-sm animate-pulse">
              Loading requests...
            </div>
          )}

          {!loading && filteredItems.length === 0 && (
            <div className="p-12 text-center text-slate-400 text-sm space-y-2">
              <p className="font-semibold text-slate-600">No matching procurement requests found.</p>
              <p className="text-xs">Try selecting another stage filter or creating a new request.</p>
            </div>
          )}

          {!loading && filteredItems.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 border-y border-slate-200 text-slate-500 uppercase font-semibold text-[11px] tracking-wider">
                  <tr>
                    <th className="px-6 py-3">ID</th>
                    <th className="px-6 py-3">Requirements / Product</th>
                    <th className="px-6 py-3">Status</th>
                    <th className="px-6 py-3">Vendor</th>
                    <th className="px-6 py-3">Deal Total</th>
                    <th className="px-6 py-3">Payment</th>
                    <th className="px-6 py-3">Created</th>
                    <th className="px-6 py-3 text-right">View Trace</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredItems.map((req) => (
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
                      <td className="px-6 py-4">
                        <Badge variant="outline" className="text-[10px]">
                          {req.order?.payment_status || 'NOT_STARTED'}
                        </Badge>
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
