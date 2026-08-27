'use client';

import { useEffect, useState, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { formatINR, formatTimestamp } from '@/lib/status';
import { Card, SectionHeading, Button, Select, EmptyState } from '@/components/ui/Primitives';
import Badge from '@/components/ui/Badge';
import TraceModal from '@/components/TraceModal';

const STATUS_OPTIONS = ['', 'PAID', 'REQUIRES_APPROVAL', 'BLOCKED', 'FAILED'];

export default function TransactionsPanel({ settings, refreshKey }) {
  const [txns, setTxns] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('');
  const [openId, setOpenId] = useState(null);

  const load = useCallback(() => {
    setError(null);
    api
      .listTransactions(settings.apiBaseUrl, { agentId: settings.agentId, status: status || undefined })
      .then(setTxns)
      .catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [settings.apiBaseUrl, settings.agentId, status]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <Card className="p-5">
      <SectionHeading
        eyebrow="Every proposal, decided and recorded"
        title="Transactions"
        action={
          <div className="flex items-center gap-2">
            <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-44">
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s || 'All statuses'}
                </option>
              ))}
            </Select>
            <Button variant="ghost" onClick={load}>
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        }
      />

      {error && (
        <div className="mb-4 text-xs font-mono text-signal-block bg-signal-block-dim border border-signal-block/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {!txns && !error && <p className="text-sm text-fog-soft">Loading transactions…</p>}

      {txns && txns.length === 0 && (
        <EmptyState title="No transactions yet" hint="Propose one above to see it appear here." />
      )}

      {txns && txns.length > 0 && (
        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px] font-mono uppercase tracking-wide text-fog-soft">
                <th className="px-1 py-2 font-medium">Transaction</th>
                <th className="px-1 py-2 font-medium">Merchant</th>
                <th className="px-1 py-2 font-medium text-right">Amount</th>
                <th className="px-1 py-2 font-medium">Status</th>
                <th className="px-1 py-2 font-medium text-right">When</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((t) => (
                <tr
                  key={t.transaction_id}
                  onClick={() => setOpenId(t.transaction_id)}
                  className="cursor-pointer border-t border-ink-500 hover:bg-ink-700/50 transition-colors"
                >
                  <td className="px-1 py-2.5 font-mono text-xs text-fog-bright">{t.transaction_id}</td>
                  <td className="px-1 py-2.5 font-mono text-xs text-fog-soft">{t.merchant_id}</td>
                  <td className="px-1 py-2.5 font-mono text-xs text-right tabular text-fog-bright">
                    {formatINR(t.amount)}
                  </td>
                  <td className="px-1 py-2.5">
                    <Badge status={t.status} size="sm" />
                  </td>
                  <td className="px-1 py-2.5 text-xs text-right text-fog-soft">{formatTimestamp(t.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <TraceModal
        transactionId={openId}
        apiBaseUrl={settings.apiBaseUrl}
        onClose={() => setOpenId(null)}
        onChanged={load}
      />
    </Card>
  );
}
