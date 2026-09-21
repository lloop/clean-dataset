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
    ) -> str:
        handler = self._handlers.get(current_ext)

        if handler and hasattr(handler, "detect_extension"):
            print(f"TRYING DECLARED HANDLER: {current_ext}")

            if handler.detect_extension(content):
                print(f"MATCH: {current_ext}")
                return current_ext

        # Here is where the order needs to be worked on
        for extension, handler in self._handlers.items():
            if extension == current_ext:
                continue

            if not hasattr(handler, "detect_extension"):
                continue

            print(f"TRYING OTHER HANDLER: {extension}")

            if handler.detect_extension(content):
                print(
                    f"MATCH: {extension} | "
                    f"HANDLER: {current_ext}"
                )
                return extension

        return current_ext