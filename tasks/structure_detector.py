import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Union


class StructureCorruptionDetector:
    """Validates file structural integrity based on target file extensions."""

    SUPPORTED_EXTENSIONS = {".json", ".xml", ".csv"}

    # TODO what the fuck is this extension filter about?
    def detect_structure_corruption(
        self, file_path: Union[str, Path], extension: str
    ) -> Dict[str, Any]:
        """Parses the file with the appropriate format parser and returns detection results."""
        path = Path(file_path)
        ext = extension.lower()

        if ext not in self.SUPPORTED_EXTENSIONS:
            return {
                "is_corrupted": False,
                "error_message": f"Unsupported extension for structural validation: {ext}",
            }

        try:
            if ext == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)

            elif ext == ".xml":
                ET.parse(path)

            elif ext == ".csv":
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if not rows:
                        raise ValueError("Empty CSV file")

                    expected_cols = len(rows[0])
                    for i, row in enumerate(rows, start=1):
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