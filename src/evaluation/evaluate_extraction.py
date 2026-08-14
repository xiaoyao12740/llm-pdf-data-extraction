import json
from pathlib import Path

FIELDS=("report_date","period_start","period_end","region","sample_count","positive_count","positive_rate")


def _equal(field,predicted,expected):
    if predicted is None: return False
    if field=="positive_rate": return abs(float(predicted)-float(expected))<=.0001
    return predicted==expected


def evaluate(results,truth_path):
    truth=json.loads(Path(truth_path).read_text(encoding="utf-8")); expected={x["file"]:x["ground_truth"] for x in truth["records"]}; total=len(results)*len(FIELDS); correct=missing=0; by_field={field:{"correct":0,"total":0,"missing":0} for field in FIELDS}
    for result in results:
        gold=expected[result["file"]]; predicted=result["record"]
        for field in FIELDS:
            value=predicted.get(field); by_field[field]["total"]+=1
            if value is None: missing+=1; by_field[field]["missing"]+=1
            if _equal(field,value,gold[field]): correct+=1; by_field[field]["correct"]+=1
    for stats in by_field.values(): stats["accuracy"]=round(stats["correct"]/stats["total"],4); stats["missing_rate"]=round(stats["missing"]/stats["total"],4)
    return {"documents":len(results),"fields_evaluated":total,"field_accuracy":round(correct/total,4),"exact_match_documents":sum(all(_equal(f,r["record"].get(f),expected[r["file"]][f]) for f in FIELDS) for r in results),"missing_field_rate":round(missing/total,4),"validation_issue_count":sum(len(r["validation_issues"]) for r in results),"by_field":by_field}


def save_metrics(metrics,path): Path(path).write_text(json.dumps(metrics,indent=2),encoding="utf-8")
