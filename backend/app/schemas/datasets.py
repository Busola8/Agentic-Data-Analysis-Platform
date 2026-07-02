from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DatasetStatus = Literal["ready", "rejected", "processing"]
DatasetFormat = Literal["csv", "xlsx", "parquet", "pdf"]
DatasetKind = Literal["transactions", "budgets", "invoices", "financial_document", "general"]


class DataQualityIssue(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    column: str | None = None
    affected_rows: int | None = None


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    non_null_count: int
    null_count: int
    unique_count: int | None = None
    sample_values: list[Any] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    dataset_kind: DatasetKind = "general"
    row_count: int | None = None
    column_count: int | None = None
    columns: list[ColumnProfile] = Field(default_factory=list)
    sheet_names: list[str] = Field(default_factory=list)
    page_count: int | None = None
    extracted_character_count: int | None = None
    warnings: list[str] = Field(default_factory=list)
    quality_issues: list[DataQualityIssue] = Field(default_factory=list)


class DatasetRecord(BaseModel):
    id: str
    company: str
    original_filename: str
    format: DatasetFormat
    content_type: str | None
    size_bytes: int
    sha256: str
    status: DatasetStatus
    uploaded_at: datetime
    profile: DatasetProfile
    source: Literal["file_upload"] = "file_upload"


class DatasetList(BaseModel):
    items: list[DatasetRecord]
    count: int
