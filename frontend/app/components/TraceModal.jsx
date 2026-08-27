'use client';

import { useEffect, useState } from 'react';
import { X, Check, Ban, Loader2 } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { formatINR, signalFor } from '@/lib/status';
import { Button } from '@/components/ui/Primitives';
import Badge from '@/components/ui/Badge';
import PipelineTrace from '@/components/PipelineTrace';

const CHECK_ROWS = [
  ['spend_limit_check', 'Spend limit'],
  ['merchant_check', 'Merchant'],
  ['category_check', 'Category'],
  ['agent_status_check', 'Agent status'],
  ['velocity_check', 'Velocity'],
];

export default function TraceModal({ transactionId, apiBaseUrl, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!transactionId) return;
    setData(null);
    setError(null);
    api
      .transactionTrace(apiBaseUrl, transactionId)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [transactionId, apiBaseUrl]);

  if (!transactionId) return null;

  const trace = data?.decision_trace;
  const finalSignal = trace ? signalFor(trace.decision) : signalFor(data?.status);
  const overrides = { identity: 'allow', intent: 'allow' };
  if (trace) {
    if (trace.decision === 'BLOCK') overrides.payment = 'halt';
    else if (trace.decision === 'REQUIRE_APPROVAL')
      overrides.payment = data?.payment ? finalSignal : 'hold';
    else overrides.payment = data?.payment?.status === 'FAILED' ? 'block' : 'allow';
  }

  async function act(action) {
    setBusy(true);
    setError(null);
    try {
      if (action === 'approve') await api.approveTransaction(apiBaseUrl, transactionId);
      else await api.rejectTransaction(apiBaseUrl, transactionId);
      const fresh = await api.transactionTrace(apiBaseUrl, transactionId);
      setData(fresh);
      if (onChanged) onChanged();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-4 overflow-y-auto">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative card w-full max-w-lg p-5 animate-rise my-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wide text-fog-soft">Decision trace</div>
            <div className="font-mono text-sm text-fog-bright">{transactionId}</div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md text-fog-soft hover:text-fog-bright hover:bg-ink-700 focus-ring">
            <X className="h-4 w-4" />
          </button>
        </div>

        {error && (
          <div className="mb-4 text-xs font-mono text-signal-block bg-signal-block-dim border border-signal-block/30 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        {!data && !error && <p className="text-sm text-fog-soft">Loading trace…</p>}

        {data && (
          <>
            <div className="flex items-center justify-between mb-4">
              <Badge status={data.status} />
              <span className="font-mono text-sm text-fog-bright tabular">{formatINR(data.amount)}</span>
            </div>

            <PipelineTrace mode="result" finalSignal={finalSignal} overrides={overrides} />

            {trace ? (
              <div className="mt-4 space-y-2">
                <p className="text-sm text-fog-bright">{trace.reason}</p>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  {CHECK_ROWS.map(([key, label]) => (
                    <div key={key} className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-ink-900 border border-ink-500">
                      <span className="text-fog-soft">{label}</span>
                      <span className={trace[key] ? 'text-signal-allow' : 'text-signal-block'}>
                        {String(trace[key])}
                      </span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-ink-900 border border-ink-500">
                    <span className="text-fog-soft">Intent match</span>
                    <span className="text-fog-bright">{Math.round((trace.intent_match ?? 0) * 100)}%</span>
                  </div>
                  <div className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-ink-900 border border-ink-500">
                    <span className="text-fog-soft">Risk score</span>
                    <span className="text-fog-bright">{trace.risk_score}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm text-fog-soft">No decision trace recorded for this transaction yet.</p>
            )}

            {data.payment && (
              <div className="mt-4 p-3 rounded-lg bg-ink-900 border border-ink-500">
                <div className="text-[11px] font-mono uppercase tracking-wide text-fog-soft mb-2">Payment</div>
                <div className="grid grid-cols-2 gap-y-1 text-xs font-mono">
                  <span className="text-fog-soft">status</span>
                  <span className="text-fog-bright text-right">{data.payment.status}</span>
                  <span className="text-fog-soft">mode</span>
                  <span className="text-fog-bright text-right">{data.payment.is_mock ? 'mock adapter' : 'razorpay test mode'}</span>
                  {data.payment.failure_reason && (
                    <>
                      <span className="text-fog-soft">failure</span>
                      <span className="text-signal-block text-right">{data.payment.failure_reason}</span>
                    </>
                  )}
                </div>
              </div>
            )}

            {data.status === 'REQUIRES_APPROVAL' && (
              <div className="mt-4 flex items-center gap-2">
                <Button variant="allow" onClick={() => act('approve')} disabled={busy}>
                  {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                  Approve
                </Button>
                <Button variant="danger" onClick={() => act('reject')} disabled={busy}>
                  <Ban className="h-3.5 w-3.5" />
                  Reject
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
