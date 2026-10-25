"""UI language only. Catalog keys never change worker protocols or user resources."""
import json
import os
from pathlib import Path

CATALOG_DIR = Path(__file__).with_name('locales')
CATALOGS = {code: json.loads((CATALOG_DIR / (code + '.json')).read_text()) for code in ('es', 'en')}
_language = None


def set_language(code):
    global _language
    _language = code if code in CATALOGS else 'es'


def language():
    global _language
    if _language is None:
        _language = 'es'  # Safe fallback even when reporting a corrupt settings file.
        code = os.environ.get('NAATIK_NEXT_UI_LANGUAGE')
        if code is None:
            from .storage import load_settings
            try:
                code = load_settings().get('ui_language', 'es')
            except Exception:
                code = 'es'
        set_language(code)
    return _language


def t(source):
    return CATALOGS[language()].get(source, source)


def choose_language(parent, current='es'):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox
    dialog = QDialog(parent)
    dialog.setWindowTitle('Idioma / Language')
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel('Idioma de interfaz / Interface language'))
    choice = QComboBox()
    choice.addItem('Español', 'es'); choice.addItem('English', 'en')
    choice.setCurrentIndex(max(0, choice.findData(current)))
    layout.addWidget(choice)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText('Aplicar / Apply')
    buttons.button(QDialogButtonBox.Cancel).setText('Cancelar / Cancel')
    buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    return choice.currentData() if dialog.exec() == QDialog.Accepted else None


def translate_widgets(owner):
    """Refresh presentation without rebuilding windows, tasks or editable user content."""
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import (QLabel, QAbstractButton, QGroupBox, QComboBox,
                                  QTabWidget, QLineEdit, QPlainTextEdit, QMenu, QTableWidget)
    from PySide6.QtGui import QAction
    reverse = {v: k for catalog in CATALOGS.values() for k, v in catalog.items()}
    def convert(value):
        # Only complete catalog entries: never rewrite fragments of user content.
        return t(reverse.get(value, value))
    for widget in [owner, *owner.findChildren(QObject)]:
        blocked = widget.blockSignals(True)
        try:
            if isinstance(widget, (QLabel, QAbstractButton, QAction)):
                widget.setText(convert(widget.text()))
            if isinstance(widget, (QGroupBox, QMenu)):
                widget.setTitle(convert(widget.title()))
            if isinstance(widget, QComboBox) and not widget.isEditable():
                for index in range(widget.count()):
                    widget.setItemText(index, convert(widget.itemText(index)))
            if isinstance(widget, QTabWidget):
                for index in range(widget.count()):
                    widget.setTabText(index, convert(widget.tabText(index)))
            if isinstance(widget, (QLineEdit, QPlainTextEdit)):
                widget.setPlaceholderText(convert(widget.placeholderText()))
            if isinstance(widget, QTableWidget):
                for index in range(widget.columnCount()):
                    item = widget.horizontalHeaderItem(index)
                    if item: item.setText(convert(item.text()))
            if hasattr(widget, 'windowTitle'):
                widget.setWindowTitle(convert(widget.windowTitle()))
        finally:
            widget.blockSignals(blocked)
    if getattr(owner, 'tutorial_dialog', None):
        owner.tutorial_dialog.render()
