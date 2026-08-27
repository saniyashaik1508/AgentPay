'use client';

import { useCallback, useEffect, useState } from 'react';

const DEFAULTS = {
  apiBaseUrl: 'http://localhost:8000',
  userId: 'USR-demo1',
  agentId: 'AGT-shopping7821',
  agentSecret: '',
};

const STORAGE_KEY = 'agentpay.settings.v1';

function readStorage() {
  if (typeof window === 'undefined') return DEFAULTS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return DEFAULTS;
  }
}

/**
 * Shared settings: API base URL + demo credentials, persisted to
 * localStorage so a page refresh doesn't lose them. This is a plain
 * Next.js app running in the user's own browser (not a sandboxed
 * artifact), so localStorage is the right tool here.
 */
export function useSettings() {
  const [settings, setSettings] = useState(DEFAULTS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setSettings(readStorage());
    setHydrated(true);
  }, []);

  const update = useCallback((patch) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      }
      return next;
    });
  }, []);

  return { settings, update, hydrated };
}
