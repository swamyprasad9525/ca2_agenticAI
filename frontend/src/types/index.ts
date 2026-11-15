export interface TenderDocument {
  id: string;
  tender_id: string;
  filename: string;
  file_path: string;
  document_type: string;
  page_count: number;
  file_size_bytes: number;
  sha256_checksum: string;
  created_at: string;
}

export interface EvaluationCriterion {
  id: string;
  tender_id: string;
  criterion_code: string;
  criterion_type: 'TECHNICAL' | 'COMMERCIAL';
  section: string;
  title: string;
  description: string;
  max_points: number;
  weight: number;
  scoring_rubric: string;
  created_at: string;
}

export interface MandatoryRequirement {
  id: string;
  tender_id: string;
  requirement_code: string;
  category: string;
  title: string;
  description: string;
  pass_criteria: string;
  created_at: string;
}

export interface Tender {
  id: string;
  title: string;
  reference_number: string;
  description?: string;
  issuing_organization: string;
  submission_deadline?: string;
  estimated_budget?: number;
  currency: string;
  status: string;
  created_at: string;
  updated_at: string;
  documents: TenderDocument[];
  criteria: EvaluationCriterion[];
  mandatory_requirements: MandatoryRequirement[];
}

export interface Vendor {
  id: string;
  name: string;
  registration_number?: string;
  contact_email?: string;
  country?: string;
  created_at: string;
  updated_at: string;
}

export interface BidDocument {
  id: string;
  bid_id: string;
  filename: string;
  file_path: string;
  document_type: string;
  page_count: number;
  file_size_bytes: number;
  created_at: string;
}

export interface Bid {
  id: string;
  tender_id: string;
  vendor_id: string;
  total_quoted_price?: number;
  currency: string;
  status: string;
  submission_timestamp: string;
  documents: BidDocument[];
  vendor?: Vendor;
}

export interface EvidenceReference {
  id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  section_reference?: string;
  verbatim_quote: string;
  confidence_score: number;
}

export interface ComplianceItem {
  id: string;
  requirement_id: string;
  status: 'PASS' | 'FAIL' | 'UNCLEAR';
  findings: string;
  is_disqualified: boolean;
  requires_human_review: boolean;
  evidence: EvidenceReference[];
}

export interface ScorecardEntry {
  id: string;
  run_id: string;
  vendor_id: string;
  criterion_id?: string;
  score_type: 'TECHNICAL' | 'COMMERCIAL' | 'COMPOSITE';
  raw_points?: number;
  max_points?: number;
  weight?: number;
  weighted_score?: number;
  normalized_score?: number;
  rank?: number;
  justification?: string;
  version: number;
  evidence: EvidenceReference[];
}

export interface VendorScorecardSummary {
  vendor_id: string;
  vendor_name: string;
  is_disqualified: boolean;
  disqualification_reasons: string[];
  requires_human_review: boolean;
  compliance_status: string;
  compliance_items: ComplianceItem[];
  technical_scores: ScorecardEntry[];
  commercial_score?: ScorecardEntry;
  composite_score?: number;
  rank?: number;
}

export interface SharedScorecardResponse {
  run_id: string;
  tender_id: string;
  status: string;
  current_step?: string;
  total_vendors: number;
  eligible_vendors_count: number;
  disqualified_vendors_count: number;
  vendor_summaries: VendorScorecardSummary[];
  agent_executions: Array<{
    id: string;
    agent_name: string;
    vendor_id?: string;
    status: string;
    retry_count: number;
    started_at?: string;
    completed_at?: string;
  }>;
  updated_at: string;
}

export interface EvaluationRun {
  id: string;
  tender_id: string;
  status: string;
  current_step?: string;
  eligible_vendors_count: number;
  disqualified_vendors_count: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface AwardRecommendation {
  run_id: string;
  tender_id: string;
  recommended_vendor_id?: string;
  recommended_vendor_name?: string;
  winning_composite_score?: number;
  runner_up_vendor_id?: string;
  runner_up_vendor_name?: string;
  executive_summary: string;
  award_justification: string;
  risk_assessment: string[];
  status: 'RECOMMENDED_AWAITING_APPROVAL' | 'APPROVED' | 'REJECTED' | 'OVERRIDDEN';
  generated_at: string;
}

export interface HumanSignOffPayload {
  officer_name: string;
  officer_role: string;
  decision: 'APPROVE_AWARD' | 'REJECT_ALL' | 'OVERRIDE_WINNER' | 'REQUEST_RE_EVALUATION';
  selected_vendor_id: string;
  justification_comments: string;
  override_reason?: string;
}
