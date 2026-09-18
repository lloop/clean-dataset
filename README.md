# Shampoo and Conditioner

Do your files have split ends? At root level, are you plagued with zero byte dandruff? Than Shampoo and Conditioner is for you!

A Python pipeline for evaluating a deliberately messy, multi-format dataset. It identifies duplicate files, detects common file corruptions, repairs misleading file extensions when the content can be classified, copies valid files into an organized output directory, and records an audit trail of the run.

## What It Checks

The pipeline tests four data-quality problems:

1. **Exact duplicates** - Computes a SHA-256 hash for each file and quarantines any later file with content identical to a file already seen.
2. **Character corruption** - For text files, detects null-byte injection, Unicode replacement characters (`U+FFFD`), and common mojibake signatures such as `Ã` and `â€™`.
3. **Structural corruption** - Validates JSON with a JSON parser, XML with an XML parser, and CSV files by checking that every row has the same number of columns. Files that fail parsing or validation are quarantined.
4. **Incorrect or scrambled extensions** - Compares the filename extension with the detected file type. When the content has a different, recognizable type, the file is copied to the valid output with the corrected extension.

The pipeline processes files in this order: duplicate detection, file-type detection, character checks, structural checks, then extension repair or delivery to the valid dataset. It copies files rather than modifying the originals in `dataset_dirty`.

## Requirements

- Python 3.10 or newer
- `python-magic` and the system `libmagic` library
- `beautifulsoup4`
- `html5lib`
- `defusedxml`
- `magika`
- `orjson`
- `polars`

The file named `requirements.yxy` currently does not contain all imports required by the pipeline and is not named as a standard pip requirements file. Install the dependencies in your environment with:

```bash
python -m pip install python-magic beautifulsoup4 html5lib defusedxml magika orjson polars
```

On Debian or Ubuntu, `python-magic` may also require:

```bash
sudo apt-get install libmagic1
```

## Running the Cleaner

With the included sample dataset:

```bash
python3 main.py
```

By default, the script reads from `dataset_dirty/` and recreates `dataset_clean/` on every run. Custom directories can be supplied with the command-line options:

```bash
python3 main.py --source path/to/input --clean path/to/output
```

The command prints counts for evaluated files, duplicates, repaired extensions, character corruptions, structural corruptions, quarantined files, and valid files retained.

## Output Layout

Each run recreates the selected output directory with this structure:

```text
dataset_clean/
├── valid/
│   ├── csv/
│   ├── html/
│   ├── json/
│   ├── jpg/
│   ├── py/
│   ├── txt/
│   └── ...
├── quarantine/
│   ├── duplicates/
│   ├── corrupted_character/
│   └── corrupted_structure/
├── audit_summary.json
└── audit_summary.md
```

- `valid/` contains clean files grouped by their final extension.
- `quarantine/duplicates/` contains exact duplicate copies.
- `quarantine/corrupted_character/` contains files rejected by the character-corruption detector.
- `quarantine/corrupted_structure/` contains files rejected by format validation.
- `audit_summary.json` contains timestamped metrics and filename-level lists of duplicates, extension repairs, character corruptions, and structural corruptions.
- `audit_summary.md` provides a human-readable version of the audit.

## Libraries Used

The project combines Python's standard library with focused file-analysis libraries:

- **`hashlib`** - SHA-256 content hashing for exact duplicate detection.
- **`magika`** - Content-based file classification with a confidence score.
- **`python-magic` / `libmagic`** - MIME and magic-byte inspection.
- **`orjson`** - Fast JSON content validation and type detection.
- **`defusedxml`** - Safer XML parsing for type detection; `xml.etree.ElementTree` validates XML structure.
- **`BeautifulSoup` with `html5lib`** - HTML detection and parsing.
- **`polars`** - CSV schema/content detection.
- **Python `csv` module** - CSV row-width validation.
- **`argparse`, `pathlib`, `shutil`, and `json`** - CLI arguments, paths, file copying, and audit report serialization.

## Project Structure

```text
main.py                    # Pipeline entry point and CLI
tasks/
├── character_detector.py  # Text corruption signatures
├── deduplicator.py        # SHA-256 duplicate detection
├── extension_detector.py  # Content-based extension detection
├── quarantine.py           # Valid-file and quarantine routing
├── reporter.py             # JSON and Markdown audit reports
└── structure_detector.py  # Format integrity validation
schemas/
└── audit_schema.py         # Audit record data classes
dataset_dirty/              # Input files
dataset_clean/              # Recreated output directory
```

## Notes

- The source dataset is never edited; files are copied into the output or quarantine locations.
- A failed character or structural check takes precedence over extension repair, so rejected files are not placed in `valid/`.
- The pipeline skips directories and a top-level `manifest.json` during its main processing pass.
