import React from 'react';
import { ShieldCheck, Bell } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <div className="bg-sky-600 text-white p-2 rounded-lg shadow-sm">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-slate-900 tracking-tight text-base">
            TenderEval
          </span>
          <span className="ml-2 text-xs font-semibold uppercase tracking-wider text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
            Enterprise AI
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Multi-Agent Core Online
        </div>
        <button className="text-slate-500 hover:text-slate-700 p-2 rounded-lg hover:bg-slate-100 transition-colors">
          <Bell className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-600 font-medium text-xs">
            PO
          </div>
          <div className="text-left hidden md:block">
            <p className="text-xs font-semibold text-slate-800">Procurement Officer</p>
            <p className="text-[10px] text-slate-500">Evaluation Committee</p>
          </div>
        </div>
      </div>
    </header>
  );
};
