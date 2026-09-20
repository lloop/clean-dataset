from dataclasses import dataclass, field

from schemas.file_schema import FileRecords


@dataclass
class PipelineAuditSummary:
    total_processed: int = 0
    duplicates: int = 0
    character_corrupted: int = 0
    structure_corrupted: int = 0
    corrupted_extensions: int = 0
    clean_saved: int = 0
    file_records: list[FileRecords] = field(default_factory=list)

    def build_summary(self):
        self.total_processed = len(self.file_records)

        self.duplicates = sum(
            record.duplicate
            for record in self.file_records
        )

        self.corrupted_extensions = sum(
            record.extension_mismatch
            for record in self.file_records
        )

        self.character_corrupted = sum(
            bool(record.character_corruption)
            for record in self.file_records
        )

        self.structure_corrupted = sum(
            bool(record.structural_corruption)
            for record in self.file_records
        )