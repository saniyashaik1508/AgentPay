'use client';

import { useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import { Play, Loader2, Search, ArrowRight } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { formatINR, signalFor } from '@/lib/status';
import { Card, SectionHeading, Button, Field, Input, Select } from '@/components/ui/Primitives';
import Badge from '@/components/ui/Badge';
import PipelineTrace from '@/components/PipelineTrace';

// Static mirror of seed/seed_data.py — a frontend convenience for picking a
// demo product without the backend exposing a product-listing endpoint.
const DEMO_PRODUCTS = [
  { id: 'PRD-shoes1', name: 'Running Shoes', category: 'Footwear', product_type: 'shoes', price: 4299 },
  { id: 'PRD-shoes2', name: 'Trail Running Shoes', category: 'Footwear', product_type: 'shoes', price: 4999 },
  { id: 'PRD-watch1', name: 'Smartwatch', category: 'Electronics', product_type: 'smartwatch', price: 6999 },
  { id: 'PRD-laptop1', name: 'Laptop', category: 'Electronics', product_type: 'laptop', price: 65000 },
  { id: 'PRD-headphones1', name: 'Headphones', category: 'Electronics', product_type: 'headphones', price: 2499 },
  { id: 'PRD-backpack1', name: 'Backpack', category: 'Accessories', product_type: 'backpack', price: 1899 },
  { id: 'PRD-books1', name: 'Book Bundle', category: 'Books', product_type: 'books', price: 899 },
  { id: 'PRD-luxwatch1', name: 'Luxury Watch', category: 'Luxury', product_type: 'watch', price: 14999 },
];

function overridesFor(decision, paymentStatus) {
  const finalSignal = signalFor(decision);
  const overrides = { identity: 'allow', intent: 'allow' };
  if (decision === 'BLOCK') {
    overrides.payment = 'halt';
  } else if (decision === 'REQUIRE_APPROVAL') {
    overrides.payment = 'hold';
  } else if (paymentStatus === 'FAILED') {
    overrides.payment = 'block';
  } else {
    overrides.payment = 'allow';
  }
  return { finalSignal, overrides };
}

export default function RunPanel({ settings, onTransaction }) {
  const [mode, setMode] = useState('evaluate'); // 'evaluate' | 'agent'
  const [productId, setProductId] = useState(DEMO_PRODUCTS[0].id);
  const [maxAmount, setMaxAmount] = useState(DEMO_PRODUCTS[0].price);
  const [requestText, setRequestText] = useState('Find me running shoes under ₹5,000');
  const [category, setCategory] = useState('Footwear');
  const [productType, setProductType] = useState('shoes');

  const [pipeline, setPipeline] = useState({ mode: 'idle', activeIndex: -1, finalSignal: null, overrides: {} });
  const [result, setResult] = useState(null);
  const [agentTranscript, setAgentTranscript] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const timerRef = useRef(null);

  const selectedProduct = DEMO_PRODUCTS.find((p) => p.id === productId);

  useEffect(() => {
    if (selectedProduct) {
      setMaxAmount(selectedProduct.price);
      setCategory(selectedProduct.category);
      setProductType(selectedProduct.product_type);
    }
  }, [productId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => clearInterval(timerRef.current), []);

  function startPipelineAnimation() {
    setResult(null);
    setAgentTranscript(null);
    setError(null);
    let step = 0;
    setPipeline({ mode: 'running', activeIndex: 0, finalSignal: null, overrides: {} });
    timerRef.current = setInterval(() => {
      step += 1;
      if (step <= 3) {
        setPipeline((p) => ({ ...p, activeIndex: step }));
      }
    }, 260);
  }

  function resolvePipeline(decision, paymentStatus) {
    clearInterval(timerRef.current);
    const { finalSignal, overrides } = overridesFor(decision, paymentStatus);
    setPipeline({ mode: 'result', activeIndex: -1, finalSignal, overrides });
  }

  function haltPipeline() {
    clearInterval(timerRef.current);
    setPipeline({ mode: 'idle', activeIndex: -1, finalSignal: null, overrides: {} });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!settings.agentSecret) {
      setError('Add the agent secret in settings (top right) — it was printed once when you ran the seed script.');
      return;
    }
    setSubmitting(true);
    startPipelineAnimation();
    try {
      if (mode === 'evaluate') {
        const res = await api.evaluateTransaction(settings.apiBaseUrl, {
          agent_id: settings.agentId,
          agent_secret: settings.agentSecret,
          product_id: productId,
          category,
          product_type: productType,
          max_amount: Number(maxAmount),
        });
        setResult(res);
        resolvePipeline(res.decision, res.payment?.status);
        if (onTransaction) onTransaction(res.transaction_id);
      } else {
        const res = await api.runAgent(settings.apiBaseUrl, {
          agent_id: settings.agentId,
          agent_secret: settings.agentSecret,
          user_request_text: requestText,
          category,
          product_type: productType,
          max_amount: Number(maxAmount),
        });
        setAgentTranscript(res.transcript || []);
        const proposal = (res.transcript || []).find((t) => t.tool === 'propose_transaction' || t.tool?.startsWith('propose_transaction'));
        if (proposal && proposal.result && !proposal.result.error) {
          resolvePipeline(proposal.result.decision, proposal.result.payment_status);
          if (onTransaction) onTransaction(proposal.result.transaction_id);
        } else {
          haltPipeline();
        }
      }
    } catch (err) {
      haltPipeline();
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="p-5">
      <SectionHeading
        eyebrow="AI proposes → policy decides → payment executes → audit records"
        title="Propose a transaction"
      />

      <div className="mb-4 inline-flex rounded-lg bg-ink-900 border border-ink-500 p-1">
        {[
          { key: 'evaluate', label: 'Evaluate a product' },
          { key: 'agent', label: 'Natural-language agent' },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setMode(t.key)}
            className={clsx(
              'px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              mode === t.key ? 'bg-ink-600 text-fog-bright' : 'text-fog-soft hover:text-fog-bright'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {mode === 'evaluate' ? (
          <Field label="Product" hint="Seeded demo catalog">
            <Select value={productId} onChange={(e) => setProductId(e.target.value)}>
              {DEMO_PRODUCTS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} — {formatINR(p.price)} ({p.category})
                </option>
              ))}
            </Select>
          </Field>
        ) : (
          <Field label="What should the agent shop for?">
            <Input value={requestText} onChange={(e) => setRequestText(e.target.value)} />
          </Field>
        )}

        <div className="grid grid-cols-3 gap-3">
          <Field label="Category">
            <Input value={category} onChange={(e) => setCategory(e.target.value)} />
          </Field>
          <Field label="Product type">
            <Input value={productType} onChange={(e) => setProductType(e.target.value)} />
          </Field>
          <Field label="Max amount (₹)">
            <Input type="number" value={maxAmount} onChange={(e) => setMaxAmount(e.target.value)} />
          </Field>
        </div>

        <Button type="submit" disabled={submitting}>
          {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : mode === 'evaluate' ? <Play className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />}
          {mode === 'evaluate' ? 'Evaluate' : 'Run agent'}
        </Button>
      </form>

      {(pipeline.mode !== 'idle') && (
        <div className="mt-5 pt-5 border-t border-ink-500">
          <PipelineTrace {...pipeline} />
        </div>
      )}

      {error && (
        <div className="mt-4 text-xs font-mono text-signal-block bg-signal-block-dim border border-signal-block/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-4 p-4 rounded-lg bg-ink-900 border border-ink-500 animate-rise">
          <div className="flex items-center justify-between mb-2">
            <Badge status={result.decision} />
            <span className="text-xs font-mono text-fog-soft">{result.transaction_id}</span>
          </div>
          <p className="text-sm text-fog-bright mb-2">{result.reason}</p>
          <div className="grid grid-cols-3 gap-3 text-xs font-mono text-fog-soft">
            <div>intent match <span className="text-fog-bright">{(result.intent_match * 100).toFixed(0)}%</span></div>
            <div>risk score <span className="text-fog-bright">{result.risk_score}</span> ({result.risk_band})</div>
            <div>
              payment{' '}
              <span className="text-fog-bright">
                {result.payment ? result.payment.status : 'not attempted'}
              </span>
            </div>
          </div>
        </div>
      )}

      {agentTranscript && (
        <div className="mt-4 space-y-2 animate-rise">
          {agentTranscript.map((step, i) => (
            <div key={i} className="p-3 rounded-lg bg-ink-900 border border-ink-500 text-xs">
              {step.role === 'agent_text' ? (
                <p className="text-fog-bright">{step.content}</p>
              ) : (
                <>
                  <div className="flex items-center gap-2 font-mono text-fog-soft mb-1">
                    <ArrowRight className="h-3 w-3" />
                    {step.tool}
                  </div>
                  <pre className="font-mono text-[11px] text-fog-bright whitespace-pre-wrap break-words">
                    {JSON.stringify(step.result, null, 2)}
                  </pre>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
