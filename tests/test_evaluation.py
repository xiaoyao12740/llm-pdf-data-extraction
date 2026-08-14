import json
from src.evaluation.evaluate_extraction import evaluate


def test_metrics_are_computed_from_ground_truth(tmp_path):
    gold={"records":[{"file":"a.pdf","ground_truth":{"report_date":"2026-01-08","period_start":"2026-01-01","period_end":"2026-01-07","region":"North","sample_count":100,"positive_count":10,"positive_rate":.1}}]}
    path=tmp_path/"truth.json"; path.write_text(json.dumps(gold))
    metrics=evaluate([{"file":"a.pdf","record":gold["records"][0]["ground_truth"],"validation_issues":[]}],path)
    assert metrics["field_accuracy"]==1 and metrics["exact_match_documents"]==1
