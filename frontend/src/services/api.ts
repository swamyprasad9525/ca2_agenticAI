import {
  Tender,
  Vendor,
  Bid,
  EvaluationRun,
  SharedScorecardResponse,
} from '../types';

const BASE_URL = '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.message || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export const api = {
  // ==================== Tenders ====================
  async getTenders(): Promise<Tender[]> {
    const res = await fetch(`${BASE_URL}/tenders`);
    return handleResponse<Tender[]>(res);
  },

  async getTender(id: string): Promise<Tender> {
    const res = await fetch(`${BASE_URL}/tenders/${id}`);
    return handleResponse<Tender>(res);
  },

  async createTender(payload: {
    title: string;
    reference_number: string;
    description?: string;
    issuing_organization: string;
    submission_deadline?: string;
    estimated_budget?: number;
    currency?: string;
  }): Promise<Tender> {
    const res = await fetch(`${BASE_URL}/tenders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<Tender>(res);
  },

  async uploadTenderDocument(tenderId: string, file: File, documentType: string = 'TENDER_RFP'): Promise<Tender> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    const res = await fetch(`${BASE_URL}/tenders/${tenderId}/documents`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<Tender>(res);
  },

  // ==================== Vendors ====================
  async getVendors(): Promise<Vendor[]> {
    const res = await fetch(`${BASE_URL}/vendors`);
    return handleResponse<Vendor[]>(res);
  },

  async registerVendor(payload: {
    name: string;
    registration_number?: string;
    contact_email?: string;
    country?: string;
  }): Promise<Vendor> {
    const res = await fetch(`${BASE_URL}/vendors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<Vendor>(res);
  },

  // ==================== Bids ====================
  async getBidsForTender(tenderId: string): Promise<Bid[]> {
    const res = await fetch(`${BASE_URL}/tenders/${tenderId}/bids`);
    return handleResponse<Bid[]>(res);
  },

  async submitBid(vendorId: string, payload: {
    tender_id: string;
    vendor_id: string;
    total_quoted_price?: number;
    currency?: string;
  }): Promise<Bid> {
    const res = await fetch(`${BASE_URL}/vendors/${vendorId}/bids`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<Bid>(res);
  },

  async uploadBidDocument(bidId: string, file: File, documentType: string = 'TECHNICAL_BID'): Promise<Bid> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);

    const res = await fetch(`${BASE_URL}/bids/${bidId}/documents`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<Bid>(res);
  },

  // ==================== Evaluations & Scorecard ====================
  async startEvaluation(tenderId: string): Promise<EvaluationRun> {
    const res = await fetch(`${BASE_URL}/evaluations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tender_id: tenderId }),
    });
    return handleResponse<EvaluationRun>(res);
  },

  async getEvaluationStatus(runId: string): Promise<EvaluationRun> {
    const res = await fetch(`${BASE_URL}/evaluations/${runId}/status`);
    return handleResponse<EvaluationRun>(res);
  },

  async getSharedScorecard(runId: string): Promise<SharedScorecardResponse> {
    const res = await fetch(`${BASE_URL}/evaluations/${runId}/scorecard`);
    return handleResponse<SharedScorecardResponse>(res);
  },

  async triggerEvaluationWorkflow(runId: string, vendorIds?: string[]): Promise<any> {
    const res = await fetch(`${BASE_URL}/evaluations/${runId}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(vendorIds || null),
    });
    return handleResponse<any>(res);
  },

  async getAwardRecommendation(runId: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/evaluations/${runId}/recommendation`);
    return handleResponse<any>(res);
  },

  async submitHumanSignOff(runId: string, payload: any): Promise<any> {
    const res = await fetch(`${BASE_URL}/evaluations/${runId}/sign-off`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  getExportPdfUrl(runId: string): string {
    return `${BASE_URL}/evaluations/${runId}/export/pdf`;
  },

  getExportCsvUrl(runId: string): string {
    return `${BASE_URL}/evaluations/${runId}/export/csv`;
  },

  getExportJsonUrl(runId: string): string {
    return `${BASE_URL}/evaluations/${runId}/export/json`;
  },
};

