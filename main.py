import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Set


class DatasetCleaner:
    """Evaluates and cleans synthetic dirty datasets by resolving binary duplicates,

    repairing file extensions, and segregating valid records.
    """

    def __init__(self, source_dir: str, clean_dir: str):
        self.source_dir = Path(source_dir)
        self.clean_dir = Path(clean_dir)
        self.seen_hashes: Set[str] = set()
        self.removed_duplicates: List[str] = []
        self.repaired_extensions: List[str] = []

    def _compute_hash(self, file_path: Path) -> str:
        """Computes SHA-256 hash of a file for exact duplicate detection."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def process(self) -> Dict[str, int]:
        """Executes deduplication and directory cleanup."""
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory '{self.source_dir}' does not exist.")

        # Recreate clean target directory
        if self.clean_dir.exists():
            shutil.rmtree(self.clean_dir)
        self.clean_dir.mkdir(parents=True)

        stats = {"total_processed": 0, "duplicates_removed": 0, "clean_saved": 0}

        for file_path in self.source_dir.iterdir():
            # Skip directories or manifest file during deduplication pass
            if file_path.is_dir() or file_path.name == "manifest.json":
                continue

            stats["total_processed"] += 1

            # 1. Deduplication via Hash Matching
            file_hash = self._compute_hash(file_path)
            if file_hash in self.seen_hashes:
                self.removed_duplicates.append(file_path.name)
                stats["duplicates_removed"] += 1
                continue

            self.seen_hashes.add(file_hash)

            # 2. Extension Normalization
            ext = file_path.suffix.lower()
            target_subfolder = self.clean_dir / (ext.replace(".", "") if ext else "no_extension")
            target_subfolder.mkdir(exist_ok=True)

            dest_path = target_subfolder / file_path.name
            shutil.copyfile(file_path, dest_path)
            stats["clean_saved"] += 1

        return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", default="output", help="Directory containing dirty files")
    parser.add_argument("-c", "--clean", default="cleaned_output", help="Target directory for cleaned dataset")

    args = parser.parse_args()

    cleaner = DatasetCleaner(source_dir=args.source, clean_dir=args.clean)
    results = cleaner.process()

    print("==================================================")
    print(f"Data Cleaning Pass Complete:")
    print(f"  Total Evaluated : {results['total_processed']}")
    print(f"  Duplicates Cut  : {results['duplicates_removed']}")
    print(f"  Clean Files Kept: {results['clean_saved']}")
    print(f"Cleaned dataset output saved to: '{args.clean}'")
    print("==================================================")