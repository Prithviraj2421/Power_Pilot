import React from 'react';

export interface WorkspaceLayoutProps {
  children: React.ReactNode;
}

export const WorkspaceLayout: React.FC<WorkspaceLayoutProps> = ({ children }) => {
  return <div className="w-full space-y-6">{children}</div>;
};
