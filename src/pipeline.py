import argparse, hashlib, json
from pathlib import Path
from .parsers.pdf_text_parser import parse_pdf
from .extraction.rule_extractor import extract_fields
from .validation.validators import validate_record

ROOT=Path(__file__).resolve().parents[1]


def run(raw_dir=ROOT/"data/raw", output=ROOT/"data/processed/extraction_details.json"):
    results=[]
    for path in sorted(Path(raw_dir).glob("*.pdf")):
        pages=parse_pdf(path); fields=extract_fields(pages); record={f["field_name"]:f["normalized_candidate"] for f in fields}; results.append({"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"page_count":len(pages),"fields":fields,"validation_issues":validate_record(record)})
    Path(output).parent.mkdir(parents=True,exist_ok=True); Path(output).write_text(json.dumps(results,indent=2),encoding="utf-8"); print(f"Processed {len(results)} PDF files -> {output}")
    return results


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args(); run()
