import os
import re
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
from docx import Document

from backend.app.core.logging import logger
from backend.app.core.exceptions import DocumentProcessingError

# Attempt import of pdfplumber for table extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class ParsedPage:
    def __init__(self, page_number: int, text: str, tables: Optional[List[str]] = None, headings: Optional[List[str]] = None):
        self.page_number = page_number
        self.text = text
        self.tables = tables or []
        self.headings = headings or []


class DocumentParser:
    """Extracts raw text, structured tables, and headings from PDF and DOCX files while preserving page numbers."""

    @staticmethod
    def _format_table_as_markdown(table_rows: List[List[Optional[str]]]) -> str:
        """Converts raw rows of table cells into clean markdown format."""
        if not table_rows or len(table_rows) < 1:
            return ""

        clean_rows = []
        for row in table_rows:
            clean_cells = [re.sub(r"\s+", " ", str(cell or "").strip()) for cell in row]
            if any(clean_cells):  # Only keep non-empty rows
                clean_rows.append(clean_cells)

        if not clean_rows:
            return ""

        col_count = max(len(r) for r in clean_rows)
        # Normalize cell count across rows
        normalized_rows = [r + [""] * (col_count - len(r)) for r in clean_rows]

        header = "| " + " | ".join(normalized_rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * col_count) + " |"
        body = ["| " + " | ".join(r) + " |" for r in normalized_rows[1:]]

        return "\n".join([header, separator] + body)

    @classmethod
    def parse_pdf(cls, file_path: str) -> List[ParsedPage]:
        pages: List[ParsedPage] = []
        
        # Try pdfplumber first for rich text + table extraction
        if HAS_PDFPLUMBER:
            try:
                with pdfplumber.open(file_path) as pdf:
                    for idx, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        tables = []
                        raw_tables = page.extract_tables() or []
                        for raw_tbl in raw_tables:
                            md_tbl = cls._format_table_as_markdown(raw_tbl)
                            if md_tbl:
                                tables.append(md_tbl)

                        # Detect potential headings
                        headings = re.findall(r"(?:^[0-9]+(?:\.[0-9]+)*\s+[A-Z][A-Za-z0-9\s]{2,60}$|^[A-Z\s]{4,40}$)", text, re.MULTILINE)

                        combined_text = text
                        if tables:
                            combined_text += "\n\n### Extracted Tables:\n" + "\n\n".join(tables)

                        pages.append(ParsedPage(page_number=idx + 1, text=combined_text, tables=tables, headings=headings))
                if pages:
                    return pages
            except Exception as e:
                logger.warning(f"pdfplumber extraction failed for {file_path}: {e}. Falling back to PyPDF.")

        # Fallback to PyPDF
        try:
            reader = PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                headings = re.findall(r"(?:^[0-9]+(?:\.[0-9]+)*\s+[A-Z][A-Za-z0-9\s]{2,60}$|^[A-Z\s]{4,40}$)", text, re.MULTILINE)
                pages.append(ParsedPage(page_number=idx + 1, text=text, headings=headings))
            return pages
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise DocumentProcessingError(f"Error parsing PDF document: {str(e)}")

    @classmethod
    def parse_docx(cls, file_path: str) -> List[ParsedPage]:
        try:
            doc = Document(file_path)
            
            # Extract tables as markdown
            doc_tables = []
            for tbl in doc.tables:
                raw_rows = []
                for row in tbl.rows:
                    raw_rows.append([cell.text for cell in row.cells])
                md = cls._format_table_as_markdown(raw_rows)
                if md:
                    doc_tables.append(md)

            # Extract paragraphs and detect headings
            full_text = []
            detected_headings = []
            for p in doc.paragraphs:
                p_text = p.text.strip()
                if not p_text:
                    continue
                if p.style and "Heading" in p.style.name:
                    detected_headings.append(p_text)
                full_text.append(p_text)

            # Segment into logical ~500-word pages preserving headings
            pages: List[ParsedPage] = []
            current_page_text = []
            current_headings = []
            current_word_count = 0
            page_num = 1

            for p_text in full_text:
                words = p_text.split()
                current_word_count += len(words)
                current_page_text.append(p_text)
                if p_text in detected_headings:
                    current_headings.append(p_text)

                if current_word_count >= 500:
                    text_block = "\n".join(current_page_text)
                    pages.append(ParsedPage(page_number=page_num, text=text_block, headings=list(current_headings)))
                    page_num += 1
                    current_page_text = []
                    current_headings = []
                    current_word_count = 0

            # Attach extracted tables to the final pages or create table page
            if current_page_text:
                text_block = "\n".join(current_page_text)
                pages.append(ParsedPage(page_number=page_num, text=text_block, headings=list(current_headings)))

            if doc_tables and pages:
                pages[-1].text += "\n\n### Extracted Tables:\n" + "\n\n".join(doc_tables)
                pages[-1].tables = doc_tables

            return pages or [ParsedPage(page_number=1, text="")]
        except Exception as e:
            logger.error(f"Failed to parse DOCX {file_path}: {e}")
            raise DocumentProcessingError(f"Error parsing DOCX document: {str(e)}")

    @classmethod
    def parse(cls, file_path: str) -> List[ParsedPage]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return cls.parse_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return cls.parse_docx(file_path)
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return [ParsedPage(page_number=1, text=f.read())]
