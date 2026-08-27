'use client';

import { useSettings } from '@/lib/store';
import Header from '@/components/Header';
import MerchantPanel from '@/components/MerchantPanel';

export default function MerchantConsolePage() {
  const { settings, update, hydrated } = useSettings();

  if (!hydrated) return null;

  return (
    <>
      <Header settings={settings} update={update} hydrated={hydrated} />
      <main className="max-w-6xl mx-auto px-5 py-8">
        <div className="mb-8">
          <p className="text-[11px] font-mono uppercase tracking-[0.14em] text-fog-soft mb-2">
            Merchant console
          </p>
          <h1 className="font-display text-2xl font-semibold text-fog-bright max-w-2xl">
            See agentic commerce the way your storefront experiences it.
          </h1>
          <p className="text-sm text-fog-soft mt-2 max-w-xl">
            Conversion, revenue, and blocked attempts from AI agents transacting on your catalog, plus
            rule-based recommendations grounded in that data.
          </p>
        </div>
        <MerchantPanel settings={settings} />
      </main>
    </>
  );
}
