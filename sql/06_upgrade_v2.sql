USE pdf_extraction;

ALTER TABLE extraction_runs
  ADD COLUMN batch_id CHAR(36) NULL AFTER document_id,
  ADD COLUMN pipeline_version VARCHAR(50) NULL AFTER batch_id,
  ADD COLUMN schema_version VARCHAR(50) NULL AFTER pipeline_version,
  ADD COLUMN prompt_version VARCHAR(50) NULL AFTER schema_version,
  ADD COLUMN config_hash CHAR(64) NULL AFTER prompt_version,
  ADD COLUMN git_commit CHAR(40) NULL AFTER config_hash;

-- Preserve legacy rows while making the v2 provenance contract explicit.
UPDATE extraction_runs
SET batch_id = COALESCE(batch_id, UUID()),
    pipeline_version = COALESCE(pipeline_version, '1.0.0-legacy'),
    schema_version = COALESCE(schema_version, '1'),
    config_hash = COALESCE(config_hash, REPEAT('0', 64));

ALTER TABLE extraction_runs
  MODIFY COLUMN batch_id CHAR(36) NOT NULL,
  MODIFY COLUMN pipeline_version VARCHAR(50) NOT NULL,
  MODIFY COLUMN schema_version VARCHAR(50) NOT NULL,
  MODIFY COLUMN config_hash CHAR(64) NOT NULL;

ALTER TABLE extracted_fields
  ADD CONSTRAINT uk_fields_run_name UNIQUE (run_id, field_name);

ALTER TABLE monitoring_records
  ADD CONSTRAINT uk_records_run UNIQUE (run_id);
