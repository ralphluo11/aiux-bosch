from __future__ import annotations

import csv
import io
import json
import mimetypes
import os
import re
import urllib.error
import urllib.request
import zipfile
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from .config import load_llm_settings


MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 200_000
MAX_ZIP_ENTRY_BYTES = 8 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 40 * 1024 * 1024
SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".docx", ".pptx", ".xlsx", ".pdf",
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MEDIA_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}


class DocumentExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedDocument:
    file_name: str
    file_type: str
    content: str
    unit_count: int

    def as_dict(self) -> dict:
        return {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "content": self.content,
            "unit_count": self.unit_count,
        }


def extract_document(file_name: str, data: bytes) -> ExtractedDocument:
    safe_name = Path(file_name.replace("\\", "/")).name
    extension = Path(safe_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentExtractionError(f"unsupported_file_type:{extension or 'none'}")
    if not data:
        raise DocumentExtractionError("uploaded_file_is_empty")
    if len(data) > MAX_FILE_BYTES:
        raise DocumentExtractionError("uploaded_file_limit_is_25mb")

    if extension in {".txt", ".md"}:
        content = _decode_text(data)
        unit_count = len([line for line in content.splitlines() if line.strip()])
    elif extension == ".csv":
        content, unit_count = _extract_csv(data)
    elif extension == ".json":
        content, unit_count = _extract_json(data)
    elif extension == ".docx":
        content, unit_count = _extract_docx(data)
    elif extension == ".pptx":
        content, unit_count = _extract_pptx(data)
    elif extension == ".xlsx":
        content, unit_count = _extract_xlsx(data)
    elif extension == ".pdf":
        content, unit_count = _extract_pdf(data)
    elif extension in IMAGE_EXTENSIONS:
        content, unit_count = _extract_image(safe_name, extension, data)
    else:
        content, unit_count = _transcribe_media(safe_name, extension, data)

    content = content.strip()
    if not content:
        raise DocumentExtractionError("no_extractable_text_found")
    if len(content) > MAX_EXTRACTED_CHARACTERS:
        raise DocumentExtractionError("extracted_text_limit_is_200000_characters")
    return ExtractedDocument(safe_name, extension.lstrip("."), content, unit_count)


def _decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("text_file_must_be_utf8") from exc


def _extract_csv(data: bytes) -> tuple[str, int]:
    text = _decode_text(data)
    rows = []
    for row_number, row in enumerate(csv.reader(io.StringIO(text)), start=1):
        values = [value.strip() for value in row]
        if any(values):
            rows.append(f"[CSV row {row_number}] " + " | ".join(values))
    return "\n".join(rows), len(rows)


def _extract_json(data: bytes) -> tuple[str, int]:
    try:
        value = json.loads(_decode_text(data))
    except json.JSONDecodeError as exc:
        raise DocumentExtractionError("invalid_json_document") from exc
    content = json.dumps(value, ensure_ascii=False, indent=2)
    unit_count = len(value) if isinstance(value, (list, dict)) else 1
    return content, unit_count


def _extract_pdf(data: bytes) -> tuple[str, int]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentExtractionError("pdf_parser_dependency_missing:pypdf") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        blocks = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                blocks.append(f"[PDF page {page_number}] {text}")
                continue
            image_blocks = []
            for image_index, image in enumerate(page.images, start=1):
                try:
                    image_text, _ = _extract_image(
                        f"page-{page_number}-image-{image_index}.{image.name.rsplit('.', 1)[-1]}",
                        Path(image.name).suffix.lower(),
                        image.data,
                    )
                except DocumentExtractionError as exc:
                    if str(exc) == "live_ai_key_required_for_image_audio_video":
                        raise DocumentExtractionError("scanned_pdf_requires_live_ai_ocr") from exc
                    raise
                image_blocks.append(image_text)
            if image_blocks:
                blocks.append(f"[PDF page {page_number} OCR]\n" + "\n".join(image_blocks))
    except Exception as exc:
        raise DocumentExtractionError("invalid_or_encrypted_pdf") from exc
    if not blocks:
        raise DocumentExtractionError("pdf_has_no_text_layer:image_ocr_required")
    return "\n\n".join(blocks), len(reader.pages)


def _ai_settings() -> tuple[str, str]:
    # timeout_seconds is unused here: media requests use the fixed 180s
    # timeout in _read_json_response, not the text-analysis default.
    settings = load_llm_settings(default_timeout_seconds=180.0)
    if not settings.api_key:
        raise DocumentExtractionError("live_ai_key_required_for_image_audio_video")
    return settings.api_key, settings.base_url.rstrip("/")


def _extract_image(file_name: str, extension: str, data: bytes) -> tuple[str, int]:
    api_key, base_url = _ai_settings()
    mime_type = mimetypes.guess_type(file_name)[0] or "image/png"
    model = os.environ.get("AI_UX_VISION_MODEL") or os.environ.get("AI_UX_LLM_MODEL", "gpt-4.1-mini")
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract all visible text from this research image. Preserve reading order. Prefix sections with [IMAGE region: top|middle|bottom]. Describe charts only when labels and values are visible. Do not infer missing text or facts."},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64encode(data).decode('ascii')}"}},
            ],
        }],
        "temperature": 0,
    }
    result = _json_request(f"{base_url}/chat/completions", api_key, payload)
    try:
        content = result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, AttributeError) as exc:
        raise DocumentExtractionError("image_ocr_response_invalid") from exc
    return f"[IMAGE file {file_name}]\n{content}", 1


def _transcribe_media(file_name: str, extension: str, data: bytes) -> tuple[str, int]:
    api_key, base_url = _ai_settings()
    base_url = os.environ.get("AI_UX_AUDIO_BASE_URL", base_url).rstrip("/")
    model = os.environ.get("AI_UX_TRANSCRIBE_MODEL", "gpt-4o-transcribe-diarize")
    fields = {"model": model, "response_format": "diarized_json", "chunking_strategy": "auto"}
    result = _multipart_json_request(f"{base_url}/audio/transcriptions", api_key, fields, file_name, data)
    segments = result.get("segments") if isinstance(result, dict) else None
    if not isinstance(segments, list) or not segments:
        raise DocumentExtractionError("transcription_requires_timestamped_segments")
    blocks = []
    for index, segment in enumerate(segments, start=1):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = _format_time(segment.get("start"))
        end = _format_time(segment.get("end"))
        speaker = str(segment.get("speaker", "Speaker")).strip() or "Speaker"
        blocks.append(f"[MEDIA {start}-{end} {speaker}] {text}")
    if not blocks:
        raise DocumentExtractionError("transcription_returned_no_text")
    return "\n".join(blocks), len(blocks)


def _format_time(value: object) -> str:
    try:
        seconds = max(0.0, float(value))
    except (TypeError, ValueError):
        return "??:??.???"
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes):02d}:{seconds:06.3f}"


def _json_request(url: str, api_key: str, payload: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    return _read_json_response(request, "multimodal_request_failed")


def _multipart_json_request(url: str, api_key: str, fields: dict[str, str], file_name: str, data: bytes) -> dict:
    boundary = f"----uxgs{os.urandom(12).hex()}"
    chunks = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    chunks.extend([f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{file_name}\"\r\nContent-Type: {mime_type}\r\n\r\n".encode(), data, b"\r\n", f"--{boundary}--\r\n".encode()])
    request = urllib.request.Request(url, data=b"".join(chunks), headers={"Authorization": f"Bearer {api_key}", "Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    return _read_json_response(request, "transcription_request_failed")


def _read_json_response(request: urllib.request.Request, error_code: str) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise DocumentExtractionError(error_code) from exc
    if not isinstance(result, dict):
        raise DocumentExtractionError(error_code)
    return result


def _open_ooxml(data: bytes) -> zipfile.ZipFile:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise DocumentExtractionError("invalid_ooxml_file") from exc
    infos = archive.infolist()
    if sum(info.file_size for info in infos) > MAX_ZIP_TOTAL_BYTES:
        archive.close()
        raise DocumentExtractionError("ooxml_uncompressed_content_is_too_large")
    for info in infos:
        if info.file_size > MAX_ZIP_ENTRY_BYTES:
            archive.close()
            raise DocumentExtractionError("ooxml_entry_is_too_large")
    return archive


def _read_xml(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(archive.read(name))
    except KeyError as exc:
        raise DocumentExtractionError(f"missing_ooxml_part:{name}") from exc
    except ElementTree.ParseError as exc:
        raise DocumentExtractionError(f"invalid_ooxml_xml:{name}") from exc


def _extract_docx(data: bytes) -> tuple[str, int]:
    with _open_ooxml(data) as archive:
        root = _read_xml(archive, "word/document.xml")
    paragraphs = []
    for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        text = "".join(
            node.text or ""
            for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        ).strip()
        if text:
            paragraphs.append(f"[DOCX paragraph {len(paragraphs) + 1}] {text}")
    return "\n".join(paragraphs), len(paragraphs)


def _extract_pptx(data: bytes) -> tuple[str, int]:
    with _open_ooxml(data) as archive:
        slide_names = sorted(
            (
                name
                for name in archive.namelist()
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ),
            key=lambda name: int(re.search(r"slide(\d+)\.xml", name).group(1)),
        )
        blocks = []
        for slide_index, name in enumerate(slide_names, start=1):
            root = _read_xml(archive, name)
            texts = [
                (node.text or "").strip()
                for node in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t")
                if (node.text or "").strip()
            ]
            if texts:
                blocks.append(f"[PPTX slide {slide_index}] " + " | ".join(texts))
    return "\n".join(blocks), len(blocks)


def _extract_xlsx(data: bytes) -> tuple[str, int]:
    with _open_ooxml(data) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        workbook = _read_xml(archive, "xl/workbook.xml")
        relationships = _xlsx_relationships(archive)
        blocks = []
        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        relation_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        for sheet in workbook.iter(f"{namespace}sheet"):
            sheet_name = sheet.attrib.get("name", "Sheet")
            target = relationships.get(sheet.attrib.get(relation_key, ""))
            if not target:
                continue
            part_name = target.lstrip("/")
            if not part_name.startswith("xl/"):
                part_name = f"xl/{part_name}"
            root = _read_xml(archive, part_name)
            for row in root.iter(f"{namespace}row"):
                values = []
                for cell in row.findall(f"{namespace}c"):
                    value = _xlsx_cell_value(cell, namespace, shared_strings)
                    if value != "":
                        values.append(f"{cell.attrib.get('r', '?')}={value}")
                if values:
                    row_number = row.attrib.get("r", "?")
                    blocks.append(
                        f"[XLSX sheet {sheet_name} row {row_number}] " + " | ".join(values)
                    )
    return "\n".join(blocks), len(blocks)


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = _read_xml(archive, "xl/sharedStrings.xml")
    strings = []
    for item in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
        strings.append(
            "".join(
                node.text or ""
                for node in item.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
            )
        )
    return strings


def _xlsx_relationships(archive: zipfile.ZipFile) -> dict[str, str]:
    root = _read_xml(archive, "xl/_rels/workbook.xml.rels")
    namespace = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
    return {
        item.attrib.get("Id", ""): item.attrib.get("Target", "")
        for item in root.iter(namespace)
    }


def _xlsx_cell_value(cell: ElementTree.Element, namespace: str, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter(f"{namespace}t")
        ).strip()
    value_node = cell.find(f"{namespace}v")
    if value_node is None or value_node.text is None:
        return ""
    value = value_node.text
    if cell_type == "s":
        try:
            return shared[int(value)]
        except (ValueError, IndexError):
            return ""
    if cell_type == "b":
        return "TRUE" if value == "1" else "FALSE"
    return value.strip()
