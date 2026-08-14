from datetime import date

from pydantic import BaseModel, ConfigDict


class MonitoringRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    region: str | None = None
    sample_count: int | None = None
    positive_count: int | None = None
    positive_rate: float | None = None
    report_id: str | None = None
    report_title: str | None = None
    organization: str | None = None
    alert_level: str | None = None
    notes: str | None = None
