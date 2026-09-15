import argparse
import csv
import json
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
        # self.duplicates_removed: List[str] = []
        # self.repaired_extensions: List[str] = []
        # self.structure_corrupted: List[str] = []
        # self.character_corrupted: List[str] = []

        self.audit_records = FileAuditCollections()
        self.quarantine_mgr = QuarantineManager(self.clean_dir)
        self.reporter = AuditReporter(self.clean_dir)
        self.deduplicator = FileDeduplicator()
        self.extension_detector = ExtensionDetector()
        self.character_detector = CharacterCorruptionDetector()

    def process(self) -> Dict[str, int]:
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

        stats = {
            "total_processed": 0,
            "duplicates_removed": 0,
            "corrupted_quarantined": 0,
            "character_corrupted": 0,
            "structural_corrupted": 0,
            "clean_saved": 0,
            "repaired_extensions": 0,
        }

        for file_path in self.source_dir.iterdir():
            # Skip directories or manifest file during deduplication pass
            if file_path.is_dir() or file_path.name == "manifest.json":
                continue

            stats["total_processed"] += 1

            # Deduplication via Hash Matching
            if self.deduplicator.is_duplicate(file_path):
                # self.duplicates_removed.append(file_path.name)
                self.audit_records.removed_duplicates.append(file_path.name)
                self.quarantine_mgr.quarantine_duplicate(file_path)
                stats["duplicates_removed"] += 1
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
                        # self.character_corrupted.append(f"{file_path.name} [Char: {labels}]")
                        self.audit_records.character_corrupted.append(f"{file_path.name} [Char: {labels}]")
                        self.quarantine_mgr.quarantine_corrupt_char(file_path)
                        stats["character_corrupted"] += 1
                        stats["corrupted_quarantined"] += 1
                        continue
                except Exception:
                    pass

            # Structural Corruption Pass
            is_structurally_corrupt = self._check_structural_corruption(file_path, true_ext)
            if is_structurally_corrupt:
                # self.structure_corrupted.append(f"{file_path.name} [Structural]")
                self.audit_records.structure_corrupted.append(f"{file_path.name} [Structural]")
                self.quarantine_mgr.quarantine_corrupt_struct(file_path)
                stats["structural_corrupted"] += 1
                stats["corrupted_quarantined"] += 1
                continue

            # Extension Repair and Save
            current_ext = file_path.suffix.lower()
            if current_ext != true_ext:
                repaired_path = file_path.with_suffix(true_ext)
                # self.repaired_extensions.append(
                #     f"{file_path.name} -> {repaired_path.name}"
                # )
                self.audit_records.repaired_extensions.append(f"{file_path.name} -> {repaired_path.name}")
                self.quarantine_mgr.save_valid_file(file_path, repaired_path)
                stats["repaired_extensions"] += 1
            else:
                self.quarantine_mgr.save_valid_file(file_path)
                stats["clean_saved"] += 1

        # Generate output reports inside output folder
        self.reporter.generate_report(
            stats, self.audit_records
        )
        # self.reporter.generate_report(
        #     stats, self.duplicates_removed, self.repaired_extensions
        # )

        return stats

    def _check_structural_corruption(self, file_path: Path, ext: str) -> bool:
        """Validates structural integrity based on the file format."""
        try:
            if ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
            elif ext == ".xml":
                with open(file_path, "r", encoding="utf-8") as f:
                    ET.fromstring(f.read())
            elif ext == ".csv":
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if rows:
                        expected_cols = len(rows[0])
                        for row in rows:
                            if len(row) != expected_cols:
                                return True
            return False
        except Exception:
            # Syntax or parser failure indicates structural corruption
            return True


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
    print(f"  Total Evaluated : {results['total_processed']}")
    print(f"  Duplicates Cut  : {results['duplicates_removed']}")
    print(f"  Extensions Repaired  : {results['repaired_extensions']}")
    print(f"  Character Corruptions: {results['character_corrupted']}")
    print(f"  Structural Corruptions: {results['structural_corrupted']}")
    print(f"  Total Quarantined: {results['corrupted_quarantined']}")
    print(f"  Clean Files Kept: {results['clean_saved']}")
    print(f"Cleaned dataset output saved to: '{args.clean}'")
    print("==================================================")