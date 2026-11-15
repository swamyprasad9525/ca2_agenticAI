# RAG_IMPLEMENTATION.md — Retrieval-Augmented Generation Architecture

## 1. Overview

The Tender and Procurement Evaluation System incorporates a domain-specialized, citation-anchored Retrieval-Augmented Generation (RAG) pipeline designed specifically for enterprise procurement documents (PDF and DOCX). The pipeline emphasizes strict document-level and vendor-level metadata isolation, structural chunking, table extraction, and zero-loss citation tracking.

---

## 2. Ingestion Pipeline

### 2.1 Document Parser (`backend/app/rag/document_parser.py`)
- **PDF Extraction**:
  - Primary engine: `pdfplumber` for high-fidelity text extraction, page boundary tracking, and table cell layout detection.
  - Fallback engine: `pypdf` for resilient fallback handling if `pdfplumber` encounters font/stream corruptions.
- **DOCX Extraction**:
  - `python-docx` extracting paragraphs, style hierarchies (Headings 1-4), and table structures.
- **Table Preservation**:
  - Tables are identified, extracted, and formatted into clean GitHub Flavored Markdown (GFM) tables (e.g. `| TC-01 | Cloud Scalability | 40 |`). This guarantees that numeric rubrics, weights, and price cards remain semantically intact for RAG retrieval.

---

## 3. Structural Chunking Engine (`backend/app/rag/chunker.py`)

Standard fixed-character chunkers destroy table boundaries and split critical criteria across chunks. The system implements a **Semantic Structural Chunker**:
- **Target Size**: 500 words (~2,500 characters) with a 50-word sliding overlap.
- **Heading & Section Awareness**: Detects document sections, numbered clauses (e.g., "Section 4.2.1"), and RFP parts, stamping them into chunk metadata.
- **Table Integrity Guarantee**: Markdown tables are treated as atomic units and are never split mid-row across chunks.
- **Metadata Tagging**: Every chunk is permanently stamped with:
  - `chunk_id`: Unique identifier (e.g. `chunk-doc123-p4-c1`)
  - `document_id`: UUID of parent file
  - `document_name`: Filename (e.g. `Tender_RFP_Final.pdf`)
  - `page_number`: 1-based page number in the original file
  - `section_heading`: Most recent section or clause title
  - `metadata`: Key-value dictionary containing `tender_id`, `vendor_id`, and `document_type` (`TENDER`, `BID_PROPOSAL`, `COMMERCIAL_QUOTE`).

---

## 4. Vector Storage & Isolation (`backend/app/rag/vector_store.py`)

### 4.1 Hybrid Persistent Vector Store (`HybridPersistentVectorStore`)
- Implements a hybrid lexical-semantic matching engine with BM25-style term frequency, exact phrase matching, and section heading weighting.
- Backed by disk persistence (`chroma_db/vector_index.json`), maintaining chunk metadata and indices across server restarts.

### 4.2 Strict Tenant & Vendor Isolation
- All retrieval queries enforce mandatory metadata filtering:
  - When evaluating Vendor A, the retriever applies `filters={"tender_id": ..., "vendor_id": "v-alpha"}`.
  - Vendor A's queries can never access or retrieve text from Vendor B's submissions.
  - Tender specification queries filter exclusively on `{"tender_id": ..., "document_type": "TENDER"}`.

---

## 5. Retriever Interface (`backend/app/rag/retriever.py`)

`HybridRetriever` provides targeted, agent-specific query methods:
1. `retrieve_for_criteria(tender_id)`: Fetches technical requirements, scoring rubrics, and mandatory compliance lists.
2. `retrieve_for_compliance(tender_id, vendor_id, requirement_title, pass_criteria)`: Retrieves proof documents (ISO certificates, licenses, tax filings).
3. `retrieve_for_technical_criteria(tender_id, vendor_id, criterion_title, rubric)`: Retrieves technical architecture, methodology, and SLA proposals.
4. `retrieve_for_commercial_proposal(tender_id, vendor_id)`: Retrieves pricing sheets, fee schedules, and total cost summaries.

---

## 6. Citation Anchoring Architecture

Every agent verdict references a `RetrievalResult` converted into an `EvidenceReference`:
```json
{
  "document_id": "doc-alpha-01",
  "document_name": "Alpha_Cloud_Proposal.pdf",
  "page_number": 5,
  "section_reference": "Section 4.1: High Availability Cluster",
  "verbatim_quote": "Active-active multi-region Kubernetes cluster with automated failover and 99.99% uptime availability SLA.",
  "confidence_score": 0.98
}
```
In the web interface, procurement auditors can click "Inspect Citations" on any score or compliance row to open the Citation Drawer and inspect the exact excerpt and page location.

