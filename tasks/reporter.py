import json
from datetime import datetime
from pathlib import Path
from typing import Any
from dataclasses import asdict
from schemas.audit_schema import PipelineAuditSummary
from tasks.cross_reference import CrossReference


class AuditReporter:
    """Generates a structured JSON audit report."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.cross_reference = CrossReference()

    def generate_report(
        self,
        audit_summary: PipelineAuditSummary,
        manifest: dict[str, Any] | None,
    ) -> Path:
        """Writes audit_summary.json into the output directory."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        cross_reference = None

        if manifest is not None:
            cross_reference = self.cross_reference.compare(
                manifest,
                audit_summary.file_records,
            )

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_processed": audit_summary.total_processed,
            "detected_scrambled_extensions": audit_summary.corrupted_extensions,
            "scrambled_extension_files": [
                record.filename
                for record in audit_summary.file_records
                if record.extension_mismatch
            ],
            "detected_character_corrupted": audit_summary.character_corrupted,
            "character_corrupted_files": [
                record.filename
                for record in audit_summary.file_records
                if record.character_corruption
            ],
            "detected_structure_corrupted": audit_summary.structure_corrupted,
            "structure_corrupted_files": [
                record.filename
                for record in audit_summary.file_records
                if record.structural_corruption
            ],
            "detected_duplicates": audit_summary.duplicates,
            "clean_saved": audit_summary.clean_saved,
            "cross_reference": cross_reference,
            "file_records": [
                {
                    key: value
                    for key, value in asdict(record).items()
                    if key != "magika_result"
                }
                for record in audit_summary.file_records
            ],
        }

        json_path = self.output_dir / "audit_summary.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        return json_path