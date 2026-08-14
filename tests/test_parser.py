from src.generators.generate_sample_pdfs import generate
from src.parsers.pdf_text_parser import parse_pdf


def test_generated_pdf_parses(tmp_path):
    raw = tmp_path / "raw"
    generate(1, 42, raw, tmp_path / "truth.json")
    pages = parse_pdf(next(raw.glob("*.pdf")))
    assert pages and pages[0]["page_number"] == 1 and pages[0]["text"]
