import pymupdf
import pytest

from src.generators.generate_sample_pdfs import generate
from src.parsers.pdf_text_parser import parse_pdf


def test_generated_pdf_parses(tmp_path):
    raw = tmp_path / "raw"
    generate(1, 42, raw, tmp_path / "truth.json")
    pages = parse_pdf(next(raw.glob("*.pdf")))
    assert pages and pages[0]["page_number"] == 1 and pages[0]["text"]


def test_multi_page_pdf_preserves_page_numbers(tmp_path):
    path = tmp_path / "two-pages.pdf"
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "first page")
    document.new_page().insert_text((72, 72), "second page")
    document.save(path)
    document.close()

    pages = parse_pdf(path)
    assert [page["page_number"] for page in pages] == [1, 2]
    assert "second page" in pages[1]["text"]


def test_image_only_pdf_returns_page_without_inventing_text(tmp_path):
    path = tmp_path / "scan.pdf"
    document = pymupdf.open()
    document.new_page()
    document.save(path)
    document.close()

    pages = parse_pdf(path)
    assert len(pages) == 1 and pages[0]["text"] == ""


def test_corrupt_pdf_is_rejected(tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"this is not a pdf")
    with pytest.raises(Exception, match="PDF|pdf|format"):
        parse_pdf(path)
