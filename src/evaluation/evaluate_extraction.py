import argparse
import json
from pathlib import Path

FIELDS = ("report_date", "period_start", "period_end", "region", "sample_count", "positive_count", "positive_rate")
ANOMALY_TO_ISSUE = {"date_range": "date_range", "missing_field": "missing", "rate_mismatch": "rate_mismatch"}


def _equal(field, predicted, expected):
    if expected is None:
        return predicted is None
    if predicted is None:
        return False
    if field == "positive_rate":
        return abs(float(predicted) - float(expected)) <= 0.0001
    return predicted == expected


def _truth(record, key):
    if key in record:
        return record[key]
    if key == "canonical_truth" and "ground_truth" in record:
        return record["ground_truth"]
    raise KeyError(f"Ground truth record lacks {key}")


def _score(results, expected, truth_key):
    total = correct = missing = exact = 0
    by_field = {field: {"correct": 0, "total": 0, "missing": 0} for field in FIELDS}
    for result in results:
        gold = _truth(expected[result["file"]], truth_key)
        predicted = result["record"]
        document_exact = True
        for field in FIELDS:
            value = predicted.get(field)
            total += 1
            by_field[field]["total"] += 1
            if value is None:
                missing += 1
                by_field[field]["missing"] += 1
            matched = _equal(field, value, gold[field])
            correct += int(matched)
            by_field[field]["correct"] += int(matched)
            document_exact &= matched
        exact += int(document_exact)
    for stats in by_field.values():
        stats["accuracy"] = round(stats["correct"] / stats["total"], 4)
        stats["missing_rate"] = round(stats["missing"] / stats["total"], 4)
    return {
        "field_accuracy": round(correct / total, 4),
        "exact_match_documents": exact,
        "missing_field_rate": round(missing / total, 4),
        "by_field": by_field,
    }


def _recovery_score(results, expected, truth_key):
    totals = {
        "missing_truth_count": 0,
        "correct_abstentions": 0,
        "present_truth_count": 0,
        "correct_present_values": 0,
    }
    by_field = {
        field: {key: 0 for key in totals}
        for field in FIELDS
    }
    for result in results:
        gold = _truth(expected[result["file"]], truth_key)
        predicted = result["record"]
        for field in FIELDS:
            expected_value = gold[field]
            value = predicted.get(field)
            target = by_field[field]
            if expected_value is None:
                totals["missing_truth_count"] += 1
                target["missing_truth_count"] += 1
                if value is None:
                    totals["correct_abstentions"] += 1
                    target["correct_abstentions"] += 1
            else:
                totals["present_truth_count"] += 1
                target["present_truth_count"] += 1
                if _equal(field, value, expected_value):
                    totals["correct_present_values"] += 1
                    target["correct_present_values"] += 1

    def rates(stats):
        missing = stats["missing_truth_count"]
        present = stats["present_truth_count"]
        return {
            **stats,
            "missing_abstention_accuracy": round(stats["correct_abstentions"] / missing, 4) if missing else None,
            "present_value_recovery_accuracy": round(stats["correct_present_values"] / present, 4)
            if present
            else None,
        }

    return {**rates(totals), "by_field": {field: rates(stats) for field, stats in by_field.items()}}


def evaluate(results, truth_path):
    truth = json.loads(Path(truth_path).read_text(encoding="utf-8"))
    expected = {item["file"]: item for item in truth["records"]}
    matched_results = [result for result in results if result["file"] in expected]
    if not matched_results:
        raise ValueError("No extraction result has matching ground truth")
    source = _score(matched_results, expected, "source_truth")
    canonical = _score(matched_results, expected, "canonical_truth")
    source_recovery = _recovery_score(matched_results, expected, "source_truth")
    tp = fp = fn = 0
    for result in matched_results:
        expected_issue = ANOMALY_TO_ISSUE.get(expected[result["file"]].get("anomaly_type"))
        predicted = {
            issue["issue_type"]
            for issue in result["validation_issues"]
            if issue["issue_type"] in ANOMALY_TO_ISSUE.values()
        }
        if expected_issue:
            tp += int(expected_issue in predicted)
            fn += int(expected_issue not in predicted)
            fp += len(predicted - {expected_issue})
        else:
            fp += len(predicted)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "documents": len(matched_results),
        "fields_evaluated": len(matched_results) * len(FIELDS),
        "source_extraction": source,
        "canonical_consistency": canonical,
        "missing_truth_count": source_recovery["missing_truth_count"],
        "correct_abstentions": source_recovery["correct_abstentions"],
        "missing_abstention_accuracy": source_recovery["missing_abstention_accuracy"],
        "present_truth_count": source_recovery["present_truth_count"],
        "correct_present_values": source_recovery["correct_present_values"],
        "present_value_recovery_accuracy": source_recovery["present_value_recovery_accuracy"],
        "source_recovery": source_recovery,
        "anomaly_detection": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
        },
        "validation_issue_count": sum(len(result["validation_issues"]) for result in matched_results),
    }


def save_metrics(metrics, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("data/processed/extraction_details.json"))
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/metrics/evaluation_metrics.json"))
    args = parser.parse_args()
    metrics = evaluate(json.loads(args.results.read_text(encoding="utf-8")), args.ground_truth)
    save_metrics(metrics, args.output)
    print(json.dumps(metrics, indent=2))
