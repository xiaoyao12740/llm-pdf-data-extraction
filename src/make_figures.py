from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/figures"
BLUE = "#183153"
CYAN = "#14b8a6"
LIGHT = "#eef6ff"
ORANGE = "#f59e0b"


def flow(name, title, nodes):
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.set_xlim(0, len(nodes))
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(title, fontsize=20, fontweight="bold", color=BLUE, pad=20)
    for i, node in enumerate(nodes):
        box = FancyBboxPatch(
            (i + 0.08, 0.35), 0.75, 0.28, boxstyle="round,pad=.03", facecolor=LIGHT, edgecolor=CYAN, linewidth=2
        )
        ax.add_patch(box)
        ax.text(i + 0.455, 0.49, node, ha="center", va="center", fontsize=10, fontweight="bold", color=BLUE)
        if i < len(nodes) - 1:
            ax.annotate(
                "",
                xy=(i + 1.05, 0.49),
                xytext=(i + 0.85, 0.49),
                arrowprops={"arrowstyle": "->", "color": ORANGE, "lw": 2},
            )
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def cards():
    fig, axes = plt.subplots(1, 5, figsize=(15, 4))
    fig.suptitle("Five Reproducible Synthetic PDF Layouts", fontsize=20, fontweight="bold", color=BLUE)
    labels = [("A", "Key–Value"), ("B", "Aliases"), ("C", "Multiline"), ("D", "Table"), ("E", "Narrative")]
    for ax, (letter, label) in zip(axes, labels, strict=True):
        ax.axis("off")
        ax.add_patch(
            FancyBboxPatch(
                (0.08, 0.1), 0.84, 0.75, boxstyle="round,pad=.04", facecolor=LIGHT, edgecolor=CYAN, linewidth=2
            )
        )
        ax.text(0.5, 0.62, letter, ha="center", fontsize=30, fontweight="bold", color=ORANGE)
        ax.text(0.5, 0.35, label, ha="center", fontsize=12, fontweight="bold", color=BLUE)
    fig.tight_layout()
    fig.savefig(OUT / "02_pdf_templates.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def schema():
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.set_title("MySQL 8.0 Traceability Model", fontsize=20, fontweight="bold", color=BLUE)
    positions = {
        "documents": (1, 2.5),
        "extraction_runs": (4, 2.5),
        "extracted_fields": (7, 4.2),
        "monitoring_records": (7, 2.5),
        "validation_issues": (7, 0.8),
    }
    for name, (x, y) in positions.items():
        ax.add_patch(
            FancyBboxPatch((x, y), 2, 0.8, boxstyle="round,pad=.04", facecolor=LIGHT, edgecolor=CYAN, linewidth=2)
        )
        ax.text(x + 1, y + 0.4, name, ha="center", va="center", fontweight="bold", color=BLUE)
    for dest in ("extracted_fields", "monitoring_records", "validation_issues"):
        ax.annotate(
            "",
            xy=(positions[dest][0], positions[dest][1] + 0.4),
            xytext=(6, 2.9),
            arrowprops={"arrowstyle": "->", "color": ORANGE, "lw": 2},
        )
    ax.annotate("", xy=(4, 2.9), xytext=(3, 2.9), arrowprops={"arrowstyle": "->", "color": ORANGE, "lw": 2})
    fig.savefig(OUT / "04_mysql_schema.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    flow(
        "01_system_architecture.png",
        "System Architecture",
        ["PDF", "Page Parser", "Rule Engine", "Selective LLM", "Normalizer", "Validator", "MySQL", "Exports"],
    )
    cards()
    flow(
        "03_extraction_pipeline.png",
        "Traceable Extraction Pipeline",
        ["Discover", "Parse Pages", "Rule Candidates", "LLM Gate", "Normalize", "Validate", "Persist", "Evaluate"],
    )
    schema()
