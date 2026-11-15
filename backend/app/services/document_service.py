import asyncio
import hashlib
import os
import uuid
from typing import Tuple, Optional, Dict, Any
from pypdf import PdfReader
from docx import Document

from backend.app.core.config import settings
from backend.app.core.exceptions import DocumentProcessingError
from backend.app.core.logging import logger
from backend.app.rag.document_parser import DocumentParser
from backend.app.rag.chunker import DocumentChunker
from backend.app.rag.vector_store import default_vector_store


class DocumentService:
    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = upload_dir
        self.chunker = DocumentChunker()
        self.vector_store = default_vector_store
        os.makedirs(self.upload_dir, exist_ok=True)

    def _write_file_sync(self, file_path: str, content: bytes) -> None:
        with open(file_path, "wb") as f:
            f.write(content)

    async def save_uploaded_file(
        self,
        filename: str,
        content: bytes,
        document_id: Optional[str] = None,
        tender_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        document_type: str = "TENDER_RFP",
    ) -> Tuple[str, str, int, int]:
        """
        Saves uploaded file content to disk, parses text/tables, chunks, and indexes in vector store.
        Returns: (saved_file_path, sha256_checksum, file_size_bytes, page_count)
        """
        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise DocumentProcessingError(
                f"File size ({len(content)} bytes) exceeds maximum limit ({settings.MAX_UPLOAD_SIZE_BYTES} bytes)"
            )

        file_ext = os.path.splitext(filename)[1].lower()
        doc_id = document_id or str(uuid.uuid4())
        unique_name = f"{doc_id}_{filename}"
        file_path = os.path.join(self.upload_dir, unique_name)

        # Write to disk asynchronously
        await asyncio.to_thread(self._write_file_sync, file_path, content)

        # Compute SHA-256
        sha256 = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        # Parse document into pages (with table preservation)
        pages = DocumentParser.parse(file_path)
        page_count = len(pages) if pages else 1

        # Chunk and index in vector store
        chunks = self.chunker.chunk_pages(
            document_id=doc_id,
            document_name=filename,
            pages=pages,
            tender_id=tender_id,
            vendor_id=vendor_id,
            base_metadata={
                "document_type": document_type,
                "tender_id": tender_id,
                "vendor_id": vendor_id,
            },
        )
        await self.vector_store.add_chunks(chunks)
        logger.info(f"Indexed {len(chunks)} chunks for {filename} (Doc ID: {doc_id})")

        return file_path, sha256, file_size, page_count
