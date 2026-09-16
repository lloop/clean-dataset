from dataclasses import dataclass, field
from typing import List, Dict, Union, Tuple

# @dataclass
# class FileAuditCollections:
#     removed_duplicates: List[str] = field(default_factory=list)
#     repaired_extensions: List[str] = field(default_factory=list)
#     character_corrupted: List[str] = field(default_factory=list)
#     structure_corrupted: List[str] = field(default_factory=list)


@dataclass
class PipelineAuditSummary:
    total_processed: int = 0
    duplicates: int = 0
    character_corrupted: int = 0
    structure_corrupted: int = 0
    corrupted_extensions: int = 0
    clean_saved: int = 0
    list_detected_files: Dict[str, List[Union[str, Dict[str, str]]]] = field(
        default_factory=lambda: {
            "removed_duplicates": [],
            "repaired_extensions": [],
            "character_corrupted": [],
            "structure_corrupted": [],
        }
    )