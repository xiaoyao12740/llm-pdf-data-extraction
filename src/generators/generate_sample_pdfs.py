import argparse
import json
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ("key_value", "aliases", "multiline", "table", "narrative")


def _story(record, template, shown_rate, anomaly=None):
    styles = getSampleStyleSheet()
    normal = styles["BodyText"]
    title = [Paragraph(record["report_title"], styles["Title"]), Spacer(1, 18)]
    shown_start, shown_end = record["period_start"], record["period_end"]
    if anomaly == "date_range":
        shown_start, shown_end = shown_end, shown_start
    period = f"{shown_start} to {shown_end}"
    if template == "key_value":
        lines = [
            f"Report Date: {record['report_date']}",
            f"Period Start: {shown_start}",
            f"Period End: {shown_end}",
            f"Region: {record['region']}",
            f"Samples Tested: {record['sample_count']:,}",
            f"Positive Cases: {record['positive_count']:,}",
            f"Positive Rate: {shown_rate:.2%}",
        ]
    elif template == "aliases":
        lines = [
            f"Generated On: {record['report_date']}",
            f"From: {shown_start}",
            f"To: {shown_end}",
            f"Area: {record['region']}",
            f"Total Tests: {record['sample_count']:,}",
            f"Detected Positive: {record['positive_count']:,}",
            f"Detection Rate: {shown_rate:.2%}",
        ]
    elif template == "multiline":
        lines = [
            f"Report Date\n{record['report_date']}",
            f"Period Start\n{shown_start}",
            f"Period End\n{shown_end}",
            f"Region\n{record['region']}",
            f"Number Tested\n{record['sample_count']:,}",
            f"Positives\n{record['positive_count']:,}",
            f"Rate\n{shown_rate:.2%}",
        ]
    elif template == "narrative":
        lines = [
            f"Report Date: {record['report_date']}",
            f"Period Start: {shown_start}",
            f"Period End: {shown_end}",
            f"Region: {record['region']}",
            f"The reporting cohort comprised {record['sample_count']:,} specimens during {period}. "
            f"Laboratory confirmation identified {record['positive_count']:,} positive specimens.",
            f"The corresponding positivity was {shown_rate:.2%}.",
        ]
    else:
        data = [
            ["Report Date", "From", "To", "Region", "Tests", "Positive", "Rate"],
            [
                record["report_date"],
                shown_start,
                shown_end,
                record["region"],
                f"{record['sample_count']:,}",
                f"{record['positive_count']:,}",
                f"{shown_rate:.2%}",
            ],
        ]
        if anomaly == "missing_field":
            data = [row[:-1] for row in data]
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183153")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return title + [table]
    if anomaly == "missing_field":
        lines = [line for line in lines if "Rate" not in line and "positivity" not in line]
    return title + [Paragraph(line.replace("\n", "<br/>"), normal) for line in lines]


def generate(count=100, seed=42, raw_dir=None, truth_path=None):
    rng = random.Random(seed)
    raw = Path(raw_dir or ROOT / "data/raw")
    truth = Path(truth_path or ROOT / "data/ground_truth/ground_truth.json")
    raw.mkdir(parents=True, exist_ok=True)
    truth.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(count):
        template = TEMPLATES[i % len(TEMPLATES)]
        end = date(2026, 1, 7) + timedelta(days=i)
        start = end - timedelta(days=6)
        samples = rng.randint(500, 2500)
        positive = rng.randint(0, samples // 5)
        rate = positive / samples
        anomaly = (
            "date_range"
            if i % 29 == 0
            else "missing_field"
            if i % 23 == 0
            else "rate_mismatch"
            if i % 17 == 0
            else None
        )
        shown_rate = min(1, rate + 0.02) if anomaly == "rate_mismatch" else rate
        rec = {
            "report_id": f"RPT_{i + 1:04d}",
            "report_title": "Weekly Monitoring Report",
            "organization": "Demo Monitoring Center",
            "report_date": (end + timedelta(days=1)).isoformat(),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "region": ["North", "South", "East", "West"][i % 4],
            "sample_count": samples,
            "positive_count": positive,
            "positive_rate": round(rate, 6),
            "alert_level": "normal" if rate < 0.1 else "watch",
            "notes": None,
        }
        name = f"report_{i + 1:03d}_{template}.pdf"
        SimpleDocTemplate(str(raw / name), pagesize=A4).build(_story(rec, template, shown_rate, anomaly))
        shown_start, shown_end = rec["period_start"], rec["period_end"]
        if anomaly == "date_range":
            shown_start, shown_end = shown_end, shown_start
        source_truth = {
            key: rec[key]
            for key in (
                "report_date",
                "period_start",
                "period_end",
                "region",
                "sample_count",
                "positive_count",
                "positive_rate",
            )
        }
        source_truth["period_start"], source_truth["period_end"] = shown_start, shown_end
        source_truth["positive_rate"] = None if anomaly == "missing_field" else round(shown_rate, 4)
        records.append(
            {
                "file": name,
                "template": template,
                "anomaly_type": anomaly,
                "source_truth": source_truth,
                "canonical_truth": rec,
            }
        )
    truth.write_text(
        json.dumps(
            {
                "seed": seed,
                "count": count,
                "template_counts": Counter(r["template"] for r in records),
                "records": records,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"generated": count, "template_counts": Counter(r["template"] for r in records)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.count, args.seed)
