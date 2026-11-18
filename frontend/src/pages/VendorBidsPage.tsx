import React, { useEffect, useState } from 'react';
import { Plus, Users, Upload, FileText, Globe, Mail } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { api } from '../services/api';
import { Vendor, Tender, Bid } from '../types';

export const VendorBidsPage: React.FC = () => {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(true);

  // Register Vendor Modal
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [vName, setVName] = useState('');
  const [vReg, setVReg] = useState('');
  const [vEmail, setVEmail] = useState('');
  const [vCountry, setVCountry] = useState('');

  // Submit Bid Modal
  const [isSubmitBidOpen, setIsSubmitBidOpen] = useState(false);
  const [selectedTenderId, setSelectedTenderId] = useState('');
  const [selectedVendorId, setSelectedVendorId] = useState('');
  const [quotedPrice, setQuotedPrice] = useState('');
  const [bidCurrency, setBidCurrency] = useState('USD');

  // Upload Bid Document Modal
  const [isUploadDocOpen, setIsUploadDocOpen] = useState(false);
  const [uploadBidId, setUploadBidId] = useState<string | null>(null);
  const [bidDocType, setBidDocType] = useState('TECHNICAL_BID');
  const [bidFile, setBidFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // Selected Tender for viewing Bids
  const [activeTenderId, setActiveTenderId] = useState<string>('');
  const [tenderBids, setTenderBids] = useState<Bid[]>([]);

  async function loadData() {
    setLoading(true);
    try {
      const [vList, tList] = await Promise.all([
        api.getVendors(),
        api.getTenders(),
      ]);
      setVendors(vList);
      setTenders(tList);
      if (tList.length > 0 && !activeTenderId) {
        setActiveTenderId(tList[0].id);
        const bids = await api.getBidsForTender(tList[0].id);
        setTenderBids(bids);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleTenderChange(tenderId: string) {
    setActiveTenderId(tenderId);
    try {
      const bids = await api.getBidsForTender(tenderId);
      setTenderBids(bids);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleRegisterVendor(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.registerVendor({
        name: vName,
        registration_number: vReg,
        contact_email: vEmail,
        country: vCountry,
      });
      setIsRegisterOpen(false);
      setVName('');
      setVReg('');
      setVEmail('');
      setVCountry('');
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error registering vendor');
    }
  }

  async function handleSubmitBid(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.submitBid(selectedVendorId, {
        tender_id: selectedTenderId,
        vendor_id: selectedVendorId,
        total_quoted_price: quotedPrice ? parseFloat(quotedPrice) : undefined,
        currency: bidCurrency,
      });
      setIsSubmitBidOpen(false);
      setQuotedPrice('');
      if (activeTenderId === selectedTenderId) {
        const bids = await api.getBidsForTender(activeTenderId);
        setTenderBids(bids);
      }
    } catch (err: any) {
      alert(err.message || 'Error submitting bid');
    }
  }

  async function handleUploadBidDoc(e: React.FormEvent) {
    e.preventDefault();
    if (!uploadBidId || !bidFile) return;
    setUploading(true);
    try {
      await api.uploadBidDocument(uploadBidId, bidFile, bidDocType);
      setIsUploadDocOpen(false);
      setBidFile(null);
      if (activeTenderId) {
        const bids = await api.getBidsForTender(activeTenderId);
        setTenderBids(bids);
      }
    } catch (err: any) {
      alert(err.message || 'Error uploading bid document');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Vendor & Bid Management</h1>
          <p className="text-sm text-slate-500 mt-1">
            Register participating vendors and manage technical and commercial bid submissions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsRegisterOpen(true)}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-sm font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Register Vendor
          </button>
          <button
            onClick={() => setIsSubmitBidOpen(true)}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white text-sm font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Submit Vendor Bid
          </button>
        </div>
      </div>

      {/* Tender Selector Tab Bar */}
      {tenders.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mr-2">
            Active Tender:
          </span>
          {tenders.map((t) => (
            <button
              key={t.id}
              onClick={() => handleTenderChange(t.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                activeTenderId === t.id
                  ? 'bg-sky-600 text-white font-semibold'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {t.reference_number} ({t.title.slice(0, 25)}...)
            </button>
          ))}
        </div>
      )}

      {/* Bids for Selected Tender */}
      <Card
        title="Submitted Vendor Proposals"
        subtitle="Technical and commercial proposals submitted for evaluation"
      >
        {loading ? (
          <p className="text-sm text-slate-400 py-6 text-center">Loading submissions...</p>
        ) : tenderBids.length === 0 ? (
          <div className="text-center py-8">
            <Users className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-600 font-medium">No bids submitted for this tender</p>
            <p className="text-xs text-slate-400 mt-1">
              Click 'Submit Vendor Bid' above to register a proposal.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {tenderBids.map((bid) => (
              <div
                key={bid.id}
                className="p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-slate-800 text-base">
                        {bid.vendor?.name || 'Registered Vendor'}
                      </h4>
                      <Badge variant="info">Bid Submitted</Badge>
                    </div>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 mt-1">
                      {bid.vendor?.registration_number && (
                        <span>Reg: {bid.vendor.registration_number}</span>
                      )}
                      {bid.total_quoted_price && (
                        <span className="font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          Quoted: {bid.currency} {Number(bid.total_quoted_price).toLocaleString()}
                        </span>
                      )}
                      <span>{bid.documents.length} File(s) Attached</span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setUploadBidId(bid.id);
                      setIsUploadDocOpen(true);
                    }}
                    className="px-3 py-1.5 text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-lg flex items-center gap-1.5 transition-colors self-start md:self-auto"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Attach Proposal File
                  </button>
                </div>

                {/* Attached Bid Documents */}
                {bid.documents.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap gap-2">
                    {bid.documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center gap-2 px-2.5 py-1 bg-slate-50 border border-slate-200 rounded text-xs text-slate-700"
                      >
                        <FileText className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-medium">{doc.filename}</span>
                        <span className="text-[10px] text-sky-600 bg-sky-50 px-1 rounded">
                          {doc.document_type}
                        </span>
                        <span className="text-[10px] text-slate-400">({doc.page_count} pgs)</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Registered Vendors Directory */}
      <Card
        title="Registered Vendors Directory"
        subtitle="All commercial suppliers eligible to participate in tenders"
      >
        {vendors.length === 0 ? (
          <p className="text-xs text-slate-400 py-4 text-center">No vendors registered yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {vendors.map((v) => (
              <div
                key={v.id}
                className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-slate-800 text-sm">{v.name}</h4>
                  <Badge variant="neutral">Vendor</Badge>
                </div>
                <div className="text-xs text-slate-500 space-y-1">
                  {v.registration_number && <p>ID: {v.registration_number}</p>}
                  {v.contact_email && (
                    <p className="flex items-center gap-1.5">
                      <Mail className="w-3 h-3 text-slate-400" />
                      {v.contact_email}
                    </p>
                  )}
                  {v.country && (
                    <p className="flex items-center gap-1.5">
                      <Globe className="w-3 h-3 text-slate-400" />
                      {v.country}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Register Vendor Modal */}
      <Modal isOpen={isRegisterOpen} onClose={() => setIsRegisterOpen(false)} title="Register Commercial Vendor">
        <form onSubmit={handleRegisterVendor} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Company / Vendor Name</label>
            <input
              type="text"
              required
              placeholder="e.g. Apex Cloud Solutions LLC"
              value={vName}
              onChange={(e) => setVName(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Registration / Tax ID</label>
              <input
                type="text"
                placeholder="e.g. US-EIN-987654321"
                value={vReg}
                onChange={(e) => setVReg(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Country of Incorporation</label>
              <input
                type="text"
                placeholder="e.g. United States"
                value={vCountry}
                onChange={(e) => setVCountry(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Email</label>
            <input
              type="email"
              placeholder="bids@apexcloud.com"
              value={vEmail}
              onChange={(e) => setVEmail(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsRegisterOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-slate-800 hover:bg-slate-900 rounded-lg shadow-sm"
            >
              Register Vendor
            </button>
          </div>
        </form>
      </Modal>

      {/* Submit Bid Modal */}
      <Modal isOpen={isSubmitBidOpen} onClose={() => setIsSubmitBidOpen(false)} title="Submit Vendor Bid">
        <form onSubmit={handleSubmitBid} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Target Tender</label>
            <select
              required
              value={selectedTenderId}
              onChange={(e) => setSelectedTenderId(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
            >
              <option value="">-- Choose Tender --</option>
              {tenders.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.reference_number}: {t.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Submitting Vendor</label>
            <select
              required
              value={selectedVendorId}
              onChange={(e) => setSelectedVendorId(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
            >
              <option value="">-- Choose Vendor --</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Total Quoted Price</label>
              <input
                type="number"
                step="0.01"
                placeholder="e.g. 4850000"
                value={quotedPrice}
                onChange={(e) => setQuotedPrice(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Currency</label>
              <select
                value={bidCurrency}
                onChange={(e) => setBidCurrency(e.target.value)}
                className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="SGD">SGD (S$)</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsSubmitBidOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm"
            >
              Submit Bid
            </button>
          </div>
        </form>
      </Modal>

      {/* Upload Bid Document Modal */}
      <Modal isOpen={isUploadDocOpen} onClose={() => setIsUploadDocOpen(false)} title="Upload Proposal Document">
        <form onSubmit={handleUploadBidDoc} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Proposal Document Type</label>
            <select
              value={bidDocType}
              onChange={(e) => setBidDocType(e.target.value)}
              className="w-full text-sm px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
            >
              <option value="TECHNICAL_BID">Technical Proposal (Architecture, Methodology, SLAs)</option>
              <option value="COMMERCIAL_BID">Commercial Proposal (Pricing Schedule, Rate Card)</option>
              <option value="COMPLIANCE_CERT">Compliance Certifications (ISO, SOC2, Financials)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select File (PDF or DOCX)</label>
            <input
              type="file"
              required
              accept=".pdf,.docx,.doc"
              onChange={(e) => setBidFile(e.target.files?.[0] || null)}
              className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100 border border-slate-300 rounded-lg p-2"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsUploadDocOpen(false)}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploading}
              className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-sm disabled:opacity-50"
            >
              {uploading ? 'Uploading & Indexing...' : 'Upload Document'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
