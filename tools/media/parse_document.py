"""
Structured PDF Layout Parser Engine.

Extracts structural layout Markdown text, parses native tables, and slices high-definition
figures into media/ with MD5 deduplication for repeating headers/logos.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from core.errors import NotFoundError
from core.logging import loggable
from core.schemas import DocumentParseResult, ExtractedImageMetadata

if TYPE_CHECKING:
    from core.context import VaultContext


@loggable("parse_document")
def parse_document(
    pdf_path: str,
    ctx: VaultContext,
    output_media_dir: Path | None = None,
) -> DocumentParseResult:
    """
    Parse PDF into structured Markdown preserving layout, tables, and HD figures.
    """
    import pymupdf
    import pymupdf4llm

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise NotFoundError(
            error_code="pdf_not_found",
            user_message=f"PDF file not found: {pdf_path}",
            actionable_hint="Verify that the PDF file path exists on disk.",
        )

    with pymupdf.open(str(pdf_file)) as doc:
        page_count = len(doc)

        # 1. Convert layout text to Markdown via layout parser
        try:
            md_text = pymupdf4llm.to_markdown(str(pdf_file))
        except Exception:
            pages_text = [page.get_text() for page in doc]
            md_text = "\n\n".join(filter(None, pages_text))

        # 2. Inspect image streams for HD figure extraction & deduplication
        cfg_pdf = ctx.settings.system.ingest.pdf
        min_dim = cfg_pdf.min_image_dimension
        max_repeat = cfg_pdf.max_repeated_image_count

        # First pass: count MD5 occurrences per image stream
        hash_counts: dict[str, set[int]] = {}

        for page_idx, page in enumerate(doc):
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue
                    image_bytes = base_image["image"]
                    img_hash = hashlib.md5(image_bytes).hexdigest()
                    if img_hash not in hash_counts:
                        hash_counts[img_hash] = set()
                    hash_counts[img_hash].add(page_idx)
                except Exception:
                    continue

        # Second pass: save non-repeating HD figures if output_media_dir provided
        extracted_images: list[ExtractedImageMetadata] = []
        if output_media_dir:
            output_media_dir.mkdir(parents=True, exist_ok=True)

            for page_idx, page in enumerate(doc):
                for img_idx, img_info in enumerate(page.get_images(full=True)):
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if not base_image:
                            continue
                        image_bytes = base_image["image"]
                        width = base_image.get("width", 0)
                        height = base_image.get("height", 0)
                        ext = base_image.get("ext", "png")

                        # Check dimensions
                        if width < min_dim or height < min_dim:
                            continue

                        img_hash = hashlib.md5(image_bytes).hexdigest()
                        # Skip repeating logos/headers appearing across > max_repeat pages
                        if len(hash_counts.get(img_hash, set())) > max_repeat:
                            continue

                        img_name = f"fig_{page_idx + 1}_{img_idx + 1}.{ext}"
                        img_out_path = output_media_dir / img_name
                        if not img_out_path.exists():
                            with open(img_out_path, "wb") as f:
                                f.write(image_bytes)

                        extracted_images.append(
                            ExtractedImageMetadata(
                                path=str(img_out_path),
                                page_number=page_idx + 1,
                                md5_hash=img_hash,
                                width=width,
                                height=height,
                                caption=f"Figure on page {page_idx + 1}",
                            )
                        )
                    except Exception:
                        continue

    total_chars = len(md_text.strip())
    is_scanned = (total_chars / max(1, page_count)) < cfg_pdf.scanned_char_threshold

    return DocumentParseResult(
        text=md_text,
        page_count=page_count,
        images=extracted_images,
        is_scanned=is_scanned,
    )
