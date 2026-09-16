import json
from pathlib import Path
from typing import Dict, Any


class ManifestLoader:

    def __init__(self, manifest_path: str):
        self.manifest_path = Path(manifest_path)

    def load(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(
                f"Manifest not found: {self.manifest_path}"
            )

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)