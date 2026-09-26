import re
# from magika import Magika

class XMLHandler:
    
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

        if (
            magika_result.output.label.lower() == "xml"
            and magika_result.score >= 0.75
        ):
            if isinstance(content, bytes):
                raw_bytes = content
            else:
                raw_bytes = content.encode("utf-8")

            return self.has_strong_xml_evidence(raw_bytes)

        return False
   

    def has_strong_xml_evidence(
        self,
        content: bytes,
    ) -> bool:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            return False

        tests = {
            "xml_declaration": bool(
                re.search(r"<\?xml\b", text, re.IGNORECASE)
            ),
            "opening_tag": bool(
                re.search(r"<[A-Za-z_][\w:.-]*(?:\s[^>]*)?>", text)
            ),
            "closing_tag": bool(
                re.search(r"</[A-Za-z_][\w:.-]*\s*>", text)
            ),
            "nested_tags": bool(
                re.search(
                    r"<([A-Za-z_][\w:.-]*)[^>]*>[\s\S]*?</\1\s*>",
                    text,
                )
            ),
        }

        return sum(tests.values()) >= 2
    
    def detect_structure_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        import xml.etree.ElementTree as ET

        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="surrogateescape")
        else:
            text = content

        if not text.strip():
            return {
                "is_corrupted": True,
                "error_message": "Empty XML file",
            }

        try:
            ET.fromstring(text.replace("\x00", ""))
        except ET.ParseError as error:
            return {
                "is_corrupted": True,
                "error_message": str(error),
            }

        return {
            "is_corrupted": False,
            "error_message": None,
        }