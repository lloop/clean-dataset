import argparse
import json
import shutil
from pathlib import Path
from typing import Dict, List

from tasks.deduplicator import FileDeduplicator
from tasks.detector import ExtensionDetector
from tasks.quarantine import QuarantineManager
from tasks.reporter import AuditReporter

DIRTY_DIR = Path("dataset_dirty")
CLEAN_DIR = Path("dataset_clean")


class DatasetCleaner:
    """Evaluates and cleans synthetic dirty datasets by resolving binary duplicates,
    repairing file extensions, and segregating valid records.
    """

    def __init__(self, source_dir: str, clean_dir: str):
        self.source_dir = Path(source_dir)
        self.clean_dir = Path(clean_dir)
        self.removed_duplicates: List[str] = []
        self.repaired_extensions: List[str] = []

        self.quarantine_mgr = QuarantineManager(self.clean_dir)
        self.reporter = AuditReporter(self.clean_dir)
        self.deduplicator = FileDeduplicator()
        self.extension_detector = ExtensionDetector()

    def process(self) -> Dict[str, int]:
        """Executes deduplication and directory cleanup."""
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
                self.removed_duplicates.append(file_path.name)
                self.quarantine_mgr.quarantine_duplicate(file_path)
                stats["duplicates_removed"] += 1
                continue

            # Extension Repair Check
            true_ext = self.extension_detector.detect_true_extension(file_path)
            current_ext = file_path.suffix.lower()
            if current_ext != true_ext:
                repaired_path = file_path.with_suffix(true_ext)
                self.repaired_extensions.append(
                    f"{file_path.name} -> {repaired_path.name}"
                )
                self.quarantine_mgr.save_valid_file(file_path, repaired_path)
                stats["repaired_extensions"] += 1
            else:
                self.quarantine_mgr.save_valid_file(file_path)
                stats["clean_saved"] += 1

        # Generate output reports (JSON + Markdown) inside output folder
        self.reporter.generate_report(
            stats, self.removed_duplicates, self.repaired_extensions
        )

        return stats


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
    print(f"  Clean Files Kept: {results['clean_saved']}")
    print(f"Cleaned dataset output saved to: '{args.clean}'")
    print("==================================================")