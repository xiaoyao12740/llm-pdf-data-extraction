import argparse, csv, hashlib, json
from collections import Counter
from pathlib import Path
from pydantic import ValidationError
from .database.mysql_client import build_engine
from .database.repository import save_extraction
from .evaluation.evaluate_extraction import evaluate, save_metrics
from .extraction.rule_extractor import extract_fields
from .llm.ollama_client import OllamaClient
from .normalization.normalizer import fields_to_record, normalize_value
from .parsers.pdf_text_parser import parse_pdf
from .validation.schema import MonitoringRecord
from .validation.validators import validate_record

ROOT=Path(__file__).resolve().parents[1]
TARGET_FIELDS=("report_date","period_start","period_end","region","sample_count","positive_count","positive_rate")


def _llm_candidates(pages, fields, provider, threshold=.60):
    current={item["field_name"]:item for item in fields}; rejected=[]; context="\n\n".join(f'[Page {p["page_number"]}]\n{p["text"]}' for p in pages)
    for field in TARGET_FIELDS:
        if field in current and current[field]["confidence"]>=threshold: continue
        try: result=provider.extract_field(field,context)
        except (OSError,ValueError,KeyError,TypeError) as error:
            rejected.append({"field_name":field,"issue_type":"llm_response_rejected","severity":"warning","message":str(error)})
            continue
        if result.value is None: continue
        try: normalized=normalize_value(field,result.value)
        except (TypeError,ValueError): continue
        candidate={"field_name":field,"raw_value":str(result.value),"normalized_candidate":normalized,"page_number":next((p["page_number"] for p in pages if result.evidence in p["text"]),1),"source_text":result.evidence,"extraction_method":"llm","confidence":max(0,min(1,result.confidence)),"reason":result.reason}
        if field not in current or candidate["confidence"]>current[field]["confidence"]: current[field]=candidate
    return list(current.values()),rejected


def process_pdf(path, provider=None,confidence_threshold=.60):
    pages=parse_pdf(path); fields=extract_fields(pages)
    llm_issues=[]
    if provider: fields,llm_issues=_llm_candidates(pages,fields,provider,confidence_threshold)
    record=fields_to_record(fields); schema_issues=[]
    try: record=MonitoringRecord(**record).model_dump(mode="json",exclude_none=False)
    except ValidationError as error: schema_issues=[{"field_name":"schema","issue_type":"schema","severity":"error","message":item["msg"]} for item in error.errors()]
    issues=validate_record(record)+schema_issues+llm_issues
    invalid_fields={issue["field_name"] for issue in issues}
    for field in fields: field["validation_status"]="invalid" if field["field_name"] in invalid_fields else "valid"
    return {"file":path.name,"file_path":str(path.resolve()),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"page_count":len(pages),"fields":fields,"record":record,"validation_issues":issues}


def export_results(results,processed_dir):
    processed=Path(processed_dir); processed.mkdir(parents=True,exist_ok=True)
    (processed/"extraction_details.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    records=[{"file":r["file"],**r["record"]} for r in results]
    (processed/"structured_records.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
    if records:
        with (processed/"structured_records.csv").open("w",newline="",encoding="utf-8-sig") as handle:
            writer=csv.DictWriter(handle,fieldnames=records[0]); writer.writeheader(); writer.writerows(records)


def run(raw_dir=ROOT/"data/raw",processed_dir=ROOT/"data/processed",llm="disabled",model="qwen2.5:7b",database="disabled",confidence_threshold=.60):
    provider=None
    if llm=="ollama":
        provider=OllamaClient(model=model)
        if not provider.health_check(): raise RuntimeError("Ollama API is unavailable; start Ollama or use --llm disabled")
    results=[process_pdf(path,provider,confidence_threshold) for path in sorted(Path(raw_dir).glob("*.pdf"))]
    export_results(results,processed_dir)
    metrics=evaluate(results,ROOT/"data/ground_truth/ground_truth.json"); metrics.update({"method":"rules+ollama" if provider else "rules_only","llm_model":model if provider else None})
    metrics_path=ROOT/"reports/metrics"/("rules_llm_metrics.json" if provider else "rules_only_metrics.json"); save_metrics(metrics,metrics_path)
    summary={"documents":len(results),"successful_parses":sum(r["page_count"]>0 for r in results),"extraction_methods":dict(Counter(f["extraction_method"] for r in results for f in r["fields"])),"validation_issue_types":dict(Counter(i["issue_type"] for r in results for i in r["validation_issues"])),"valid_documents":sum(not r["validation_issues"] for r in results)}
    save_metrics(summary,ROOT/"reports/metrics/validation_summary.json")
    if database=="mysql":
        engine=build_engine()
        for result in results: save_extraction(engine,result,"ollama" if provider else None,model if provider else None)
    print(json.dumps({"processed":len(results),"method":metrics["method"],"field_accuracy":metrics["field_accuracy"],"missing_field_rate":metrics["missing_field_rate"],"validation_issues":metrics["validation_issue_count"],"database":database},indent=2))
    return results


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--llm",choices=("disabled","ollama"),default="disabled"); parser.add_argument("--model",default="qwen2.5:7b"); parser.add_argument("--database",choices=("disabled","mysql"),default="disabled"); parser.add_argument("--confidence-threshold",type=float,default=.60); args=parser.parse_args(); run(llm=args.llm,model=args.model,database=args.database,confidence_threshold=args.confidence_threshold)
