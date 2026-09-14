import hashlib
from pathlib import Path
from typing import Set


class FileDeduplicator:
    """Manages SHA-256 exact binary duplicate detection."""

    def __init__(self):
        self.seen_hashes: Set[str] = set()

    def is_duplicate(self, file_path: Path) -> bool:
        """Computes hash and returns True if file has already been seen."""
        file_hash = self._compute_hash(file_path)
        if file_hash in self.seen_hashes:
            return True
        self.seen_hashes.add(file_hash)
        return False

    def _compute_hash(self, file_path: Path) -> str:
        """Computes SHA-256 hash of a file for exact duplicate detection."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()