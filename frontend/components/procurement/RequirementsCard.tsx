import React from 'react';
import { ProcurementConstraints } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatINR } from '@/lib/utils';
import { FileText, Target, AlertCircle, ShieldCheck, Tag, Calendar, Layers } from 'lucide-react';

interface RequirementsCardProps {
  constraints?: ProcurementConstraints | null;
  rawPrompt?: string;
  maxBudget?: number | null;
}

export function RequirementsCard({ constraints, rawPrompt, maxBudget }: RequirementsCardProps) {
  if (!constraints) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <FileText className="w-5 h-5 text-sky-600" />
            Request Requirements
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 italic">No structured constraints parsed yet.</p>
          {rawPrompt && (
            <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider mb-1">Raw Prompt</p>
              <p className="text-sm text-slate-800 font-mono">"{rawPrompt}"</p>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  const calculatedBudget =
    constraints.quantity && constraints.max_unit_price
      ? constraints.quantity * constraints.max_unit_price
      : maxBudget;

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <FileText className="w-5 h-5 text-sky-600" />
          Extracted Requirements & Financial Constraints
        </CardTitle>
        {constraints.needs_clarification && (
          <Badge variant="warning">
            <AlertCircle className="w-3.5 h-3.5 mr-1" />
            Needs Clarification
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {rawPrompt && (
          <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
              Natural Language Input
            </span>
            <p className="text-sm text-slate-900 font-medium italic">"{rawPrompt}"</p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/50">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium mb-1">
              <Tag className="w-3.5 h-3.5 text-slate-400" />
              Category & Product
            </div>
            <p className="text-sm font-semibold text-slate-900">
              {constraints.item_description}
            </p>
            {constraints.category && (
              <p className="text-xs text-slate-500 mt-0.5">{constraints.category}</p>
            )}
          </div>

          <div className="p-3.5 rounded-lg border border-slate-100 bg-slate-50/50">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium mb-1">
              <Layers className="w-3.5 h-3.5 text-slate-400" />
              Quantity
            </div>
            <p className="text-sm font-semibold text-slate-900">
              {constraints.quantity ? `${constraints.quantity} units` : 'Not specified'}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">Exact unit demand</p>
          </div>

          <div className="p-3.5 rounded-lg border border-emerald-100 bg-emerald-50/40">
            <div className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold mb-1">
              <Target className="w-3.5 h-3.5 text-emerald-600" />
              Target Unit Price
            </div>
            <p className="text-base font-bold text-emerald-800">
              {constraints.target_unit_price ? formatINR(constraints.target_unit_price) : 'N/A'}
            </p>
            <p className="text-[11px] text-emerald-600 mt-0.5 font-medium">
              Optimization Objective
            </p>
          </div>

          <div className="p-3.5 rounded-lg border border-rose-100 bg-rose-50/40">
            <div className="flex items-center gap-1.5 text-xs text-rose-700 font-semibold mb-1">
              <ShieldCheck className="w-3.5 h-3.5 text-rose-600" />
              Maximum Unit Price
            </div>
            <p className="text-base font-bold text-rose-800">
              {constraints.max_unit_price ? formatINR(constraints.max_unit_price) : 'N/A'}
            </p>
            <p className="text-[11px] text-rose-600 mt-0.5 font-medium">
              Hard Policy Constraint Ceiling
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-slate-100">
          <div>
            <span className="text-xs text-slate-500 font-medium block mb-1">Maximum Total Budget</span>
            <p className="text-sm font-bold text-slate-900">
              {calculatedBudget ? formatINR(calculatedBudget) : 'Unbounded'}
            </p>
          </div>

          <div>
            <span className="text-xs text-slate-500 font-medium block mb-1">Max Delivery Lead Time</span>
            <p className="text-sm font-semibold text-slate-800 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              {constraints.max_lead_time_days ? `${constraints.max_lead_time_days} days` : 'Any lead time'}
            </p>
          </div>

          <div>
            <span className="text-xs text-slate-500 font-medium block mb-1">Required Certifications</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {constraints.required_certifications && constraints.required_certifications.length > 0 ? (
                constraints.required_certifications.map((cert) => (
                  <Badge key={cert} variant="info" className="text-[11px]">
                    {cert}
                  </Badge>
                ))
              ) : (
                <span className="text-xs text-slate-400">None required</span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
