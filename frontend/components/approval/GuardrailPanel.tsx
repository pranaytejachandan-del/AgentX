import React from 'react';
import { GuardrailResult } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatINR } from '@/lib/utils';
import { ShieldCheck, CheckCircle2, XCircle, AlertTriangle, Lock } from 'lucide-react';

interface GuardrailPanelProps {
  guardrailResult?: GuardrailResult | null;
}

export function GuardrailPanel({ guardrailResult }: GuardrailPanelProps) {
  if (!guardrailResult) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <ShieldCheck className="w-5 h-5 text-sky-600" />
            Financial Guardrails & Policy Check
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 italic">
            Deterministic policy check not evaluated yet. Will run automatically after deal agreement.
          </p>
        </CardContent>
      </Card>
    );
  }

  const { passed_all, requires_human_approval, approval_threshold = 100000, total_amount, rules, error } = guardrailResult;

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <ShieldCheck className="w-5 h-5 text-sky-600" />
          Deterministic Financial Guardrails & Business Policy Checks
        </CardTitle>
        <div className="flex items-center gap-2">
          {passed_all ? (
            <Badge variant="success" className="text-xs">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
              All Rules Passed
            </Badge>
          ) : (
            <Badge variant="danger" className="text-xs">
              <XCircle className="w-3.5 h-3.5 mr-1" />
              Policy Violation / Blocked
            </Badge>
          )}

          {requires_human_approval && (
            <Badge variant="warning" className="text-xs">
              <Lock className="w-3.5 h-3.5 mr-1" />
              Approval Required ({formatINR(total_amount)} &gt; {formatINR(approval_threshold)})
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>Policy Error: {error}</span>
          </div>
        )}

        {/* Rules Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {rules && rules.length > 0 ? (
            rules.map((rule, idx) => (
              <div
                key={rule.rule_name || idx}
                className={`p-3.5 rounded-xl border flex items-start justify-between gap-3 transition-colors ${
                  rule.passed
                    ? 'bg-emerald-50/30 border-emerald-200/80'
                    : 'bg-rose-50/50 border-rose-200'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  {rule.passed ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <h5 className="text-xs font-bold text-slate-900">{rule.rule_name}</h5>
                    <p className="text-xs text-slate-600 mt-0.5">{rule.message}</p>

                    {(rule.actual_value != null || rule.expected_threshold != null) && (
                      <div className="mt-1 text-[11px] font-mono text-slate-500">
                        {rule.actual_value != null && <span>Actual: {String(rule.actual_value)}</span>}
                        {rule.expected_threshold != null && (
                          <span className="ml-2">| Max/Expected: {String(rule.expected_threshold)}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <Badge variant={rule.passed ? 'success' : 'danger'} className="text-[10px] uppercase shrink-0">
                  {rule.passed ? 'PASSED' : 'BLOCKED'}
                </Badge>
              </div>
            ))
          ) : (
            <div className="col-span-2 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
              8 deterministic safety checks evaluated: Max Unit Price, Max Budget, Quantity Integrity, Delivery Time, Required Certifications, GST Verification, Currency, Product/Vendor Integrity.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
