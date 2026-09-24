import ast
from magika import Magika
import re

class PythonHandler:
    
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

        if self.has_null_bytes(text) or "\\u0000" in text:
            detected_types.append("null_byte_injection")

        if self.has_unicode_replacement_char(text):
            detected_types.append("unicode_replacement_char")

        if self.has_mojibake(text):
            detected_types.append("mojibake")

        return {
            "is_corrupted": len(detected_types) > 0,
            "detected_corruptions": detected_types,
        }

    def has_null_bytes(self, text: str) -> bool:
        return "\x00" in text

    def has_unicode_replacement_char(self, text: str) -> bool:
        return "\ufffd" in text

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
                result.output.label.lower() == "python"
                and result.score >= 0.75
            ):
                return self.has_strong_python_evidence(raw_bytes)

        except Exception:
            pass

        return False

    def has_strong_python_evidence(
        self,
        content: bytes,
    ) -> bool:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception as e:
            return False

        tests = {
            "function": bool(
                re.search(r"(?m)^\s*def\s+\w+\s*\(", text)
            ),
            "class": bool(
                re.search(r"(?m)^\s*class\s+\w+", text)
            ),
            "import": bool(
                re.search(r"(?m)^\s*(?:from\s+\S+\s+)?import\s+", text)
            ),
            "if_main": bool(
                re.search(
                    r'(?m)^\s*if\s+__name__\s*==\s*["\']__main__["\']\s*:',
                    text,
                )
            ),
        }
        
        return sum(tests.values()) >= 1
    
    def detect_structure_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="surrogateescape").replace("\x00", "").replace("\ufffd", "")
        else:
            text = content.replace("\x00", "").replace("\ufffd", "")

        text = text.strip()

        if not text:
            return {
                "is_corrupted": True,
                "error_message": "Empty Python file",
            }

        try:
            ast.parse(text)
        except (SyntaxError, ValueError, TypeError) as error:
            return {
                "is_corrupted": True,
                "error_message": str(error),
            }

        return {
            "is_corrupted": False,
            "error_message": None,
        }