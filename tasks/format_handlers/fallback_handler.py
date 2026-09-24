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
        
    def detect_structure_corruption(
        self,
        content: str | bytes,
    ) -> dict:
        return {
            "is_corrupted": False,
            "error_message": None,
        }