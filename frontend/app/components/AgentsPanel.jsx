'use client';

import { useEffect, useState, useCallback } from 'react';
import { Plus, ShieldOff, Bot, Loader2 } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { formatINR } from '@/lib/status';
import { Card, SectionHeading, Button, Field, Input } from '@/components/ui/Primitives';
import Badge from '@/components/ui/Badge';

const emptyForm = {
  name: '',
  agent_type: 'Shopping Assistant',
  max_transaction_amount: 100000,
  daily_limit: 150000,
  approval_threshold: 50000,
  hard_block_threshold: 100000,
  allowed_categories: 'Footwear, Electronics, Accessories, Books, Groceries',
  blocked_categories: 'Gambling, Financial products, Luxury',
  allowed_merchants: '',
};

export default function AgentsPanel({ settings, onCredentialsIssued }) {
  const [agents, setAgents] = useState(null);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [issued, setIssued] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(() => {
    setError(null);
    api
      .listAgents(settings.apiBaseUrl, settings.userId)
      .then(setAgents)
      .catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [settings.apiBaseUrl, settings.userId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRevoke(agentId) {
    setBusyId(agentId);
    try {
      await api.revokeAgent(settings.apiBaseUrl, agentId);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusyId(null);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        owner_id: settings.userId,
        name: form.name || `Agent-${Math.floor(Math.random() * 9000 + 1000)}`,
        agent_type: form.agent_type,
        max_transaction_amount: Number(form.max_transaction_amount),
        daily_limit: Number(form.daily_limit),
        approval_threshold: Number(form.approval_threshold),
        hard_block_threshold: Number(form.hard_block_threshold),
        allowed_categories: splitList(form.allowed_categories),
        blocked_categories: splitList(form.blocked_categories),
        allowed_merchants: splitList(form.allowed_merchants),
      };
      const res = await api.registerAgent(settings.apiBaseUrl, payload);
      setIssued(res);
      setForm(emptyForm);
      load();
      if (onCredentialsIssued) onCredentialsIssued(res);
    } catch (e2) {
      setError(e2 instanceof ApiError ? e2.message : String(e2));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="p-5">
      <SectionHeading
        eyebrow="Identity & spend passports"
        title="Agents"
        action={
          <Button variant="secondary" onClick={() => setShowForm((v) => !v)}>
            <Plus className="h-3.5 w-3.5" />
            {showForm ? 'Close' : 'Register agent'}
          </Button>
        }
      />

      {error && (
        <div className="mb-4 text-xs font-mono text-signal-block bg-signal-block-dim border border-signal-block/30 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-5 p-4 rounded-lg bg-ink-900 border border-ink-500 animate-rise">
          <div className="grid sm:grid-cols-2 gap-3">
            <Field label="Name">
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="ShoppingAgent-4213"
              />
            </Field>
            <Field label="Agent type">
              <Input
                value={form.agent_type}
                onChange={(e) => setForm({ ...form, agent_type: e.target.value })}
              />
            </Field>
            <Field label="Per-transaction ceiling (₹)">
              <Input
                type="number"
                value={form.max_transaction_amount}
                onChange={(e) => setForm({ ...form, max_transaction_amount: e.target.value })}
              />
            </Field>
            <Field label="Daily limit (₹)">
              <Input
                type="number"
                value={form.daily_limit}
                onChange={(e) => setForm({ ...form, daily_limit: e.target.value })}
              />
            </Field>
            <Field label="Approval threshold (₹)" hint="Above this, a human must approve.">
              <Input
                type="number"
                value={form.approval_threshold}
                onChange={(e) => setForm({ ...form, approval_threshold: e.target.value })}
              />
            </Field>
            <Field label="Hard block threshold (₹)" hint="Above this, always blocked.">
              <Input
                type="number"
                value={form.hard_block_threshold}
                onChange={(e) => setForm({ ...form, hard_block_threshold: e.target.value })}
              />
            </Field>
            <Field label="Allowed categories" hint="Comma-separated">
              <Input
                value={form.allowed_categories}
                onChange={(e) => setForm({ ...form, allowed_categories: e.target.value })}
              />
            </Field>
            <Field label="Blocked categories" hint="Comma-separated">
              <Input
                value={form.blocked_categories}
                onChange={(e) => setForm({ ...form, blocked_categories: e.target.value })}
              />
            </Field>
            <Field label="Allowed merchants" hint="Comma-separated merchant ids; empty = any">
              <Input
                value={form.allowed_merchants}
                onChange={(e) => setForm({ ...form, allowed_merchants: e.target.value })}
              />
            </Field>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              Issue spend passport
            </Button>
          </div>
        </form>
      )}

      {issued && (
        <div className="mb-5 p-4 rounded-lg bg-steel-dim border border-steel/30 animate-rise">
          <p className="text-xs font-mono uppercase tracking-wide text-steel-bright mb-2">
            Agent secret — shown once, save it now
          </p>
          <div className="space-y-1 font-mono text-sm">
            <div>
              <span className="text-fog-soft">agent_id </span>
              <span className="text-fog-bright">{issued.agent_id}</span>
            </div>
            <div>
              <span className="text-fog-soft">agent_secret </span>
              <span className="text-fog-bright break-all">{issued.agent_secret}</span>
            </div>
          </div>
        </div>
      )}

      {!agents && !error && <p className="text-sm text-fog-soft">Loading agents…</p>}

      {agents && agents.length === 0 && (
        <p className="text-sm text-fog-soft">No agents registered for {settings.userId} yet.</p>
      )}

      {agents && agents.length > 0 && (
        <div className="space-y-2">
          {agents.map((a) => (
            <div
              key={a.agent_id}
              className="flex items-center justify-between gap-4 p-3 rounded-lg bg-ink-900 border border-ink-500"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="h-8 w-8 rounded-full bg-ink-600 flex items-center justify-center shrink-0">
                  <Bot className="h-4 w-4 text-fog" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-fog-bright truncate">{a.name}</span>
                    <Badge status={a.status} size="sm" />
                  </div>
                  <div className="text-xs font-mono text-fog-soft truncate">
                    {a.agent_id} · trust {a.trust_level?.toLowerCase()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <div className="text-right hidden sm:block">
                  <div className="text-xs text-fog-soft">per-txn / daily</div>
                  <div className="text-sm font-mono tabular text-fog-bright">
                    {formatINR(a.max_transaction_amount)} / {formatINR(a.daily_limit)}
                  </div>
                </div>
                <Button
                  variant="danger"
                  disabled={a.status === 'REVOKED' || busyId === a.agent_id}
                  onClick={() => handleRevoke(a.agent_id)}
                >
                  {busyId === a.agent_id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <ShieldOff className="h-3.5 w-3.5" />
                  )}
                  {a.status === 'REVOKED' ? 'Revoked' : 'Revoke'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function splitList(str) {
  return str
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}
