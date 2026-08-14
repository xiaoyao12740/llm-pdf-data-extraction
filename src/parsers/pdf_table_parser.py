from pathlib import Path
import pdfplumber


def extract_tables(path: Path) -> dict[int, list[list[list[str | None]]]]:
    with pdfplumber.open(path) as pdf:
        return {index: page.extract_tables() for index, page in enumerate(pdf.pages, 1)}
