import json

with open("dataset_dirty/metadata/manifest.json", "r") as f:
    data = json.load(f)

files = data.get("files", [])

# Total records with character_corruption_label set
raw_corrupted = [
    r for r in files 
    if r.get("character_corruption_label") not in (None, "none", "")
]

# Check for duplicate filenames in manifest
filenames = [r["filename"] for r in raw_corrupted if "filename" in r]
unique_filenames = set(filenames)

# Check for zero-byte files
zero_byte_corrupted = [r for r in raw_corrupted if r.get("size_bytes", 0) == 0]

print(f"Raw corrupted count in manifest array: {len(raw_corrupted)}")
print(f"Unique filenames among corrupted:     {len(unique_filenames)} (Lost to key collision: {len(raw_corrupted) - len(unique_filenames)})")
print(f"Zero-byte corrupted files:             {len(zero_byte_corrupted)}")