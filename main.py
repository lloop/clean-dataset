import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, List, Set

import magic
from bs4 import BeautifulSoup
import defusedxml.ElementTree as SafeET
from magika import Magika
import orjson
import polars as pl

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
        self.seen_hashes: Set[str] = set()
        self.removed_duplicates: List[str] = []
        self.repaired_extensions: List[str] = []
        self.quarantine_mgr = QuarantineManager(self.clean_dir)
        self.reporter = AuditReporter(self.clean_dir)
        self.magika = Magika()
        self.mime_engine = magic.Magic(mime=True)

    def _normalize_magika_label(self, label: str) -> str:
        if not label:
            return "unknown"
        label = label.lower().strip()
        label_map = {
            "python": ".py",
            "jpeg": ".jpg",
            "text": ".txt",
            "javascript": ".js",
        }
        mapped = label_map.get(label, label)
        return mapped if mapped.startswith(".") else f".{mapped}"

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
            file_hash = self._compute_hash(file_path)
            if file_hash in self.seen_hashes:
                self.removed_duplicates.append(file_path.name)
                self.quarantine_mgr.quarantine_duplicate(file_path)
                stats["duplicates_removed"] += 1
                continue
            self.seen_hashes.add(file_hash)

            # Extension Repair Check
            true_ext = self._detect_true_extension(file_path)
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

    def _detect_true_extension(self, file_path: Path) -> str:
        current_ext = file_path.suffix.lower()

        # ------------------------------------------------------------------
        # Phase 1: High-Confidence Magika Classifier
        # ------------------------------------------------------------------
        try:
            res = self.magika.identify_path(file_path)
            if res.score >= 0.75:
                detected_ext = self._normalize_magika_label(res.output.label)
                aliases = {".jpeg": ".jpg", ".htm": ".html", ".text": ".txt"}
                norm_current = aliases.get(current_ext, current_ext)
                norm_detected = aliases.get(detected_ext, detected_ext)

                if norm_detected != norm_current:
                    return norm_detected
                return current_ext
        except Exception:
            pass

        # ------------------------------------------------------------------
        # Phase 2: C-Engine Magic Byte Inspection (python-magic / libmagic)
        # ------------------------------------------------------------------
        try:
            mime_type = self.mime_engine.from_file(str(file_path))
            direct_mime_map = {
                "application/json": ".json",
                "text/xml": ".xml",
                "application/xml": ".xml",
                "text/html": ".html",
                "image/jpeg": ".jpg",
                "image/png": ".png",
            }
            if mime_type in direct_mime_map:
                return direct_mime_map[mime_type]

            # Binary extension claims plain text
            if mime_type == "text/plain" and current_ext in {
                ".jpg",
                ".jpeg",
                ".png",
                ".pdf",
                ".zip",
                ".exe",
            }:
                pass
            elif mime_type != "text/plain":
                return current_ext
        except Exception:
            pass

        # ------------------------------------------------------------------
        # Phase 3: Text Schema Spec Parsers
        # ------------------------------------------------------------------
        return self._validate_text_schema(file_path, current_ext)

    def _validate_text_schema(self, file_path: Path, current_ext: str) -> str:
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read(32768)
        except Exception:
            return current_ext

        if not raw_bytes.strip():
            return current_ext

        # 1. JSON (orjson)
        try:
            orjson.loads(raw_bytes)
            return ".json"
        except Exception:
            pass

        try:
            text_content = raw_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            return current_ext

        # 2. XML (defusedxml)
        if text_content.startswith("<") and not text_content.startswith("<!--"):
            try:
                SafeET.fromstring(text_content)
                return ".xml"
            except Exception:
                pass

        # 3. HTML (BeautifulSoup + html5lib)
        if any(
            tag in text_content.lower()
            for tag in ("<html", "<body", "<!--", "<div")
        ):
            try:
                soup = BeautifulSoup(text_content, "html5lib")
                if soup.html and len(soup.find_all()) > 0:
                    return ".html"
            except Exception:
                pass

        # 4. Tabular CSV (Polars)
        try:
            df = pl.read_csv(
                file_path,
                n_rows=20,
                has_header=True,
                ignore_errors=False,
                raise_if_empty=True,
            )
            if df.width > 1 and df.height > 0:
                return ".csv"
        except Exception:
            pass

        return ".txt"


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