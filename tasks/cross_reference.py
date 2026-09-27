# tasks/cross_reference.py
from typing import Dict, Any, Sequence, List, Union, Mapping, Optional
from schemas.file_schema import FileRecords
from config import STRUCTURE_LABEL_MATCHES

class CrossReference:

    def compare(
        self,
        manifest: Dict[str, Any],
        file_records: Sequence[FileRecords],
    ) -> Dict[str, Any]:

        return {
            "duplicates": self.compare_duplicates(
                manifest,
                file_records,
            ),
            "character_corruption": self.compare_character_corrupted(
                manifest,
                file_records,
            ),
            "structural_corruption": self.compare_structure_corrupted(
                manifest,
                file_records,
            ),
            "extensions": self.compare_extensions_scrambled(
                manifest,
                file_records,
            ),
        }

    def compare_duplicates(
        self,
        manifest: Dict[str, Any],
        file_records: list[FileRecords],
    ) -> Dict[str, Any]:

        # Extract pairs from manifest using the correct 'copied_from' key
        manifest_pairs = {
            frozenset([record["filename"], record["copied_from"]])
            for record in manifest.get("files", [])
            if record.get("is_duplicate") and record.get("copied_from") not in (None, "none")
        }

        # Extract detected pairs
        detected_pairs = {
            frozenset([record.filename, record.matched_file])
            for record in file_records
            if record.duplicate and record.matched_file
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
        file_records: list[FileRecords],
    ) -> Dict[str, Any]:

        manifest_records = {
            record["filename"]: set(
                record.get("character_corruption_labels", [])
            )
            for record in manifest.get("files", [])
            if "filename" in record
        }

        detected_records = {
            record.filename: set(record.character_corruption)
            for record in file_records
        }

        false_positives = []
        false_negatives = []
        correct = []

        for filename in manifest_records:
            manifest_labels = manifest_records[filename]
            detected_labels = detected_records.get(filename, set())

            if manifest_labels == detected_labels:
                if manifest_labels:
                    correct.append(filename)
                continue

            if manifest_labels - detected_labels:
                false_negatives.append({
                    "file": filename,
                    "expected": sorted(manifest_labels),
                    "detected": sorted(detected_labels),
                    "missing": sorted(manifest_labels - detected_labels),
                })

            if detected_labels - manifest_labels:
                false_positives.append({
                    "file": filename,
                    "expected": sorted(manifest_labels),
                    "detected": sorted(detected_labels),
                    "unexpected": sorted(detected_labels - manifest_labels),
                })

        return {
            "manifest_count": sum(bool(labels) for labels in manifest_records.values()),
            "detected_count": sum(bool(labels) for labels in detected_records.values()),
            "correct_count": len(correct),
            "false_positive_count": len(false_positives),
            "false_negative_count": len(false_negatives),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        }
            
    def compare_structure_corrupted(
        self,
        manifest: Dict[str, Any],
        file_records: list[FileRecords],
    ) -> Dict[str, Any]:

        manifest_records = {
            record["filename"]: set(
                record.get("structure_corruption_label", [])
            )
            for record in manifest.get("files", [])
            if "filename" in record
        }

        detected_records = {
            record.filename: set(record.structural_corruption)
            for record in file_records
        }

        false_positives = []
        false_negatives = []
        correct = []

        for filename in manifest_records:
            manifest_labels = manifest_records[filename]
            detected_labels = detected_records.get(filename, set())

            manifest_corrupted = bool(manifest_labels)
            detected_corrupted = bool(detected_labels)

            if manifest_corrupted and detected_corrupted:
                correct.append(filename)

            elif manifest_corrupted and not detected_corrupted:
                false_negatives.append({
                    "file": filename,
                    "expected": sorted(manifest_labels),
                    "detected": sorted(detected_labels),
                })

            elif not manifest_corrupted and detected_corrupted:
                false_positives.append({
                    "file": filename,
                    "expected": sorted(manifest_labels),
                    "detected": sorted(detected_labels),
                })
                
        return {
            "manifest_count": sum(bool(labels) for labels in manifest_records.values()),
            "detected_count": sum(bool(labels) for labels in detected_records.values()),
            "correct_count": len(correct),
            "false_positive_count": len(false_positives),
            "false_negative_count": len(false_negatives),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        }
            
    # def compare_structure_corrupted(
    #     self,
    #     manifest: Dict[str, Any],
    #     file_records: list[FileRecords],
    # ) -> Dict[str, Any]:

    #     manifest_records = {
    #         record["filename"]: {
    #             "size_bytes": record.get("size_bytes", 0),
    #             "labels": record.get("structure_corruption_label", []),
    #         }
    #         for record in manifest.get("files", [])
    #         if "filename" in record
    #     }

    #     manifest_corrupted = {
    #         filename
    #         for filename, data in manifest_records.items()
    #         if data["labels"]
    #     }

    #     detected_records = {
    #         record.filename: record
    #         for record in file_records
    #         if record.structural_corruption
    #     }

    #     detected_set = set(detected_records)

    #     false_positives_set = detected_set - manifest_corrupted
    #     false_negatives_set = manifest_corrupted - detected_set

    #     false_positives = [
    #         {
    #             "file": filename,
    #             "labels": manifest_records.get(filename, {}).get("labels", []),
    #             "detected_details": detected_records[filename].structural_corruption,
    #         }
    #         for filename in sorted(false_positives_set)
    #     ]

    #     false_negatives = [
    #         {
    #             "file": filename,
    #             "labels": manifest_records[filename]["labels"],
    #         }
    #         for filename in sorted(false_negatives_set)
    #     ]

    #     return {
    #         "manifest_count": len(manifest_corrupted),
    #         "detected_count": len(detected_set),
    #         "false_positive_count": len(false_positives),
    #         "false_negative_count": len(false_negatives),
    #         "false_positives": false_positives,
    #         "false_negatives": false_negatives,
    #     }
    
    def compare_extensions_scrambled(
        self,
        manifest: Dict[str, Any],
        file_records: list[FileRecords],
    ) -> Dict[str, Any]:

        manifest_records = {
            record["filename"]: {
                "size_bytes": record.get("size_bytes", 0),
                "extension_scrambled": record.get("extension_scrambled"),
                "original_extension": record.get("original_extension"),
            }
            for record in manifest.get("files", [])
            if "filename" in record
        }

        manifest_scrambled = {
            filename
            for filename, data in manifest_records.items()
            if data["extension_scrambled"] and data["size_bytes"] > 0
        }

        detected_records = {
            record.filename: record
            for record in file_records
            if record.extension_mismatch
        }

        detected_set = set(detected_records)

        false_positives_set = detected_set - manifest_scrambled
        false_negatives_set = manifest_scrambled - detected_set

        false_positives = [
            {
                "file": filename,
                "original_extension": (
                    manifest_records.get(filename, {}).get("original_extension")
                    or "none"
                ),
                "detected_details": {
                    "actual_extension": detected_records[filename].actual_extension
                },
            }
            for filename in sorted(false_positives_set)
        ]

        false_negatives = [
            {
                "file": filename,
                "original_extension": manifest_records[filename]["original_extension"],
            }
            for filename in sorted(false_negatives_set)
        ]

        return {
            "manifest_count": len(manifest_scrambled),
            "detected_count": len(detected_set),
            "false_positive_count": len(false_positives),
            "false_negative_count": len(false_negatives),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        }