from magika import Magika
import re

class HTMLHandler:
    
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
                result.output.label.lower() == "html"
                and result.score >= 0.75
            ):
                return self.has_strong_html_evidence(raw_bytes)

        except Exception:
            pass

        return False

    def has_strong_html_evidence(
        self,
        content: bytes,
    ) -> bool:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            return False

        tests = {
            "doctype": bool(
                re.search(r"<!DOCTYPE\s+html\b", text, re.IGNORECASE)
            ),
            "html_tag": bool(
                re.search(r"<\s*html\b", text, re.IGNORECASE)
            ),
            "head_tag": bool(
                re.search(r"<\s*head\b", text, re.IGNORECASE)
            ),
            "body_tag": bool(
                re.search(r"<\s*body\b", text, re.IGNORECASE)
            ),
            "closing_tags": bool(
                re.search(r"</\s*[a-zA-Z][^>]*>", text)
            ),
        }

        return sum(tests.values()) >= 2