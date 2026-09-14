# tasks/reporter.py
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class AuditReporter:
    """Generates structured JSON and Markdown audit reports summarizing dataset cleaning runs."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)

    def generate_report(
        self,
        stats: Dict[str, int],
        removed_duplicates: List[str],
        repaired_extensions: List[str],
    ) -> Path:
        """Writes audit_summary.json and audit_summary.md into the clean output directory."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().isoformat()

        report_data: Dict[str, Any] = {
            "timestamp": timestamp,
            "summary": stats,
            "quarantined_duplicates": removed_duplicates,
            "repaired_extensions": repaired_extensions,
        }

        # Write JSON Report
        json_path = self.output_dir / "audit_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # Write Markdown Report
        md_path = self.output_dir / "audit_summary.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._format_markdown(report_data))

        return md_path

    def _format_markdown(self, data: Dict[str, Any]) -> str:
        stats = data["summary"]
        duplicates = data["quarantined_duplicates"]
        repaired = data["repaired_extensions"]

        md_lines = [
            "# Dataset Cleaning Audit Report",
            f"**Execution Timestamp:** `{data['timestamp']}`\n",
            "## Processing Metrics",
            f"- **Total Evaluated Files:** {stats.get('total_processed', 0)}",
            f"- **Duplicates Quarantined:** {stats.get('duplicates_removed', 0)}",
            f"- **Extensions Repaired:** {stats.get('repaired_extensions', 0)}",
            f"- **Clean Valid Files:** {stats.get('clean_saved', 0)}\n",
            "## Quarantined Duplicates",
        ]

        if duplicates:
            for item in duplicates:
                md_lines.append(f"- `{item}`")
        else:
            md_lines.append("_No duplicate files identified._")

        md_lines.append("\n## Repaired Extensions")
        if repaired:
            for item in repaired:
                md_lines.append(f"- `{item}`")
        else:
            md_lines.append("_No extensions required repair._")

        return "\n".join(md_lines)