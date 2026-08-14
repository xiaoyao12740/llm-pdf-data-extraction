USE pdf_extraction;
SELECT COUNT(*) AS document_count FROM documents;
SELECT status,COUNT(*) AS runs,ROUND(100*COUNT(*)/SUM(COUNT(*)) OVER(),2) AS percentage FROM extraction_runs GROUP BY status;
SELECT issue_type,severity,COUNT(*) AS issue_count FROM validation_issues GROUP BY issue_type,severity ORDER BY issue_count DESC;
SELECT extraction_method,COUNT(*) AS field_count,AVG(confidence) AS average_confidence FROM extracted_fields GROUP BY extraction_method;
SELECT field_name,AVG(confidence) AS average_confidence FROM extracted_fields GROUP BY field_name;
