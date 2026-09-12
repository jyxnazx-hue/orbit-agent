import os
import base64
from typing import Dict, Any, Union
from pypdf import PdfReader

SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_DOC_EXTS = {".pdf", ".txt", ".md", ".csv", ".json"}
SUPPORTED_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg"}

def parse_any_input(file_path: str) -> Dict[str, Any]:
    """
    Universal ingestion engine:
    Inspects file extension and extracts content or prepares multimodal payloads
    for the Bedrock Nova foundation model.
    """
    if not os.path.exists(file_path):
        return {"type": "error", "content": f"File not found: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()

    # 1. Image / Photo Ingestion (Handwritten notes, flyers, whiteboards, screenshots)
    if ext in SUPPORTED_IMAGE_EXTS:
        with open(file_path, "rb") as img_file:
            img_bytes = img_file.read()
            # Determine format
            fmt = "jpeg" if ext in [".jpg", ".jpeg"] else ext.replace(".", "")
            return {
                "type": "image",
                "format": fmt,
                "bytes": img_bytes,
                "summary": f"Image artifact: {os.path.basename(file_path)}"
            }

    # 2. PDF Document Ingestion
    elif ext == ".pdf":
        reader = PdfReader(file_path)
        extracted_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted_text.append(f"--- Page {i+1} ---\n{text}")
        full_text = "\n".join(extracted_text)
        return {
            "type": "document",
            "format": "pdf",
            "content": full_text if full_text.strip() else "PDF contains no selectable text (scanned image).",
            "summary": f"Parsed PDF ({len(reader.pages)} pages)"
        }

    # 3. Plain Text, Markdown, CSV, JSON
    elif ext in SUPPORTED_DOC_EXTS:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            return {
                "type": "document",
                "format": ext.replace(".", ""),
                "content": content,
                "summary": f"Parsed text/data document: {os.path.basename(file_path)}"
            }

    # 4. Audio Ingestion (Fallback/transcription hook)
    elif ext in SUPPORTED_AUDIO_EXTS:
        # Browser frontend transcribes via Web Speech API or passes audio payload
        return {
            "type": "audio",
            "format": ext.replace(".", ""),
            "path": file_path,
            "summary": f"Audio file staged: {os.path.basename(file_path)}"
        }

    else:
        # Fallback binary / raw
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return {"type": "raw", "content": f.read()[:4000]}