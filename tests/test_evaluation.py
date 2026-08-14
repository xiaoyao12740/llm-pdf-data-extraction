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
    assert metrics["missing_truth_count"] == 0
    assert metrics["missing_abstention_accuracy"] is None
    assert metrics["present_value_recovery_accuracy"] == 1


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
    assert metrics["missing_truth_count"] == 1
    assert metrics["correct_abstentions"] == 1
    assert metrics["missing_abstention_accuracy"] == 1
    assert metrics["source_recovery"]["by_field"]["positive_rate"]["present_truth_count"] == 0


def test_abstention_denominator_only_contains_missing_truth(tmp_path):
    base = {
        "report_date": "2026-01-08",
        "period_start": "2026-01-01",
        "period_end": "2026-01-07",
        "region": "North",
        "sample_count": 100,
        "positive_count": 10,
    }
    missing = {**base, "positive_rate": None}
    present = {**base, "positive_rate": 0.1}
    path = tmp_path / "truth.json"
    path.write_text(
        json.dumps(
            {
                "records": [
                    {"file": "missing.pdf", "source_truth": missing, "canonical_truth": missing},
                    {"file": "present.pdf", "source_truth": present, "canonical_truth": present},
                ]
            }
        )
    )
    results = [
        {"file": "missing.pdf", "record": missing, "validation_issues": []},
        {"file": "present.pdf", "record": {**present, "positive_rate": None}, "validation_issues": []},
    ]
    metrics = evaluate(results, path)
    rate = metrics["source_recovery"]["by_field"]["positive_rate"]
    assert metrics["missing_truth_count"] == 1
    assert metrics["correct_abstentions"] == 1
    assert metrics["missing_abstention_accuracy"] == 1
    assert rate["present_truth_count"] == 1
    assert rate["present_value_recovery_accuracy"] == 0
