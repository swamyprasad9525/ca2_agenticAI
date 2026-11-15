import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  Users,
  Award,
  CheckCircle2,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { api } from '../services/api';
import { Tender, Vendor } from '../types';

export const Dashboard: React.FC = () => {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [tList, vList] = await Promise.all([
          api.getTenders().catch(() => []),
          api.getVendors().catch(() => []),
        ]);
        setTenders(tList);
        setVendors(vList);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const stats = [
    {
      label: 'Active Tenders',
      value: tenders.length,
      icon: FileText,
      color: 'bg-sky-50 text-sky-600 border-sky-100',
    },
    {
      label: 'Registered Vendors',
      value: vendors.length,
      icon: Users,
      color: 'bg-indigo-50 text-indigo-600 border-indigo-100',
    },
    {
      label: 'Specialized Agents',
      value: '5 Active',
      icon: CheckCircle2,
      color: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    },
    {
      label: 'Evaluation Mode',
      value: 'Deterministic',
      icon: Award,
      color: 'bg-amber-50 text-amber-600 border-amber-100',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Procurement Evaluation Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Autonomous multi-agent tender assessment & evidence-based scorecard management.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/tenders"
            className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2"
          >
            <FileText className="w-4 h-4" />
            Create Tender
          </Link>
          <Link
            to="/evaluations"
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-sm font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2"
          >
            <TrendingUp className="w-4 h-4" />
            Evaluation Workspace
          </Link>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <div
            key={i}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4"
          >
            <div className={`p-3 rounded-xl border ${stat.color}`}>
              <stat.icon className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">{stat.label}</p>
              <p className="text-xl font-bold text-slate-900 mt-0.5">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Two Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Tenders */}
        <div className="lg:col-span-2">
          <Card
            title="Recent Tenders & RFPs"
            subtitle="Authoritative tender documents governing active evaluations"
            action={
              <Link
                to="/tenders"
                className="text-xs font-semibold text-sky-600 hover:text-sky-800 flex items-center gap-1"
              >
                View all <ArrowRight className="w-3 h-3" />
              </Link>
            }
          >
            {loading ? (
              <p className="text-sm text-slate-400 py-4 text-center">Loading tenders...</p>
            ) : tenders.length === 0 ? (
              <div className="text-center py-8">
                <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-600 font-medium">No tenders created yet</p>
                <p className="text-xs text-slate-400 mt-1">
                  Upload an RFP or tender document to configure evaluation criteria.
                </p>
                <Link
                  to="/tenders"
                  className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 bg-sky-50 text-sky-700 border border-sky-200 rounded-lg text-xs font-semibold hover:bg-sky-100"
                >
                  Create your first tender
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 text-xs">
                      <th className="pb-3 font-medium">Reference</th>
                      <th className="pb-3 font-medium">Title</th>
                      <th className="pb-3 font-medium">Organization</th>
                      <th className="pb-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {tenders.slice(0, 5).map((t) => (
                      <tr key={t.id} className="hover:bg-slate-50/50">
                        <td className="py-3 font-mono text-xs text-slate-600">
                          {t.reference_number}
                        </td>
                        <td className="py-3 font-medium text-slate-800">{t.title}</td>
                        <td className="py-3 text-slate-500 text-xs">{t.issuing_organization}</td>
                        <td className="py-3">
                          <Badge variant={t.status === 'ACTIVE' ? 'success' : 'neutral'}>
                            {t.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        {/* Multi-Agent Architecture Overview */}
        <div>
          <Card
            title="Multi-Agent Governance"
            subtitle="Microsoft Agent Framework Pipeline"
          >
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="w-6 h-6 rounded-full bg-sky-100 text-sky-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  1
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-800">Criteria Agent</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Extracts mandatory Pass/Fail rules, technical weights, and pricing formulas.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  2
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-800">Compliance Agent</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Evaluates bids against mandatory criteria; flags non-compliant vendors as disqualified.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  3
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-800">Technical Scorer</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Evaluates eligible vendor technical proposals; provides citations and rubric points.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  4
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-800">Commercial Scorer</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Analyzes pricing schedules and delegates math to the deterministic calculation engine.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100">
                <span className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  5
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-800">Award Manager</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Aggregates shared scorecard, computes rankings, and prepares sign-off report.
                  </p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
