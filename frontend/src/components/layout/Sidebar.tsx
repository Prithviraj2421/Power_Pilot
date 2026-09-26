import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileText, Settings, Sparkles, ChevronLeft, ChevronRight, Zap } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { cn } from '../../utils/cn';

export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useAppStore();

  const navItems = [
    { label: 'Dataset Upload', path: '/', icon: <FileText className="w-4 h-4" /> },
    { label: 'Intelligence Workspace', path: '/workspace', icon: <LayoutDashboard className="w-4 h-4" /> },
    { label: 'Settings', path: '/settings', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <aside
      className={cn(
        'h-screen bg-card/80 backdrop-blur-2xl border-r border-white/10 flex flex-col transition-all duration-300 relative z-30 sticky top-0',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-white/10">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-primary/20 text-primary rounded-xl border border-primary/30 shadow-glow-blue">
              <Zap className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold text-base text-white tracking-tight">
                Power<span className="text-primary">Pilot</span>
              </span>
              <span className="text-[10px] text-gray-500 font-mono tracking-widest uppercase">BI PLATFORM</span>
            </div>
          </div>
        )}
        {sidebarCollapsed && (
          <div className="mx-auto p-1.5 bg-primary/20 text-primary rounded-xl border border-primary/30">
            <Zap className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 p-3 space-y-1.5">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all relative group',
                isActive
                  ? 'bg-primary text-white shadow-glow-blue border border-primary/50'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              )
            }
          >
            {({ isActive }) => (
              <>
                <span className="flex-shrink-0">{item.icon}</span>
                {!sidebarCollapsed && <span>{item.label}</span>}
                {isActive && (
                  <span className="absolute left-0 top-2 bottom-2 w-1 bg-white rounded-r-full" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Collapse Toggle Footer */}
      <div className="p-3 border-t border-white/10">
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center justify-center p-2 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
        >
          {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
};
