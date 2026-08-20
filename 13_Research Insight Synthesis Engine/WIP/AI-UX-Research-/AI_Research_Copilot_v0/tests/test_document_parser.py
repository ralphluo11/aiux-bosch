from __future__ import annotations

import io
import json
import os
import unittest
import zipfile
from unittest.mock import MagicMock, patch

from ai_ux_core.document_parser import DocumentExtractionError, extract_document


def ooxml(parts: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class DocumentParserTests(unittest.TestCase):
    def test_extracts_docx_paragraphs_with_provenance(self) -> None:
        data = ooxml(
            {
                "word/document.xml": """
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:body><w:p><w:r><w:t>用户需要更清晰的反馈。</w:t></w:r></w:p></w:body>
                </w:document>
                """
            }
        )
        result = extract_document("notes.docx", data)
        self.assertEqual(result.file_type, "docx")
        self.assertIn("[DOCX paragraph 1] 用户需要更清晰的反馈。", result.content)

    def test_extracts_pptx_by_slide(self) -> None:
        data = ooxml(
            {
                "ppt/slides/slide1.xml": """
                <p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
                  <p:cSld><a:p><a:r><a:t>研究结论</a:t></a:r></a:p></p:cSld>
                </p:sld>
                """
            }
        )
        result = extract_document("report.pptx", data)
        self.assertIn("[PPTX slide 1] 研究结论", result.content)

    def test_extracts_xlsx_by_sheet_and_row(self) -> None:
        data = ooxml(
            {
                "xl/workbook.xml": """
                <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                  <sheets><sheet name="Feedback" sheetId="1" r:id="rId1"/></sheets>
                </workbook>
                """,
                "xl/_rels/workbook.xml.rels": """
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  <Relationship Id="rId1" Target="worksheets/sheet1.xml"/>
                </Relationships>
                """,
                "xl/worksheets/sheet1.xml": """
                <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <sheetData><row r="2"><c r="A2" t="inlineStr"><is><t>加载太慢</t></is></c></row></sheetData>
                </worksheet>
                """,
            }
        )
        result = extract_document("feedback.xlsx", data)
        self.assertIn("[XLSX sheet Feedback row 2] A2=加载太慢", result.content)

    def test_rejects_legacy_office_format(self) -> None:
        with self.assertRaisesRegex(DocumentExtractionError, "unsupported_file_type"):
            extract_document("legacy.xls", b"not-an-xls")

    def test_image_ocr_uses_live_ai_and_keeps_image_locator(self) -> None:
        response = MagicMock()
        response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "[IMAGE region: middle] Research goal"}}]
        }).encode()
        response.__enter__.return_value = response
        with patch.dict(os.environ, {"AI_UX_LLM_API_KEY": "test-key", "AI_UX_LLM_BASE_URL": "https://example.test/v1"}), patch("urllib.request.urlopen", return_value=response):
            result = extract_document("screen.png", b"fake-image")
        self.assertIn("[IMAGE file screen.png]", result.content)
        self.assertIn("Research goal", result.content)

    def test_media_transcription_keeps_timestamps_and_speaker(self) -> None:
        response = MagicMock()
        response.read.return_value = json.dumps({
            "segments": [{"start": 1.25, "end": 4.5, "speaker": "A", "text": "具体经历"}]
        }).encode()
        response.__enter__.return_value = response
        with patch.dict(os.environ, {"AI_UX_LLM_API_KEY": "test-key", "AI_UX_LLM_BASE_URL": "https://example.test/v1"}), patch("urllib.request.urlopen", return_value=response):
            result = extract_document("interview.mp3", b"fake-audio")
        self.assertIn("[MEDIA 00:01.250-00:04.500 A] 具体经历", result.content)


if __name__ == "__main__":
    unittest.main()
