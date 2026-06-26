import pytest
from api.tools import DocumentLoader


class TestDocumentLoader:
    def test_is_supported_pdf(self):
        assert DocumentLoader.is_supported("report.pdf") is True

    def test_is_supported_docx(self):
        assert DocumentLoader.is_supported("report.docx") is True

    def test_is_supported_txt(self):
        assert DocumentLoader.is_supported("report.txt") is True

    def test_is_supported_unsupported(self):
        assert DocumentLoader.is_supported("report.png") is False

    def test_init(self):
        loader = DocumentLoader(chunk_size=500, chunk_overlap=50)
        assert loader.text_splitter._chunk_size == 500
