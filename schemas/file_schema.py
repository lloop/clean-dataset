from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FileRecords:
    filename: str
    file_hash: Optional[str] = None
    is_binary: bool = False
    extension_mismatch: bool = False
    actual_extension: Optional[str] = None
    duplicate: bool = False
    matched_file: Optional[str] = None
    character_corruption: List[str] = field(default_factory=list)
    structural_corruption: List[str] = field(default_factory=list)