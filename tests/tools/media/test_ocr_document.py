import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.schemas import DocumentParseResult


def test_ocr_document_schema_and_execution(ctx):
    from tools.media.ocr_document import ocr_document

    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = Path(tmp_dir) / "scanned_sample.pdf"
        pdf_path.touch()
        # Mock PyMuPDF doc with blank image page
        doc_mock = MagicMock()
        doc_mock.__len__.return_value = 1
        doc_mock.__enter__.return_value = doc_mock
        page_mock = MagicMock()
        pix_mock = MagicMock()
        pix_mock.tobytes.return_value = b"fake_png_bytes"
        page_mock.get_pixmap.return_value = pix_mock
        doc_mock.__iter__.return_value = iter([page_mock])

        mock_ocr_instance = MagicMock()
        mock_ocr_instance.return_value = ([
            [[[10, 10], [100, 10], [100, 30], [10, 30]], "Scanned OCR Heading Text", 0.98],
            [[[10, 40], [200, 40], [200, 60], [10, 60]], "Sample OCR body text paragraph.", 0.95],
        ], None)

        with patch("pymupdf.open", return_value=doc_mock), \
             patch("rapidocr_onnxruntime.RapidOCR", return_value=mock_ocr_instance):
            res = ocr_document(str(pdf_path), ctx)

        assert isinstance(res, DocumentParseResult)
        assert res.is_scanned is True
        assert "Scanned OCR Heading Text" in res.text
        assert "Sample OCR body text paragraph." in res.text
