import argparse, json, random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ("key_value", "aliases", "multiline", "table", "narrative")


def _story(record, template, shown_rate):
    styles = getSampleStyleSheet(); normal = styles["BodyText"]
    title = [Paragraph(record["report_title"], styles["Title"]), Spacer(1, 18)]
    period = f'{record["period_start"]} to {record["period_end"]}'
    if template == "key_value":
        lines = [f'Report Date: {record["report_date"]}', f'Period Start: {record["period_start"]}', f'Period End: {record["period_end"]}', f'Region: {record["region"]}', f'Samples Tested: {record["sample_count"]:,}', f'Positive Cases: {record["positive_count"]:,}', f'Positive Rate: {shown_rate:.2%}']
    elif template == "aliases":
        lines = [f'Generated On: {record["report_date"]}', f'From: {record["period_start"]}', f'To: {record["period_end"]}', f'Area: {record["region"]}', f'Total Tests: {record["sample_count"]:,}', f'Detected Positive: {record["positive_count"]:,}', f'Detection Rate: {shown_rate:.2%}']
    elif template == "multiline":
        lines = [f'Report Date\n{record["report_date"]}', f'Period Start\n{record["period_start"]}', f'Period End\n{record["period_end"]}', f'Region\n{record["region"]}', f'Number Tested\n{record["sample_count"]:,}', f'Positives\n{record["positive_count"]:,}', f'Rate\n{shown_rate:.2%}']
    elif template == "narrative":
        lines = [f'Report Date: {record["report_date"]}', f'Period Start: {record["period_start"]}', f'Period End: {record["period_end"]}', f'Region: {record["region"]}', f'During {period}, laboratories processed a total of {record["sample_count"]:,} samples in {record["region"]}. Of which {record["positive_count"]:,} were positive.', f'Positive Rate: {shown_rate:.2%}']
    else:
        data = [["Report Date", "From", "To", "Region", "Tests", "Positive", "Rate"], [record["report_date"], record["period_start"], record["period_end"], record["region"], f'{record["sample_count"]:,}', f'{record["positive_count"]:,}', f'{shown_rate:.2%}']]
        table = Table(data, repeatRows=1); table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#183153")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .5, colors.grey), ("PADDING", (0,0), (-1,-1), 6)]))
        return title + [table]
    return title + [Paragraph(line.replace("\n", "<br/>"), normal) for line in lines]


def generate(count=100, seed=42, raw_dir=None, truth_path=None):
    rng = random.Random(seed); raw = Path(raw_dir or ROOT / "data/raw"); truth = Path(truth_path or ROOT / "data/ground_truth/ground_truth.json")
    raw.mkdir(parents=True, exist_ok=True); truth.parent.mkdir(parents=True, exist_ok=True)
    records=[]
    for i in range(count):
        template=TEMPLATES[i % len(TEMPLATES)]; end=date(2026,1,7)+timedelta(days=i); start=end-timedelta(days=6); samples=rng.randint(500,2500); positive=rng.randint(0, samples//5); rate=positive/samples
        anomaly = "rate_mismatch" if i % 17 == 0 else None; shown_rate=min(1, rate+.02) if anomaly else rate
        rec={"report_id":f"RPT_{i+1:04d}","report_title":"Weekly Monitoring Report","organization":"Demo Monitoring Center","report_date":(end+timedelta(days=1)).isoformat(),"period_start":start.isoformat(),"period_end":end.isoformat(),"region":["North","South","East","West"][i%4],"sample_count":samples,"positive_count":positive,"positive_rate":round(rate,6),"alert_level":"normal" if rate<.1 else "watch","notes":None}
        name=f"report_{i+1:03d}_{template}.pdf"; SimpleDocTemplate(str(raw/name), pagesize=A4).build(_story(rec, template, shown_rate))
        records.append({"file":name,"template":template,"anomaly_type":anomaly,"displayed_positive_rate":round(shown_rate,6),"ground_truth":rec})
    truth.write_text(json.dumps({"seed":seed,"count":count,"template_counts":Counter(r["template"] for r in records),"records":records}, indent=2), encoding="utf-8")
    print(json.dumps({"generated":count,"template_counts":Counter(r["template"] for r in records)}, indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--count",type=int,default=100); parser.add_argument("--seed",type=int,default=42); args=parser.parse_args(); generate(args.count,args.seed)
