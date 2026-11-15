from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.app.rag.chunker import DocumentChunk
from backend.app.rag.vector_store import VectorStoreProvider, default_vector_store
from backend.app.schemas.evidence import EvidenceReferenceBase


class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section_heading: Optional[str] = None
    extracted_passage: str
    confidence_score: float = 1.0

    def to_evidence_reference(self) -> EvidenceReferenceBase:
        return EvidenceReferenceBase(
            document_id=self.document_id,
            document_name=self.document_name,
            page_number=self.page_number,
            section_reference=self.section_heading,
            verbatim_quote=self.extracted_passage[:400],
            confidence_score=self.confidence_score,
        )


class HybridRetriever:
    """
    RAG service used across all 5 agents.
    Provides targeted queries with metadata filtering, strict tender/vendor isolation, and verifiable citations.
    """

    def __init__(self, vector_store: VectorStoreProvider = default_vector_store):
        self.vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        tender_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[RetrievalResult]:
        filters: Dict[str, Any] = {}
        if tender_id:
            filters["tender_id"] = tender_id
        if vendor_id:
            filters["vendor_id"] = vendor_id
        if document_type:
            filters["document_type"] = document_type

        chunks = await self.vector_store.similarity_search(query=query, top_k=top_k, filters=filters)
        results = []
        for c in chunks:
            results.append(
                RetrievalResult(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    document_name=c.document_name,
                    page_number=c.page_number,
                    section_heading=c.section_heading,
                    extracted_passage=c.text,
                    confidence_score=1.0,
                )
            )
        return results

    # Targeted query methods for procurement evaluation
    async def get_technical_criteria_evidence(self, tender_id: str) -> List[RetrievalResult]:
        return await self.retrieve(
            query="technical evaluation criteria scoring rubric maximum points weight architecture methodology",
            top_k=6,
            tender_id=tender_id,
        )

    async def get_mandatory_requirements_evidence(self, tender_id: str) -> List[RetrievalResult]:
        return await self.retrieve(
            query="mandatory requirements eligibility pass fail disqualification certifications legal tax",
            top_k=6,
            tender_id=tender_id,
        )

    async def get_commercial_formula_evidence(self, tender_id: str) -> List[RetrievalResult]:
        return await self.retrieve(
            query="commercial price evaluation formula lowest price weighting total cost of ownership payment terms",
            top_k=5,
            tender_id=tender_id,
        )

    async def get_vendor_compliance_evidence(self, vendor_id: str, requirement_keywords: str) -> List[RetrievalResult]:
        return await self.retrieve(
            query=f"compliance certificate declaration {requirement_keywords}",
            top_k=4,
            vendor_id=vendor_id,
        )

    async def get_vendor_technical_evidence(self, vendor_id: str, criterion_keywords: str) -> List[RetrievalResult]:
        return await self.retrieve(
            query=f"technical proposal capability architecture SLA {criterion_keywords}",
            top_k=4,
            vendor_id=vendor_id,
        )

    async def get_vendor_pricing_evidence(self, vendor_id: str) -> List[RetrievalResult]:
        return await self.retrieve(
            query="commercial price quotation total cost rate card fee taxes delivery",
            top_k=5,
            vendor_id=vendor_id,
        )
