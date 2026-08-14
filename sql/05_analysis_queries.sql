USE pdf_extraction;
SELECT region,COUNT(*) AS record_count FROM monitoring_records GROUP BY region ORDER BY record_count DESC;
SELECT region,SUM(sample_count) AS samples,SUM(positive_count) AS positives,SUM(positive_count)/NULLIF(SUM(sample_count),0) AS weighted_rate FROM monitoring_records GROUP BY region;
