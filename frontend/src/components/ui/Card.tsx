import React from 'react';
import { cn } from '../../utils/cn';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  glass?: boolean;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  glass = true,
  hoverable = false,
  ...props
}) => {
  return (
    <div
      className={cn(
        'bg-card/75 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-card transition-all duration-300 relative overflow-hidden group',
        glass && 'glass-panel',
        hoverable && 'hover:border-primary/40 hover:shadow-glow-blue hover:-translate-y-0.5 cursor-pointer',
        className
      )}
      {...props}
    >
      {/* Subtle Linear Ambient Radial Gradient */}
      <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
      {children}
    </div>
  );
};
