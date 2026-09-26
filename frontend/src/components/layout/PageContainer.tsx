import React from 'react';
import { cn } from '../../utils/cn';

export interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
}

export const PageContainer: React.FC<PageContainerProps> = ({ children, className }) => {
  return <div className={cn('max-w-7xl mx-auto p-6 md:p-8', className)}>{children}</div>;
};
