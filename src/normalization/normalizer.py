import re
from datetime import date, datetime


def normalize_value(field, value):
    if value is None: return None
    if field in {"sample_count","positive_count"}: return int(str(value).replace(",",""))
    if field == "positive_rate":
        numeric=float(str(value).strip().rstrip("%")); return numeric/100 if "%" in str(value) or numeric>1 else numeric
    if field in {"report_date","period_start","period_end"}:
        if isinstance(value,(date,datetime)): return value.date().isoformat() if isinstance(value,datetime) else value.isoformat()
        return datetime.strptime(str(value).replace("/","-"),"%Y-%m-%d").date().isoformat()
    if field == "region": return " ".join(re.sub(r"\s+region\s*$","",str(value),flags=re.I).split()).title()
    return str(value).strip()


def fields_to_record(fields):
    return {item["field_name"]:normalize_value(item["field_name"],item.get("normalized_candidate",item.get("raw_value"))) for item in fields}
