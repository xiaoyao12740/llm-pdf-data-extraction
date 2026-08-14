from datetime import datetime
from pathlib import Path

from sqlalchemy import text


def health_check(engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1


def save_extraction(engine, result: dict, llm_provider=None, llm_model=None, run_metadata=None) -> int:
    """Persist one complete provenance graph atomically and return run_id."""
    path = Path(result["file_path"])
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO documents(file_name,file_path,file_hash,page_count,file_size)
            VALUES(:file_name,:file_path,:sha256,:page_count,:file_size)
            ON DUPLICATE KEY UPDATE document_id=LAST_INSERT_ID(document_id),file_name=VALUES(file_name),file_path=VALUES(file_path),page_count=VALUES(page_count),file_size=VALUES(file_size)"""),
            {**result, "file_name": path.name, "file_size": path.stat().st_size},
        )
        document_id = connection.execute(
            text("SELECT document_id FROM documents WHERE file_hash=:sha256"), result
        ).scalar_one()
        metadata = run_metadata or {}
        run = connection.execute(
            text("""INSERT INTO extraction_runs(document_id,batch_id,pipeline_version,schema_version,prompt_version,config_hash,git_commit,parser_name,llm_enabled,llm_provider,llm_model,status,started_at)
            VALUES(:document_id,:batch_id,:pipeline_version,:schema_version,:prompt_version,:config_hash,:git_commit,'pymupdf+pdfplumber',:llm_enabled,:provider,:model,'running',:started_at)"""),
            {
                "document_id": document_id,
                "llm_enabled": bool(llm_provider),
                "provider": llm_provider,
                "model": llm_model,
                "started_at": datetime.now(),
                **metadata,
            },
        )
        run_id = run.lastrowid
        for field in result["fields"]:
            connection.execute(
                text("""INSERT INTO extracted_fields(run_id,field_name,raw_value,normalized_value,page_number,source_text,extraction_method,confidence,validation_status)
                VALUES(:run_id,:field_name,:raw_value,:normalized_value,:page_number,:source_text,:extraction_method,:confidence,:validation_status)"""),
                {
                    "run_id": run_id,
                    "normalized_value": str(field.get("normalized_candidate"))
                    if field.get("normalized_candidate") is not None
                    else None,
                    "validation_status": field.get("validation_status", "valid"),
                    **field,
                },
            )
        record = {
            key: result["record"].get(key)
            for key in (
                "report_title",
                "organization",
                "report_date",
                "period_start",
                "period_end",
                "region",
                "sample_count",
                "positive_count",
                "positive_rate",
                "alert_level",
                "notes",
            )
        }
        connection.execute(
            text("""INSERT INTO monitoring_records(run_id,report_title,organization,report_date,period_start,period_end,region,sample_count,positive_count,positive_rate,alert_level,notes)
            VALUES(:run_id,:report_title,:organization,:report_date,:period_start,:period_end,:region,:sample_count,:positive_count,:positive_rate,:alert_level,:notes)"""),
            {"run_id": run_id, **record},
        )
        for issue in result["validation_issues"]:
            connection.execute(
                text("""INSERT INTO validation_issues(run_id,field_name,issue_type,severity,expected_value,actual_value,message)
                VALUES(:run_id,:field_name,:issue_type,:severity,:expected_value,:actual_value,:message)"""),
                {
                    "run_id": run_id,
                    "expected_value": issue.get("expected_value"),
                    "actual_value": issue.get("actual_value"),
                    **issue,
                },
            )
        status = "partial" if result["validation_issues"] else "success"
        connection.execute(
            text("UPDATE extraction_runs SET status=:status,finished_at=:finished WHERE run_id=:run_id"),
            {"status": status, "finished": datetime.now(), "run_id": run_id},
        )
    return run_id
