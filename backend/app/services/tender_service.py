from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import TenderNotFoundError
from backend.app.core.logging import logger
from backend.app.db.models.tender import Tender, TenderDocument
from backend.app.db.models.criteria import EvaluationCriterion, MandatoryRequirement
from backend.app.repositories.tender_repo import TenderRepository
from backend.app.services.document_service import DocumentService
from backend.app.schemas.tender import TenderCreate, TenderRead, TenderUpdate
from backend.app.schemas.criteria import (
    EvaluationCriterionCreate,
    MandatoryRequirementCreate,
)


class TenderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TenderRepository(session)
        self.doc_service = DocumentService()

    async def create_tender(self, data: TenderCreate) -> TenderRead:
        existing = await self.repo.get_by_reference(data.reference_number)
        if existing:
            raise ValueError(f"Tender with reference '{data.reference_number}' already exists")

        tender = Tender(
            title=data.title,
            reference_number=data.reference_number,
            description=data.description,
            issuing_organization=data.issuing_organization,
            submission_deadline=data.submission_deadline,
            estimated_budget=data.estimated_budget,
            currency=data.currency,
            status="DRAFT",
        )
        created = await self.repo.create(tender)
        await self.session.commit()
        logger.info(f"Created Tender {created.id} ({created.reference_number})")
        return await self.get_tender(created.id)

    async def get_tender(self, tender_id: str) -> TenderRead:
        tender = await self.repo.get_with_relations(tender_id)
        if not tender:
            raise TenderNotFoundError(f"Tender with ID '{tender_id}' not found")
        return TenderRead.model_validate(tender)

    async def list_tenders(self, skip: int = 0, limit: int = 100) -> List[TenderRead]:
        tenders = await self.repo.get_all(skip=skip, limit=limit)
        results = []
        for t in tenders:
            full = await self.repo.get_with_relations(t.id)
            if full:
                results.append(TenderRead.model_validate(full))
        return results

    async def add_document(
        self,
        tender_id: str,
        filename: str,
        content: bytes,
        document_type: str = "TENDER_RFP",
    ) -> TenderRead:
        import uuid
        tender = await self.repo.get_by_id(tender_id)
        if not tender:
            raise TenderNotFoundError(f"Tender with ID '{tender_id}' not found")

        doc_id = str(uuid.uuid4())
        file_path, sha256, file_size, page_count = await self.doc_service.save_uploaded_file(
            filename=filename,
            content=content,
            document_id=doc_id,
            tender_id=tender_id,
            document_type=document_type,
        )

        doc = TenderDocument(
            id=doc_id,
            tender_id=tender_id,
            filename=filename,
            file_path=file_path,
            document_type=document_type,
            page_count=page_count,
            file_size_bytes=file_size,
            sha256_checksum=sha256,
        )
        await self.repo.add_document(doc)
        await self.session.commit()
        logger.info(f"Attached and indexed document {filename} for Tender {tender_id}")
        return await self.get_tender(tender_id)

    async def configure_criteria(
        self,
        tender_id: str,
        mandatory: List[MandatoryRequirementCreate],
        technical: List[EvaluationCriterionCreate],
    ) -> TenderRead:
        tender = await self.repo.get_by_id(tender_id)
        if not tender:
            raise TenderNotFoundError(f"Tender with ID '{tender_id}' not found")

        for req in mandatory:
            m = MandatoryRequirement(
                tender_id=tender_id,
                requirement_code=req.requirement_code,
                category=req.category.value if hasattr(req.category, "value") else str(req.category),
                title=req.title,
                description=req.description,
                pass_criteria=req.pass_criteria,
            )
            self.session.add(m)

        for tc in technical:
            c = EvaluationCriterion(
                tender_id=tender_id,
                criterion_code=tc.criterion_code,
                criterion_type=tc.criterion_type.value if hasattr(tc.criterion_type, "value") else str(tc.criterion_type),
                section=tc.section,
                title=tc.title,
                description=tc.description,
                max_points=tc.max_points,
                weight=tc.weight,
                scoring_rubric=tc.scoring_rubric,
            )
            self.session.add(c)

        await self.session.commit()
        logger.info(f"Configured {len(mandatory)} mandatory & {len(technical)} criteria for Tender {tender_id}")
        return await self.get_tender(tender_id)

