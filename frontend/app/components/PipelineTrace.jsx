'use client';

import clsx from 'clsx';
import { ShieldCheck, Target, Scale, Radar, CreditCard, FileClock } from 'lucide-react';
import { signalClasses } from '@/lib/status';

const STEPS = [
  { key: 'identity', label: 'Identity', icon: ShieldCheck },
  { key: 'intent', label: 'Intent', icon: Target },
  { key: 'policy', label: 'Policy', icon: Scale },
  { key: 'risk', label: 'Risk', icon: Radar },
  { key: 'payment', label: 'Payment', icon: CreditCard },
  { key: 'audit', label: 'Audit', icon: FileClock },
];

/**
 * The signature element: mirrors the README's architecture diagram
 * (identity -> intent -> policy -> risk -> payment -> audit) as a literal
 * pipeline, used both live (while a proposal is being evaluated) and
 * statically (to render a stored decision trace).
 *
 * mode: 'idle' | 'running' | 'result'
 * activeIndex: which step pulses while running
 * finalSignal: 'allow' | 'hold' | 'block' — base color once resolved
 * overrides: { [stepKey]: 'allow' | 'hold' | 'block' | 'halt' } per-step overrides
 */
export default function PipelineTrace({ mode = 'idle', activeIndex = -1, finalSignal = null, overrides = {} }) {
  return (
    <div className="flex items-center w-full overflow-x-auto py-1">
      {STEPS.map((step, i) => {
        const override = overrides[step.key];
        const isActive = mode === 'running' && i === activeIndex;
        const isPast = mode === 'running' && i < activeIndex;
        const isResult = mode === 'result';

        let dotClass = 'bg-ink-500';
        let ringClass = '';
        let labelClass = 'text-fog-soft';
        let iconMuted = false;
        let resultSignal = null;

        if (isActive) {
          dotClass = 'bg-steel';
          ringClass = 'ring-4 ring-steel-dim animate-pulseNode';
          labelClass = 'text-steel-bright';
        } else if (isPast) {
          dotClass = 'bg-steel';
          labelClass = 'text-fog-bright';
        } else if (isResult) {
          if (override === 'halt') {
            dotClass = 'bg-ink-500';
            labelClass = 'text-fog-soft/50';
            iconMuted = true;
          } else {
            resultSignal = override || finalSignal || 'neutral';
            const cls = signalClasses[resultSignal];
            dotClass = cls.dot;
            labelClass = cls.text;
          }
        }

        const Icon = step.icon;
        const connectorClass = isPast
          ? 'bg-steel'
          : isResult && override !== 'halt'
          ? signalClasses[resultSignal || finalSignal || 'neutral'].dot
          : 'bg-ink-500';

        return (
          <div key={step.key} className="flex items-center flex-1 min-w-[84px] last:flex-none last:min-w-0">
            <div className="flex flex-col items-center gap-1.5 shrink-0">
              <div
                className={clsx(
                  'h-8 w-8 rounded-full flex items-center justify-center transition-colors duration-300',
                  dotClass,
                  ringClass
                )}
              >
                <Icon className={clsx('h-4 w-4', iconMuted ? 'text-fog-soft/40' : 'text-ink-950')} strokeWidth={2.25} />
              </div>
              <span className={clsx('text-[10px] font-mono uppercase tracking-wide whitespace-nowrap', labelClass)}>
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={clsx('h-px flex-1 mx-1 mb-4 transition-colors duration-300', connectorClass)} />
            )}
          </div>
        );
      })}
    </div>
  );
}
