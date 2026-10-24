import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Layers, 
  BarChart3, 
  PieChart, 
  Clock, 
  Network, 
  LineChart, 
  BookOpen, 
  Settings, 
  ShieldAlert,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggleCollapse }) => {
  const navItems = [
    { name: 'Overview', to: '/dashboard', icon: LayoutDashboard },
    { name: 'Bridge Portfolio', to: '/bridges', icon: Layers },
    { name: 'Priority Ranking', to: '/priority', icon: BarChart3 },
    { name: 'Budget Optimization', to: '/optimization', icon: PieChart },
    { name: 'Deferral Intelligence', to: '/deferral', icon: Clock },
    { name: 'Network Impact', to: '/network', icon: Network },
    { name: 'Analytics & Baselines', to: '/analytics', icon: LineChart },
    { name: 'Methodology', to: '/methodology', icon: BookOpen },
    { name: 'Settings', to: '/settings', icon: Settings },
  ];

  return (
    <aside
      className={`bg-slate-900 border-r border-slate-800 flex flex-col justify-between transition-all duration-200 z-30 shrink-0 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div>
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
          {!collapsed ? (
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded bg-sky-600/20 border border-sky-500/50 flex items-center justify-center shrink-0">
                <ShieldAlert className="w-5 h-5 text-sky-400" />
              </div>
              <div className="truncate">
                <h1 className="text-sm font-bold tracking-tight text-slate-100 uppercase">
                  Bridge<span className="text-sky-400">Intel</span>
                </h1>
                <p className="text-[10px] text-slate-400 font-mono tracking-tight">ENGINEERING DECISION ENGINE</p>
              </div>
            </div>
          ) : (
            <div className="w-8 h-8 mx-auto rounded bg-sky-600/20 border border-sky-500/50 flex items-center justify-center" title="Bridge Maintenance Intelligence Platform">
              <ShieldAlert className="w-5 h-5 text-sky-400" />
            </div>
          )}

          <button
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="p-2 space-y-1 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                title={collapsed ? item.name : undefined}
                aria-label={item.name}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-sky-600/15 text-sky-400 font-semibold border border-sky-500/30 shadow-xs'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/70'
                  } ${collapsed ? 'justify-center px-0' : ''}`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!collapsed && <span className="truncate">{item.name}</span>}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Safety Notice Footer */}
      {!collapsed && (
        <div className="p-3 m-3 bg-slate-950/60 border border-slate-800/80 rounded-md text-[11px] text-slate-400">
          <div className="flex items-center gap-1.5 text-sky-400 font-semibold mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
            Decision Support Standard
          </div>
          <p className="text-[10px] leading-relaxed text-slate-500">
            Recommendations do not replace certified physical inspection or licensed structural engineering sign-off.
          </p>
        </div>
      )}
    </aside>
  );
};
