"""Qt rich text with all resource resolution and link navigation disabled."""
from PySide6.QtWidgets import QTextBrowser


class DictionaryView(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)

    def loadResource(self, resource_type, url):
        # Block http, file, data and relative resource paths alike.
        return None
