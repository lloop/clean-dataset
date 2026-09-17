import hashlib
from pathlib import Path
from typing import Set, Dict


class FileDeduplicator:
    """Manages SHA-256 exact binary duplicate detection."""

    def __init__(self):
        # hash -> filename
        self.seen_hashes: Dict[str, str] = {}

    def is_duplicate(self, file_path: Path) -> str | None:
        # Ignore 0-byte files if they shouldn't be counted as binary duplicates
        if file_path.stat().st_size == 0:
            return None

        file_hash = self._compute_hash(file_path)
        if not file_hash:
            return None

        if file_hash in self.seen_hashes:
            return self.seen_hashes[file_hash]

        self.seen_hashes[file_hash] = file_path.name
        return None

    def _compute_hash(self, file_path: Path) -> str:
        """Computes SHA-256 hash of a file for exact duplicate detection."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()