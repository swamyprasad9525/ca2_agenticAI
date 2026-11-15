import React, { useEffect, useState } from 'react';
import { Plus, FileText, Upload, DollarSign, Building } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { api } from '../services/api';
import { Tender } from '../types';

export const TendersPage: React.FC = () => {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(true);

  // Create Tender Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [refNum, setRefNum] = useState('');
  const [org, setOrg] = useState('');
  const [budget, setBudget] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [description, setDescription] = useState('');

  // Upload Document Modal State
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedTenderId, setSelectedTenderId] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  async function loadTenders() {
    setLoading(true);
    try {
      const data = await api.getTenders();
      setTenders(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTenders();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.createTender({
        title,
        reference_number: refNum,
        issuing_organization: org,
        estimated_budget: budget ? parseFloat(budget) : undefined,
        currency,
        description,
      });
      setIsCreateOpen(false);
      setTitle('');
      setRefNum('');
      setOrg('');
      setBudget('');
      setDescription('');
      await loadTenders();
    } catch (err: any) {
      alert(err.message || 'Error creating tender');
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedTenderId || !uploadFile) return;
    setUploading(true);
    try {
      await api.uploadTenderDocument(selectedTenderId, uploadFile, 'TENDER_RFP');
      setIsUploadOpen(false);
      setUploadFile(null);
      await loadTenders();
    } catch (err: any) {
      alert(err.message || 'Error uploading document');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Tenders & RFPs</h1>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative tender documents governing procurement evaluation criteria.
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Create New Tender
        </button>
      </div>

      {/* Tenders Grid */}
      {loading ? (
        <p className="text-sm text-slate-400 py-8 text-center">Loading tenders...</p>
      ) : tenders.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-700">No Tenders Registered</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Create an official tender entry and upload its Request for Proposal (RFP) specification.
            </p>
            <button
              onClick={() => setIsCreateOpen(true)}
              className="mt-4 px-4 py-2 bg-sky-600 text-white text-xs font-semibold rounded-lg hover:bg-sky-700 transition-colors"
            >
              Create Tender Now
            </button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {tenders.map((t) => (
            <Card key={t.id}>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                      {t.reference_number}
                    </span>
                    <Badge variant={t.status === 'ACTIVE' ? 'success' : 'neutral'}>
                      {t.status}
                    </Badge>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900">{t.title}</h3>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                    <span className="flex items-center gap-1.5">
                      <Building className="w-3.5 h-3.5 text-slate-400" />
                      {t.issuing_organization}
                    </span>
                    {t.estimated_budget && (
                      <span className="flex items-center gap-1.5">
                        <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                        {t.currency} {t.estimated_budget.toLocaleString()}
                      </span>
                    )}
                    <span className="flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-slate-400" />
                      {t.documents.length} Document(s) Attached
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setSelectedTenderId(t.id);
                      setIsUploadOpen(true);
                    }}
                    className="px-3 py-1.5 text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-lg flex items-center gap-1.5 transition-colors"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Upload RFP Doc
                  </button>
                </div>
              </div>

              {/* Document List */}
              {t.documents.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <p className="text-xs font-semibold text-slate-600 mb-2">Attached RFP Files:</p>
                  <div className="flex flex-wrap gap-2">
                    {t.documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center gap-2 px-2.5 py-1 bg-slate-50 border border-slate-200 rounded text-xs text-slate-700"
                      >
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-medium">{doc.filename}</span>
                        <span className="text-[10px] text-slate-400">({doc.page_count} pgs)</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Create Tender Modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Create Procurement Tender">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Tender Title</label>
            <input
              type="text"
              required
              placeholder="e.g. Enterprise Cloud ERP Modernization RFP"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Reference Number</label>
              <input
                type="text"
                required
                placeholder="e.g. RFP-2026-IT-0042"
                value={refNum}
                onChange={(e) => setRefNum(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Issuing Organization</label>
              <input
                type="text"
                required
                placeholder="e.g. Department of Transport"
                value={org}
                onChange={(e) => setOrg(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Estimated Budget</label>
              <input
                type="number"
                step="0.01"
                placeholder="e.g. 5000000"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="SGD">SGD (S$)</option>
                <option value="AED">AED (AED)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Description</label>
            <textarea
              rows={3}
              placeholder="Scope of work, project goals, and submission guidelines..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm"
            >
              Create Tender
            </button>
          </div>
        </form>
      </Modal>

      {/* Upload RFP Document Modal */}
      <Modal isOpen={isUploadOpen} onClose={() => setIsUploadOpen(false)} title="Upload RFP Document">
        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Select Document (PDF or Word DOCX)
            </label>
            <input
              type="file"
              required
              accept=".pdf,.docx,.doc"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100 border border-slate-300 rounded-lg p-2"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Uploaded files are strictly treated as untrusted documents; citations will be extracted with exact page numbers.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsUploadOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploading}
              className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm disabled:opacity-50"
            >
              {uploading ? 'Processing Document...' : 'Upload & Index'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
