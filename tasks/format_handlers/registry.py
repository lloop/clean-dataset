from .csv_handler import CSVHandler
from .fallback_handler import FallbackHandler
from .html_handler import HTMLHandler
from .json_handler import JSONHandler
from .python_handler import PythonHandler
from .text_handler import TextHandler
from .xml_handler import XMLHandler

# TODO: I think a good refactor is to run the Magika analysis once at the top
# of the attempt to detect the extension and that Magika analasis data goes in to 
# the file object so only one analysis is needed per file in the pipeline.
# That way a file is brought in to the scrambled extension area and it is 
# immediately tested for the extension it has. As a part of that it undergoes 
# the Magika analysis. That analysis is added to the file object so if it fails 
# or not it has that. Bringing that data file object info to the AI part is
# very efficient.

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