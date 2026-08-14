import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from .config import config_value, load_config
from .database.mysql_client import build_engine
from .database.repository import save_extraction
from .evaluation.evaluate_extraction import evaluate, save_metrics
from .extraction.rule_extractor import extract_fields
from .llm.ollama_client import OllamaClient
from .normalization.normalizer import fields_to_record, normalize_value
from .parsers.pdf_text_parser import parse_pdf
from .validation.schema import MonitoringRecord
from .validation.validators import validate_record

ROOT = Path(__file__).resolve().parents[1]
TARGET_FIELDS = (
    "report_date",
    "period_start",
    "period_end",
    "region",
    "sample_count",
    "positive_count",
    "positive_rate",
)


def _llm_candidates(pages, fields, provider, threshold=0.60, stats=None):
    current = {item["field_name"]: item for item in fields}
    rejected = []
    stats = stats if stats is not None else Counter()
    for field in TARGET_FIELDS:
        if field in current and current[field]["confidence"] >= threshold:
            continue
        stats["calls"] += 1
        try:
            result = provider.extract_field(field, pages)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            stats["rejected"] += 1
            rejected.append(
                {
                    "field_name": field,
                    "issue_type": "llm_response_rejected",
                    "severity": "warning",
                    "message": str(error),
                }
            )
            continue
        if result.value is None:
            stats["abstained"] += 1
            continue
        try:
            normalized = normalize_value(field, result.value)
        except (TypeError, ValueError) as error:
            rejected.append(
                {
                    "field_name": field,
                    "issue_type": "llm_response_rejected",
                    "severity": "warning",
                    "message": f"LLM value normalization failed: {error}",
                }
            )
            stats["rejected"] += 1
            continue
        candidate = {
            "field_name": field,
            "raw_value": str(result.value),
            "normalized_candidate": normalized,
            "page_number": result.page_number,
            "source_text": result.evidence,
            "extraction_method": "llm",
            "confidence": max(0, min(1, result.confidence)),
            "reason": result.reason,
        }
        # A deterministic candidate is never replaced solely by model-reported confidence.
        if field not in current:
            current[field] = candidate
            stats["accepted"] += 1
    return list(current.values()), rejected


def process_pdf(
    path,
    provider=None,
    confidence_threshold=0.60,
    run_issues=None,
    llm_stats=None,
    rate_tolerance=0.005,
):
    pages = parse_pdf(path)
    fields = extract_fields(pages)
    llm_issues = []
    if provider:
        fields, llm_issues = _llm_candidates(pages, fields, provider, confidence_threshold, llm_stats)
    record = fields_to_record(fields)
    schema_issues = []
    try:
        record = MonitoringRecord(**record).model_dump(mode="json", exclude_none=False)
    except ValidationError as error:
        schema_issues = [
            {
                "field_name": str(item["loc"][0]) if item["loc"] else "schema",
                "issue_type": "schema",
                "severity": "error",
                "message": item["msg"],
            }
            for item in error.errors()
        ]
    issues = validate_record(record, tolerance=rate_tolerance) + schema_issues + llm_issues + list(run_issues or [])
    invalid_fields = {issue["field_name"] for issue in issues}
    for field in fields:
        field["validation_status"] = "invalid" if field["field_name"] in invalid_fields else "valid"
    return {
        "file": path.name,
        "file_path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "page_count": len(pages),
        "fields": fields,
        "record": record,
        "validation_issues": issues,
    }


def export_results(results, processed_dir):
    processed = Path(processed_dir)
    processed.mkdir(parents=True, exist_ok=True)
    (processed / "extraction_details.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    records = [{"file": r["file"], **r["record"]} for r in results]
    (processed / "structured_records.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    if records:
        with (processed / "structured_records.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=records[0])
            writer.writeheader()
            writer.writerows(records)


def _git_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = completed.stdout.strip()
    return commit if len(commit) == 40 else None


def run(
    raw_dir=None,
    processed_dir=None,
    llm=None,
    model=None,
    database=None,
    confidence_threshold=None,
    evaluate_results=False,
    ground_truth=None,
    llm_failure_policy=None,
    config_path=None,
):
    config = load_config(config_path)
    raw_dir = Path(raw_dir or ROOT / config_value(config, "paths", "raw", "data/raw"))
    processed_dir = Path(processed_dir or ROOT / config_value(config, "paths", "processed", "data/processed"))
    llm = llm or ("ollama" if config_value(config, "llm", "enabled", False) else "disabled")
    model = model or config_value(config, "llm", "model", "qwen2.5:7b")
    database = database or ("mysql" if config_value(config, "database", "enabled", False) else "disabled")
    confidence_threshold = (
        confidence_threshold
        if confidence_threshold is not None
        else float(config_value(config, "llm", "confidence_threshold", 0.60))
    )
    llm_failure_policy = llm_failure_policy or config_value(config, "llm", "failure_policy", "fallback_rules")
    rate_tolerance = float(config_value(config, "validation", "rate_tolerance", 0.005))
    base_url = config_value(config, "llm", "base_url", "http://localhost:11434")
    timeout = float(config_value(config, "llm", "timeout", 120))
    provider = None
    run_issues = []
    llm_stats = Counter()
    started = perf_counter()
    batch_id = str(uuid4())
    config_payload = json.dumps(
        {
            "llm": llm,
            "model": model,
            "confidence_threshold": confidence_threshold,
            "llm_failure_policy": llm_failure_policy,
            "rate_tolerance": rate_tolerance,
            "base_url": base_url,
            "timeout": timeout,
        },
        sort_keys=True,
    )
    if llm == "ollama":
        provider = OllamaClient(model=model, base_url=base_url, timeout=timeout)
        if not provider.health_check():
            if llm_failure_policy == "fail_fast":
                raise RuntimeError("Ollama API is unavailable")
            provider = None
            run_issues = [
                {
                    "field_name": "llm",
                    "issue_type": "llm_unavailable",
                    "severity": "warning",
                    "message": "Ollama API unavailable; rules-only fallback used",
                }
            ]
    run_metadata = {
        "batch_id": batch_id,
        "pipeline_version": "2.0.0",
        "schema_version": "2",
        "prompt_version": "2" if provider else None,
        "config_hash": hashlib.sha256(config_payload.encode()).hexdigest(),
        "git_commit": _git_commit(),
    }
    results = [
        process_pdf(path, provider, confidence_threshold, run_issues, llm_stats, rate_tolerance)
        for path in sorted(Path(raw_dir).glob("*.pdf"))
    ]
    export_results(results, processed_dir)
    metrics = None
    if evaluate_results:
        truth_path = Path(
            ground_truth
            or ROOT / config_value(config, "paths", "ground_truth", "data/ground_truth/ground_truth.json")
        )
        metrics = evaluate(results, truth_path)
        metrics.update(
            {
                "method": "rules+ollama" if provider else "rules_only",
                "llm_model": model if provider else None,
                "llm_telemetry": dict(llm_stats)
                if provider
                else {"calls": 0, "accepted": 0, "abstained": 0, "rejected": 0},
            }
        )
        metrics_path = ROOT / "reports/metrics" / ("rules_llm_metrics.json" if provider else "rules_only_metrics.json")
        save_metrics(metrics, metrics_path)
    summary = {
        "documents": len(results),
        "successful_parses": sum(r["page_count"] > 0 for r in results),
        "extraction_methods": dict(Counter(f["extraction_method"] for r in results for f in r["fields"])),
        "validation_issue_types": dict(Counter(i["issue_type"] for r in results for i in r["validation_issues"])),
        "valid_documents": sum(not r["validation_issues"] for r in results),
    }
    save_metrics(summary, ROOT / "reports/metrics/validation_summary.json")
    if database == "mysql":
        engine = build_engine()
        for result in results:
            save_extraction(engine, result, "ollama" if provider else None, model if provider else None, run_metadata)
    output = {
        "processed": len(results),
        "method": "rules+ollama" if provider else "rules_only",
        "validation_issues": sum(len(r["validation_issues"]) for r in results),
        "database": database,
        "evaluated": bool(metrics),
        "elapsed_seconds": round(perf_counter() - started, 2),
        "llm_telemetry": dict(llm_stats),
    }
    if metrics:
        output.update(
            {
                "source_field_accuracy": metrics["source_extraction"]["field_accuracy"],
                "canonical_field_match": metrics["canonical_consistency"]["field_accuracy"],
                "anomaly_f1": metrics["anomaly_detection"]["f1"],
            }
        )
    print(json.dumps(output, indent=2))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--llm", choices=("disabled", "ollama"))
    parser.add_argument("--model")
    parser.add_argument("--database", choices=("disabled", "mysql"))
    parser.add_argument("--confidence-threshold", type=float)
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--ground-truth", type=Path)
    parser.add_argument("--llm-failure-policy", choices=("fallback_rules", "fail_fast"))
    args = parser.parse_args()
    run(
        llm=args.llm,
        model=args.model,
        database=args.database,
        confidence_threshold=args.confidence_threshold,
        evaluate_results=args.evaluate,
        ground_truth=args.ground_truth,
        llm_failure_policy=args.llm_failure_policy,
        config_path=args.config,
    )
