"""Check Uniqueness.

Tests for collisions among files expected to be unique.
"""

import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

output_dir = Path("dataset_dirty")
manifest_path = output_dir / "metadata" / "manifest.json"

with open(manifest_path, "r") as f:
    data = json.load(f)
    records = data if isinstance(data, list) else data.get("files", [])

# Map filenames to records using any available path/filename property
manifest = {}
for r in records:
    # Check all common field names used for the file path
    raw_path = r.get("final_filename") or r.get("file_path") or r.get("path") or r.get("filename") or ""
    filename = os.path.basename(raw_path)
    if filename:
        manifest[filename] = r

# Group non-duplicate ("unique") generations by hash
unique_hashes = defaultdict(list)
dup_count = 0

for p in output_dir.iterdir():
    if p.is_file() and p.name != "manifest.json":
        meta = manifest.get(p.name, {})

        # Cast string booleans ("true"/"False") or explicit booleans cleanly
        is_dup = str(meta.get("is_duplicate", False)).lower() == "true"

        if is_dup:
            dup_count += 1
            continue

        # Hash files expected to be unique
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        unique_hashes[h].append(p.name)

# Check for collisions among files meant to be unique
accidental_collisions = {
    h: files for h, files in unique_hashes.items() if len(files) > 1
}

if accidental_collisions:
    for h, files in accidental_collisions.items():
        print(f"\nCollision on hash {h[:8]}:")
        for f in files:
            print(f"  - {f}")
else:
    print("\nSUCCESS: 0 hash collisions across all unique generations!")

print(f"Logged Intentional Duplicates Skipped: {dup_count}")
print(f"Accidental Collisions Among Primary Files: {len(accidental_collisions)}")