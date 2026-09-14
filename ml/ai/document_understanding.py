"""Multimodal Document Understanding layer for CrimeLens AI (Phase 2).

Provides format-agnostic structural, sectional, page-aware, and tabular understanding
of criminal investigation documents (PDFs, scans, images, text, and structured records).
Produces an internal structured intermediate representation for downstream extraction.

CRITICAL RULES:
1. Format-agnostic: Does NOT assume a fixed FIR template.
2. Grounded: Does NOT invent missing fields, page numbers, or snippets.
3. Safe: Does NOT assign criminal risk scores, guilt assessments, or accusations.
4. Isolated: ZERO connection to PostgreSQL, Neo4j, or FastAPI.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from ml.ai.client.client import AIClient
from ml.ai.errors import AIError, redact_secrets
from ml.ai.router import DocumentModality, DocumentRouter, RoutedDocument
from ml.ai.types import MultimodalInput
from ml.config import MLConfig, default_config
from ml.ocr.tesseract import extract_text_from_image, is_ocr_available
from ml.preprocessing.text_normalizer import normalize_text


@dataclass(frozen=True)
class DocumentPage:
    """Page-level container preserving document pagination context."""

    page_number: int
    text: str
    visual_elements: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentSection:
    """Semantic section within a document (e.g. heading, narrative, statement, table)."""

    title: Optional[str]
    section_type: str
    content: str
    page_number: Optional[int] = None
    confidence: float = 1.0


@dataclass(frozen=True)
class DocumentTable:
    """Tabular region identified within a document."""

    title: Optional[str]
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    page_number: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentUnderstanding:
    """Normalized, format-agnostic internal document understanding representation."""

    document_id: Optional[str]
    filename: Optional[str]
    document_type: str
    language: Optional[str]
    page_count: int
    pages: list[DocumentPage]
    sections: list[DocumentSection]
    tables: list[DocumentTable]
    full_text: str
    visual_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_scanned: bool = False
    confidence: float = 1.0

    def get_page(self, page_number: int) -> Optional[DocumentPage]:
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def get_section(self, section_type: str) -> Optional[DocumentSection]:
        st_upper = section_type.upper()
        for sec in self.sections:
            if sec.section_type.upper() == st_upper:
                return sec
        return None

    def get_sections_by_type(self, section_type: str) -> list[DocumentSection]:
        st_upper = section_type.upper()
        return [sec for sec in self.sections if sec.section_type.upper() == st_upper]

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary with secret scrubbing."""
        raw = asdict(self)

        def _scrub(obj: Any) -> Any:
            if isinstance(obj, dict):
                cleaned = {}
                for k, v in obj.items():
                    if any(term in str(k).lower() for term in ("key", "secret", "token", "password")):
                        continue
                    cleaned[k] = _scrub(v)
                return cleaned
            if isinstance(obj, list):
                return [_scrub(item) for item in obj]
            if isinstance(obj, str):
                return redact_secrets(obj)
            return obj

        return _scrub(raw)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentUnderstanding:
        pages = [
            DocumentPage(
                page_number=p.get("page_number", 1),
                text=p.get("text", ""),
                visual_elements=p.get("visual_elements", []),
                metadata=p.get("metadata", {}),
            )
            for p in data.get("pages", [])
        ]
        sections = [
            DocumentSection(
                title=s.get("title"),
                section_type=s.get("section_type", "GENERAL"),
                content=s.get("content", ""),
                page_number=s.get("page_number"),
                confidence=float(s.get("confidence", 1.0)),
            )
            for s in data.get("sections", [])
        ]
        tables = [
            DocumentTable(
                title=t.get("title"),
                headers=t.get("headers", []),
                rows=t.get("rows", []),
                page_number=t.get("page_number"),
                metadata=t.get("metadata", {}),
            )
            for t in data.get("tables", [])
        ]
        return cls(
            document_id=data.get("document_id"),
            filename=data.get("filename"),
            document_type=data.get("document_type", "GENERIC_DOCUMENT"),
            language=data.get("language", "en"),
            page_count=int(data.get("page_count", len(pages) or 1)),
            pages=pages,
            sections=sections,
            tables=tables,
            full_text=data.get("full_text", ""),
            visual_context=data.get("visual_context", {}),
            metadata=data.get("metadata", {}),
            is_scanned=bool(data.get("is_scanned", False)),
            confidence=float(data.get("confidence", 1.0)),
        )


class DocumentUnderstandingEngine:
    """Coordinates format-agnostic document understanding across AI and deterministic fallback."""

    def __init__(
        self,
        *,
        client: Optional[AIClient] = None,
        config: Optional[MLConfig] = None,
        router: Optional[DocumentRouter] = None,
    ) -> None:
        self.client = client
        self.config = config or default_config
        self.router = router or DocumentRouter()

    def understand(
        self,
        input_or_routed: RoutedDocument | MultimodalInput | str | bytes,
        *,
        document_id: Optional[str] = None,
        filename: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> DocumentUnderstanding:
        """Analyze a document and produce a structured DocumentUnderstanding instance.

        Args:
            input_or_routed: RoutedDocument, MultimodalInput, string text, file path, or bytes.
            document_id: Staging document identifier.
            filename: Original filename if available.
            context: Optional contextual hints.

        Returns:
            DocumentUnderstanding: Structured document representation.
        """
        if isinstance(input_or_routed, RoutedDocument):
            routed = input_or_routed
        else:
            routed = self.router.route(input_or_routed, filename=filename)

        doc_id = document_id or routed.metadata.get("document_id")
        fname = filename or routed.filename or routed.metadata.get("filename")

        # 1. Attempt AI-assisted understanding if enabled and client is operational
        if self.config.ai_enabled and self.client is not None and self.client.provider.is_available:
            try:
                return self._understand_with_ai(routed, doc_id=doc_id, filename=fname, context=context)
            except AIError:
                # Fall back safely to deterministic structural extraction
                pass

        # 2. Deterministic format-agnostic structural extraction
        return self._understand_deterministic(routed, doc_id=doc_id, filename=fname)

    def _understand_with_ai(
        self,
        routed: RoutedDocument,
        *,
        doc_id: Optional[str],
        filename: Optional[str],
        context: Optional[dict[str, Any]],
    ) -> DocumentUnderstanding:
        ai_context = {
            **(context or {}),
            "document_id": doc_id,
            "filename": filename,
            "modality": routed.modality.value,
            "task": "document_understanding",
        }

        response = self.client.analyze(routed.multimodal_input, context=ai_context)  # type: ignore

        # Validate and unpack untrusted model response
        payload = response.structured_payload
        ai_doc = payload.get("document_understanding")
        if isinstance(ai_doc, dict):
            return DocumentUnderstanding.from_dict({
                **ai_doc,
                "document_id": doc_id,
                "filename": filename,
                "is_scanned": routed.is_scanned,
            })

        # Fall back to synthesizing from candidate keys
        deterministic = self._understand_deterministic(routed, doc_id=doc_id, filename=filename)
        inferred_type = payload.get("document_type") or deterministic.document_type
        detected_lang = payload.get("language") or deterministic.language

        return DocumentUnderstanding(
            document_id=doc_id,
            filename=filename,
            document_type=str(inferred_type),
            language=str(detected_lang),
            page_count=deterministic.page_count,
            pages=deterministic.pages,
            sections=deterministic.sections,
            tables=deterministic.tables,
            full_text=deterministic.full_text,
            visual_context={**deterministic.visual_context, "ai_processed": True},
            metadata={**deterministic.metadata, "provider": response.provider_name},
            is_scanned=routed.is_scanned,
            confidence=min(1.0, max(0.0, float(payload.get("confidence", 0.9)))),
        )

    def _understand_deterministic(
        self,
        routed: RoutedDocument,
        *,
        doc_id: Optional[str],
        filename: Optional[str],
    ) -> DocumentUnderstanding:
        # A. Resolve raw text per modality
        raw_text, visual_elements = self._extract_modality_text(routed)

        # B. Page segmentation BEFORE form-feed stripping
        raw_pages = self._segment_pages(raw_text, visual_elements)
        pages = [
            DocumentPage(
                page_number=p.page_number,
                text=normalize_text(p.text),
                visual_elements=p.visual_elements,
                metadata=p.metadata,
            )
            for p in raw_pages
        ]
        clean_full_text = "\n\n".join(p.text for p in pages if p.text.strip()) or normalize_text(raw_text)

        # C. Section extraction (format-agnostic heuristics)
        sections = self._extract_sections(clean_full_text, pages)

        # D. Table extraction (pipe/tab/comma delimited detection)
        tables = self._extract_tables(clean_full_text, pages)

        # E. Document classification
        doc_type, type_confidence = self._classify_document_type(clean_full_text, filename, routed.modality)

        visual_context = {
            "modality": routed.modality.value,
            "is_scanned": routed.is_scanned,
            "requires_ocr": routed.requires_ocr,
            "visual_elements": visual_elements,
        }

        return DocumentUnderstanding(
            document_id=doc_id,
            filename=filename,
            document_type=doc_type,
            language="en",
            page_count=len(pages),
            pages=pages,
            sections=sections,
            tables=tables,
            full_text=clean_full_text,
            visual_context=visual_context,
            metadata={
                "routing_modality": routed.modality.value,
                "byte_size": routed.multimodal_input.byte_size,
            },
            is_scanned=routed.is_scanned,
            confidence=type_confidence,
        )

    def _extract_modality_text(self, routed: RoutedDocument) -> tuple[str, list[str]]:
        visual_elements: list[str] = []

        if routed.modality == DocumentModality.TEXT:
            if isinstance(routed.raw_content, bytes):
                try:
                    return routed.raw_content.decode("utf-8"), visual_elements
                except UnicodeDecodeError:
                    return routed.raw_content.decode("latin-1"), visual_elements
            return str(routed.raw_content), visual_elements

        if routed.modality == DocumentModality.IMAGE:
            visual_elements.extend(["image_scan", "visual_layout"])
            if isinstance(routed.raw_content, bytes) and is_ocr_available():
                try:
                    text = extract_text_from_image(routed.raw_content)
                    return text, visual_elements
                except Exception:
                    pass
            extracted = routed.multimodal_input.extracted_text or ""
            return extracted, visual_elements

        if routed.modality == DocumentModality.PDF:
            visual_elements.append("pdf_layout")
            if routed.multimodal_input.extracted_text:
                return routed.multimodal_input.extracted_text, visual_elements
            if isinstance(routed.raw_content, bytes):
                text_from_stream = self._extract_text_from_pdf_bytes(routed.raw_content)
                if text_from_stream.strip():
                    return text_from_stream, visual_elements
                # If scanned PDF and OCR is available
                if is_ocr_available():
                    try:
                        ocr_text = extract_text_from_image(routed.raw_content)
                        return ocr_text, visual_elements
                    except Exception:
                        pass
            return "", visual_elements

        if routed.modality == DocumentModality.STRUCTURED:
            visual_elements.append("structured_data")
            if isinstance(routed.raw_content, bytes):
                return routed.raw_content.decode("utf-8", errors="replace"), visual_elements
            return str(routed.raw_content), visual_elements

        return "", visual_elements

    def _extract_text_from_pdf_bytes(self, data: bytes) -> str:
        """Extract text chunks from uncompressed PDF text operators (BT ... ET)."""
        chunks: list[str] = []
        for match in re.finditer(rb"\((.*?)\)\s*Tj", data):
            try:
                chunks.append(match.group(1).decode("latin-1"))
            except Exception:
                continue
        if chunks:
            return " ".join(chunks)
        return ""

    def _segment_pages(self, raw_text: str, visual_elements: list[str]) -> list[DocumentPage]:
        if not raw_text.strip():
            return [DocumentPage(page_number=1, text="", visual_elements=visual_elements)]

        # 1. Split on explicit form-feed \f if present
        if "\f" in raw_text:
            chunks = raw_text.split("\f")
            pages: list[DocumentPage] = []
            page_num = 1
            for chunk in chunks:
                if chunk.strip():
                    pages.append(DocumentPage(
                        page_number=page_num,
                        text=chunk.strip(),
                        visual_elements=visual_elements,
                    ))
                    page_num += 1
            return pages or [DocumentPage(page_number=1, text=raw_text.strip(), visual_elements=visual_elements)]

        # 2. Header markers e.g. --- Page X --- or [Page X] or Page X of Y
        header_marker_pattern = re.compile(
            r"(?:^|\n)(?:---+\s*Page\s+\d+\s*---+|\[\s*Page\s+\d+\s*\]|Page\s+\d+\s+of\s+\d+)(?:\n|$)",
            re.IGNORECASE,
        )
        splits = header_marker_pattern.split(raw_text)
        if len(splits) > 1:
            pages = []
            page_num = 1
            for chunk in splits:
                if chunk.strip():
                    pages.append(DocumentPage(
                        page_number=page_num,
                        text=chunk.strip(),
                        visual_elements=visual_elements,
                    ))
                    page_num += 1
            return pages or [DocumentPage(page_number=1, text=raw_text.strip(), visual_elements=visual_elements)]

        return [DocumentPage(page_number=1, text=raw_text.strip(), visual_elements=visual_elements)]

    def _extract_sections(self, text: str, pages: list[DocumentPage]) -> list[DocumentSection]:
        sections: list[DocumentSection] = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        current_title: Optional[str] = None
        current_type = "GENERAL"
        current_lines: list[str] = []

        def _is_heading(line: str) -> bool:
            if len(line) > 70:
                return False
            # Line ends with a colon
            if line.endswith(":") and len(line.split()) <= 6:
                return True
            # All uppercase header (at least 4 chars)
            if line.isupper() and len(line) >= 4 and not any(ch.isdigit() for ch in line):
                return True
            # Numbered section e.g. 1. Introduction or Section 2: Details
            if re.match(r"^(?:[0-9]{1,2}[\.\)]|Section\s+[0-9]+:?)\s+[A-Z]", line, re.IGNORECASE):
                return True
            # Standard legal/investigation prefixes
            if re.match(r"^(?:Subject|Reference|Complaint|Statement|Incident|Facts|Occurrence|Seizure|Details|Conclusion)\s*:", line, re.IGNORECASE):
                return True
            return False

        for line in lines:
            if _is_heading(line):
                if current_lines:
                    sections.append(DocumentSection(
                        title=current_title,
                        section_type=current_type,
                        content="\n".join(current_lines),
                        confidence=0.9,
                    ))
                    current_lines = []
                current_title = line.rstrip(":")
                current_type = self._map_section_type(line)
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(DocumentSection(
                title=current_title,
                section_type=current_type,
                content="\n".join(current_lines),
                confidence=0.9,
            ))

        return sections

    def _map_section_type(self, heading: str) -> str:
        h = heading.lower()
        if any(w in h for w in ("subject", "reference", "date", "police station", "district", "report", "analysis", "dossier", "overview", "summary")):
            return "METADATA"
        if any(w in h for w in ("statement", "depose", "affidavit", "witness")):
            return "STATEMENT"
        if any(w in h for w in ("incident", "facts", "occurrence", "complaint", "allegation")):
            return "INCIDENT_DESCRIPTION"
        if any(w in h for w in ("transaction", "amount", "account", "bank", "credit", "debit", "financial")):
            return "FINANCIAL_RECORD"
        if any(w in h for w in ("communication", "call", "cdr", "imei", "tower", "phone", "duration")):
            return "COMMUNICATION_RECORD"
        if any(w in h for w in ("seizure", "recovery", "memo", "panchnama", "inventory")):
            return "SEIZURE_RECORD"
        return "NARRATIVE"



    def _extract_tables(self, text: str, pages: list[DocumentPage]) -> list[DocumentTable]:
        tables: list[DocumentTable] = []
        lines = text.splitlines()

        pipe_rows: list[list[str]] = []
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("|") and line_str.endswith("|") and line_str.count("|") >= 3:
                cells = [c.strip() for c in line_str.split("|")[1:-1]]
                # Filter out markdown divider rows e.g. |---|---|
                if all(re.match(r"^:?-+:?$", cell) for cell in cells if cell):
                    continue
                pipe_rows.append(cells)
            else:
                if len(pipe_rows) >= 2:
                    tables.append(DocumentTable(
                        title=None,
                        headers=pipe_rows[0],
                        rows=pipe_rows[1:],
                        page_number=1,
                    ))
                pipe_rows = []

        if len(pipe_rows) >= 2:
            tables.append(DocumentTable(
                title=None,
                headers=pipe_rows[0],
                rows=pipe_rows[1:],
                page_number=1,
            ))

        return tables

    def _classify_document_type(
        self,
        text: str,
        filename: Optional[str],
        modality: DocumentModality,
    ) -> tuple[str, float]:
        content = (text + " " + (filename or "")).lower()

        if modality == DocumentModality.STRUCTURED:
            if any(w in content for w in ("caller", "callee", "cdr", "duration", "imei", "tower")):
                return "CALL_DETAIL_RECORD", 0.95
            if any(w in content for w in ("transaction", "transfer", "amount", "sender", "receiver")):
                return "FINANCIAL_STATEMENT", 0.95
            return "STRUCTURED_DATA", 0.90

        if any(w in content for w in ("first information report", "f.i.r.", "fir no", "police station", "under section")):
            return "POLICE_REPORT", 0.95
        if any(w in content for w in ("seizure memo", "panchnama", "articles seized", "recovery memo")):
            return "SEIZURE_MEMO", 0.90
        if any(w in content for w in ("statement of", "deposes as under", "witness statement", "affidavit")):
            return "WITNESS_STATEMENT", 0.90
        if any(w in content for w in ("bank statement", "account number", "ifsc", "debit balance", "credit balance")):
            return "FINANCIAL_STATEMENT", 0.90
        if any(w in content for w in ("call detail record", "cdr analysis", "call log")):
            return "CALL_DETAIL_RECORD", 0.90
        if any(w in content for w in ("legal notice", "summons", "warrant", "hon'ble court")):
            return "LEGAL_NOTICE", 0.85

        return "GENERIC_DOCUMENT", 0.60
