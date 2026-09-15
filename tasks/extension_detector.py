from pathlib import Path
import magic
from bs4 import BeautifulSoup
import defusedxml.ElementTree as SafeET
from magika import Magika
import orjson
import polars as pl


class ExtensionDetector:
    """Multi-layer file classification engine for resolving scrambled extensions."""

    def __init__(self):
        self.magika = Magika()
        self.mime_engine = magic.Magic(mime=True)

    def detect_true_extension(self, file_path: Path) -> str:
        current_ext = file_path.suffix.lower()

        # High-Confidence Magika Classifier
        try:
            res = self.magika.identify_path(file_path)
            if res.score >= 0.75:
                detected_ext = self._normalize_magika_label(res.output.label)
                aliases = {".jpeg": ".jpg", ".htm": ".html", ".text": ".txt"}
                norm_current = aliases.get(current_ext, current_ext)
                norm_detected = aliases.get(detected_ext, detected_ext)

                if norm_detected != norm_current:
                    return norm_detected
                return current_ext
        except Exception:
            pass

        # C-Engine Magic Byte Inspection (python-magic / libmagic)
        try:
            mime_type = self.mime_engine.from_file(str(file_path))
            direct_mime_map = {
                "application/json": ".json",
                "text/xml": ".xml",
                "application/xml": ".xml",
                "text/html": ".html",
                "image/jpeg": ".jpg",
                "image/png": ".png",
            }
            if mime_type in direct_mime_map:
                return direct_mime_map[mime_type]

            # Binary extension claims plain text
            if mime_type == "text/plain" and current_ext in {
                ".jpg",
                ".jpeg",
                ".png",
                ".pdf",
                ".zip",
                ".exe",
            }:
                pass
            elif mime_type != "text/plain":
                return current_ext
        except Exception:
            pass

        # Text Schema Spec Parsers
        return self._validate_text_schema(file_path, current_ext)

    def _normalize_magika_label(self, label: str) -> str:
        if not label:
            return "unknown"
        label = label.lower().strip()
        label_map = {
            "python": ".py",
            "jpeg": ".jpg",
            "text": ".txt",
            "javascript": ".js",
        }
        mapped = label_map.get(label, label)
        return mapped if mapped.startswith(".") else f".{mapped}"

    def _validate_text_schema(self, file_path: Path, current_ext: str) -> str:
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read(32768)
        except Exception:
            return current_ext

        if not raw_bytes.strip():
            return current_ext

        # JSON (orjson)
        try:
            orjson.loads(raw_bytes)
            return ".json"
        except Exception:
            pass

        try:
            text_content = raw_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            return current_ext

        # XML (defusedxml)
        if text_content.startswith("<") and not text_content.startswith("<!--"):
            try:
                SafeET.fromstring(text_content)
                return ".xml"
            except Exception:
                pass

        # HTML (BeautifulSoup + html5lib)
        if any(
            tag in text_content.lower()
            for tag in ("<html", "<body", "<!--", "<div")
        ):
            try:
                soup = BeautifulSoup(text_content, "html5lib")
                if soup.html and len(soup.find_all()) > 0:
                    return ".html"
            except Exception:
                pass

        # Tabular CSV (Polars)
        try:
            df = pl.read_csv(
                file_path,
                n_rows=20,
                has_header=True,
                ignore_errors=False,
                raise_if_empty=True,
            )
            if df.width > 1 and df.height > 0:
                return ".csv"
        except Exception:
            pass

        return ".txt"