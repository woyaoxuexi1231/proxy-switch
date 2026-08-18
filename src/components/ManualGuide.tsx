import { useState } from 'react';
import type { ManualStep } from '../types';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '../lib/cn';

interface Props {
  steps: ManualStep[];
  defaultOpen?: boolean;
}

export function ManualGuide({ steps, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [expandedStep, setExpandedStep] = useState<number | null>(
    defaultOpen ? 0 : null,
  );

  if (steps.length === 0) return null;

  return (
    <div className="mt-3">
      <button
        type="button"
        className="inline-flex items-center gap-1 text-[12px] font-medium text-slate-500 hover:text-[#0a1b33] transition-colors"
        onClick={() => setOpen(!open)}
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5" strokeWidth={2} />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" strokeWidth={2} />
        )}
        How to configure manually
      </button>
      {open && (
        <div className="mt-2 space-y-1 border-l border-slate-200 pl-3">
          {steps.map((step, i) => (
            <div key={`${step.title}-${i}`}>
              <button
                type="button"
                className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-[#0a1b33] transition-colors"
                onClick={() =>
                  setExpandedStep(expandedStep === i ? null : i)
                }
              >
                {expandedStep === i ? (
                  <ChevronDown className="h-3 w-3" strokeWidth={2} />
                ) : (
                  <ChevronRight className="h-3 w-3" strokeWidth={2} />
                )}
                {step.title}
              </button>
              {expandedStep === i && (
                <pre
                  className={cn(
                    'mt-1.5 mb-2 overflow-x-auto rounded-lg bg-slate-50 px-3 py-2',
                    'font-mono text-[11px] leading-relaxed text-[#0a1b33] whitespace-pre-wrap break-all',
                  )}
                >
                  {step.commands.map((cmd, j) => (
                    <div key={j} className="min-h-[18px]">
                      {cmd || '\u00a0'}
                    </div>
                  ))}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
