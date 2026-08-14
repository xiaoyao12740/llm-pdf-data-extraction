import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
METRICS = ROOT / "reports/metrics"
OUT = ROOT / "reports/figures"
COLOR = "#14b8a6"


def generate():
    rules = json.loads((METRICS / "rules_only_metrics.json").read_text())
    source = rules["source_extraction"]
    fields = list(source["by_field"])
    accuracy = [source["by_field"][f]["accuracy"] for f in fields]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(fields, accuracy, color=COLOR)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Source extraction accuracy")
    ax.tick_params(axis="x", rotation=30)
    ax.set_title("Rules-only Source Extraction Accuracy (measured)")
    fig.tight_layout()
    fig.savefig(OUT / "05_field_accuracy.png", dpi=170)
    plt.close(fig)
    methods = [("Rules Only", rules)]
    llm = METRICS / "rules_llm_metrics.json"
    if llm.exists():
        methods.append(("Rules + Ollama", json.loads(llm.read_text())))
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(
        [x[0] for x in methods],
        [x[1]["source_extraction"]["field_accuracy"] for x in methods],
        color=[COLOR, "#f59e0b"][: len(methods)],
    )
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Source extraction accuracy")
    ax.set_title("Measured Semantic Recovery Comparison")
    fig.tight_layout()
    fig.savefig(OUT / "06_method_comparison.png", dpi=170)
    plt.close(fig)
    details = json.loads((ROOT / "data/processed/extraction_details.json").read_text())
    counts = {}
    for result in details:
        for issue in result["validation_issues"]:
            counts[issue["issue_type"]] = counts.get(issue["issue_type"], 0) + 1
    plotted = counts or {"none": 0}
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(list(plotted), list(plotted.values()), color="#f59e0b")
    ax.set_title("Validation Issues by Type")
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(OUT / "07_validation_issues.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    generate()
