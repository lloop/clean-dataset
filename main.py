import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

from schemas.audit_schema import FileAuditCollections, PipelineAuditSummary
from tasks.character_detector import CharacterCorruptionDetector
from tasks.structure_detector import StructureCorruptionDetector
from tasks.deduplicator import FileDeduplicator
from tasks.extension_detector import ExtensionDetector
from tasks.quarantine import QuarantineManager
from tasks.reporter import AuditReporter

DIRTY_DIR = Path("dataset_dirty")
CLEAN_DIR = Path("dataset_clean")


class DatasetCleaner:
    """Evaluates and cleans synthetic dirty datasets by resolving binary duplicates,
    detecting character/structural corruptions, repairing file extensions, and segregating valid records.
    """

    def __init__(self, source_dir: str, clean_dir: str):
        self.source_dir = Path(source_dir)
        self.clean_dir = Path(clean_dir)

        self.audit_records = FileAuditCollections()
        self.audit_summary = PipelineAuditSummary()
        self.quarantine_mgr = QuarantineManager(self.clean_dir)
        self.reporter = AuditReporter(self.clean_dir)
        self.deduplicator = FileDeduplicator()
        self.extension_detector = ExtensionDetector()
        self.character_detector = CharacterCorruptionDetector()
        self.structure_detector = StructureCorruptionDetector()

    def process(self) -> PipelineAuditSummary:
        """Executes deduplication, corruption detection, extension repair, and directory cleanup."""
        if not self.source_dir.exists():
            raise FileNotFoundError(
                f"Source directory '{self.source_dir}' does not exist."
            )

        # Recreate clean target directory
        if self.clean_dir.exists():
            shutil.rmtree(self.clean_dir)
        self.clean_dir.mkdir(parents=True)

        # Setup destination valid/ and quarantine/ structures
        self.quarantine_mgr.setup_directories()

        # stats = {
        #     "total_processed": 0,
        #     "duplicates": 0,
        #     "corrupted_quarantined": 0,
        #     "character_corrupted": 0,
        #     "structural_corrupted": 0,
        #     "clean_saved": 0,
        #     "repaired_extensions": 0,
        # }

        for file_path in self.source_dir.iterdir():
            # Skip directories or manifest file during deduplication pass
            if file_path.is_dir() or file_path.name == "manifest.json":
                continue

            self.audit_summary.total_processed += 1

            # Deduplication via Hash Matching
            if self.deduplicator.is_duplicate(file_path):
                self.audit_records.removed_duplicates.append(file_path.name)
                self.quarantine_mgr.quarantine_duplicate(file_path)
                self.audit_summary.duplicates += 1
                continue

            # Detect binary files
            true_ext = self.extension_detector.detect_true_extension(file_path)
            is_binary = true_ext in [".jpg", ".jpeg", ".png", ".gif", ".ico"]

            # Character Corruption Pass
            if not is_binary:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    char_result = self.character_detector.detect_character_corruption(content)
                    if char_result["is_corrupted"]:
                        labels = ", ".join(char_result["detected_corruptions"])
                        self.audit_records.character_corrupted.append(f"{file_path.name} [Char: {labels}]")
                        self.quarantine_mgr.quarantine_corrupt_char(file_path)
                        self.audit_summary.character_corrupted += 1
                        continue
                except OSError as error:
                    print(f"ERROR reading {file_path}: {error}")
                    self.quarantine_mgr.quarantine_corrupt_char(file_path, reason="read_error")
                    continue

            # Structural Corruption Pass
            is_structurally_corrupt = self.structure_detector.is_structurally_corrupt(file_path, true_ext)
            if is_structurally_corrupt:
                self.audit_records.structure_corrupted.append(f"{file_path.name} [Structural]")
                self.quarantine_mgr.quarantine_corrupt_struct(file_path)
                self.audit_summary.structure_corrupted += 1
                continue

            # Extension Repair and Save
            current_ext = file_path.suffix.lower()
            if current_ext != true_ext:
                repaired_path = file_path.with_suffix(true_ext)
                self.audit_records.repaired_extensions.append(f"{file_path.name} -> {repaired_path.name}")
                self.quarantine_mgr.save_valid_file(file_path, repaired_path)
                self.audit_summary.corrupted_extensions += 1
                self.audit_summary.clean_saved += 1
            else:
                self.quarantine_mgr.save_valid_file(file_path)
                self.audit_summary.clean_saved += 1

        # Generate output reports inside output folder
        self.reporter.generate_report(
            self.audit_summary, self.audit_records
        )

        # self.audit_summary
        return self.audit_summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--source",
        default=DIRTY_DIR,
        help="Directory containing dirty files",
    )
    parser.add_argument(
        "-c",
        "--clean",
        default=CLEAN_DIR,
        help="Target directory for cleaned dataset",
    )
    args = parser.parse_args()

    cleaner = DatasetCleaner(source_dir=args.source, clean_dir=args.clean)
    results = cleaner.process()

    print("==================================================")
    print("Data Cleaning Pass Complete:")
    print(f"  Total Evaluated : {results.total_processed}")
    print(f"  Duplicates Cut  : {results.duplicates}")
    print(f"  Extensions Repaired  : {results.corrupted_extensions}")
    print(f"  Character Corruptions: {results.character_corrupted}")
    print(f"  Structural Corruptions: {results.structure_corrupted}")
    print(f"  Clean Files Kept: {results.clean_saved}")
    print(f"Cleaned dataset output saved to: '{args.clean}'")
    print("==================================================")