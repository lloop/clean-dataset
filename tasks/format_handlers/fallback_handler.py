class FallbackHandler:

    def detect_character_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        # print("FallbackHandler: no format-specific handler available.")

        return {
            "is_corrupted": False,
            "detected_corruptions": [],
        }