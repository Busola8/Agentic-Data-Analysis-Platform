from fastapi.testclient import TestClient
from io import BytesIO

import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from openpyxl import Workbook
from pypdf import PdfWriter

from app.main import app
from app.services.dataset_store import DatasetStore
import app.routers.datasets as datasets_module


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_dataset_store(tmp_path, monkeypatch):
    monkeypatch.setattr(datasets_module, "STORE", DatasetStore(tmp_path))


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_summary_is_traceable():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["company"] == "Bauto Services"
    assert payload["generated_from"] == "deterministic-demo-dataset-v1"
    assert len(payload["trend"]) == 12
    assert payload["metrics"][0]["currency"] == "NGN"


def test_dashboard_rejects_reversed_period():
    response = client.get(
        "/api/v1/dashboard/summary",
        params={"start_date": "2026-07-01", "end_date": "2026-06-01"},
    )
    assert response.status_code == 422


def test_csv_upload_returns_profile():
    content = b"date,amount,department\n2026-06-01,125000,Operations\n2026-06-02,85000,Sales\n"
    response = client.post("/api/v1/datasets", files={"file": ("transactions.csv", BytesIO(content), "text/csv")})
    assert response.status_code == 201
    payload = response.json()
    assert payload["company"] == "Bauto Services"
    assert payload["profile"]["row_count"] == 2
    assert payload["profile"]["column_count"] == 3
    assert len(payload["sha256"]) == 64
    assert payload["profile"]["dataset_kind"] == "transactions"


def test_upload_rejects_unsupported_format():
    response = client.post("/api/v1/datasets", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415


def test_xlsx_upload_returns_financial_profile():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["invoice_number", "supplier", "due_date", "amount"])
    sheet.append(["INV-001", "Acme Ltd", "2026-07-31", 450000])
    content = BytesIO()
    workbook.save(content)
    response = client.post("/api/v1/datasets", files={"file": ("invoices.xlsx", content.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 201
    assert response.json()["profile"]["dataset_kind"] == "invoices"


def test_parquet_upload_returns_profile():
    table = pa.table({"department": ["Sales", "Operations"], "budget": [5000000, 7000000], "period": ["Q1", "Q1"]})
    content = BytesIO()
    pq.write_table(table, content)
    response = client.post("/api/v1/datasets", files={"file": ("budget.parquet", content.getvalue(), "application/octet-stream")})
    assert response.status_code == 201
    payload = response.json()
    assert payload["profile"]["dataset_kind"] == "budgets"
    assert payload["profile"]["row_count"] == 2


def test_pdf_upload_flags_ocr_when_no_text_exists():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    content = BytesIO()
    writer.write(content)
    response = client.post("/api/v1/datasets", files={"file": ("statement.pdf", content.getvalue(), "application/pdf")})
    assert response.status_code == 201
    payload = response.json()
    assert payload["profile"]["dataset_kind"] == "financial_document"
    assert payload["profile"]["quality_issues"][0]["code"] == "ocr_required"


def test_duplicate_upload_is_rejected():
    content = b"date,amount\n2026-06-01,125000\n"
    first = client.post("/api/v1/datasets", files={"file": ("first.csv", content, "text/csv")})
    second = client.post("/api/v1/datasets", files={"file": ("second.csv", content, "text/csv")})
    assert first.status_code == 201
    assert second.status_code == 409


def test_spoofed_file_extension_is_rejected():
    response = client.post("/api/v1/datasets", files={"file": ("fake.pdf", b"not really a pdf", "application/pdf")})
    assert response.status_code == 422


def test_damaged_pdf_returns_validation_error_not_server_error():
    response = client.post("/api/v1/datasets", files={"file": ("damaged.pdf", b"%PDF-1.7 broken", "application/pdf")})
    assert response.status_code == 422


def test_quality_issues_report_missing_invalid_and_duplicate_data():
    content = b"date,amount,currency\nnot-a-date,125000,NGN\nnot-a-date,125000,NGN\n2026-06-02,,USD\n"
    response = client.post("/api/v1/datasets", files={"file": ("quality.csv", content, "text/csv")})
    assert response.status_code == 201
    codes = {issue["code"] for issue in response.json()["profile"]["quality_issues"]}
    assert {"duplicate_rows", "invalid_dates", "missing_values", "mixed_currencies"} <= codes
