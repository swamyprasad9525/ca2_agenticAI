# DEMO_GUIDE.md — System Demonstration & Quickstart Walkthrough

## 1. Quickstart Environment Setup

### Prerequisites
- Python 3.12+ (installed in virtual environment `.venv`)
- Node.js 18+ and npm

### 1.1 Start the FastAPI Backend
```bash
# Activate Python virtual environment
.\.venv\Scripts\activate

# Launch FastAPI ASGI server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
API Documentation will be live at: `http://localhost:8000/docs`.

### 1.2 Start the React Frontend
```bash
# In a separate terminal
cd frontend
npm run dev
```
Open your browser at: `http://localhost:5173`.

---

## 2. Automated Test & Demo Execution

You can run the full multi-agent automated demonstration with a single command:
```bash
.\.venv\Scripts\pytest.exe backend\tests\test_e2e_demo.py -v -s
```
This test automatically:
1. Seeds a government RFP for cloud infrastructure.
2. Registers 4 synthetic competing vendors (Alpha, Beta, Gamma, Delta).
3. Executes concurrent fan-out compliance and scoring.
4. Enforces the compliance gate (disqualifying Delta and flagging Gamma).
5. Executes the deterministic scoring engine to recommend Alpha as the winner.
6. Simulates procurement officer sign-off (`APPROVE_AWARD`).
7. Validates the generated PDF report, CSV scorecard, and JSON audit dump.

---

## 3. Step-by-Step Web UI Walkthrough

### Step 1: Browse Tenders
1. Navigate to **Tenders** in the navigation bar.
2. View existing tender specifications or click **New Tender** to create an RFP.
3. Upload tender specifications (PDF or DOCX).

### Step 2: Manage Vendor Bids
1. Navigate to **Vendor Bids**.
2. Register vendor candidates (e.g. *Alpha Cloud Systems*, *Beta Data Corp*).
3. Submit formal bid quotations and attach proposal / pricing documents.

### Step 3: Run Multi-Agent Evaluation
1. Navigate to **Evaluation Workspace**.
2. Select the target tender and click **Initialize Evaluation Run**.
3. Click **Run Autonomous Evaluation**:
   - Watch the 5 specialized agents execute in real time.
   - Criteria Agent extracts rubrics and weights.
   - Compliance Agent screens all bidders concurrently.
   - Technical and Commercial Scorers evaluate eligible proposals.
   - Award Manager computes composite scores, ranks vendors, and presents the **Recommended Contract Winner**.

### Step 4: Audit Shared Scorecard
1. Click **View Shared Scorecard** or navigate to **Scorecard**.
2. Inspect the ranked comparative matrix across all vendors.
3. Click **Inspect Citations** on any row to open the Citation Drawer and inspect the exact verbatim quotes and page numbers supporting the finding.

### Step 5: Governance Sign-Off & Report Export
1. Navigate to **Reports & Sign-Off**.
2. Review the Executive Summary, Award Justification, and Procurement Risk Assessment.
3. Fill in the Procurement Officer Sign-Off form and click **Submit Statutory Sign-Off**.
4. Click **Export PDF Dossier** to download the official audit report, or **Export CSV** / **Export JSON** for spreadsheets and data archives.

