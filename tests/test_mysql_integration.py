import hashlib
import os
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.database.mysql_client import build_engine
from src.database.repository import health_check, save_extraction

pytestmark = pytest.mark.skipif(os.getenv("RUN_MYSQL_TESTS") != "1", reason="MySQL integration environment not enabled")


def _result(path: Path, digest: str, duplicate_field=False):
    field = {
        "field_name": "sample_count",
        "raw_value": "100",
        "normalized_candidate": 100,
        "page_number": 1,
        "source_text": "Tests: 100",
        "extraction_method": "rule",
        "confidence": 0.98,
        "validation_status": "valid",
    }
    return {
        "file": path.name,
        "file_path": str(path),
        "sha256": digest,
        "page_count": 1,
        "fields": [field, dict(field)] if duplicate_field else [field],
        "record": {
            "report_title": None,
            "organization": None,
            "report_date": "2026-01-08",
            "period_start": "2026-01-01",
            "period_end": "2026-01-07",
            "region": "North",
            "sample_count": 100,
            "positive_count": 5,
            "positive_rate": 0.05,
            "alert_level": None,
            "notes": None,
        },
        "validation_issues": [],
    }


def test_mysql_transaction_and_duplicate_document_identity(tmp_path):
    engine = build_engine()
    assert health_check(engine)
    with engine.begin() as connection:
        for table in ("validation_issues", "monitoring_records", "extracted_fields", "extraction_runs", "documents"):
            connection.execute(text(f"DELETE FROM {table}"))
    first = tmp_path / "a.pdf"
    first.write_bytes(b"same-pdf")
    digest = hashlib.sha256(first.read_bytes()).hexdigest()
    metadata = {
        "batch_id": "00000000-0000-0000-0000-000000000001",
        "pipeline_version": "test",
        "schema_version": "2",
        "prompt_version": None,
        "config_hash": "0" * 64,
        "git_commit": None,
    }
    save_extraction(engine, _result(first, digest), run_metadata=metadata)
    second = tmp_path / "b.pdf"
    second.write_bytes(first.read_bytes())
    save_extraction(engine, _result(second, digest), run_metadata=metadata)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM documents")).scalar_one() == 1
        assert connection.execute(text("SELECT file_name FROM documents")).scalar_one() == "b.pdf"
        before = connection.execute(text("SELECT COUNT(*) FROM extraction_runs")).scalar_one()
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"broken")
    broken_digest = hashlib.sha256(broken.read_bytes()).hexdigest()
    with pytest.raises(IntegrityError):
        save_extraction(engine, _result(broken, broken_digest, True), run_metadata=metadata)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM extraction_runs")).scalar_one() == before
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM documents WHERE file_hash=:digest"), {"digest": broken_digest}
            ).scalar_one()
            == 0
        )
