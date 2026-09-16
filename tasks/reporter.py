# tasks/reporter.py
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import asdict
from tasks.cross_reference import CrossReference
from schemas.audit_schema import PipelineAuditSummary


class AuditReporter:
    """Generates structured JSON and Markdown audit reports summarizing dataset cleaning runs."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.cross_reference = CrossReference()

    def generate_report(
        self,
        audit_summary: PipelineAuditSummary,
        # audit_records: FileAuditCollections,
        manifest: Dict[str, Any],
    ) -> Path:
        """Writes audit_summary.json and audit_summary.md into the clean output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat()
        
        duplicate_cross_reference = self.cross_reference.compare_duplicates(
            manifest,
            audit_summary.list_detected_files["removed_duplicates"]
        )

        report_data: Dict[str, Any] = {
            "timestamp": timestamp,
            "total_processed": audit_summary.total_processed,
            "repaired_extensions": audit_summary.corrupted_extensions,
            "character_corrupted": audit_summary.character_corrupted,
            "structure_corrupted": audit_summary.structure_corrupted,
            "duplicates": audit_summary.duplicates,
            "clean_saved": audit_summary.clean_saved,
            "list_detected_files": audit_summary.list_detected_files,
            "cross_reference": {
                "duplicates": duplicate_cross_reference
            }
        }

        # Write JSON report
        json_path = self.output_dir / "audit_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2) 

        return json_path
