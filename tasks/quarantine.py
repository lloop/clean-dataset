import json
import shutil
from pathlib import Path
from typing import Optional


class QuarantineManager:
    """Manages valid files and quarantined files."""

    def __init__(self, clean_dir: Path):
        self.clean_dir = clean_dir
        self.valid_dir = self.clean_dir / "valid"
        self.quarantine_dir = self.clean_dir / "quarantine"
        self.quarantine_files_dir = self.quarantine_dir / "files"
        self.quarantine_manifest = (
            self.quarantine_dir / "quarantine_manifest.json"
        )

    def setup_quarantine_directories(self) -> None:
        """Recreates the output directory layout."""
        if self.clean_dir.exists():
            shutil.rmtree(self.clean_dir)

        self.valid_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_files_dir.mkdir(parents=True, exist_ok=True)

    def save_valid_file(
        self,
        file_path: Path,
        target_path: Optional[Path] = None,
    ) -> Path:
        """Copies a valid file into a folder grouped by file extension."""
        final_path = target_path or file_path

        ext = final_path.suffix.lower().replace(".", "") or "no_extension"
        target_folder = self.valid_dir / ext
        target_folder.mkdir(parents=True, exist_ok=True)

        dest_path = target_folder / final_path.name
        shutil.copyfile(file_path, dest_path)

        return dest_path

    def quarantine_file(self, file_path: Path) -> Path:
        """Copies a file into the single quarantine files directory."""
        dest_path = self.quarantine_files_dir / file_path.name
        shutil.copyfile(file_path, dest_path)

        return dest_path

    def save_quarantine_manifest(self, records: list[dict]) -> Path:
        """Writes the quarantine manifest."""
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        with open(
            self.quarantine_manifest,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                {"files": records},
                f,
                indent=2,
            )

        return self.quarantine_manifest