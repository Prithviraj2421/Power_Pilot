import React from 'react';
import { cn } from '../../utils/cn';

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  label: string;
  onRemove?: () => void;
  icon?: React.ReactNode;
}

export const Chip: React.FC<ChipProps> = ({ label, onRemove, icon, className, ...props }) => {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1 bg-surface border border-border rounded-lg text-xs font-medium text-gray-300',
        className
      )}
      {...props}
    >
      {icon && <span>{icon}</span>}
      <span>{label}</span>
      {onRemove && (
        <button
          onClick={onRemove}
          className="ml-1 text-gray-400 hover:text-white transition-colors focus:outline-none"
        >
          &times;
        </button>
      )}
    </span>
  );
};
