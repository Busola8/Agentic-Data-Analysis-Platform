# Agentic Financial Analysis Platform API

FastAPI backend for governed financial ingestion and analysis for Bauto Services.

## Current capabilities

- Upload CSV, XLSX, Parquet and digital PDF files.
- Enforce extension and 50 MB size limits.
- Verify XLSX, Parquet and PDF file signatures instead of trusting filenames.
- Store immutable raw files using generated dataset identifiers.
- Record SHA-256 checksums and upload metadata.
- Reject duplicate uploads by content fingerprint.
- Profile rows, columns, nulls, types and sample values for tabular files.
- Classify transaction, budget and invoice datasets from their schemas.
- Report duplicate rows, missing values, invalid dates and mixed currencies.
- Detect PDFs that may require OCR.
- List and retrieve dataset metadata.
- Serve a deterministic financial dashboard summary.

Runtime uploads are stored under `backend/data/` and are excluded from Git. The local
JSON metadata store is intentionally temporary; PostgreSQL will replace it when the
Docker infrastructure phase begins.

## Run locally

```powershell
uv sync --group dev
uv run fastapi dev app/main.py
```

API documentation is available at `http://127.0.0.1:8000/docs`.

## Test

```powershell
uv run pytest -q
```
