'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import { Settings, Circle } from 'lucide-react';
import { api } from '@/lib/api';
import { Field, Input } from '@/components/ui/Primitives';

const TABS = [
  { href: '/', label: 'User Console' },
  { href: '/merchant', label: 'Merchant Console' },
];

export default function Header({ settings, update, hydrated }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [connState, setConnState] = useState('checking'); // checking | ok | down

  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    setConnState('checking');
    api
      .health(settings.apiBaseUrl)
      .then(() => !cancelled && setConnState('ok'))
      .catch(() => !cancelled && setConnState('down'));
    return () => {
      cancelled = true;
    };
  }, [settings.apiBaseUrl, hydrated]);

  return (
    <header className="border-b border-ink-500 bg-ink-900/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between gap-6">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-md bg-steel-dim border border-steel/30 flex items-center justify-center">
              <span className="font-display text-sm font-bold text-steel-bright">A</span>
            </div>
            <span className="font-display text-base font-semibold tracking-tight">AgentPay</span>
          </div>
          <nav className="flex items-center gap-1">
            {TABS.map((t) => (
              <Link
                key={t.href}
                href={t.href}
                className={clsx(
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  pathname === t.href
                    ? 'bg-ink-700 text-fog-bright'
                    : 'text-fog-soft hover:text-fog-bright hover:bg-ink-700/60'
                )}
              >
                {t.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 text-xs font-mono text-fog-soft">
            <Circle
              className={clsx(
                'h-2 w-2',
                connState === 'ok' && 'fill-signal-allow text-signal-allow',
                connState === 'down' && 'fill-signal-block text-signal-block',
                connState === 'checking' && 'fill-fog-soft text-fog-soft'
              )}
            />
            {connState === 'ok' && 'backend connected'}
            {connState === 'down' && 'backend unreachable'}
            {connState === 'checking' && 'checking…'}
          </div>
          <div className="relative">
            <button
              onClick={() => setOpen((v) => !v)}
              className="p-2 rounded-md text-fog-soft hover:text-fog-bright hover:bg-ink-700 focus-ring"
              aria-label="Connection settings"
            >
              <Settings className="h-4 w-4" />
            </button>
            {open && (
              <div className="absolute right-0 mt-2 w-80 card p-4 shadow-2xl animate-rise z-40">
                <p className="text-xs text-fog-soft mb-3">
                  Points this dashboard at your running AgentPay backend.
                </p>
                <div className="space-y-3">
                  <Field label="API base URL">
                    <Input
                      value={settings.apiBaseUrl}
                      onChange={(e) => update({ apiBaseUrl: e.target.value })}
                      placeholder="http://localhost:8000"
                    />
                  </Field>
                  <Field label="Owner / user id">
                    <Input value={settings.userId} onChange={(e) => update({ userId: e.target.value })} />
                  </Field>
                  <Field label="Agent id" hint="Seeded demo agent by default.">
                    <Input value={settings.agentId} onChange={(e) => update({ agentId: e.target.value })} />
                  </Field>
                  <Field label="Agent secret" hint="Printed once by `python -m seed.seed_data`.">
                    <Input
                      value={settings.agentSecret}
                      onChange={(e) => update({ agentSecret: e.target.value })}
                      placeholder="paste the seeded agent secret"
                      type="password"
                    />
                  </Field>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
