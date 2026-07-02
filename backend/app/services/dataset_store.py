import json
import re
from pathlib import Path

from app.schemas.datasets import DatasetRecord


class DatasetStore:
    """Small local metadata store, replaced by PostgreSQL in the infrastructure phase."""

    def __init__(self, root: Path) -> None:
        self.raw_dir = root / "raw"
        self.metadata_dir = root / "metadata"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: DatasetRecord) -> None:
        target = self.metadata_dir / f"{record.id}.json"
        target.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def get(self, dataset_id: str) -> DatasetRecord | None:
        if re.fullmatch(r"ds_[a-f0-9]{32}", dataset_id) is None:
            return None
        target = self.metadata_dir / f"{dataset_id}.json"
        if not target.exists():
            return None
        return DatasetRecord.model_validate_json(target.read_text(encoding="utf-8"))

    def list(self) -> list[DatasetRecord]:
        records: list[DatasetRecord] = []
        for target in self.metadata_dir.glob("*.json"):
            try:
                records.append(DatasetRecord.model_validate(json.loads(target.read_text(encoding="utf-8"))))
            except (ValueError, OSError):
                continue
        return sorted(records, key=lambda item: item.uploaded_at, reverse=True)

    def find_by_sha256(self, digest: str) -> DatasetRecord | None:
        return next((record for record in self.list() if record.sha256 == digest), None)
