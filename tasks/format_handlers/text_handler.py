import re
from magika import Magika

class TextHandler:
    
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
            content: str | bytes
        ) -> bool:
            if isinstance(content, str):
                raw_bytes = content.encode("utf-8")
            else:
                raw_bytes = content

            try:
                result = self.magika.identify_bytes(raw_bytes)

                # magika_is_text = result.output.is_text
                # magika_label = result.output.label.lower()
                # magika_score = result.score
                
                if result.output.is_text:
                    return True

                # if magika_score >= 0.5:
                #     if magika_label == "rst":
                #         return self.has_strong_rst_evidence(raw_bytes)

                #     return magika_label in {
                #         "txt",
                #         "text",
                #     }

            except Exception:
                pass

            return False
        
    def has_strong_rst_evidence(
        self,
        content: bytes,
    ) -> bool:
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception as error:
            print(f"DECODE FAILED: {error}")
            return False
        
        tests = {
            "directive": bool(
                re.search(r"(?m)^\.\. [a-zA-Z0-9_-]+::", text)
            ),
            "role": bool(
                re.search(r"(?m)^:[a-zA-Z0-9_-]+:`[^`]+`", text)
            ),
            "reference": bool(
                re.search(r"(?m)^\.\. _[^:]+:", text)
            ),
            "literal_block": bool(
                re.search(r"(?m)^::\s*$", text)
            ),
        }

        return sum(tests.values()) >= 2
    
    def detect_structure_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="surrogateescape")
        else:
            text = content

        if not text.strip():
            return {
                "is_corrupted": True,
                "error_message": "Empty text file",
            }

        return {
            "is_corrupted": False,
            "error_message": None,
        }