# tasks/cross_reference.py

from typing import Dict, Any, List, Union


class CrossReference:

    def compare_duplicates(
        self,
        manifest: Dict[str, Any],
        detected_duplicates: List[Union[str, Dict[str, str]]]
    ) -> Dict[str, Any]:

        # Map manifest duplicates to their matched/original file target
        manifest_duplicates_map = {
            record["filename"]: record.get("copied_from") or record.get("original_file", "unknown")
            for record in manifest.get("files", [])
            if record.get("is_duplicate")
        }

        # Map detected duplicates to their matched file target
        detected_duplicates_map = {
            item["file"]: item.get("matched_file", "unknown")
            for item in detected_duplicates
            if isinstance(item, dict)
        }

        manifest_set = set(manifest_duplicates_map.keys())
        detected_set = set(detected_duplicates_map.keys())

        false_negatives_keys = manifest_set - detected_set
        false_positives_keys = detected_set - manifest_set

        # Format as list of dictionaries
        false_positives = [
            {
                "file": filename,
                "matched_file": detected_duplicates_map[filename]
            }
            for filename in sorted(false_positives_keys)
        ]

        false_negatives = [
            {
                "file": filename,
                "copied_from": manifest_duplicates_map[filename]
            }
            for filename in sorted(false_negatives_keys)
        ]

        return {
            "manifest_count": len(manifest_set),
            "detected_count": len(detected_set),
            "missed_count": len(false_negatives),
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }