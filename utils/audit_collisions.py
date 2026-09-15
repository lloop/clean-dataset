"""Audit Collision

Finds files that are binary duplicates (matching SHA-256) but are

marked as `is_duplicate: False` in the manifest.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List


def audit_unintended_collisions(output_dir: str = "output") -> List[Dict]:
    """Finds files that are binary duplicates (matching SHA-256) but are

    marked as `is_duplicate: False` in the manifest.
    """
    out_path = Path(output_dir)
    manifest_path = out_path / "metadata" / "manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at '{manifest_path}'")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Map filename -> manifest entry for quick lookup
    manifest_map = {entry["filename"]: entry for entry in manifest_data["files"]}

    seen_hashes: Dict[str, str] = {}
    unintended_collisions = []

    for file_path in out_path.iterdir():
        if file_path.is_dir() or file_path.name == "manifest.json":
            continue

        filename = file_path.name

        # Calculate SHA-256
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()

        # Check for binary hash collision
        if file_hash in seen_hashes:
            original_filename = seen_hashes[file_hash]
            manifest_entry = manifest_map.get(filename, {})

            # Flag if the file is a binary duplicate but manifest registered it as non-duplicate
            if not manifest_entry.get("is_duplicate", False):
                unintended_collisions.append(
                    {
                        "filename": filename,
                        "collided_with": original_filename,
                        "extension": manifest_entry.get("extension", file_path.suffix),
                        "source_template": manifest_entry.get("source_template", "unknown"),
                        "mutation_label": manifest_entry.get("mutation_label", "none"),
                        "file_path": str(file_path),
                    }
                )
        else:
            seen_hashes[file_hash] = filename

    return unintended_collisions


if __name__ == "__main__":
    collisions = audit_unintended_collisions(output_dir="dataset_dirty")

    print(f"==================================================")
    print(f"Unintended Collisions Found: {len(collisions)}")
    print(f"==================================================")

    for item in collisions:
        print(f"File         : {item['filename']}")
        print(f"Matches Content Of : {item['collided_with']}")
        print(f"Mutation Applied   : {item['mutation_label']}")
        print("-" * 50)
        
        



