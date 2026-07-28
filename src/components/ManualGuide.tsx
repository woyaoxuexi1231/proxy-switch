import { useState } from 'react';
import type { ManualStep } from '../types';
import './ManualGuide.css';

interface Props {
  steps: ManualStep[];
}

export function ManualGuide({ steps }: Props) {
  const [open, setOpen] = useState(false);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  if (steps.length === 0) return null;

  return (
    <div className="manual-guide">
      <button
        className="manual-toggle"
        onClick={() => setOpen(!open)}
      >
        <span>{open ? '▾' : '▸'} How to configure manually</span>
      </button>
      {open && (
        <div className="manual-content">
          {steps.map((step, i) => (
            <div key={i} className="manual-step">
              <button
                className="manual-step-toggle"
                onClick={() =>
                  setExpandedStep(expandedStep === i ? null : i)
                }
              >
                <span>
                  {expandedStep === i ? '▾' : '▸'} {step.title}
                </span>
              </button>
              {expandedStep === i && (
                <pre className="manual-commands">
                  {step.commands.map((cmd, j) => (
                    <div key={j} className="manual-cmd-line">
                      {cmd || ' '}
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
