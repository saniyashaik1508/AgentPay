import clsx from 'clsx';

export function Card({ children, className, ...props }) {
  return (
    <div className={clsx('card', className)} {...props}>
      {children}
    </div>
  );
}

export function SectionHeading({ eyebrow, title, action }) {
  return (
    <div className="flex items-end justify-between gap-4 mb-4">
      <div>
        {eyebrow && (
          <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-fog-soft mb-1">
            {eyebrow}
          </div>
        )}
        <h2 className="font-display text-lg font-semibold text-fog-bright">{title}</h2>
      </div>
      {action}
    </div>
  );
}

export function Button({ children, variant = 'primary', className, ...props }) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium px-3.5 py-2 transition-colors focus-ring disabled:opacity-40 disabled:cursor-not-allowed';
  const variants = {
    primary: 'bg-steel text-ink-950 hover:bg-steel-bright',
    secondary: 'bg-ink-600 text-fog-bright border border-ink-400 hover:bg-ink-500',
    ghost: 'text-fog hover:text-fog-bright hover:bg-ink-700',
    danger: 'bg-signal-block-dim text-signal-block border border-signal-block/30 hover:bg-signal-block/20',
    allow: 'bg-signal-allow-dim text-signal-allow border border-signal-allow/30 hover:bg-signal-allow/20',
  };
  return (
    <button className={clsx(base, variants[variant], className)} {...props}>
      {children}
    </button>
  );
}

export function Field({ label, children, hint }) {
  return (
    <label className="block">
      <span className="block text-xs font-mono uppercase tracking-wide text-fog-soft mb-1.5">
        {label}
      </span>
      {children}
      {hint && <span className="block mt-1 text-xs text-fog-soft">{hint}</span>}
    </label>
  );
}

export function Input(props) {
  return (
    <input
      className={clsx(
        'w-full rounded-lg bg-ink-900 border border-ink-500 px-3 py-2 text-sm text-fog-bright placeholder:text-fog-soft focus-ring focus:border-steel',
        props.className
      )}
      {...props}
    />
  );
}

export function Select(props) {
  return (
    <select
      className={clsx(
        'w-full rounded-lg bg-ink-900 border border-ink-500 px-3 py-2 text-sm text-fog-bright focus-ring focus:border-steel',
        props.className
      )}
      {...props}
    />
  );
}

export function EmptyState({ title, hint }) {
  return (
    <div className="text-center py-10 px-4">
      <p className="text-sm text-fog font-medium">{title}</p>
      {hint && <p className="text-xs text-fog-soft mt-1">{hint}</p>}
    </div>
  );
}
