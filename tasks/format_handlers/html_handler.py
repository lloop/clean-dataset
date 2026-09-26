import re

class HTMLHandler:
    
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
        magika_result,
    ) -> bool:

        if isinstance(content, bytes):
            raw_bytes = content
        else:
            raw_bytes = content.encode("utf-8")

        magika_label = magika_result.output.label.lower()
        confidence = magika_result.score

        evidence_count = self.count_html_evidence(raw_bytes)

        # Magika agrees with HTML.
        if magika_label == "html":
            if confidence >= 0.8:
                return evidence_count >= 1
            elif confidence >= 0.6:
                return evidence_count >= 2
            else:
                return evidence_count >= 2

        # Magika does not classify the file as HTML.
        if confidence >= 0.8:
            return evidence_count == 5
        elif confidence >= 0.6:
            return evidence_count >= 4
        elif confidence >= 0.4:
            return evidence_count >= 3
        else:
            return evidence_count >= 4
          
    def count_html_evidence(
        self,
        content: bytes,
    ) -> int:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            return 0

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

        return sum(tests.values())

    def detect_structure_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="surrogateescape")
        else:
            text = content

        text = text.strip()

        if not text:
            return {
                "is_corrupted": True,
                "error_message": "Empty HTML file",
            }

        tests = {
            "html_tag": bool(
                re.search(r"<\s*html\b", text, re.IGNORECASE)
            ),
            "closing_html_tag": bool(
                re.search(r"</\s*html\s*>", text, re.IGNORECASE)
            ),
            "head_tag": bool(
                re.search(r"<\s*head\b", text, re.IGNORECASE)
            ),
            "body_tag": bool(
                re.search(r"<\s*body\b", text, re.IGNORECASE)
            ),
        }

        if tests["html_tag"] and not tests["closing_html_tag"]:
            return {
                "is_corrupted": True,
                "error_message": "Unclosed HTML tag",
            }

        return {
            "is_corrupted": False,
            "error_message": None,
        }