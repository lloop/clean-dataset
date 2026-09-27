from .csv_handler import CSVHandler
from .fallback_handler import FallbackHandler
from .html_handler import HTMLHandler
from .json_handler import JSONHandler
from .python_handler import PythonHandler
from .text_handler import TextHandler
from .xml_handler import XMLHandler

class FormatHandlerRegistry:

    def __init__(self):
        self._handlers = {
            ".json": JSONHandler(),
            ".csv": CSVHandler(),
            ".html": HTMLHandler(),
            ".xml": XMLHandler(),
            ".py": PythonHandler(),
            ".txt": TextHandler(),
        }

        self._fallback = FallbackHandler()
        
    def get_handler(self, extension: str):
        return self._handlers.get(
            extension.lower(),
            self._fallback,
        )
        
    def detect_extension(
        self,
        content: bytes,
        current_ext: str,
        magika_result,
    ) -> str:

        if current_ext != ".txt":
            handler = self._handlers.get(current_ext)

            if handler and hasattr(handler, "detect_extension"):
                if handler.detect_extension(content, magika_result):
                    return current_ext

        for extension, handler in self._handlers.items():
            if extension == current_ext or extension == ".txt":
                continue

            if not hasattr(handler, "detect_extension"):
                continue

            if handler.detect_extension(content, magika_result):
                return extension

        text_handler = self._handlers.get(".txt")

        if text_handler and text_handler.detect_extension(
            content,
            magika_result,
        ):
            return ".txt"

        return current_ext