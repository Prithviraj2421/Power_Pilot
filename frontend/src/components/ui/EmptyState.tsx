import React from 'react';
import { FolderOpen } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  action,
  icon = <FolderOpen className="w-12 h-12 text-gray-500" />,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-12 text-center border-2 border-dashed border-border rounded-xl bg-card/40',
        className
      )}
    >
      <div className="p-4 bg-surface rounded-full mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-white mb-1">{title}</h3>
      <p className="text-sm text-gray-400 max-w-md mb-6">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
