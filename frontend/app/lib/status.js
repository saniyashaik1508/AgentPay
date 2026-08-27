// Maps backend status/decision strings to the traffic-light signal system
// used throughout the UI. This mapping is functional, not decorative — it
// mirrors the policy engine's actual ALLOW / REQUIRE_APPROVAL / BLOCK output.

export function signalFor(status) {
  if (!status) return 'neutral';
  const s = status.toUpperCase();
  if (['ALLOW', 'PAID', 'SUCCESS', 'ACTIVE'].includes(s)) return 'allow';
  if (['REQUIRE_APPROVAL', 'REQUIRES_APPROVAL', 'PENDING'].includes(s)) return 'hold';
  if (['BLOCK', 'BLOCKED', 'FAILED', 'REVOKED', 'SUSPENDED', 'REJECTED'].includes(s)) return 'block';
  return 'neutral';
}

export const signalClasses = {
  allow: {
    dot: 'bg-signal-allow',
    text: 'text-signal-allow',
    bg: 'bg-signal-allow-dim',
    border: 'border-signal-allow/30',
  },
  hold: {
    dot: 'bg-signal-hold',
    text: 'text-signal-hold',
    bg: 'bg-signal-hold-dim',
    border: 'border-signal-hold/30',
  },
  block: {
    dot: 'bg-signal-block',
    text: 'text-signal-block',
    bg: 'bg-signal-block-dim',
    border: 'border-signal-block/30',
  },
  neutral: {
    dot: 'bg-fog-soft',
    text: 'text-fog',
    bg: 'bg-ink-600',
    border: 'border-ink-400',
  },
};

export function formatINR(amount) {
  if (amount === null || amount === undefined) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatTimestamp(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
