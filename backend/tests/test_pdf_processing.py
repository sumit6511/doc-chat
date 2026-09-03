import pytest

from app.errors import CorruptedFileError
from app.services.ingestion_service import extract_pages_text, open_pdf
from tests.conftest import make_minimal_pdf_bytes


class TestOpenPdf:
    def test_valid_pdf_opens(self):
        content = make_minimal_pdf_bytes(pages=2)
        doc = open_pdf(content)
        try:
            assert doc.page_count == 2
        finally:
            doc.close()

    def test_corrupted_file_raises(self):
        with pytest.raises(CorruptedFileError):
            open_pdf(b"this is not a pdf file at all")

    def test_empty_bytes_raises(self):
        with pytest.raises(CorruptedFileError):
            open_pdf(b"")


class TestExtractPagesText:
    def test_extract_text_returns_one_entry_per_page(self):
        content = make_minimal_pdf_bytes(text="Distributed Systems", pages=3)
        pages = extract_pages_text(content)
        assert len(pages) == 3

    def test_page_metadata_is_preserved_by_position(self):
        content = make_minimal_pdf_bytes(text="RPC allows remote calls", pages=2)
        pages = extract_pages_text(content)
        assert "page 1" in pages[0]
        assert "page 2" in pages[1]
        assert "RPC allows remote calls" in pages[0]

    def test_extracted_text_contains_expected_content(self):
        content = make_minimal_pdf_bytes(text="Remote Method Invocation", pages=1)
        pages = extract_pages_text(content)
        assert "Remote Method Invocation" in pages[0]
