import React from 'react';
import { cn } from '../../utils/cn';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  height?: string;
  width?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className, height, width, style, ...props }) => {
  return (
    <div
      className={cn('animate-pulse bg-surface/80 rounded-lg', className)}
      style={{ height, width, ...style }}
      {...props}
    />
  );
};
