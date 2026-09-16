# tasks/quarantine.py
import shutil
from pathlib import Path
from typing import Optional


class QuarantineManager:
    """Manages routing of clean, duplicate, and corrupted files into separate directory hierarchies."""

    # I might want to stop quarentining corrupted files in the future
    # Because the files could have multiple problems and I don't know how to resolve which 
    # folder they would go in to.
    def __init__(self, clean_dir: Path):
        self.clean_dir = clean_dir
        self.valid_dir = self.clean_dir / "valid"
        self.quarantine_dir = self.clean_dir / "quarantine"
        self.duplicates_dir = self.quarantine_dir / "duplicates"
        self.corrupt_struct_dir = self.quarantine_dir / "corrupted_structure"
        self.corrupt_char_dir = self.quarantine_dir / "corrupted_character"

    def setup_directories(self) -> None:
        """Recreates output directory layout."""
        if self.clean_dir.exists():
            shutil.rmtree(self.clean_dir)
            
        self.valid_dir.mkdir(parents=True, exist_ok=True)
        self.duplicates_dir.mkdir(parents=True, exist_ok=True)
        self.corrupt_struct_dir.mkdir(parents=True, exist_ok=True)
        self.corrupt_char_dir.mkdir(parents=True, exist_ok=True)


    def save_valid_file(self, file_path: Path, target_path: Optional[Path] = None) -> Path:
        """Copies valid files into subfolders grouped by file extension."""
        final_path = target_path or file_path
        ext = final_path.suffix.lower().replace(".", "") or "no_extension"
        target_folder = self.valid_dir / ext
        target_folder.mkdir(exist_ok=True)
        dest_path = target_folder / final_path.name
        shutil.copyfile(file_path, dest_path)
        return dest_path

    def quarantine_duplicate(self, file_path: Path) -> Path:
        """Copies duplicate files into the quarantine/duplicates directory."""
        dest_path = self.duplicates_dir / file_path.name
        shutil.copyfile(file_path, dest_path)
        return dest_path

    def quarantine_corrupt_struct(self, file_path: Path, reason: str = "unknown") -> Path:
        """Copies corrupted files into quarantine/corrupted_structure grouped by failure reason."""
        target_folder = self.corrupt_struct_dir / reason
        target_folder.mkdir(exist_ok=True)

        dest_path = target_folder / file_path.name
        shutil.copyfile(file_path, dest_path)
        return dest_path
    
    def quarantine_corrupt_char(self, file_path: Path, reason: str = "unknown") -> Path:
        """Copies corrupted files into quarantine/corrupted_character grouped by failure reason."""
        target_folder = self.corrupt_char_dir / reason
        target_folder.mkdir(exist_ok=True)

        dest_path = target_folder / file_path.name
        shutil.copyfile(file_path, dest_path)
        return dest_path