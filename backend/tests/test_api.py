import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["api_version"] == "v1"


@pytest.mark.asyncio
async def test_tender_and_vendor_api_flow(client: AsyncClient):
    # 1. Create Tender
    tender_payload = {
        "title": "Cloud Infrastructure Migration",
        "reference_number": "RFP-API-2026-001",
        "description": "Migration of legacy datacenter to multi-region cloud.",
        "issuing_organization": "Ministry of Digital Affairs",
        "estimated_budget": 3500000.00,
        "currency": "USD",
    }
    t_res = await client.post("/api/v1/tenders", json=tender_payload)
    assert t_res.status_code == 201
    tender = t_res.json()
    assert tender["id"] is not None
    tender_id = tender["id"]

    # 2. Get Tender
    get_res = await client.get(f"/api/v1/tenders/{tender_id}")
    assert get_res.status_code == 200
    assert get_res.json()["reference_number"] == "RFP-API-2026-001"

    # 3. Register Vendor
    vendor_payload = {
        "name": "CloudNova Technologies",
        "registration_number": "CN-9922-US",
        "contact_email": "contracts@cloudnova.io",
        "country": "United States",
    }
    v_res = await client.post("/api/v1/vendors", json=vendor_payload)
    assert v_res.status_code == 201
    vendor = v_res.json()
    vendor_id = vendor["id"]

    # 4. Submit Bid
    bid_payload = {
        "tender_id": tender_id,
        "vendor_id": vendor_id,
        "total_quoted_price": 3200000.00,
        "currency": "USD",
    }
    b_res = await client.post(f"/api/v1/vendors/{vendor_id}/bids", json=bid_payload)
    assert b_res.status_code == 201
    bid = b_res.json()
    assert float(bid["total_quoted_price"]) == 3200000.0

    # 5. Initialize Evaluation
    eval_res = await client.post("/api/v1/evaluations", json={"tender_id": tender_id})
    assert eval_res.status_code == 201
    run = eval_res.json()
    run_id = run["id"]
    assert run["status"] == "INITIALIZED"

    # 6. Check Evaluation Status
    status_res = await client.get(f"/api/v1/evaluations/{run_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["id"] == run_id

    # 7. Get Scorecard
    scorecard_res = await client.get(f"/api/v1/evaluations/{run_id}/scorecard")
    assert scorecard_res.status_code == 200
    assert scorecard_res.json()["run_id"] == run_id

    # Index RAG chunks for vendor so compliance checks pass
    from backend.app.rag.chunker import DocumentChunk
    from backend.app.rag.vector_store import default_vector_store

    await default_vector_store.add_chunks([
        DocumentChunk(
            chunk_id=f"chunk-{vendor_id}-01",
            document_id="doc-test-1",
            document_name="CloudNova_Proposal.pdf",
            page_number=1,
            section_heading="Certifications & Legal Standing",
            text="CloudNova Technologies is a legally incorporated company with formal registration and valid ISO 27001 Information Security certification.",
            metadata={"tender_id": tender_id, "vendor_id": vendor_id, "document_type": "BID_PROPOSAL"},
        ),
        DocumentChunk(
            chunk_id=f"chunk-{vendor_id}-02",
            document_id="doc-test-2",
            document_name="CloudNova_Proposal.pdf",
            page_number=3,
            section_heading="Technical Architecture",
            text="Scalable multi-cloud Kubernetes deployment with automated SLA monitoring and 99.99% availability.",
            metadata={"tender_id": tender_id, "vendor_id": vendor_id, "document_type": "BID_PROPOSAL"},
        ),
    ])

    # 8. Trigger Evaluation Workflow via API
    run_exec_res = await client.post(f"/api/v1/evaluations/{run_id}/run")
    assert run_exec_res.status_code == 200
    rec = run_exec_res.json()
    assert rec["recommended_vendor_id"] == vendor_id
    assert rec["status"] == "RECOMMENDED_AWAITING_APPROVAL"

    # 9. Get Recommendation Dossier via API
    rec_res = await client.get(f"/api/v1/evaluations/{run_id}/recommendation")
    assert rec_res.status_code == 200
    assert rec_res.json()["recommended_vendor_id"] == vendor_id

    # 10. Human Sign-Off via API
    sign_off_payload = {
        "officer_name": "Sarah Jenkins",
        "officer_role": "Chief Procurement Officer",
        "decision": "APPROVE_AWARD",
        "selected_vendor_id": vendor_id,
        "justification_comments": "Fully meets technical criteria and within allocated budget envelope.",
    }
    sign_off_res = await client.post(f"/api/v1/evaluations/{run_id}/sign-off", json=sign_off_payload)
    assert sign_off_res.status_code == 200
    assert sign_off_res.json()["status"] == "APPROVED"

    # 11. Test Export Endpoints
    # PDF
    pdf_res = await client.get(f"/api/v1/evaluations/{run_id}/export/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 100

    # CSV
    csv_res = await client.get(f"/api/v1/evaluations/{run_id}/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "CloudNova Technologies" in csv_res.text

    # JSON
    json_res = await client.get(f"/api/v1/evaluations/{run_id}/export/json")
    assert json_res.status_code == 200
    assert json_res.json()["evaluation_run_id"] == run_id
