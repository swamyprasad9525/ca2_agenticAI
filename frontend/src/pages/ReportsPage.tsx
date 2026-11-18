import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FileCheck2,
  ShieldAlert,
  CheckCircle,
  HelpCircle,
  Lock,
  FileDown,
  AlertTriangle,
  UserCheck,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { api } from '../services/api';
import { AwardRecommendation, SharedScorecardResponse } from '../types';

export const ReportsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const runIdParam = searchParams.get('run');

  const [runId, setRunId] = useState(runIdParam || '');
  const [recommendation, setRecommendation] = useState<AwardRecommendation | null>(null);
  const [scorecard, setScorecard] = useState<SharedScorecardResponse | null>(null);
  const [loading, setLoading] = useState(false);

  // Sign-off form
  const [officerName, setOfficerName] = useState('');
  const [officerRole, setOfficerRole] = useState('Chief Procurement Officer');
  const [decision, setDecision] = useState<'APPROVE_AWARD' | 'REJECT_ALL' | 'OVERRIDE_WINNER'>('APPROVE_AWARD');
  const [selectedVendorId, setSelectedVendorId] = useState('');
  const [justification, setJustification] = useState('');
  const [signingOff, setSigningOff] = useState(false);
  const [signOffSuccess, setSignOffSuccess] = useState(false);

  useEffect(() => {
    if (runIdParam) {
      setRunId(runIdParam);
      loadReportData(runIdParam);
    }
  }, [runIdParam]);

  async function loadReportData(idToLoad: string) {
    if (!idToLoad) return;
    setLoading(true);
    setSignOffSuccess(false);
    try {
      const rec = await api.getAwardRecommendation(idToLoad);
      setRecommendation(rec);
      if (rec && rec.recommended_vendor_id) {
        setSelectedVendorId(rec.recommended_vendor_id);
      }
      const sc = await api.getSharedScorecard(idToLoad);
      setScorecard(sc);
    } catch (err: any) {
      console.error(err);
      setRecommendation(null);
      setScorecard(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleSignOffSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!runId || !officerName || !justification) {
      alert('Please complete all required sign-off fields.');
      return;
    }

    setSigningOff(true);
    try {
      const updated = await api.submitHumanSignOff(runId, {
        officer_name: officerName,
        officer_role: officerRole,
        decision: decision,
        selected_vendor_id: selectedVendorId,
        justification_comments: justification,
      });
      setRecommendation(updated);
      setSignOffSuccess(true);
      alert(`Decision recorded successfully: ${decision}`);
    } catch (err: any) {
      alert(err.message || 'Error submitting sign-off');
    } finally {
      setSigningOff(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Governance & Audit Reports
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Human-in-the-loop review, formal audit trails, and executive award recommendation reports.
          </p>
        </div>

        {runId && recommendation && (
          <div className="flex items-center gap-2">
            <a
              href={api.getExportPdfUrl(runId)}
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-xs transition-colors"
            >
              <FileDown className="w-4 h-4 text-slate-500" /> Export PDF Dossier
            </a>
            <a
              href={api.getExportCsvUrl(runId)}
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-xs transition-colors"
            >
              <FileDown className="w-4 h-4 text-slate-500" /> Export CSV
            </a>
            <a
              href={api.getExportJsonUrl(runId)}
              target="_blank"
              rel="noreferrer"
              className="px-3.5 py-2 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-xs transition-colors"
            >
              <FileDown className="w-4 h-4 text-slate-500" /> Export JSON
            </a>
          </div>
        )}
      </div>

      {/* Governance Banner */}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-amber-900 space-y-1">
          <p className="font-bold">Human Governance & Legal Authority Notice</p>
          <p className="text-amber-800 leading-relaxed">
            In accordance with public procurement laws and corporate governance standards, this AI system produces
            <strong> evidence-based recommendations only</strong> with status <code>AWAITING_HUMAN_APPROVAL</code>.
            Final award decisions, vendor disqualifications, and legally binding commitments remain strictly the
            prerogative of authorized human procurement officers.
          </p>
        </div>
      </div>

      {/* Select Evaluation Run Search Box */}
      <Card title="Select Evaluation Run for Audit Review">
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Enter Evaluation Run UUID..."
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            className="flex-1 text-sm px-3.5 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          <button
            onClick={() => loadReportData(runId)}
            disabled={loading || !runId}
            className="px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Load Dossier'}
          </button>
        </div>
      </Card>

      {/* Audit Dossier Contents */}
      {recommendation ? (
        <div className="space-y-6">
          {/* Executive Summary Card */}
          <div className="p-6 bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-2xl shadow-md">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-bold text-sky-400 uppercase tracking-widest">
                  AI Multi-Agent Award Recommendation
                </span>
                <h2 className="text-2xl font-black mt-1 text-white">
                  {recommendation.recommended_vendor_name || 'No Compliant Vendor'}
                </h2>
                <p className="text-xs text-slate-300 mt-2 max-w-2xl leading-relaxed">
                  {recommendation.executive_summary}
                </p>
              </div>

              <div className="text-right">
                <span className="text-xs text-slate-400">Winning Composite Score</span>
                <p className="text-3xl font-black text-emerald-400 mt-0.5">
                  {recommendation.winning_composite_score != null
                    ? `${Number(recommendation.winning_composite_score).toFixed(2)}/100`
                    : 'N/A'}
                </p>
                <div className="mt-2">
                  <Badge variant={recommendation.status === 'APPROVED' ? 'success' : 'warning'}>
                    {recommendation.status}
                  </Badge>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 font-semibold">Award Justification:</span>
                <p className="text-slate-200 mt-1 leading-relaxed">
                  {recommendation.award_justification}
                </p>
              </div>

              <div>
                <span className="text-slate-400 font-semibold">Runner-Up Vendor:</span>
                <p className="text-slate-200 mt-1">
                  {recommendation.runner_up_vendor_name || 'None'}
                </p>
                {recommendation.risk_assessment && recommendation.risk_assessment.length > 0 && (
                  <div className="mt-3">
                    <span className="text-amber-300 font-semibold flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> Risk Assessment:
                    </span>
                    <ul className="mt-1 space-y-0.5 text-slate-300">
                      {recommendation.risk_assessment.map((r, i) => (
                        <li key={i}>• {r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Formal Human Sign-Off Form */}
          <Card
            title="Formal Human Governance Sign-Off"
            subtitle="Procurement Officer verification and binding statutory decision"
          >
            {signOffSuccess || recommendation.status === 'APPROVED' ? (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3">
                <CheckCircle className="w-6 h-6 text-emerald-600 flex-shrink-0" />
                <div>
                  <h4 className="text-sm font-bold text-emerald-900">Award Decision Formally Signed Off</h4>
                  <p className="text-xs text-emerald-800 mt-0.5">
                    This evaluation has received formal human procurement officer authorization with status <code>APPROVED</code>.
                  </p>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSignOffSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Procurement Officer Full Name *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Marcus Vance"
                      value={officerName}
                      onChange={(e) => setOfficerName(e.target.value)}
                      className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Official Title / Authority *
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Chief Procurement Officer"
                      value={officerRole}
                      onChange={(e) => setOfficerRole(e.target.value)}
                      className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Formal Procurement Decision *
                    </label>
                    <select
                      value={decision}
                      onChange={(e: any) => setDecision(e.target.value)}
                      className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
                    >
                      <option value="APPROVE_AWARD">Approve Recommended Winner (Award Contract)</option>
                      <option value="OVERRIDE_WINNER">Override Winner (Select Alternate Vendor)</option>
                      <option value="REJECT_ALL">Reject All Submissions (Retender)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Selected Vendor
                    </label>
                    <select
                      value={selectedVendorId}
                      onChange={(e) => setSelectedVendorId(e.target.value)}
                      className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
                    >
                      {scorecard?.vendor_summaries.map((v) => (
                        <option key={v.vendor_id} value={v.vendor_id}>
                          {v.vendor_name} {v.is_disqualified ? '(Disqualified)' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Procurement Officer Comments & Audit Justification *
                  </label>
                  <textarea
                    rows={3}
                    required
                    placeholder="Provide official rationale, audit notes, or reasons for approval/override..."
                    value={justification}
                    onChange={(e) => setJustification(e.target.value)}
                    className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={signingOff}
                    className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-2 disabled:opacity-50"
                  >
                    <UserCheck className="w-4 h-4" />
                    {signingOff ? 'Recording Formal Sign-Off...' : 'Submit Statutory Sign-Off'}
                  </button>
                </div>
              </form>
            )}
          </Card>
        </div>
      ) : (
        /* Empty State */
        <Card
          title="Audit & Sign-Off Dossiers"
          subtitle="Completed multi-agent evaluation packages awaiting human sign-off"
        >
          <div className="text-center py-12">
            <FileCheck2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-700">No Dossier Loaded</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Enter an active Evaluation Run ID above or launch a multi-agent evaluation in the Evaluation Workspace to inspect the dossier and execute human sign-off.
            </p>
          </div>
        </Card>
      )}

      {/* System Integrity Principles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-2 text-sky-700">
            <Lock className="w-4 h-4" />
            <h4 className="font-bold text-xs uppercase tracking-wider">Zero Hallucinated Math</h4>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            All pricing formulas, weighting factors, point allocations, and rankings are executed by a deterministic
            Python calculation engine.
          </p>
        </Card>

        <Card>
          <div className="flex items-center gap-2 mb-2 text-emerald-700">
            <CheckCircle className="w-4 h-4" />
            <h4 className="font-bold text-xs uppercase tracking-wider">Mandatory Citations</h4>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Every compliance verdict and technical score is anchored to exact source document names, page numbers,
            and verbatim excerpts.
          </p>
        </Card>

        <Card>
          <div className="flex items-center gap-2 mb-2 text-indigo-700">
            <HelpCircle className="w-4 h-4" />
            <h4 className="font-bold text-xs uppercase tracking-wider">Auditability Trail</h4>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            All agent execution logs, timestamps, intermediate steps, and human review decisions are persisted
            in the shared transactional database.
          </p>
        </Card>
      </div>
    </div>
  );
};
