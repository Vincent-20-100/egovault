"""
Token Shield MCP Server — Fast, Stateless Multimodal & Document Extraction.

Exposes local, deterministic CPU tools for heavy non-text ingestion (PDF parsing,
scanned document OCR, audio/video transcription, web extraction, YouTube subtitles)
to eliminate token waste and avoid multi-modal LLM context pollution.
"""

from __future__ import annotations

import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("token-shield")


@mcp.tool()
def parse_pdf(file_path: str) -> str:
    """
    Extract structured layout Markdown and tables from a native PDF using pymupdf4llm.

    Args:
        file_path: Absolute or relative path to the local PDF file.

    Returns:
        Clean, high-density Markdown representation of the PDF content and tables.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    try:
        import pymupdf4llm
        md_text = pymupdf4llm.to_markdown(str(path))
        if md_text and md_text.strip():
            return md_text
    except Exception:
        pass

    # Fallback to standard PyMuPDF page text extraction
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        pages = [page.get_text() for page in doc]
        return "\n\n".join(filter(None, pages))


@mcp.tool()
def ocr_document(file_path: str, dpi: int = 200) -> str:
    """
    Perform fast CPU OCR on scanned PDF pages or image files using RapidOCR.

    Args:
        file_path: Path to the scanned PDF or image file (PNG, JPG, TIFF, etc.).
        dpi: Rendering resolution for PDF rasterization (default: 200).

    Returns:
        Structured Markdown text extracted via optical character recognition.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Document or image file not found: {path}")

    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()

    if path.suffix.lower() == ".pdf":
        import pymupdf
        page_transcripts: list[str] = []
        with pymupdf.open(str(path)) as doc:
            for page_idx, page in enumerate(doc):
                pix = page.get_pixmap(dpi=dpi)
                img_bytes = pix.tobytes("png")
                ocr_result, _ = engine(img_bytes)
                if not ocr_result:
                    continue
                # Sort bounding boxes top-to-bottom, left-to-right
                sorted_boxes = sorted(ocr_result, key=lambda item: (item[0][0][1], item[0][0][0]))
                lines = [item[1].strip() for item in sorted_boxes if item[1].strip()]
                if lines:
                    page_transcripts.append(f"<!-- Page {page_idx + 1} -->\n" + "\n".join(lines))
        return "\n\n".join(page_transcripts)
    else:
        # Direct image OCR
        with open(path, "rb") as f:
            img_bytes = f.read()
        ocr_result, _ = engine(img_bytes)
        if not ocr_result:
            return ""
        sorted_boxes = sorted(ocr_result, key=lambda item: (item[0][0][1], item[0][0][0]))
        return "\n".join(item[1].strip() for item in sorted_boxes if item[1].strip())


@mcp.tool()
def transcribe_audio(
    file_path: str,
    language: str = "fr",
    model_size: str = "base",
) -> str:
    """
    Transcribe a local audio or video file (MP3, WAV, M4A, MP4, MKV, OGG) to text.

    Args:
        file_path: Path to the audio or video file.
        language: Language code hint (default: 'fr').
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', default: 'base').

    Returns:
        Full text transcript of the audio recording.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Audio/video file not found: {path}")

    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(path), language=language)
    return " ".join(seg.text.strip() for seg in segments)


@mcp.tool()
def fetch_web_text(url: str) -> str:
    """
    Extract clean, boilerplate-free article text and tables from a web URL using trafilatura.

    Args:
        url: Web URL to fetch and clean.

    Returns:
        Extracted main body Markdown text without headers, footers, or navigation noise.
    """
    import trafilatura
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Failed to fetch content from URL: {url}")
    result = trafilatura.extract(
        downloaded,
        include_tables=True,
        include_links=True,
        include_images=False,
        output_format="txt",
    )
    return result or ""


@mcp.tool()
def fetch_youtube_subtitles(url_or_video_id: str, language: str = "fr") -> str:
    """
    Retrieve subtitles directly from a YouTube video URL or ID without downloading media.

    Args:
        url_or_video_id: YouTube URL or 11-character video ID.
        language: Primary language code (default: 'fr').

    Returns:
        Full timestamped subtitle transcript text.
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    # Extract video ID
    video_id = url_or_video_id
    if "youtube.com" in url_or_video_id or "youtu.be" in url_or_video_id:
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url_or_video_id)
        if match:
            video_id = match.group(1)

    transcript_list = YouTubeTranscriptApi.get_transcript(
        video_id,
        languages=[language, "en", "auto"],
    )
    return " ".join(item["text"].strip() for item in transcript_list)


if __name__ == "__main__":
    mcp.run()
