import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


class StructureCorruptionDetector:
    """Validates file structural integrity based on target file extensions."""

    def is_structurally_corrupt(self, file_path: Path, extension: str) -> Optional[str]:
        """Parses the file with the appropriate format parser.

        Returns an error message string if parsing fails or structure is invalid,
        otherwise returns None.
        """
        ext = extension.lower()
        try:
            if ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
            elif ext == ".xml":
                with open(file_path, "r", encoding="utf-8") as f:
                    ET.fromstring(f.read())
            elif ext == ".csv":
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if rows:
                        expected_cols = len(rows[0])
                        for row in rows:
                            if len(row) != expected_cols:
                                raise ValueError(
                                    f"Inconsistent column count (expected {expected_cols}, got {len(row)})"
                                )
            return None
        except Exception as e:
            return str(e)