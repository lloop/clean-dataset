import csv
import io
from magika import Magika

class CSVHandler:
    
    def __init__(self):
        self.magika = Magika()

    def detect_character_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="surrogateescape")
        else:
            text = content

        detected_types = []

        if self.has_null_bytes(text):
            detected_types.append("null_byte_injection")

        if self.has_unicode_replacement_char(text):
            detected_types.append("unicode_replacement_char")

        try:
            rows = list(csv.reader(io.StringIO(text)))

            if self.contains_mojibake(rows):
                detected_types.append("mojibake")

        except csv.Error:
            pass

        return {
            "is_corrupted": len(detected_types) > 0,
            "detected_corruptions": detected_types,
        }

    def has_null_bytes(self, text: str) -> bool:
        return "\x00" in text

    def has_unicode_replacement_char(self, text: str) -> bool:
        return "\ufffd" in text

    def contains_mojibake(self, rows: list[list[str]]) -> bool:
        return any(
            self.has_mojibake(cell)
            for row in rows
            for cell in row
        )

    def has_mojibake(self, text: str) -> bool:
        mojibake_signatures = [
            "Ã",
            "Â",
            "â€™",
            "â€œ",
            "â€",
            "Ã©",
            "Ã¨",
            "Ã±",
            "â€”",
            "Ã§",
            "Ã\xa0",
            "Ã¢",
        ]

        return any(
            signature in text
            for signature in mojibake_signatures
        )
        
    def detect_extension(
        self,
        content: str | bytes,
    ) -> bool:
        if isinstance(content, bytes):
            raw_bytes = content
        else:
            raw_bytes = content.encode("utf-8")

        try:
            result = self.magika.identify_bytes(raw_bytes)

            if (
                result.output.label.lower() == "csv"
                and result.score >= 0.75
            ):
                return self.has_strong_csv_evidence(raw_bytes)

        except Exception:
            pass

        return False

    def has_strong_csv_evidence(
        self,
        content: bytes,
    ) -> bool:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            return False

        try:
            rows = list(csv.reader(io.StringIO(text)))
        except csv.Error:
            return False

        if len(rows) < 2:
            return False

        column_counts = [len(row) for row in rows if row]

        if not column_counts:
            return False

        return max(column_counts) >= 2