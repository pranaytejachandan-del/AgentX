import React, { useState } from 'react';
import { AuditEvent } from '@/lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatDate } from '@/lib/utils';
import { FileCode2, ChevronDown, ChevronUp } from 'lucide-react';

interface AuditEventLogProps {
  events?: AuditEvent[];
}

export function AuditEventLog({ events }: AuditEventLogProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (!events || events.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            <FileCode2 className="w-5 h-5 text-sky-600" />
            Audit Event Logs
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500 italic">No raw audit log records found for this request.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <FileCode2 className="w-5 h-5 text-sky-600" />
          Immutable System Audit Log ({events.length} Records)
        </CardTitle>
        <span className="text-xs text-slate-400 font-medium">Recorded in PostgreSQL DB</span>
      </CardHeader>

      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 border-y border-slate-200 text-slate-500 uppercase font-semibold text-[11px] tracking-wider">
              <tr>
                <th className="px-6 py-3">Timestamp</th>
                <th className="px-6 py-3">Event Type</th>
                <th className="px-6 py-3">Actor</th>
                <th className="px-6 py-3">Summary / Data Payload</th>
                <th className="px-6 py-3 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {events.map((event) => {
                const isExpanded = expandedId === event.id;

                return (
                  <React.Fragment key={event.id}>
                    <tr
                      onClick={() => setExpandedId(isExpanded ? null : event.id)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-3 whitespace-nowrap text-slate-500 font-sans">
                        {formatDate(event.timestamp)}
                      </td>
                      <td className="px-6 py-3 font-semibold text-slate-900">{event.event_type}</td>
                      <td className="px-6 py-3">
                        <Badge variant="outline" className="text-[10px]">
                          {event.actor}
                        </Badge>
                      </td>
                      <td className="px-6 py-3 text-slate-600 font-sans line-clamp-1 max-w-xs">
                        {event.event_data ? JSON.stringify(event.event_data) : 'Audit log recorded.'}
                      </td>
                      <td className="px-6 py-3 text-right text-slate-400">
                        {isExpanded ? <ChevronUp className="w-4 h-4 inline" /> : <ChevronDown className="w-4 h-4 inline" />}
                      </td>
                    </tr>

                    {isExpanded && (
                      <tr className="bg-slate-900 text-slate-200 text-xs">
                        <td colSpan={5} className="p-4 font-mono overflow-x-auto">
                          <p className="text-[11px] text-slate-400 font-sans mb-1 font-semibold uppercase tracking-wider">
                            Event Payload Details (ID: {event.id})
                          </p>
                          <pre className="text-[11px] text-emerald-400 leading-relaxed">
                            {JSON.stringify(event.event_data || {}, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
