from pathlib import Path
from magika import Magika

magika = Magika()

files = [
    "LOG.json",
    "STATEMENT_COPY.json",
    "brief_copy_1.json",
    "memo_3.json",
]

for filename in files:
    path = Path("dataset_dirty/files") / filename
    content = path.read_bytes()

    result = magika.identify_bytes(content)

    print(
        f"FILE: {filename} | "
        f"LABEL: {result.output.label} | "
        f"SCORE: {result.score}"
    )