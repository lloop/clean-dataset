# tasks/reporter.py
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import asdict
from tasks.cross_reference import CrossReference
from schemas.audit_schema import PipelineAuditSummary


class AuditReporter:
    """Generates structured JSON audit report summarizing dataset cleaning runs."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.cross_reference = CrossReference()

    def generate_report(
        self,
        audit_summary: PipelineAuditSummary,
        manifest: Dict[str, Any],
    ) -> Path:
        """Writes audit_summary.json into the clean output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat()
        
        # TODO These are the true ground stats from the manifest. 
        # Supposed to be from the detected_files list. Also
        # doesn't take in to account that some are double modified.
        for item in manifest["files"]:
            audit_summary.total_processed += 1
            
            is_duplicate = any(item["filename"] == duplicate["file"] for duplicate in audit_summary.list_detected_files["detected_duplicates"])
            is_character_corrupted = any(item["filename"] == duplicate["file"] for duplicate in audit_summary.list_detected_files["detected_character_corrupted"])
            is_structure_corrupted = any(item["filename"] == duplicate["file"] for duplicate in audit_summary.list_detected_files["detected_structure_corrupted"])
            is_extension_scrambled = any(item["filename"] == duplicate["file"] for duplicate in audit_summary.list_detected_files["detected_extensions"])

            # Each item can have more than one modification
            if is_duplicate:            
                audit_summary.duplicates += 1
            if is_character_corrupted:
                audit_summary.character_corrupted += 1
            if is_structure_corrupted:
                audit_summary.structure_corrupted += 1
            if is_extension_scrambled:
                audit_summary.corrupted_extensions += 1
            if not any([
                is_duplicate,
                is_character_corrupted,
                is_structure_corrupted,
                is_extension_scrambled
            ]):
                audit_summary.clean_saved += 1
        
        duplicate_cross_reference = self.cross_reference.compare_duplicates(
            manifest,
            audit_summary.list_detected_files["detected_duplicates"]
        )
        
        character_cross_reference = self.cross_reference.compare_character_corrupted(
            manifest,
            audit_summary.list_detected_files["detected_character_corrupted"]
        )
        
        structure_cross_reference = self.cross_reference.compare_structure_corrupted(
            manifest,
            audit_summary.list_detected_files["detected_structure_corrupted"]
        )
        
        extension_cross_reference = self.cross_reference.compare_extensions_scrambled(
            manifest,
            audit_summary.list_detected_files["detected_extensions"]
        )
        
        # print("Audit summary.structure_corrupted:", audit_summary.structure_corrupted)

        report_data: Dict[str, Any] = {
            "timestamp": timestamp,
            "total_processed": audit_summary.total_processed,
            "detected_scrambled_extensions": audit_summary.corrupted_extensions,
            "detected_character_corrupted": audit_summary.character_corrupted,
            "detected_structure_corrupted": audit_summary.structure_corrupted,
            "detected_duplicates": audit_summary.duplicates,
            "clean_saved": audit_summary.clean_saved,
            "detected_files_list": audit_summary.list_detected_files,
            "cross_reference": {
                "duplicates": duplicate_cross_reference,
                "character_corrupted": character_cross_reference,
                "structure_corrupted": structure_cross_reference,
                "extensions_scrambled": extension_cross_reference
            }
        }

        # Write JSON report
        json_path = self.output_dir / "audit_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2) 

        return json_path
