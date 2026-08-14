from pathlib import Path

import pymupdf

from .pdf_table_parser import extract_tables


def parse_pdf(path: str | Path) -> list[dict]:
    pdf_path = Path(path)
    tables = extract_tables(pdf_path)
    with pymupdf.open(pdf_path) as document:
        return [
            {"page_number": number, "text": page.get_text("text"), "tables": tables.get(number, [])}
            for number, page in enumerate(document, 1)
        ]
