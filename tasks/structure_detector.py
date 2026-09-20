import csv
import json
import io
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Union


class StructureCorruptionDetector:
    """Validates file structural integrity based on target file extensions."""

    SUPPORTED_EXTENSIONS = {".json", ".xml", ".csv"}

    def detect_structure_corruption(
        self, file_path: Union[str, Path], extension: str
    ) -> Dict[str, Any]:
        """Parses the file with the appropriate format parser and returns detection results."""
        path = Path(file_path)

        # Ensure validation extension aligns with actual file extension
        actual_ext = path.suffix.lower()
        ext = extension.lower()

        if ext not in self.SUPPORTED_EXTENSIONS or actual_ext != ext:
            return {
                "is_corrupted": False,
                "error_message": f"Unsupported or mismatched extension: actual '{actual_ext}', requested '{ext}'",
            }

        try:
            if ext == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        raise ValueError("Empty JSON file")

                    # Handle single JSON object/array or NDJSON / concatenated JSON objects
                    try:
                        json.loads(content)
                    except json.JSONDecodeError:
                        # Fallback check for JSON Lines / concatenated stream
                        decoder = json.JSONDecoder()
                        pos = 0
                        length = len(content)
                        while pos < length:
                            # Strip leading whitespaces between documents
                            while pos < length and content[pos].isspace():
                                pos += 1
                            if pos >= length:
                                break
                            _, pos = decoder.raw_decode(content, pos)

            elif ext == ".xml":
                ET.parse(path)

            elif ext == ".csv":
                with open(path, "rb") as f:
                    raw = f.read()
                
                # Strip NUL bytes to prevent reader errors on raw streams
                cleaned_text = raw.replace(b"\x00", b"").decode("utf-8", errors="replace")
                
                reader = csv.reader(io.StringIO(cleaned_text))
                rows = [row for row in reader if row]  # Ignore empty lines
                if not rows:
                    raise ValueError("Empty CSV file")

                # Exclude potential footer/summary rows from rigid width checks
                data_rows = rows[:-1] if len(rows) > 1 else rows
                expected_cols = len(data_rows[0])

                for i, row in enumerate(data_rows, start=1):
                    if len(row) != expected_cols:
                        raise ValueError(
                            f"Row {i} has inconsistent column count (expected {expected_cols}, got {len(row)})"
                        )

            return {
                "is_corrupted": False,
                "error_message": None,
            }

        except Exception as e:
            return {
                "is_corrupted": True,
                "error_message": str(e),
            }