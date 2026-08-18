import type { ReactNode } from 'react';
import { cn } from '../lib/cn';

interface Props {
  children: ReactNode;
  className?: string;
}

export function Island({ children, className }: Props) {
  return (
    <div
      className={cn(
        'min-h-0 overflow-hidden rounded-[16px] bg-white',
        className,
      )}
    >
      {children}
    </div>
  );
}
