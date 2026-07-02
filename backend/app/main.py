from datetime import date
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.routers.datasets import router as datasets_router


class Metric(BaseModel):
    key: str
    label: str
    value: float
    currency: str | None = "NGN"
    change_percent: float | None = None


class TrendPoint(BaseModel):
    month: str
    revenue: float
    expenses: float


class Anomaly(BaseModel):
    id: str
    title: str
    severity: Literal["low", "medium", "high"]
    exposure: float
    detected_at: date
    evidence: str


class DashboardSummary(BaseModel):
    company: str
    period: dict[str, date]
    metrics: list[Metric]
    trend: list[TrendPoint]
    anomalies: list[Anomaly]
    source_count: int
    generated_from: str


app = FastAPI(
    title="Agentic Financial Analysis Platform API",
    version="0.1.0",
    description="Governed financial intelligence APIs for Bauto Services.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(datasets_router)


@app.get("/")
def root():
    return {"name": app.title, "docs": "/docs", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "financial-analysis-api"}


@app.get("/api/v1/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    start_date: date = Query(default=date(2025, 7, 1)),
    end_date: date = Query(default=date(2026, 6, 30)),
):
    """Return a traceable demo summary until governed ingestion is connected."""
    if start_date > end_date:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")

    revenue = [42, 47, 45, 52, 56, 61, 58, 65, 69, 73, 76, 82]
    expenses = [30, 32, 34, 35, 38, 39, 41, 42, 45, 46, 47, 49]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return DashboardSummary(
        company="Bauto Services",
        period={"start": start_date, "end": end_date},
        metrics=[
            Metric(key="revenue", label="Total revenue", value=728_400_000, change_percent=12.8),
            Metric(key="operating_profit", label="Operating profit", value=241_600_000, change_percent=8.4),
            Metric(key="cash_balance", label="Cash balance", value=184_200_000),
            Metric(key="anomaly_exposure", label="Anomaly exposure", value=9_800_000),
        ],
        trend=[TrendPoint(month=m, revenue=r * 1_000_000, expenses=e * 1_000_000) for m, r, e in zip(months, revenue, expenses)],
        anomalies=[
            Anomaly(id="ANM-007", title="Unusual supplier payment", severity="high", exposure=6_820_000, detected_at=date(2026, 6, 27), evidence="Payment is 4.3x the vendor's trailing average."),
            Anomaly(id="ANM-006", title="Fuel costs rising", severity="medium", exposure=2_980_000, detected_at=date(2026, 6, 30), evidence="Category spend increased 11.2% over 30 days."),
        ],
        source_count=4,
        generated_from="deterministic-demo-dataset-v1",
    )
