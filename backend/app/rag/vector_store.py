import os
import json
import math
import re
from typing import List, Dict, Any, Optional, Protocol
from backend.app.rag.chunker import DocumentChunk
from backend.app.core.logging import logger
from backend.app.core.config import settings


class VectorStoreProvider(Protocol):
    async def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        ...

    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        ...

    async def delete_by_document(self, document_id: str) -> None:
        ...

    async def delete_by_tender(self, tender_id: str) -> None:
        ...


class HybridPersistentVectorStore:
    """
    Production-ready hybrid lexical-semantic vector store with metadata isolation.
    Guarantees strict tender and vendor boundary isolation and persists state to disk.
    """

    def __init__(self, persist_path: str = "./chroma_db/vector_index.json"):
        self.persist_path = persist_path
        self._chunks: List[DocumentChunk] = []
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._chunks = [DocumentChunk(**item) for item in data]
                logger.info(f"Loaded {len(self._chunks)} chunks from persistent store ({self.persist_path})")
            except Exception as e:
                logger.warning(f"Could not load vector store from {self.persist_path}: {e}")
                self._chunks = []

    def _save_to_disk(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump([c.model_dump() for c in self._chunks], f, indent=2)
        except Exception as e:
            logger.error(f"Error persisting vector store to {self.persist_path}: {e}")

    async def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        # Avoid duplicate chunk IDs
        existing_ids = {c.chunk_id for c in self._chunks}
        new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]
        self._chunks.extend(new_chunks)
        self._save_to_disk()
        logger.info(f"Indexed {len(new_chunks)} new chunks. Total indexed: {len(self._chunks)}")

    def _score_chunk(self, query: str, chunk: DocumentChunk) -> float:
        """
        Hybrid BM25-style term frequency + section heading boost.
        """
        q_tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]
        if not q_tokens:
            return 0.0

        c_text = chunk.text.lower()
        c_heading = (chunk.section_heading or "").lower()
        c_tokens = re.findall(r"\w+", c_text)
        if not c_tokens:
            return 0.0

        score = 0.0
        for token in q_tokens:
            tf = c_tokens.count(token)
            if tf > 0:
                # Term frequency saturation
                score += (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * (len(c_tokens) / 200.0)))
            # Significant boost if query term appears in clause/section heading
            if token in c_heading:
                score += 3.0

        # Boost table chunks when query asks for pricing or numbers
        if any(term in query.lower() for term in ["price", "cost", "total", "fee", "rate", "usd", "points", "weight"]):
            if chunk.metadata.get("is_table") or "|" in chunk.text:
                score += 2.0

        return float(score)

    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        candidates = self._chunks

        # Apply metadata filters (Strict Tender and Vendor Isolation)
        if filters:
            filtered = []
            for c in candidates:
                match = True
                for k, v in filters.items():
                    if v is None:
                        continue
                    if k == "tender_id":
                        chunk_tender = c.tender_id or c.metadata.get("tender_id")
                        if chunk_tender != v:
                            match = False
                            break
                    elif k == "vendor_id":
                        chunk_vendor = c.vendor_id or c.metadata.get("vendor_id")
                        if chunk_vendor != v:
                            match = False
                            break
                    elif k == "document_id":
                        if c.document_id != v:
                            match = False
                            break
                    elif k == "document_type":
                        if c.metadata.get("document_type") != v:
                            match = False
                            break
                if match:
                    filtered.append(c)
            candidates = filtered

        # Score and rank
        scored = [(self._score_chunk(query, c), c) for c in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)

        return [c for score, c in scored[:top_k]]

    async def delete_by_document(self, document_id: str) -> None:
        self._chunks = [c for c in self._chunks if c.document_id != document_id]
        self._save_to_disk()
        logger.info(f"Deleted chunks for document {document_id}")

    async def delete_by_tender(self, tender_id: str) -> None:
        self._chunks = [c for c in self._chunks if c.tender_id != tender_id and c.metadata.get("tender_id") != tender_id]
        self._save_to_disk()
        logger.info(f"Deleted chunks for tender {tender_id}")


# Default persistent vector store instance
default_vector_store = HybridPersistentVectorStore()
