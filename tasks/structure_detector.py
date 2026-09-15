import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path


class StructureCorruptionDetector:
    """Validates file structural integrity based on target file extensions."""

    def is_structurally_corrupt(self, file_path: Path, extension: str) -> bool:
        """Parses the file with the appropriate format parser.

        Returns True if parsing fails or invalid structure is detected.
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
                                return True
            return False
        except Exception:
            return True