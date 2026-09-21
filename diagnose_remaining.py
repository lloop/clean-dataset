from pathlib import Path
from tasks.format_handlers.text_handler import TextHandler

path = Path("dataset_dirty/files/statement_draft.txt")
content = path.read_bytes()

handler = TextHandler()

print(handler.detect_character_corruption(content))