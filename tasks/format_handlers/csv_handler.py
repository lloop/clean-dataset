import csv
import io

class CSVHandler:
    
    def __init__(self):
        pass
    
    def detect_character_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="surrogateescape")
        else:
            text = content

        detected_types = []

        if self.has_null_bytes(text) or "\\u0000" in text:
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
        magika_result,
    ) -> bool:

        if (
            magika_result.output.label.lower() == "csv"
            and magika_result.score >= 0.75
        ):
            if isinstance(content, bytes):
                raw_bytes = content
            else:
                raw_bytes = content.encode("utf-8")

            return self.has_strong_csv_evidence(raw_bytes)

        return False
    
    def has_strong_csv_evidence(
        self,
        content: bytes,
    ) -> bool:
        try:
            text = content.decode("utf-8", errors="ignore").replace("\x00", "")
        except Exception:
            return False

        for delimiter in (",", ";"):
            try:
                rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
            except csv.Error as error:
                print(f"CSV parsing error: {error}")
                return False

            if len(rows) < 2:
                continue

            column_counts = [len(row) for row in rows if row]

            if column_counts and max(column_counts) >= 2:
                return True

        return False

    def detect_structure_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="surrogateescape").replace("\x00", "")
        else:
            text = content.replace("\x00", "")

        try:
            rows = list(csv.reader(io.StringIO(text)))
        except csv.Error as error:
            return {
                "is_corrupted": True,
                "error_message": str(error),
            }

        rows = [row for row in rows if row]

        if not rows:
            return {
                "is_corrupted": True,
                "error_message": "Empty CSV file",
            }
            
        comma_rows = list(csv.reader(io.StringIO(text), delimiter=","))
        semicolon_rows = list(csv.reader(io.StringIO(text), delimiter=";"))

        comma_columns = [len(row) for row in comma_rows if row]
        semicolon_columns = [len(row) for row in semicolon_rows if row]

        if (
            max(semicolon_columns, default=0) > 1
            and max(comma_columns, default=0) <= 1
        ):
            return {
                "is_corrupted": True,
                "error_message": "Unexpected semicolon delimiter",
            }

        data_rows = rows
        expected_cols = len(data_rows[0])

        for i, row in enumerate(data_rows, start=1):
            if len(row) != expected_cols:
                return {
                    "is_corrupted": True,
                    "error_message": (
                        f"Row {i} has inconsistent column count "
                        f"(expected {expected_cols}, got {len(row)})"
                    ),
                }

        return {
            "is_corrupted": False,
            "error_message": None,
        }