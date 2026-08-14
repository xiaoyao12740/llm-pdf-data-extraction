import json

from src.evaluation.evaluate_extraction import evaluate


def test_source_and_canonical_metrics_are_separate(tmp_path):
    canonical = {
        "report_date": "2026-01-08",
        "period_start": "2026-01-01",
        "period_end": "2026-01-07",
        "region": "North",
        "sample_count": 100,
        "positive_count": 10,
        "positive_rate": 0.1,
    }
    source = {**canonical, "positive_rate": 0.2}
    item = {"file": "a.pdf", "source_truth": source, "canonical_truth": canonical, "anomaly_type": "rate_mismatch"}
    path = tmp_path / "truth.json"
    path.write_text(json.dumps({"records": [item]}))
    result = {"file": "a.pdf", "record": source, "validation_issues": [{"issue_type": "rate_mismatch"}]}
    metrics = evaluate([result], path)
    assert metrics["source_extraction"]["field_accuracy"] == 1
    assert metrics["canonical_consistency"]["field_accuracy"] < 1
    assert metrics["anomaly_detection"]["f1"] == 1


def test_missing_source_value_rewards_abstention(tmp_path):
    truth = {
        "report_date": "2026-01-08",
        "period_start": "2026-01-01",
        "period_end": "2026-01-07",
        "region": "North",
        "sample_count": 100,
        "positive_count": 10,
        "positive_rate": None,
    }
    path = tmp_path / "truth.json"
    path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "file": "a.pdf",
                        "source_truth": truth,
                        "canonical_truth": {**truth, "positive_rate": 0.1},
                        "anomaly_type": "missing_field",
                    }
                ]
            }
        )
    )
    metrics = evaluate([{"file": "a.pdf", "record": truth, "validation_issues": [{"issue_type": "missing"}]}], path)
    assert metrics["source_extraction"]["field_accuracy"] == 1
