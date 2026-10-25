"""Non-blocking first-use setup; only explicit confirmation permits downloads."""
from .i18n import t
import platform
from pathlib import Path
import shutil
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QPlainTextEdit, QWidget)
from .processes import Task
from .resources import catalogue
from .manga import defaults


class SetupDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(t('Asistente de recursos — OCR, traducción y diccionarios'))
        self.resize(700, 650)
        layout = QVBoxLayout(self)
        intro = QLabel(t('Elige el idioma de trabajo y prepara el OCR. La interfaz de esta entrega está en español.\nPuedes usar Tesseract del sistema o preparar MangaOCR CPU. No se traduce automáticamente.'))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.language = QComboBox()
        for label, code in [(t('Japonés (jpn)'), 'jpn'), (t('Inglés (eng)'), 'eng'), (t('Español (spa)'), 'spa'), (t('Japonés vertical (jpn_vert)'), 'jpn_vert')]:
            self.language.addItem(label, code)
        for engine in owner.engines:
            for code in engine.get('languages', []):
                if self.language.findData(code) < 0: self.language.addItem(code, code)
        index = self.language.findData(owner.settings.get('ocr_language', 'jpn'))
        self.language.setCurrentIndex(max(index, 0))
        layout.addWidget(QLabel(t('Idioma deseado para Tesseract (requiere sus datos de idioma):')))
        layout.addWidget(self.language)
        self.engine = QComboBox()
        self.engine.addItem(t('Tesseract — requiere ejecutable y datos del sistema'), 'tesseract')
        self.engine.addItem(t('MangaOCR — japonés fijo, CPU'), 'mangaocr')
        self.engine.setCurrentIndex(max(self.engine.findData(owner.settings.get('ocr_engine', 'tesseract')), 0))
        layout.addWidget(self.engine)
        self.guide = QLabel()
        self.guide.setWordWrap(True)
        layout.addWidget(self.guide)
        self.manga_controls = QWidget()
        manga_layout = QVBoxLayout(self.manga_controls)
        layout.addWidget(self.manga_controls)
        self.python = QLineEdit(owner.settings['manga_python'])
        self.model = QLineEdit(owner.settings['manga_model'])
        manga_layout.addWidget(QLabel(t('Python MangaOCR (por defecto entorno propio .venv-mangaocr):')))
        manga_layout.addWidget(self.python)
        manga_layout.addWidget(QLabel(t('Modelo local MangaOCR:')))
        manga_layout.addWidget(self.model)
        self.add_button(manga_layout, t('Elegir modelo local…'), self.choose_model)
        self.add_button(manga_layout, t('Preparar entorno propio MangaOCR CPU…'), self.runtime)
        self.add_button(manga_layout, t('Descargar modelo verificado…'), self.download)
        self.add_button(layout, t('Comprobar requisitos / carga e inferencia'), self.probe)
        self.status = QPlainTextEdit()
        self.status.setReadOnly(True)
        layout.addWidget(self.status)
        self.add_button(layout, t('Cancelar preparación en curso'), self.cancel)
        self.add_button(layout, t('Guardar OCR y continuar'), self.save)
        self.add_button(layout, t('Preparar traducción local…'), lambda: self.open_resource(t('Traducción')))
        self.add_button(layout, t('Importar diccionarios…'), lambda: self.open_resource(t('Diccionarios')))
        self.add_button(layout, t('Cerrar sin guardar'), self.close)
        self.task = Task(self)
        self.task.result.connect(self.prepared)
        self.task.error.connect(self.status.setPlainText)
        self.task.progress.connect(self.status.setPlainText)
        self.probe_task = Task(self, program=self.python.text(), module='naatik_next.manga_worker')
        self.probe_task.result.connect(self.probed)
        self.probe_task.error.connect(self.status.setPlainText)
        self.engine.currentIndexChanged.connect(self.update_guide)
        self.language.currentIndexChanged.connect(self.update_guide)
        self.update_guide()
        self.show_requirements()

    def update_guide(self):
        manga = self.engine.currentData() == 'mangaocr'
        self.manga_controls.setVisible(manga)
        self.language.setEnabled(not manga)
        if manga:
            text = (t('1. Prepara el entorno MangaOCR CPU.\n2. Descarga el modelo verificado o elige uno local completo.\n3. Comprueba carga e inferencia. 4. Guarda el OCR.\nMangaOCR reconoce japonés; no necesita los datos de Tesseract.'))
        else:
            code = self.language.currentData()
            text = ((t('1. Instala Tesseract y los datos del idioma ') + f'{code}' + t(' con el gestor de paquetes de tu sistema.\n2. Pulsa Comprobar requisitos y revisa que el idioma aparezca disponible.\n3. Guarda el OCR y prueba una imagen en Captura y resultado.\nEste asistente no instala paquetes del sistema.')))
        self.guide.setText(text + t('\nTraducción y diccionarios son opcionales y se preparan por separado con los botones inferiores.'))

    def open_resource(self, title):
        if not self.idle(): return
        for index in range(self.owner.tabs.count()):
            if self.owner.tabs.tabText(index) == title:
                self.owner.tabs.setCurrentIndex(index)
                self.close()
                return

    def probed(self, result):
        records = result if isinstance(result, list) else [result]
        selected = next((item for item in records if isinstance(item, dict)
                         and item.get('id') == self.engine.currentData()), None)
        if selected is None:
            self.status.setPlainText(t('No se obtuvo un diagnóstico del motor seleccionado. Reintenta la comprobación.'))
            return
        text = f"{selected.get('name', selected['id'])}: {t(selected.get('status', 'sin comprobar'))}\n{selected.get('detail', '')}"
        if selected['id'] == 'tesseract':
            languages = selected.get('languages', [])
            text += t('\nIdiomas disponibles: ') + (', '.join(languages) or 'ninguno')
            if self.language.currentData() not in languages:
                text = t('Requiere atención: faltan los datos del idioma elegido.\n') + text
                text += t('\nInstala esos datos y vuelve a comprobar.')
            else:
                text += t('\nGuarda las elecciones y prueba una imagen con el idioma elegido.')
        elif selected.get('status') == 'listo':
            text += t('\nCarga e inferencia comprobadas. Puedes guardar el OCR.')
        self.status.setPlainText(text)

    def add_button(self, layout, title, callback):
        button = QPushButton(title)
        button.clicked.connect(callback)
        layout.addWidget(button)

    def show_requirements(self):
        import os
        self.status.setPlainText(
            ('Host: ' + f'{platform.system()}' + ' ' + f'{platform.machine()}' + '; Python ' + f'{sys.version.split()[0]}' + '\nTesseract: ' + f"{shutil.which('tesseract') or 'falta; instala tesseract y datos jpn/eng/spa'}" + t('\nCaptura: KDE/X11 con Spectacle 6; sesión ') + f"{os.environ.get('XDG_SESSION_TYPE', 'desconocida')}" + '\nSpectacle: ' + f"{shutil.which('spectacle') or 'falta; Abrir imagen sigue disponible'}" + t('\nPresencia de un comando no acredita Listo. OCR se prueba mediante inferencia.\nArgos necesita modelos locales por ruta; Diccionarios importa tus ZIP, no se incluyen datos.\nGPU, Wayland y otras plataformas no acreditados por esta entrega.')))

    def idle(self):
        if self.task.busy or self.probe_task.busy:
            self.status.setPlainText(t('Espera o cancela la preparación actual antes de iniciar otra.'))
            return False
        return True

    def choose_model(self):
        if not self.idle(): return
        path = QFileDialog.getExistingDirectory(self, t('Modelo MangaOCR local'), self.model.text())
        if path: self.model.setText(path)

    def runtime(self):
        if not self.idle(): return
        if QMessageBox.question(self, t('Preparar runtime CPU'),
                t('Instalar en .venv-mangaocr propio las 43 dependencias fijadas por hash (~301 MB de ruedas; más espacio al instalar).\nFuentes: PyPI y download.pytorch.org. Licencias y avisos en docs/THIRD_PARTY_DEPENDENCIES.md.\nLa variante CPU de Python 3.14 todavía no pudo validarse en este entorno sin red.\n¿Continuar?'),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        self.python.setText(defaults()['manga_python'])
        self.status.setPlainText(t('Preparando runtime CPU propio; espera o cancela. No se acredita OCR todavía.'))
        self.task.start({'action': 'prepare_runtime'}, 960000)

    def download(self):
        if not self.idle(): return
        spec = catalogue()
        size = sum(item['bytes'] for item in spec['files'])
        if QMessageBox.question(self, t('Confirmar descarga de modelo'),
                (f"{spec['id']}" + t('\nRevisión: ') + f"{spec['revision']}" + '\n' + f'{size:,}' + ' bytes\n' + f"{spec['license']}" + t('\nFuente/licencia: ') + f"{spec['license_source']}" + t('\nDestino propio: ') + f"{defaults()['manga_model']}" + t('\nNo se envía texto ni imágenes. Los parciales se conservan para reintentar.\n¿Descargar?')),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        self.status.setPlainText(t('Preparando descarga verificada; espera o cancela.'))
        self.task.start({'action': 'prepare_model'}, 1800000)

    def prepared(self, result):
        if isinstance(result, list):
            self.probed(result)
            return
        if isinstance(result, dict) and 'model' in result:
            self.model.setText(result['model'])
        self.status.setPlainText(str(result) + t('\nFalta probar carga e inferencia para acreditar OCR listo.'))

    def probe(self):
        if not self.idle(): return
        self.show_requirements()
        if self.engine.currentData() == 'mangaocr':
            self.probe_task.program = self.python.text().strip()
            self.probe_task.start({'action': 'detect', 'model': self.model.text().strip()}, 180000)
        else:
            self.task.start({'action': 'detect'}, 120000)

    def save(self):
        if not self.idle(): return
        owner = self.owner
        if any(task.busy for task in (owner.ocr_task, owner.manga_task, owner.detect_task)):
            self.status.setPlainText(t('Espera a que termine la detección/OCR principal antes de guardar.'))
            return
        owner.settings.update(manga_python=self.python.text().strip(), manga_model=self.model.text().strip(),
                              ocr_language=self.language.currentData(), ocr_engine=self.engine.currentData(), setup_completed=True)
        owner.manga_python_field.setText(owner.settings['manga_python'])
        owner.manga_model_field.setText(owner.settings['manga_model'])
        owner.persist()
        owner.redetect()
        self.close()

    def cancel(self):
        self.task.cancel()
        self.probe_task.cancel()

    def closeEvent(self, event):
        self.task.close()
        self.probe_task.close()
        event.accept()
