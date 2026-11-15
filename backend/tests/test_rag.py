import pytest
from backend.app.rag.document_parser import DocumentParser, ParsedPage
from backend.app.rag.chunker import DocumentChunker
from backend.app.rag.vector_store import HybridPersistentVectorStore
from backend.app.rag.retriever import HybridRetriever


def test_markdown_table_formatting():
    raw_rows = [
        ["Criterion Code", "Description", "Max Points", "Weight"],
        ["TC-01", "Cloud Infrastructure Architecture", "40", "40%"],
        ["TC-02", "Cybersecurity & Incident Response", "30", "30%"],
        ["TC-03", "Team Credentials & Experience", "30", "30%"],
    ]
    md = DocumentParser._format_table_as_markdown(raw_rows)
    assert "| Criterion Code | Description | Max Points | Weight |" in md
    assert "| --- | --- | --- | --- |" in md
    assert "| TC-01 | Cloud Infrastructure Architecture | 40 | 40% |" in md


def test_intelligent_chunking_preserves_tables_and_metadata():
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
    page_text = (
        "Section 4: Technical Evaluation Requirements\n\n"
        "Bidders must provide details on high availability.\n\n"
        "| Item | Description | SLA |\n"
        "|---|---|---|\n"
        "| Gateway | API Gateway | 99.95% |\n"
        "| DB | Postgres Cluster | 99.99% |\n\n"
        "All data must be encrypted at rest."
    )
    pages = [ParsedPage(page_number=3, text=page_text, headings=["Section 4: Technical Evaluation Requirements"])]

    chunks = chunker.chunk_pages(
        document_id="doc-123",
        document_name="Tender_RFP.pdf",
        pages=pages,
        tender_id="tender-99",
        vendor_id=None,
    )

    assert len(chunks) >= 2
    # Verify table chunk exists and is preserved
    table_chunk = next(c for c in chunks if c.metadata.get("is_table"))
    assert "| Gateway | API Gateway | 99.95% |" in table_chunk.text
    assert table_chunk.page_number == 3
    assert table_chunk.tender_id == "tender-99"
    assert table_chunk.section_heading == "Section 4: Technical Evaluation Requirements"


@pytest.mark.asyncio
async def test_vector_store_tender_and_vendor_isolation(tmp_path):
    store_file = str(tmp_path / "test_vector_index.json")
    vstore = HybridPersistentVectorStore(persist_path=store_file)

    chunker = DocumentChunker()
    # Tender 1 chunks
    t1_chunks = chunker.chunk_pages(
        document_id="doc-t1",
        document_name="Tender1.pdf",
        pages=[ParsedPage(page_number=1, text="Tender 1 requires ISO 27001 and budget is 1,000,000 USD")],
        tender_id="tender-1",
    )
    # Tender 2 chunks
    t2_chunks = chunker.chunk_pages(
        document_id="doc-t2",
        document_name="Tender2.pdf",
        pages=[ParsedPage(page_number=1, text="Tender 2 requires CMMI Level 5 and budget is 5,000,000 USD")],
        tender_id="tender-2",
    )
    # Vendor A bid for Tender 1
    va_chunks = chunker.chunk_pages(
        document_id="doc-va",
        document_name="VendorA_Bid.pdf",
        pages=[ParsedPage(page_number=1, text="Vendor A quotes 850,000 USD with full ISO 27001 certificate")],
        tender_id="tender-1",
        vendor_id="vendor-A",
    )
    # Vendor B bid for Tender 1
    vb_chunks = chunker.chunk_pages(
        document_id="doc-vb",
        document_name="VendorB_Bid.pdf",
        pages=[ParsedPage(page_number=1, text="Vendor B quotes 920,000 USD without ISO certificate")],
        tender_id="tender-1",
        vendor_id="vendor-B",
    )

    await vstore.add_chunks(t1_chunks + t2_chunks + va_chunks + vb_chunks)

    retriever = HybridRetriever(vector_store=vstore)

    # 1. Tender 1 isolation: Search for ISO in Tender 1
    res_t1 = await retriever.retrieve(query="ISO certification budget", tender_id="tender-1")
    assert all(r.document_id in ["doc-t1", "doc-va", "doc-vb"] for r in res_t1)
    assert not any(r.document_id == "doc-t2" for r in res_t1)

    # 2. Vendor A isolation: Query Vendor A documents only
    res_va = await retriever.retrieve(query="quotes price ISO", vendor_id="vendor-A")
    assert len(res_va) == 1
    assert res_va[0].document_id == "doc-va"
    assert "Vendor A" in res_va[0].extracted_passage

