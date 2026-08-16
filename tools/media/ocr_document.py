"""
Robust CPU OCR Engine.

Transcribes scanned PDFs or image-based documents into structured Markdown text.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from core.errors import NotFoundError
from core.logging import loggable
from core.schemas import DocumentParseResult

if TYPE_CHECKING:
    from core.context import VaultContext


@loggable("ocr_document")
def ocr_document(
    pdf_path: str,
    ctx: VaultContext,
) -> DocumentParseResult:
    """
    Perform fast CPU OCR on scanned PDF pages.
    """
    import pymupdf
    from rapidocr_onnxruntime import RapidOCR

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise NotFoundError(
            error_code="pdf_not_found",
            user_message=f"PDF file not found: {pdf_path}",
            actionable_hint="Verify that the PDF file path exists on disk.",
        )

    dpi = ctx.settings.system.ingest.ocr.dpi
    engine = RapidOCR()
    page_transcripts: list[str] = []

    with pymupdf.open(str(pdf_file)) as doc:
        page_count = len(doc)
        for page_idx, page in enumerate(doc):
            # Render page at configured DPI for OCR precision
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")

            ocr_result, _ = engine(img_bytes)
            if not ocr_result:
                continue

            # Sort OCR bounding boxes top-to-bottom, left-to-right
            sorted_boxes = sorted(
                ocr_result,
                key=lambda item: (item[0][0][1], item[0][0][0]),
            )

            lines: list[str] = [item[1].strip() for item in sorted_boxes if item[1].strip()]
            if lines:
                page_text = f"<!-- Page {page_idx + 1} -->\n" + "\n".join(lines)
                page_transcripts.append(page_text)

    full_text = "\n\n".join(page_transcripts)
    return DocumentParseResult(
        text=full_text,
        page_count=page_count,
        images=[],
        is_scanned=True,
    )
