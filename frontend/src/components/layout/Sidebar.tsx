import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Users,
  PlayCircle,
  TableProperties,
  FileCheck2,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Tenders & RFPs', path: '/tenders', icon: FileText },
    { label: 'Vendor Bids', path: '/vendors', icon: Users },
    { label: 'Evaluation Workspace', path: '/evaluations', icon: PlayCircle },
    { label: 'Scorecard Matrix', path: '/scorecard', icon: TableProperties },
    { label: 'Governance & Reports', path: '/reports', icon: FileCheck2 },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col min-h-[calc(100vh-4rem)] border-r border-slate-800">
      <div className="p-4 flex-1 space-y-1">
        <p className="px-3 text-[11px] font-semibold tracking-wider uppercase text-slate-500 mb-2">
          Procurement Lifecycle
        </p>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`
            }
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="p-4 border-t border-slate-800/80">
        <div className="bg-slate-800/40 rounded-lg p-3 text-xs text-slate-400 border border-slate-700/50">
          <p className="font-medium text-slate-200 mb-1">Microsoft Agent Framework</p>
          <p className="text-[11px] text-slate-400">
            5 Specialized Agents active. Evidence citations enforced.
          </p>
        </div>
      </div>
    </aside>
  );
};

