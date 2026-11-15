import uuid
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    tender_id: Optional[str] = None
    vendor_id: Optional[str] = None
    document_name: str
    page_number: int
    section_heading: Optional[str] = None
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunker:
    """
    Intelligent, section-aware document chunking that preserves:
    - Tables without mid-table destruction
    - Clause and section headings
    - Page boundaries
    - Document, Tender, and Vendor metadata isolation
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(
        self,
        document_id: str,
        document_name: str,
        pages: List[Any],  # List of ParsedPage
        tender_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        base_meta = base_metadata or {}
        chunks: List[DocumentChunk] = []

        current_heading: Optional[str] = None

        for page in pages:
            text = page.text.strip()
            if not text:
                continue

            # Check if this page introduced a new section heading
            page_headings = getattr(page, "headings", [])
            if page_headings:
                current_heading = page_headings[0]

            # Separate markdown tables from prose to keep tables intact
            table_blocks = re.findall(r"(?:\|[^\n]+\|\n\|(?:\s*---+\s*\|)+\n(?:\|[^\n]+\|\n?)+)", text)
            
            # If the entire page text is reasonably sized, store as a coherent chunk
            if len(text) <= self.chunk_size or table_blocks:
                # If there are tables, create chunks for tables specifically to avoid cutting them
                remaining_text = text
                for tbl in table_blocks:
                    chunks.append(
                        DocumentChunk(
                            document_id=document_id,
                            tender_id=tender_id,
                            vendor_id=vendor_id,
                            document_name=document_name,
                            page_number=page.page_number,
                            section_heading=current_heading,
                            text=tbl.strip(),
                            metadata={
                                **base_meta,
                                "page_number": page.page_number,
                                "is_table": True,
                                "tender_id": tender_id,
                                "vendor_id": vendor_id,
                            },
                        )
                    )
                    remaining_text = remaining_text.replace(tbl, "")

                # Now process remaining prose text
                remaining_text = remaining_text.strip()
                if remaining_text:
                    if len(remaining_text) <= self.chunk_size:
                        chunks.append(
                            DocumentChunk(
                                document_id=document_id,
                                tender_id=tender_id,
                                vendor_id=vendor_id,
                                document_name=document_name,
                                page_number=page.page_number,
                                section_heading=current_heading,
                                text=remaining_text,
                                metadata={
                                    **base_meta,
                                    "page_number": page.page_number,
                                    "is_table": False,
                                    "tender_id": tender_id,
                                    "vendor_id": vendor_id,
                                },
                            )
                        )
                    else:
                        self._split_and_append_text(
                            chunks=chunks,
                            text=remaining_text,
                            document_id=document_id,
                            document_name=document_name,
                            tender_id=tender_id,
                            vendor_id=vendor_id,
                            page_number=page.page_number,
                            section_heading=current_heading,
                            base_meta=base_meta,
                        )
            else:
                self._split_and_append_text(
                    chunks=chunks,
                    text=text,
                    document_id=document_id,
                    document_name=document_name,
                    tender_id=tender_id,
                    vendor_id=vendor_id,
                    page_number=page.page_number,
                    section_heading=current_heading,
                    base_meta=base_meta,
                )

        return chunks

    def _split_and_append_text(
        self,
        chunks: List[DocumentChunk],
        text: str,
        document_id: str,
        document_name: str,
        tender_id: Optional[str],
        vendor_id: Optional[str],
        page_number: int,
        section_heading: Optional[str],
        base_meta: Dict[str, Any],
    ) -> None:
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                last_space = text.rfind(" ", start, end)
                if last_space > start + (self.chunk_size // 2):
                    end = last_space

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        tender_id=tender_id,
                        vendor_id=vendor_id,
                        document_name=document_name,
                        page_number=page_number,
                        section_heading=section_heading,
                        text=chunk_text,
                        metadata={
                            **base_meta,
                            "page_number": page_number,
                            "tender_id": tender_id,
                            "vendor_id": vendor_id,
                        },
                    )
                )

            if end >= len(text):
                break
            start = max(start + 1, end - self.chunk_overlap)
