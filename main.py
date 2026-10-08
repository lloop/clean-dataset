import argparse
import shutil
import hashlib
from dataclasses import asdict
from pathlib import Path

from magika import Magika
from schemas.audit_schema import PipelineAuditSummary
from tasks.character_detector import CharacterCorruptionDetector
from tasks.duplicate_detector import FileDeduplicator
from tasks.quarantine import QuarantineManager
from tasks.reporter import AuditReporter
from tasks.manifest_loader import ManifestLoader
from schemas.file_schema import FileRecords
from tasks.format_handlers.registry import FormatHandlerRegistry

DIRTY_DIR = Path("dataset_dirty")
FILES_DIR = Path("dataset_dirty/files")
MANIFEST_DIR = Path("dataset_dirty/metadata")
CLEAN_DIR = Path("dataset_clean")


class DatasetCleaner:
    """Evaluates and cleans synthetic dirty datasets by resolving binary duplicates,
    detecting character/structural corruptions, repairing file extensions, and segregating valid records.
    """

    def __init__(
        self,
        source_dir: str,
        clean_dir: str,
        debug: bool = False,
        diagnostic: bool = False,
    ):
        self.debug = debug
        self.diagnostic = diagnostic
        self.source_dir = Path(source_dir)
        # self.file_source_dir = self.source_dir / "files"
        self.clean_dir = Path(clean_dir)

        self.audit_summary = PipelineAuditSummary()
        self.quarantine_mgr = QuarantineManager(self.clean_dir)
        self.reporter = AuditReporter(self.clean_dir)
        self.manifest_loader = ManifestLoader(str(self.source_dir / "metadata" / "manifest.json"))
        self.deduplicator = FileDeduplicator()
        self.character_detector = CharacterCorruptionDetector()
        self.format_handler_registry = FormatHandlerRegistry()

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
        if not self.diagnostic:
            self.quarantine_mgr.setup_quarantine_directories()
        
        quarantine_records = []

        for file_path in self.source_dir.iterdir():
            # Skip directories or manifest file during deduplication pass
            if file_path.is_dir() or file_path.name == "manifest.json":
                continue 
            
            # Initialize audit record
            record = FileRecords(
                filename=file_path.name
            )
            
            # Detect binary files
            current_ext = file_path.suffix.lower()
            with open(file_path, "rb") as f:
                content = f.read()
                
            # High-Confidence Magika Classifier
            magika_result = Magika().identify_bytes(content)
            record.magika_result = magika_result

            # Extension Detection
            if len(content) == 0:
                true_ext = current_ext
            else:
                true_ext = self.format_handler_registry.detect_extension(
                    content,
                    current_ext,
                    record.magika_result,
                )  
                
            # Temporary Debugging
            print(file_path.name, current_ext, "=>", true_ext)
            
            record.is_binary = true_ext in [".jpg", ".jpeg", ".png", ".gif", ".ico"]

            # Deduplication via Hash Matching
            matched_file, file_hash = self.deduplicator.is_duplicate(file_path)
            record.file_hash = file_hash
            if matched_file:
                record.duplicate = True
                record.matched_file = matched_file
            
            try:
                if not record.is_binary:
                    # Character Corruption Pass
                    handler = self.format_handler_registry.get_handler(true_ext)
                    
                    if handler:
                        char_result = handler.detect_character_corruption(content)
                    else:
                        char_result = self.character_detector.detect_character_corruption(content)

                    if char_result["is_corrupted"]:
                        record.character_corruption.extend(
                            char_result["detected_corruptions"]
                        )

            except OSError as error:
                print(f"ERROR reading {file_path}: {error}")
                                
                continue
                
            # Structural Corruption Pass
            try:
                if len(content) == 0:
                    record.structural_corruption.append("Empty file")
                else:
                    handler = self.format_handler_registry.get_handler(true_ext)

                    if handler:
                        struct_result = handler.detect_structure_corruption(content)
                    else:
                        struct_result = {
                            "is_corrupted": False,
                            "error_message": None,
                        }

                    if struct_result["is_corrupted"]:
                        record.structural_corruption.append(
                            struct_result["error_message"]
                        )

            except OSError as error:
                print(f"ERROR reading {file_path}: {error}")
                continue

            # Extension Detection
            # The extension detection function is used in the begining 
            # of the loop to detect binary files
            current_ext = file_path.suffix.lower()
            if current_ext != true_ext:
                record.actual_extension = true_ext
                record.extension_mismatch = True
                
            self.audit_summary.file_records.append(record)
            
            has_findings = (
                record.duplicate
                or bool(record.character_corruption)
                or bool(record.structural_corruption)
                or record.extension_mismatch
            )

            if has_findings:
                if not self.diagnostic:
                    self.quarantine_mgr.quarantine_file(file_path)
                quarantine_records.append(asdict(record))
            else:
                if not self.diagnostic:
                    self.quarantine_mgr.save_valid_file(
                        file_path,
                        target_path=file_path,
                    )
            
        if not self.diagnostic:
            self.quarantine_mgr.save_quarantine_manifest(quarantine_records)
            
        self.audit_summary.build_summary()
                
        manifest = self.manifest_loader.load() if not self.debug else None
        
        # Generate output reports inside output folder
        self.reporter.generate_report(
            self.audit_summary, 
            manifest
        ) 

        return self.audit_summary


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    
    # 
    parser.add_argument(
        "-d", 
        "--diagnostic",
        action="store_true",
        help="Files are not deleted, copied, or quarantined",
    )  
    
    parser.add_argument(
        "-b",
        "--debug",
        action="store_false",
        help="Work in tandem with dirty file generator",
    )
    
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

    cleaner = DatasetCleaner(
        source_dir=args.source,
        clean_dir=args.clean,
        diagnostic=args.diagnostic,
        debug=args.debug,
    )
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