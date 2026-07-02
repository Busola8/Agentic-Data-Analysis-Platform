import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.datasets import DatasetList, DatasetRecord
from app.services.dataset_store import DatasetStore
from app.services.profiling import profile_file


router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])
logger = logging.getLogger(__name__)
DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
STORE = DatasetStore(DATA_ROOT)
ALLOWED_EXTENSIONS = {".csv": "csv", ".xlsx": "xlsx", ".parquet": "parquet", ".pdf": "pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def _verify_file_signature(path: Path, file_format: str) -> None:
    with path.open("rb") as source:
        header = source.read(8)
        if file_format == "parquet":
            source.seek(-4, 2)
            footer = source.read(4)
        else:
            footer = b""
    valid = {
        "xlsx": header.startswith(b"PK\x03\x04"),
        "parquet": header.startswith(b"PAR1") and footer == b"PAR1",
        "pdf": header.startswith(b"%PDF-"),
        "csv": b"\x00" not in header,
    }[file_format]
    if not valid:
        raise HTTPException(status_code=422, detail=f"File contents do not match the .{file_format} extension.")


@router.post("", response_model=DatasetRecord, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetRecord:
    original_filename = Path(file.filename or "").name
    extension = Path(original_filename).suffix.lower()
    file_format = ALLOWED_EXTENSIONS.get(extension)
    if not original_filename or file_format is None:
        raise HTTPException(status_code=415, detail="Supported formats are CSV, XLSX, Parquet and PDF.")

    dataset_id = f"ds_{uuid4().hex}"
    target = STORE.raw_dir / f"{dataset_id}{extension}"
    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("wb") as destination:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="File exceeds the 50 MB upload limit.")
                digest.update(chunk)
                destination.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="The uploaded file is empty.")
        _verify_file_signature(target, file_format)
        existing = STORE.find_by_sha256(digest.hexdigest())
        if existing is not None:
            raise HTTPException(status_code=409, detail={"message": "This file has already been uploaded.", "dataset_id": existing.id})
        profile = profile_file(target, file_format)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except (OSError, ValueError, UnicodeError) as error:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"The file could not be parsed: {error}") from error
    except Exception as error:
        # Third-party document parsers expose different exception hierarchies.
        # Convert failures at this untrusted-file boundary without leaking internals.
        target.unlink(missing_ok=True)
        logger.warning("Dataset %s could not be parsed", dataset_id, exc_info=error)
        raise HTTPException(status_code=422, detail="The file is damaged or could not be parsed safely.") from error
    finally:
        await file.close()

    record = DatasetRecord(
        id=dataset_id,
        company="Bauto Services",
        original_filename=original_filename,
        format=file_format,
        content_type=file.content_type,
        size_bytes=size,
        sha256=digest.hexdigest(),
        status="ready",
        uploaded_at=datetime.now(UTC),
        profile=profile,
    )
    STORE.save(record)
    return record


@router.get("", response_model=DatasetList)
def list_datasets() -> DatasetList:
    items = STORE.list()
    return DatasetList(items=items, count=len(items))


@router.get("/{dataset_id}", response_model=DatasetRecord)
def get_dataset(dataset_id: str) -> DatasetRecord:
    record = STORE.get(dataset_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return record
