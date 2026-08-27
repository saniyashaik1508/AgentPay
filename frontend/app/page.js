'use client';

import { useState } from 'react';
import { useSettings } from '@/lib/store';
import Header from '@/components/Header';
import AgentsPanel from '@/components/AgentsPanel';
import RunPanel from '@/components/RunPanel';
import TransactionsPanel from '@/components/TransactionsPanel';
import RiskAuditPanel from '@/components/RiskAuditPanel';

export default function UserConsolePage() {
  const { settings, update, hydrated } = useSettings();
  const [refreshKey, setRefreshKey] = useState(0);

  function handleCredentialsIssued(res) {
    update({ agentId: res.agent_id, agentSecret: res.agent_secret });
  }

  function bump() {
    setRefreshKey((k) => k + 1);
  }

  if (!hydrated) return null;

  return (
    <>
      <Header settings={settings} update={update} hydrated={hydrated} />
      <main className="max-w-6xl mx-auto px-5 py-8">
        <div className="mb-8">
          <p className="text-[11px] font-mono uppercase tracking-[0.14em] text-fog-soft mb-2">
            User console
          </p>
          <h1 className="font-display text-2xl font-semibold text-fog-bright max-w-2xl">
            AI agents should transact for you without ever holding unlimited authority over your money.
          </h1>
          <p className="text-sm text-fog-soft mt-2 max-w-xl">
            Register an agent, hand it a scoped spend passport, and watch every proposal it makes get
            independently checked before a rupee moves.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-5">
          <div className="space-y-5">
            <AgentsPanel settings={settings} onCredentialsIssued={handleCredentialsIssued} />
            <RunPanel settings={settings} onTransaction={bump} />
          </div>
          <div className="space-y-5">
            <TransactionsPanel settings={settings} refreshKey={refreshKey} />
            <RiskAuditPanel settings={settings} refreshKey={refreshKey} />
          </div>
        </div>
      </main>
    </>
  );
}
