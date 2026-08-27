import clsx from 'clsx';
import { signalFor, signalClasses } from '@/lib/status';

export default function Badge({ status, label, size = 'md' }) {
  const signal = signalFor(status);
  const cls = signalClasses[signal];
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border font-mono uppercase tracking-wide',
        cls.bg,
        cls.text,
        cls.border,
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs'
      )}
    >
      <span className={clsx('h-1.5 w-1.5 rounded-full', cls.dot)} />
      {label || status}
    </span>
  );
}
