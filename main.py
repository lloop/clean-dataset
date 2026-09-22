import argparse
import shutil
import hashlib
from pathlib import Path

from schemas.audit_schema import PipelineAuditSummary
from tasks.character_detector import CharacterCorruptionDetector
from tasks.structure_detector import StructureCorruptionDetector
from tasks.duplicate_detector import FileDeduplicator
from tasks.extension_detector import ExtensionDetector
from tasks.quarantine import QuarantineManager
from tasks.reporter import AuditReporter
from tasks.manifest_loader import ManifestLoader
from schemas.file_schema import FileRecords
from tasks.format_handlers.registry import FormatHandlerRegistry

from magika import Magika

DIRTY_DIR = Path("dataset_dirty")
FILES_DIR = Path("dataset_dirty/files")
MANIFEST_DIR = Path("dataset_dirty/metadata")
CLEAN_DIR = Path("dataset_clean")


class DatasetCleaner:
    """Evaluates and cleans synthetic dirty datasets by resolving binary duplicates,
    detecting character/structural corruptions, repairing file extensions, and segregating valid records.
    """

    def __init__(self, source_dir: str, clean_dir: str):
        self.source_dir = Path(source_dir)
        self.file_source_dir = self.source_dir / "files"
        self.clean_dir = Path(clean_dir)

        self.audit_summary = PipelineAuditSummary()
        self.quarantine_mgr = QuarantineManager(self.clean_dir)
        self.reporter = AuditReporter(self.clean_dir)
        self.manifest_loader = ManifestLoader(str(self.source_dir / "metadata" / "manifest.json"))
        self.deduplicator = FileDeduplicator()
        self.extension_detector = ExtensionDetector()
        self.character_detector = CharacterCorruptionDetector()
        self.structure_detector = StructureCorruptionDetector()
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
        self.quarantine_mgr.setup_directories()

        for file_path in self.file_source_dir.iterdir():
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

            if len(content) == 0:
                true_ext = current_ext
            else:
                true_ext = self.format_handler_registry.detect_extension(
                    content,
                    current_ext,
                )  
                
            # # ------------------
            # if file_path.name == "presentation.txt":
            #     print(f"DEBUG PRESENTATION: declared={current_ext} detected={true_ext}")  
            # # ------------------     
            
            record.is_binary = true_ext in [".jpg", ".jpeg", ".png", ".gif", ".ico"]

            # Deduplication via Hash Matching
            matched_file, file_hash = self.deduplicator.is_duplicate(file_path)
            record.file_hash = file_hash
            if matched_file:
                record.duplicate = True
                record.matched_file = matched_file
            
            if not record.is_binary:
                # Character Corruption Pass
                try:
                    with open(file_path, "rb") as f:
                        content = f.read()
                        
                    # Temp (until all handlers are active)
                    # char_result = self.character_detector.detect_character_corruption(content)
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
                    
                    # self.quarantine_mgr.quarantine_corrupt_char(file_path, reason="read_error")
                    
                    continue
                    
            # Structural Corruption Pass
            try:
                struct_result = self.structure_detector.detect_structure_corruption(file_path, true_ext)
                
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
            
        self.audit_summary.build_summary()
                
        manifest = self.manifest_loader.load()
        
        # Generate output reports inside output folder
        self.reporter.generate_report(
            self.audit_summary, 
            manifest
        )
        
        # # Temporary
        # from dataclasses import asdict
        # import json
        # print(json.dumps(
        #     [asdict(record) for record in self.audit_summary.file_records[:3]],
        #     indent=4
        # ))

        return self.audit_summary

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    
    # These are not in effect yet
    parser.add_argument(
        "-dg", 
        "--diagnostic",
        action="store_true",
        help="Files are not deleted or copied",
    )  
    
    # These are not in effect yet
    parser.add_argument(
        "-db",
        "--debug",
        action="store_true",
        help="work in tandem with dirty file generator",
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