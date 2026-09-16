from dataclasses import dataclass, field
from typing import List


@dataclass
class FileAuditCollections:
    removed_duplicates: List[str] = field(default_factory=list)
    repaired_extensions: List[str] = field(default_factory=list)
    character_corrupted: List[str] = field(default_factory=list)
    structure_corrupted: List[str] = field(default_factory=list)


@dataclass
class PipelineAuditSummary:
    total_processed: int = 0
    duplicates: int = 0
    character_corrupted: int = 0
    structure_corrupted: int = 0
    corrupted_extensions: int = 0
    clean_saved: int = 0
    collections: FileAuditCollections = field(
        default_factory=FileAuditCollections
    )