'use client';

import { useEffect, useState, useCallback } from 'react';
import { TrendingUp, ShoppingBag, Ban, AlertTriangle, Sparkles } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { formatINR } from '@/lib/status';
import { Card, SectionHeading, Select, EmptyState } from '@/components/ui/Primitives';

function Stat({ icon: Icon, label, value, tone = 'default' }) {
  return (
    <div className="p-4 rounded-lg bg-ink-900 border border-ink-500">
      <div className="flex items-center gap-2 text-fog-soft mb-2">
        <Icon className="h-3.5 w-3.5" />
        <span className="text-[11px] font-mono uppercase tracking-wide">{label}</span>
      </div>
      <div
        className={
          tone === 'block'
            ? 'text-xl font-display font-semibold text-signal-block'
            : tone === 'allow'
            ? 'text-xl font-display font-semibold text-signal-allow'
            : 'text-xl font-display font-semibold text-fog-bright'
        }
      >
        {value}
      </div>
    </div>
  );
}

export default function MerchantPanel({ settings }) {
  const [merchants, setMerchants] = useState(null);
  const [merchantId, setMerchantId] = useState('');
  const [analytics, setAnalytics] = useState(null);
  const [insights, setInsights] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .listMerchants(settings.apiBaseUrl)
      .then((list) => {
        setMerchants(list);
        if (list.length > 0) setMerchantId((cur) => cur || list[0].merchant_id);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [settings.apiBaseUrl]);

  const load = useCallback(() => {
    if (!merchantId) return;
    setError(null);
    setAnalytics(null);
    setInsights(null);
    Promise.all([
      api.merchantAnalytics(settings.apiBaseUrl, merchantId),
      api.merchantRecommendations(settings.apiBaseUrl, merchantId),
    ])
      .then(([a, i]) => {
        setAnalytics(a);
        setInsights(i);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [settings.apiBaseUrl, merchantId]);

  useEffect(() => {
    load();
  }, [load]);

  const merchant = merchants?.find((m) => m.merchant_id === merchantId);

  return (
    <div className="space-y-5">
      <Card className="p-5">
        <SectionHeading
          eyebrow="Agent commerce, from the merchant side"
          title="Merchant analytics"
          action={
            merchants && (
              <Select value={merchantId} onChange={(e) => setMerchantId(e.target.value)} className="w-56">
                {merchants.map((m) => (
                  <option key={m.merchant_id} value={m.merchant_id}>
                    {m.name} · {m.category}
                  </option>
                ))}
              </Select>
            )
          }
        />

        {error && (
          <div className="mb-4 text-xs font-mono text-signal-block bg-signal-block-dim border border-signal-block/30 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        {merchant && (
          <div className="mb-4 flex items-center gap-2 text-xs font-mono text-fog-soft">
            <span>{merchant.merchant_id}</span>
            <span>·</span>
            <span>trust score {merchant.trust_score}</span>
          </div>
        )}

        {!analytics && !error && <p className="text-sm text-fog-soft">Loading analytics…</p>}

        {analytics && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <Stat icon={ShoppingBag} label="Agent transactions" value={analytics.agent_transactions} />
              <Stat icon={TrendingUp} label="Conversion rate" value={`${Math.round(analytics.conversion_rate * 100)}%`} tone="allow" />
              <Stat icon={Sparkles} label="Agent revenue" value={formatINR(analytics.agent_revenue)} />
              <Stat icon={Ban} label="Blocked" value={analytics.blocked_transactions} tone="block" />
              <Stat icon={AlertTriangle} label="Failed payments" value={analytics.failed_payments} tone="block" />
              <Stat icon={ShoppingBag} label="Avg order value" value={formatINR(analytics.average_order_value)} />
            </div>
            {analytics.is_demo_data && (
              <p className="mt-3 text-xs text-fog-soft">
                Figures computed from this prototype's seeded demo dataset — not a claim about real-world outcomes.
              </p>
            )}
          </>
        )}
      </Card>

      <Card className="p-5">
        <SectionHeading eyebrow="Rule-based, not ML" title="Growth insights" />
        {insights && insights.length === 0 && <EmptyState title="No insights yet" />}
        {insights && insights.length > 0 && (
          <div className="space-y-2">
            {insights.map((ins, i) => (
              <div key={i} className="p-3.5 rounded-lg bg-ink-900 border border-ink-500">
                <div className="text-[11px] font-mono uppercase tracking-wide text-steel-bright mb-1.5">
                  {ins.insight_type.replaceAll('_', ' ')}
                </div>
                <p className="text-sm text-fog-bright mb-1">{ins.message}</p>
                <p className="text-sm text-fog-soft">{ins.recommendation}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
