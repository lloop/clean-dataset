# tasks/cross_reference.py
from typing import Dict, Any, List, Union, Optional, Sequence, Mapping
from pathlib import Path


class CrossReference:

    def compare_duplicates(
        self,
        manifest: Dict[str, Any],
        detected_duplicates: List[Union[str, Dict[str, str]]]
    ) -> Dict[str, Any]:

        # Extract pairs from manifest using the correct 'copied_from' key
        manifest_pairs = {
            frozenset([record["filename"], record["copied_from"]])
            for record in manifest.get("files", [])
            if record.get("is_duplicate") and record.get("copied_from") not in (None, "none")
        }

        # Extract detected pairs
        detected_pairs = {
            frozenset([item["file"], item["matched_file"]])
            for item in detected_duplicates
            if isinstance(item, dict)
        }

        false_positives_pairs = detected_pairs - manifest_pairs
        false_negatives_pairs = manifest_pairs - detected_pairs

        false_positives = [
            {"file": pair_list[0], "matched_file": pair_list[1] if len(pair_list) > 1 else "unknown"}
            for pair_list in [list(pair) for pair in false_positives_pairs]
        ]

        false_negatives = [
            {"file": pair_list[0], "copied_from": pair_list[1] if len(pair_list) > 1 else "unknown"}
            for pair_list in [list(pair) for pair in false_negatives_pairs]
        ]

        return {
            "manifest_count": len(manifest_pairs),
            "detected_count": len(detected_pairs),
            "false_positive_count": len(false_positives_pairs),
            "false_negative_count": len(false_negatives_pairs),
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }
        
    def compare_character_corrupted(
        self,
        manifest: Dict[str, Any],
        detected_corruptions: Sequence[Union[str, Mapping[str, Optional[str]]]]
    ) -> Dict[str, Any]:
        """
        Cross-references detected character corruptions against manifest ground truth.
        Uses size_bytes directly from the manifest to filter out 0-byte files.
        """
        # Build lookup for manifest file sizes and character corruption labels
        manifest_records = {
            record["filename"]: {
                "size_bytes": record.get("size_bytes", 0),
                "label": record.get("character_corruption_label")
            }
            for record in manifest.get("files", [])
            if "filename" in record
        }

        # Ground truth set: files with character corruption label AND size_bytes > 0
        manifest_corrupted = {
            filename
            for filename, data in manifest_records.items()
            if data["label"] not in (None, "none", "") and data["size_bytes"] > 0
        }

        # Map detected corruption items to extract filename and optional metadata payload
        detected_map: Dict[str, Mapping[str, Optional[str]]] = {}
        for item in detected_corruptions:
            if isinstance(item, Mapping):
                filename = item.get("file") or item.get("filename")
                payload = item
            else:
                filename = item
                payload = {"file": str(item)}

            if filename and manifest_records.get(filename, {}).get("size_bytes", 0) > 0:
                detected_map[filename] = payload

        detected_set = set(detected_map.keys())

        # Set differences
        false_positives_set = detected_set - manifest_corrupted
        false_negatives_set = manifest_corrupted - detected_set
        true_positives_set = detected_set & manifest_corrupted

        # Build structured dictionary entries for false positives and false negatives
        false_positives = [
            {
                "file": filename,
                "label": manifest_records.get(filename, {}).get("label") or "none",
                "detected_details": detected_map[filename]
            }
            for filename in sorted(false_positives_set)
        ]

        false_negatives = [
            {
                "file": filename,
                "label": manifest_records[filename]["label"]
            }
            for filename in sorted(false_negatives_set)
        ]

        return {
            "manifest_count": len(manifest_corrupted),
            "detected_count": len(detected_set),
            "true_positive_count": len(true_positives_set),
            "false_positive_count": len(false_positives),
            "false_negative_count": len(false_negatives),
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }