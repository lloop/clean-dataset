# tasks/quarantine.py
import shutil
from pathlib import Path


class QuarantineManager:
    """Manages routing of clean, duplicate, and corrupted files into separate directory hierarchies."""

    def __init__(self, clean_dir: Path):
        self.clean_dir = clean_dir
        self.valid_dir = self.clean_dir / "valid"
        self.quarantine_dir = self.clean_dir / "quarantine"
        self.duplicates_dir = self.quarantine_dir / "duplicates"
        self.corrupt_dir = self.quarantine_dir / "corrupted"

    def setup_directories(self) -> None:
        """Recreates output directory layout."""
        if self.clean_dir.exists():
            shutil.rmtree(self.clean_dir)
            
        self.valid_dir.mkdir(parents=True, exist_ok=True)
        self.duplicates_dir.mkdir(parents=True, exist_ok=True)
        self.corrupt_dir.mkdir(parents=True, exist_ok=True)

    def save_valid_file(self, file_path: Path, target_path: Path | None = None) -> Path:
        """Copies valid files into subfolders grouped by file extension."""
        ext = file_path.suffix.lower().replace(".", "") or "no_extension"
        target_folder = self.valid_dir / ext
        target_folder.mkdir(exist_ok=True)
        file_name = target_path.name if target_path else file_path.name
        dest_path = target_folder / file_name
        shutil.copyfile(file_path, dest_path)
        return dest_path

    def quarantine_duplicate(self, file_path: Path) -> Path:
        """Copies duplicate files into the quarantine/duplicates directory."""
        dest_path = self.duplicates_dir / file_path.name
        shutil.copyfile(file_path, dest_path)
        return dest_path

    def quarantine_corrupt(self, file_path: Path, reason: str = "unknown") -> Path:
        """Copies corrupted files into quarantine/corrupted grouped by failure reason."""
        target_folder = self.corrupt_dir / reason
        target_folder.mkdir(exist_ok=True)

        dest_path = target_folder / file_path.name
        shutil.copyfile(file_path, dest_path)
        return dest_path