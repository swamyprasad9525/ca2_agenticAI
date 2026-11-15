import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Play,
  RotateCw,
  ArrowRight,
  Zap,
  CheckCircle2,
  FileDown,
  AlertTriangle,
  Award,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { api } from '../services/api';
import { Tender, EvaluationRun, AwardRecommendation } from '../types';

export const EvaluationWorkspace: React.FC = () => {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [selectedTenderId, setSelectedTenderId] = useState('');
  const [activeRun, setActiveRun] = useState<EvaluationRun | null>(null);
  const [recommendation, setRecommendation] = useState<AwardRecommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    async function loadTenders() {
      try {
        const list = await api.getTenders();
        setTenders(list);
        if (list.length > 0) setSelectedTenderId(list[0].id);
      } catch (e) {
        console.error(e);
      }
    }
    loadTenders();
  }, []);

  async function handleStartEvaluation() {
    if (!selectedTenderId) return;
    setLoading(true);
    setRecommendation(null);
    try {
      const run = await api.startEvaluation(selectedTenderId);
      setActiveRun(run);
    } catch (err: any) {
      alert(err.message || 'Error launching evaluation');
    } finally {
      setLoading(false);
    }
  }

  async function handleTriggerWorkflow() {
    if (!activeRun) return;
    setRunningPipeline(true);
    try {
      const rec = await api.triggerEvaluationWorkflow(activeRun.id);
      setRecommendation(rec);
      const updated = await api.getEvaluationStatus(activeRun.id);
      setActiveRun(updated);
    } catch (err: any) {
      alert(err.message || 'Error during multi-agent evaluation execution');
    } finally {
      setRunningPipeline(false);
    }
  }

  async function handleRefreshStatus() {
    if (!activeRun) return;
    setRefreshing(true);
    try {
      const updated = await api.getEvaluationStatus(activeRun.id);
      setActiveRun(updated);
      try {
        const rec = await api.getAwardRecommendation(activeRun.id);
        setRecommendation(rec);
      } catch {
        // Not yet generated
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setRefreshing(false);
    }
  }

  const agents = [
    {
      name: '1. Criteria Agent',
      desc: 'Parses RFP via RAG, establishes Pass/Fail rules & technical weights',
      status: activeRun ? 'Active' : 'Standby',
    },
    {
      name: '2. Compliance Agent',
      desc: 'Screens bids against mandatory eligibility; sets Pass/Fail citations',
      status: activeRun ? 'Concurrent' : 'Standby',
    },
    {
      name: '3. Technical Scorer',
      desc: 'Qualitative proposal scoring against rubric with verbatim quotes',
      status: activeRun ? 'Concurrent' : 'Standby',
    },
    {
      name: '4. Commercial Scorer',
      desc: 'Normalizes pricing & feeds formulas to deterministic math engine',
      status: activeRun ? 'Concurrent' : 'Standby',
    },
    {
      name: '5. Award Manager',
      desc: 'Computes composite ranking & prepares human approval dossier',
      status: activeRun ? 'Synthesis' : 'Standby',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Evaluation Workspace</h1>
          <p className="text-sm text-slate-500 mt-1">
            Autonomous multi-agent procurement evaluation pipeline with strict human governance.
          </p>
        </div>
      </div>

      {/* Control Panel */}
      <Card title="Launch Multi-Agent Evaluation Run">
        <div className="flex flex-col md:flex-row md:items-end gap-4">
          <div className="flex-1">
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Select Target Tender for Evaluation
            </label>
            <select
              value={selectedTenderId}
              onChange={(e) => setSelectedTenderId(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
            >
              {tenders.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.reference_number}: {t.title} ({t.documents?.length || 0} RFP docs attached)
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleStartEvaluation}
            disabled={loading || !selectedTenderId}
            className="px-5 py-2.5 bg-sky-600 hover:bg-sky-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            {loading ? 'Initializing Pipeline...' : 'Initialize Evaluation Run'}
          </button>
        </div>
      </Card>

      {/* Active Run Telemetry */}
      {activeRun && (
        <Card
          title="Active Evaluation Run Telemetry"
          subtitle={`Run ID: ${activeRun.id}`}
          action={
            <div className="flex items-center gap-2">
              <button
                onClick={handleRefreshStatus}
                disabled={refreshing}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                title="Refresh Status"
              >
                <RotateCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              </button>
              <Link
                to={`/scorecard?run=${activeRun.id}`}
                className="px-3 py-1 bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 rounded-lg text-xs font-semibold flex items-center gap-1"
              >
                View Shared Scorecard <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          }
        >
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <p className="text-[11px] font-medium text-slate-500">Pipeline Status</p>
              <div className="mt-1">
                <Badge variant={activeRun.status === 'AWARD_APPROVED' ? 'success' : 'info'}>
                  {activeRun.status}
                </Badge>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <p className="text-[11px] font-medium text-slate-500">Active Workflow Step</p>
              <p className="text-xs font-semibold text-slate-800 mt-1">
                {activeRun.current_step || 'Initializing environment...'}
              </p>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <p className="text-[11px] font-medium text-slate-500">Participating Vendors</p>
              <p className="text-xs font-semibold text-slate-800 mt-1">
                Eligible: {activeRun.eligible_vendors_count} | Disqualified: {activeRun.disqualified_vendors_count}
              </p>
            </div>
          </div>

          {/* Trigger Workflow Action Button */}
          {activeRun.status === 'INITIALIZED' && (
            <div className="mb-6 p-4 bg-sky-50 border border-sky-200 rounded-xl flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-sky-900">Ready to Execute Multi-Agent Evaluation</h4>
                <p className="text-xs text-sky-700 mt-0.5">
                  Runs Criteria Agent, Compliance Agent, Technical Scorer, Commercial Scorer, and Award Manager across all registered bids.
                </p>
              </div>
              <button
                onClick={handleTriggerWorkflow}
                disabled={runningPipeline}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Zap className="w-4 h-4" />
                {runningPipeline ? 'Executing 5 Specialized Agents...' : 'Run Autonomous Evaluation'}
              </button>
            </div>
          )}

          {/* Award Recommendation Dossier Card */}
          {recommendation && (
            <div className="mb-6 p-5 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-sm">
                    <Award className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">
                      Recommended Contract Winner
                    </span>
                    <h3 className="text-lg font-bold text-slate-900">
                      {recommendation.recommended_vendor_name || 'No Eligible Vendor'}
                    </h3>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-500">Composite Score</span>
                  <p className="text-xl font-black text-emerald-700">
                    {recommendation.winning_composite_score ? `${recommendation.winning_composite_score.toFixed(2)}/100` : 'N/A'}
                  </p>
                </div>
              </div>

              <p className="text-xs text-slate-700 mt-3 leading-relaxed">
                {recommendation.executive_summary}
              </p>

              {recommendation.risk_assessment && recommendation.risk_assessment.length > 0 && (
                <div className="mt-3 pt-3 border-t border-emerald-200/60">
                  <span className="text-[11px] font-bold text-amber-800 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Risk Considerations:
                  </span>
                  <ul className="mt-1 space-y-1">
                    {recommendation.risk_assessment.map((r, idx) => (
                      <li key={idx} className="text-[11px] text-slate-600 list-disc list-inside">
                        {r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-4 pt-3 border-t border-emerald-200/60 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Status: <strong>{recommendation.status}</strong></span>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href={api.getExportPdfUrl(activeRun.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-xs"
                  >
                    <FileDown className="w-3.5 h-3.5 text-slate-500" /> Export PDF
                  </a>
                  <a
                    href={api.getExportCsvUrl(activeRun.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-xs"
                  >
                    <FileDown className="w-3.5 h-3.5 text-slate-500" /> Export CSV
                  </a>
                  <Link
                    to={`/reports?run=${activeRun.id}`}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-xs"
                  >
                    Human Sign-Off <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* 5 Agents Pipeline Cards */}
          <div className="space-y-3">
            <p className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Autonomous Agent Lifecycle:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {agents.map((ag, i) => (
                <div
                  key={i}
                  className="p-3.5 bg-white rounded-lg border border-slate-200 shadow-sm flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-xs text-slate-800">{ag.name}</span>
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    </div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">{ag.desc}</p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">State:</span>
                    <span className="font-medium text-slate-700">{ag.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
