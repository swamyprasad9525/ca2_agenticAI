# API_DOCUMENTATION.md — Procurement Evaluation REST API

## 1. Overview

The backend exposes an asynchronous REST API built on **FastAPI**. All data payloads are validated using **Pydantic v2** models defined in `backend/app/schemas/`.

**Base URL**: `http://localhost:8000/api/v1`  
**Swagger UI**: `http://localhost:8000/docs`  
**ReDoc**: `http://localhost:8000/redoc`

---

## 2. API Endpoints Reference

### 2.1 Tenders Management (`/tenders`)

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `POST` | `/tenders` | Register a new tender specification | 201 Created |
| `GET` | `/tenders` | List all registered tenders | 200 OK |
| `GET` | `/tenders/{tender_id}` | Retrieve tender details with criteria and attached documents | 200 OK |
| `POST` | `/tenders/{tender_id}/documents` | Upload tender PDF/DOCX and index into vector store | 200 OK |
| `POST` | `/tenders/{tender_id}/criteria/extract` | Trigger Criteria Agent to extract criteria from RFP | 200 OK |
| `GET` | `/tenders/{tender_id}/criteria/plan` | Retrieve structured evaluation plan | 200 OK |
| `POST` | `/tenders/{tender_id}/criteria/approve` | Human approval of extracted evaluation plan | 200 OK |

---

### 2.2 Vendors & Bids (`/vendors`)

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `POST` | `/vendors` | Register a competing vendor company | 201 Created |
| `GET` | `/vendors` | List all registered vendors | 200 OK |
| `GET` | `/vendors/{vendor_id}` | Retrieve vendor details and bid history | 200 OK |
| `POST` | `/vendors/{vendor_id}/bids` | Submit a formal bid quotation for a tender | 201 Created |
| `POST` | `/bids/{bid_id}/documents` | Upload vendor proposal/pricing PDF and index into vector store | 200 OK |

---

### 2.3 Multi-Agent Evaluations & Orchestrator (`/evaluations`)

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `POST` | `/evaluations` | Initialize a new multi-agent evaluation run | 201 Created |
| `GET` | `/evaluations/{run_id}/status` | Check real-time pipeline status and agent execution telemetry | 200 OK |
| `POST` | `/evaluations/{run_id}/run` | **Trigger autonomous multi-agent evaluation pipeline** across all bids | 200 OK |
| `GET` | `/evaluations/{run_id}/scorecard` | Retrieve global persistent shared scorecard matrix | 200 OK |
| `GET` | `/evaluations/{run_id}/recommendation` | Retrieve executive award recommendation dossier | 200 OK |
| `POST` | `/evaluations/{run_id}/sign-off` | Record formal human procurement officer sign-off | 200 OK |

---

### 2.4 Reports & Export Endpoints (`/evaluations/{run_id}/export`)

| Method | Endpoint | Media Type | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/evaluations/{run_id}/export/pdf` | `application/pdf` | Download official procurement evaluation PDF dossier |
| `GET` | `/evaluations/{run_id}/export/csv` | `text/csv` | Download complete scorecard matrix as CSV spreadsheet |
| `GET` | `/evaluations/{run_id}/export/json` | `application/json` | Download complete evaluation archive in JSON format |

---

## 3. Sample Payloads

### 3.1 Initialize Evaluation
```http
POST /api/v1/evaluations HTTP/1.1
Content-Type: application/json

{
  "tender_id": "c1f7a0b2-3e4d-4e92-91f8-0e927519b7d4"
}
```

### 3.2 Human Sign-Off
```http
POST /api/v1/evaluations/4ca63fdd-7501-40c3-9158-929180467e51/sign-off HTTP/1.1
Content-Type: application/json

{
  "officer_name": "Marcus Vance",
  "officer_role": "Chief Procurement Officer",
  "decision": "APPROVE_AWARD",
  "selected_vendor_id": "v-alpha-01",
  "justification_comments": "Alpha Cloud demonstrates superior technical architecture and satisfies all statutory mandatory criteria within the allocated budget."
}
```

