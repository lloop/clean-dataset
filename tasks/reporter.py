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
        manifest: dict[str, Any],
    ) -> Path:
        """Writes audit_summary.json into the output directory."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        cross_reference = self.cross_reference.compare(
            manifest,
            audit_summary.file_records,
        )

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_processed": audit_summary.total_processed,
            "detected_scrambled_extensions": audit_summary.corrupted_extensions,
            "detected_character_corrupted": audit_summary.character_corrupted,
            "detected_structure_corrupted": audit_summary.structure_corrupted,
            "detected_duplicates": audit_summary.duplicates,
            "clean_saved": audit_summary.clean_saved,
            "cross_reference": cross_reference,
            "file_records": [
                asdict(record)
                for record in audit_summary.file_records
            ],
        }

        json_path = self.output_dir / "audit_summary.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        return json_path