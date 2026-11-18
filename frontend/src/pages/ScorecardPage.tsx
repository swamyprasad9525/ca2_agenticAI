import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  AlertCircle,
  FileText,
  RotateCw,
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { api } from '../services/api';
import { SharedScorecardResponse, EvidenceReference } from '../types';

export const ScorecardPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [runIdInput, setRunIdInput] = useState(searchParams.get('run') || '');
  const [scorecard, setScorecard] = useState<SharedScorecardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Evidence inspection modal
  const [inspectedEvidence, setInspectedEvidence] = useState<EvidenceReference[] | null>(null);
  const [inspectionTitle, setInspectionTitle] = useState('');

  async function loadScorecard(id: string) {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSharedScorecard(id.trim());
      setScorecard(data);
    } catch (err: any) {
      setError(err.message || 'Error loading scorecard');
      setScorecard(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const urlRunId = searchParams.get('run');
    if (urlRunId) {
      setRunIdInput(urlRunId);
      loadScorecard(urlRunId);
    }
  }, [searchParams]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    loadScorecard(runIdInput);
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Shared Scorecard Matrix</h1>
          <p className="text-sm text-slate-500 mt-1">
            Persistent, transactional multi-vendor evaluation results with citation anchoring.
          </p>
        </div>
      </div>

      {/* Lookup Bar */}
      <Card>
        <form onSubmit={handleSearch} className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Enter Evaluation Run UUID..."
              value={runIdInput}
              onChange={(e) => setRunIdInput(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-1.5"
          >
            {loading && <RotateCw className="w-3.5 h-3.5 animate-spin" />}
            Retrieve Scorecard
          </button>
        </form>
      </Card>

      {/* Error Notice */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Scorecard Results */}
      {scorecard && (
        <div className="space-y-6">
          {/* Summary Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-[11px] font-medium text-slate-500">Execution Status</p>
              <div className="mt-1">
                <Badge variant={scorecard.status === 'COMPLETED' ? 'success' : 'info'}>
                  {scorecard.status}
                </Badge>
              </div>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-[11px] font-medium text-slate-500">Total Bidders</p>
              <p className="text-xl font-bold text-slate-900 mt-0.5">{scorecard.total_vendors}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-[11px] font-medium text-slate-500">Compliant / Eligible</p>
              <p className="text-xl font-bold text-emerald-600 mt-0.5">
                {scorecard.eligible_vendors_count}
              </p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-[11px] font-medium text-slate-500">Disqualified Vendors</p>
              <p className="text-xl font-bold text-rose-600 mt-0.5">
                {scorecard.disqualified_vendors_count}
              </p>
            </div>
          </div>

          {/* Matrix Table */}
          <Card
            title="Multi-Vendor Comparative Scorecard"
            subtitle="Deterministic composite weighted scores and compliance statuses"
          >
            {scorecard.vendor_summaries.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">
                Evaluation initialized. Waiting for agent assessments to be committed to the scorecard.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 text-xs bg-slate-50/50">
                      <th className="py-3 px-3 font-semibold">Rank</th>
                      <th className="py-3 px-3 font-semibold">Vendor Name</th>
                      <th className="py-3 px-3 font-semibold">Eligibility Status</th>
                      <th className="py-3 px-3 font-semibold">Technical Score</th>
                      <th className="py-3 px-3 font-semibold">Commercial Score</th>
                      <th className="py-3 px-3 font-semibold">Composite Score</th>
                      <th className="py-3 px-3 font-semibold text-right">Evidence Audit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {scorecard.vendor_summaries.map((v) => (
                      <tr key={v.vendor_id} className="hover:bg-slate-50/50">
                        <td className="py-3.5 px-3 font-bold text-slate-800">
                          {v.rank ? `#${v.rank}` : '-'}
                        </td>
                        <td className="py-3.5 px-3 font-semibold text-slate-900">
                          {v.vendor_name}
                        </td>
                        <td className="py-3.5 px-3">
                          <Badge
                            variant={
                              v.compliance_status === 'PASSED'
                                ? 'success'
                                : v.compliance_status === 'DISQUALIFIED'
                                ? 'danger'
                                : 'warning'
                            }
                          >
                            {v.compliance_status}
                          </Badge>
                        </td>
                        <td className="py-3.5 px-3 font-mono text-xs text-slate-700">
                          {v.technical_scores.length > 0
                            ? `${v.technical_scores.reduce((acc, s) => acc + Number(s.weighted_score || 0), 0).toFixed(2)} pts`
                            : 'Pending'}
                        </td>
                        <td className="py-3.5 px-3 font-mono text-xs text-slate-700">
                          {v.commercial_score?.weighted_score != null
                            ? `${Number(v.commercial_score.weighted_score).toFixed(2)} pts`
                            : 'Pending'}
                        </td>
                        <td className="py-3.5 px-3 font-mono font-bold text-slate-900">
                          {v.composite_score != null ? `${Number(v.composite_score).toFixed(2)}` : 'Pending'}
                        </td>
                        <td className="py-3.5 px-3 text-right">
                          <button
                            onClick={() => {
                              const evidence = [
                                ...v.compliance_items.flatMap((c) => c.evidence),
                                ...v.technical_scores.flatMap((s) => s.evidence),
                              ];
                              setInspectedEvidence(evidence);
                              setInspectionTitle(`Citation Evidence — ${v.vendor_name}`);
                            }}
                            className="px-2.5 py-1 text-xs font-medium text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded flex items-center gap-1 ml-auto"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            Inspect Citations
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Evidence Drawer / Modal */}
      <Modal
        isOpen={Boolean(inspectedEvidence)}
        onClose={() => setInspectedEvidence(null)}
        title={inspectionTitle}
        maxWidth="lg"
      >
        {!inspectedEvidence || inspectedEvidence.length === 0 ? (
          <p className="text-xs text-slate-400 py-4 text-center">
            No citation evidence attached to these items yet.
          </p>
        ) : (
          <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
            {inspectedEvidence.map((ev, i) => (
              <div
                key={i}
                className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">{ev.document_name}</span>
                  <span className="text-slate-500 font-mono">Page {ev.page_number}</span>
                </div>
                {ev.section_reference && (
                  <p className="text-[11px] font-medium text-sky-700">{ev.section_reference}</p>
                )}
                <blockquote className="text-xs italic text-slate-600 bg-white p-2 rounded border border-slate-100 border-l-2 border-l-sky-500">
                  "{ev.verbatim_quote}"
                </blockquote>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};
