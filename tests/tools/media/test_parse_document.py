import tempfile
from pathlib import Path
import pypdf

from core.schemas import DocumentParseResult, ExtractedImageMetadata


def _create_sample_pdf(pdf_path: Path, num_pages: int = 3) -> Path:
    """Helper to create a valid sample PDF file with PyPDF."""
    writer = pypdf.PdfWriter()
    for i in range(num_pages):
        page = writer.add_blank_page(width=612, height=792)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return pdf_path


def test_document_parse_result_schema():
    img = ExtractedImageMetadata(
        path="data/media/test/fig_1.png",
        page_number=1,
        md5_hash="abcd1234efgh5678",
        width=300,
        height=300,
        caption="Section 1 Figure",
    )
    res = DocumentParseResult(
        text="# Section 1\n\nSample text content.",
        page_count=2,
        images=[img],
        is_scanned=False,
    )
    assert res.page_count == 2
    assert len(res.images) == 1
    assert res.images[0].md5_hash == "abcd1234efgh5678"


def test_parse_document_basic(ctx):
    from tools.media.parse_document import parse_document

    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = Path(tmp_dir) / "sample.pdf"
        _create_sample_pdf(pdf_path, num_pages=2)

        res = parse_document(str(pdf_path), ctx)
        assert isinstance(res, DocumentParseResult)
        assert res.page_count >= 1
