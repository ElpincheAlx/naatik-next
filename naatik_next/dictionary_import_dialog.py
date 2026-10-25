"""Explicit per-file confirmation after background archive validation."""
from .i18n import t
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
                               QHeaderView,QDialogButtonBox)

NAMES = {'term': 'Términos', 'grammar': 'Gramática (términos)', 'kanji': 'Kanji', 'pitch': 'Acento tonal'}


class ImportReview(QDialog):
    def __init__(self, entries, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.setWindowTitle(t('Revisar diccionarios antes de importar'))
        self.resize(1050,450)
        layout = QVBoxLayout(self)
        info = QLabel(t('Selecciona cuáles agregar. Cada ZIP es una transacción independiente. Los duplicados y errores no se importan. Los archivos con avisos requieren selección explícita; revisa los detalles de la fila.'))
        info.setWordWrap(True)
        layout.addWidget(info)
        self.table = QTableWidget(len(entries),7)
        self.table.setHorizontalHeaderLabels([t('Agregar'),t('Archivo'),t('Título'),t('Tipo'),t('Revisión'),t('Entradas'),t('Estado / avisos')])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6,QHeaderView.Stretch)
        for i,entry in enumerate(entries):
            blocked = entry.get('error') or entry.get('duplicate')
            warnings = entry.get('warnings',[])
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemIsUserCheckable | (Qt.ItemIsEnabled if not blocked else Qt.NoItemFlags))
            check.setCheckState(Qt.Checked if not blocked and not warnings else Qt.Unchecked)
            self.table.setItem(i,0,check)
            state = (t('Error: ')+entry['error'] if entry.get('error') else t('Duplicado: ')+entry['duplicate']
                     if entry.get('duplicate') else '\n'.join(warnings) if warnings else t('Validado; pendiente de confirmar'))
            values = [Path(entry['path']).name, entry.get('title','—'),
                      ', '.join(t(NAMES.get(k,k)) for k in entry.get('types',[])),entry.get('revision','—'),str(entry.get('count','—')),state]
            for j,value in enumerate(values,1):
                item = QTableWidgetItem(value)
                item.setToolTip(state)
                self.table.setItem(i,j,item)
        layout.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(t('Importar seleccionados'))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected(self):
        return [entry for i,entry in enumerate(self.entries) if self.table.item(i,0).checkState()==Qt.Checked
                and not entry.get('error') and not entry.get('duplicate')]
