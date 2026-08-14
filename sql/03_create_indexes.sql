USE pdf_extraction;
CREATE INDEX idx_runs_status ON extraction_runs(status);
CREATE INDEX idx_fields_name_status ON extracted_fields(field_name,validation_status);
CREATE INDEX idx_records_date_region ON monitoring_records(report_date,region);
CREATE INDEX idx_issues_severity ON validation_issues(severity);
