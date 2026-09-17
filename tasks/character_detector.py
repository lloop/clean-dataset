import re
from pathlib import Path
from typing import Any, Dict, List, Union


class CharacterCorruptionDetector:
    """Detects character-level encoding corruptions including null bytes,

    replacement characters, and mojibake.
    """

    def detect_character_corruption(
        self, content: Union[str, bytes]
    ) -> Dict[str, Any]:
        """Inspects text content for character encoding corruption signatures."""
        if isinstance(content, bytes):
            # Check for raw byte-level replacement chars before decoding alters them
            if b"\xef\xbf\xbd" in content:
                text_content = content.decode("utf-8", errors="replace")
            else:
                try:
                    text_content = content.decode("utf-8")
                except Exception:
                    # Fallback to latin-1 to preserve byte-to-char mapping for mojibake checks
                    text_content = content.decode("latin-1", errors="replace")
        else:
            text_content = content

        detected_types = []

        if self.has_null_bytes(text_content):
            detected_types.append("null_byte_injection")

        if self.has_unicode_replacement_char(text_content):
            detected_types.append("unicode_replacement_char")

        if self.has_mojibake(text_content):
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
            "Ã ",
            "Ã¨",
            "Ã±",
            "â€–",
            "â€”",
            "Ã§",
            "Ã\xa0",
            "Ã¢",
        ]
        return any(sig in text for sig in mojibake_signatures)