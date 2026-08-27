'use client';

import { useEffect, useState, useCallback } from 'react';
import clsx from 'clsx';
import { RefreshCw, Radar, FileClock } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { formatTimestamp } from '@/lib/status';
import { Card, SectionHeading, Button, EmptyState } from '@/components/ui/Primitives';

export default function RiskAuditPanel({ settings, refreshKey }) {
  const [tab, setTab] = useState('risk');
  const [risk, setRisk] = useState(null);
  const [audit, setAudit] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setError(null);
    Promise.all([
      api.riskEvents(settings.apiBaseUrl, settings.agentId),
      api.auditLog(settings.apiBaseUrl, { agentId: settings.agentId }),
    ])
      .then(([r, a]) => {
        setRisk(r);
        setAudit(a);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [settings.apiBaseUrl, settings.agentId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <Card className="p-5">
      <SectionHeading
        eyebrow="Signals & the append-only trail"
        title="Risk & audit"
        action={
          <Button variant="ghost" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        }
      />

      <div className="mb-4 inline-flex rounded-lg bg-ink-900 border border-ink-500 p-1">
        <button
          onClick={() => setTab('risk')}
          className={clsx(
            'px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors',
            tab === 'risk' ? 'bg-ink-600 text-fog-bright' : 'text-fog-soft hover:text-fog-bright'
          )}
        >
          <Radar className="h-3.5 w-3.5" /> Risk events
        </button>
        <button
          onClick={() => setTab('audit')}
          className={clsx(
            'px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors',
            tab === 'audit' ? 'bg-ink-600 text-fog-bright' : 'text-fog-soft hover:text-fog-bright'
          )}
        >
          <FileClock className="h-3.5 w-3.5" /> Audit log
        </button>
      </div>

      {error && (
        <div className="mb-4 text-xs font-mono text-signal-block bg-signal-block-dim border border-signal-block/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {tab === 'risk' && (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {risk && risk.length === 0 && <EmptyState title="No risk events" hint="Velocity anomalies and similar signals show up here." />}
          {risk?.map((e) => (
            <div key={e.id} className="p-3 rounded-lg bg-ink-900 border border-ink-500">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-mono uppercase tracking-wide text-signal-hold">{e.event_type}</span>
                <span className="text-xs font-mono text-fog-soft">{formatTimestamp(e.created_at)}</span>
              </div>
              <div className="text-xs font-mono text-fog-soft">
                score {e.risk_score} · {e.transaction_id || 'agent-level'}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'audit' && (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {audit && audit.length === 0 && <EmptyState title="No audit entries yet" />}
          {audit?.map((e) => (
            <div key={e.id} className="p-3 rounded-lg bg-ink-900 border border-ink-500">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-mono uppercase tracking-wide text-fog-bright">{e.event}</span>
                <span className="text-xs font-mono text-fog-soft">{formatTimestamp(e.timestamp)}</span>
              </div>
              {e.transaction_id && (
                <div className="text-xs font-mono text-fog-soft">{e.transaction_id}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
