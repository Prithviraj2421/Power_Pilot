import React from 'react';
import { Card } from './Card';
import { Badge } from './Badge';
import { cn } from '../../utils/cn';

export interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: string;
    direction: 'up' | 'down' | 'neutral';
  };
  icon?: React.ReactNode;
  badge?: string;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  icon,
  badge,
  className,
}) => {
  return (
    <Card className={cn('relative overflow-hidden', className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">{title}</p>
          <h3 className="text-2xl font-bold text-white mt-1">{value}</h3>
        </div>
        {icon && <div className="p-2.5 bg-surface border border-border rounded-lg text-primary">{icon}</div>}
      </div>

      <div className="mt-4 flex items-center justify-between text-xs">
        {trend && (
          <span
            className={cn(
              'font-medium inline-flex items-center gap-1',
              trend.direction === 'up' && 'text-success',
              trend.direction === 'down' && 'text-danger',
              trend.direction === 'neutral' && 'text-gray-400'
            )}
          >
            {trend.value}
          </span>
        )}
        {subtitle && <span className="text-gray-400">{subtitle}</span>}
        {badge && <Badge variant="primary">{badge}</Badge>}
      </div>
    </Card>
  );
};
