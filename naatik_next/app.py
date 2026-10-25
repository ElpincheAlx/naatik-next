from .i18n import t
from . import timings
if timings.enabled():
    timings.enable()

import argparse
import base64
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import shlex
from pathlib import Path
import sys
import time
import tempfile

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QImage, QImageReader, QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QPlainTextEdit, QComboBox, QFileDialog, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QSpinBox, QLineEdit,
    QMessageBox, QSplitter, QGroupBox, QKeySequenceEdit, QSystemTrayIcon, QMenu, QStyle, QScrollArea, QStackedWidget)
from .processes import Task
from .hotkey import GlobalShortcut, DEFAULT_SHORTCUT, combination
from .instance import Instance
from .shutdown_signals import ShutdownSignals
from .integrations import (write_action_script, write_action_desktop,
                           action_command, profile_environment, ACTIONS)
from .preview import ImagePreview
from .dictionary_view import DictionaryView
from .dictionary_content import render_results
from .dictionary_import_dialog import ImportReview, NAMES
from .manga import defaults as manga_defaults, descriptor as manga_descriptor
from .storage import Store, UserError, load_settings, save_settings, paths


def button(text, callback, layout):
    b = QPushButton(text)
    b.clicked.connect(callback)
    layout.addWidget(b)
    return b


def row(layout):
    r = QHBoxLayout()
    layout.addLayout(r)
    return r


def plain():
    label = QLabel()
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


class Window(QMainWindow):
    def __init__(self, *, background=False, popup_only=False, startup_action="show"):
        super().__init__()
        self.background = background
        self.popups = {}
        self.popup_tasks = []
        self.ocr_deferred = popup_only
        self.interrupted = lambda: False
        self.resident = background
        self.copy_job = None
        self.copy_capture_error_pending = False
        self.copy_ocr_error_pending = False
        self.pending_copy_capture = False
        self.preparing_engine = None
        self.preparation_generation = None
        self.copy_prepare_error_pending = False
        self.startup_argos_started = False
        self.pending_capture_ocr = None
        self.capture_trace = None
        self.notice = None
        self.setWindowTitle(t('Na’atik Next — OCR y traducción local'))
        self.resize(1080, 820)
        self.temp = tempfile.TemporaryDirectory(prefix='naatik-next-')
        self.image_path = None
        self.raw_text = ''
        self.ocr_generation = 0
        self.ocr_pending = None
        self.engines = []
        self.manga_status = None
        self.manga_action = None
        self.routes = []
        self.tasks = []
        self.translated_source = None
        self.startup_detection_started = False
        self.pending_external_capture = False
        self.capture_request_timer = QTimer(self)
        self.capture_request_timer.setSingleShot(True)
        self.capture_request_timer.timeout.connect(self.flush_external_capture)
        self.closing = False
        self.capture_active = False
        self.capture_auto_ocr = False
        self.capture_previous_state = None
        self.import_queue = []
        self.current_import = None
        self.selection_generation = 0
        self.selection_pending = None
        self.selection_running = None
        self.selection_query_term = None
        self.store = None if background else Store()
        try:
            self.settings = load_settings()
        except UserError as e:
            self.settings = {}
            QTimer.singleShot(0, lambda message=str(e): self.fail(message))
        from .tutorial import initial_state
        tutorial_state = initial_state(self.settings)
        from .i18n import set_language
        set_language(self.settings.get('ui_language', 'es'))
        self.setWindowTitle(t('Na’atik Next — OCR y traducción local'))
        self.needs_setup = not self.settings or self.settings.get("setup_completed") is False
        if not self.settings:
            self.settings["setup_completed"] = False
        self.settings['tutorial'] = tutorial_state
        self.settings.setdefault('auto_copy_ocr', True)
        for key, value in manga_defaults().items():
            self.settings.setdefault(key, value)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.make_capture()
        self.make_dicts()
        self.make_ocr()
        self.make_prefs()
        self.make_integrations()
        from .anki_ui import AnkiSection
        self.anki_section = AnkiSection(self)
        anki_scroll = QScrollArea(); anki_scroll.setWidgetResizable(True)
        anki_scroll.setWidget(self.anki_section)
        self.anki_section.parent_scroll = anki_scroll
        self.tabs.addTab(anki_scroll, 'Anki')
        from .appearance_ui import AppearanceSection
        self.appearance_section = AppearanceSection(self)
        appearance_scroll = QScrollArea(); appearance_scroll.setWidgetResizable(True)
        appearance_scroll.setWidget(self.appearance_section)
        self.tabs.addTab(appearance_scroll, t('Apariencia'))
        self.appearance_section.apply_saved()
        self.capture_task = self.task(self.captured, persistent=True)
        self.capture_task.error.disconnect(self.fail)
        self.capture_task.error.connect(self.capture_failed)
        self.capture_delay = QTimer(self)
        self.capture_delay.setSingleShot(True)
        self.capture_delay.timeout.connect(self.start_capture_worker)
        self.shortcut = GlobalShortcut(self)
        self.shortcut.activated.connect(self.global_capture)
        self.action_shortcuts = {}
        for action in ACTIONS:
            shortcut = GlobalShortcut(self)
            shortcut.activated.connect(lambda action=action: self.global_action(action))
            self.action_shortcuts[action] = shortcut
        self.ocr_task = self.task(self.recognized, persistent=True)
        self.ocr_task.error.disconnect(self.fail)
        self.ocr_task.error.connect(self.ocr_failed)
        self.manga_task = self.task(self.manga_result, persistent=True,
                                    program=self.settings['manga_python'], module='naatik_next.manga_worker')
        self.manga_task.error.disconnect(self.fail)
        self.manga_task.error.connect(self.ocr_failed)
        self.manga_task.error.connect(self.manga_failed)
        self.detect_task = self.task(self.detected)
        self.detect_task.error.disconnect(self.fail)
        self.detect_task.error.connect(self.engine_preparation_failed)
        self.import_task = self.task(self.imported)
        self.import_task.error.disconnect(self.fail)
        self.import_task.error.connect(self.import_failed)
        self.inspect_task = self.task(self.dictionaries_inspected)
        self.inspect_task.error.disconnect(self.fail)
        self.inspect_task.error.connect(self.inspection_failed)
        self.inspect_task.busy_changed.connect(self.dict_controls)
        self.inspect_task.progress.connect(self.import_status.setText)
        self.lookup_task = self.task(self.looked_up)
        # One managed worker, with at most one pending (newest) request.
        self.selection_task = Task(self)
        self.tasks.append(self.selection_task)
        self.selection_task.result.connect(self.selection_result)
        self.selection_task.error.connect(self.selection_error)
        self.selection_task.busy_changed.connect(self.busy_changed)
        self.dictionary_action_task = self.task(self.dictionary_changed)
        self.dictionary_action_task.busy_changed.connect(self.dict_controls)
        from .translation_runtime import program as translation_program
        self.argos_task = self.task(self.argos_result, persistent=True,program=translation_program())
        self.argos_action = None
        self.import_task.busy_changed.connect(lambda busy: self.dict_controls(busy))
        self.import_task.progress.connect(self.import_status.setText)
        self.import_task.error.connect(self.import_status.setText)
        self.capture_task.busy_changed.connect(self.update_capture_controls)
        self.ocr_task.busy_changed.connect(self.update_ocr_controls)
        self.manga_task.busy_changed.connect(self.update_ocr_controls)
        self.detect_task.busy_changed.connect(self.update_ocr_controls)
        for task in (self.detect_task, self.manga_task):
            task.busy_changed.connect(lambda busy: self.capture_request_timer.start(0) if not busy and (self.pending_external_capture or self.pending_copy_capture) else None)
        self.argos_task.busy_changed.connect(lambda busy: self.translate_btn.setEnabled(not busy))
        if not background:
            self.dict_refresh()
        self.apply_saved_shortcut()
        for action in self.action_shortcuts:
            self.apply_action_shortcut(action)
        actions_menu = self.menuBar().addMenu(t('Acciones'))
        for action, title in ACTIONS.items():
            entry = actions_menu.addAction(t(title))
            entry.triggered.connect(lambda checked=False, action=action: self.external_command(action))
        actions_menu.addSeparator()
        actions_menu.addAction(t('Ocultar en bandeja'), self.hide_to_tray)
        actions_menu.addAction(t('Salir de Next'), self.quit_background)
        if self.resident:
            self.ensure_tray()
        self.diagnostics()
        if not popup_only:
            QTimer.singleShot(0, self.prepare_selected)
        timings.event("window_ready")
        help_menu = self.menuBar().addMenu(t('Ayuda'))
        help_menu.addAction(t('Tutorial y configuración inicial'), self.show_tutorial)
        settings_menu = self.menuBar().addMenu(t('Configuración'))
        settings_menu.addAction(t('Idioma'), self.choose_language)
        from .tutorial import automatic
        if startup_action == 'show' and automatic(tutorial_state, background=background, popup_only=popup_only):
            QTimer.singleShot(0, self.show_tutorial)

    def show_tutorial(self):
        from .tutorial import open_tutorial
        open_tutorial(self)

    def choose_language(self):
        from .i18n import choose_language, set_language, translate_widgets
        choice = choose_language(self, self.settings.get('ui_language', 'es'))
        if choice is None:
            return
        candidate = dict(self.settings, ui_language=choice)
        try:
            save_settings(candidate)
        except Exception as error:
            self.fail(str(error))
            return
        self.settings['ui_language'] = choice
        set_language(choice)
        translate_widgets(self)

    def task(self, callback, persistent=False, **kwargs):
        task = Task(self, persistent, **kwargs)
        self.tasks.append(task)
        task.result.connect(callback)
        task.error.connect(self.fail)
        task.busy_changed.connect(self.busy_changed)
        task.progress.connect(self.statusBar().showMessage)
        return task

    def fail(self, message):
        if self.closing:
            return
        timings.event('failed', self.capture_trace)
        if self.copy_job is not None:
            self.finish_copy_capture(message)
            return
        if self.background or self.pending_copy_capture:
            self.pending_copy_capture = False
            self.notify_configuration(message)
            return
        self.showNormal() if self.isMinimized() or not self.isVisible() else None
        self.statusBar().showMessage(message)
        logging.error('%s', message)
        QMessageBox.warning(self, 'Na’atik Next', message)

    def busy_changed(self, *args):
        busy = any(t.busy for t in self.tasks)
        self.progress.setRange(0, 0 if busy else 1)
        self.progress.setValue(0 if busy else 1)
        self.cancel_btn.setEnabled(busy)
        if (self.statusBar().currentMessage() != t('Texto reconocido y copiado')
                or (busy and self.sender() not in (self.argos_task, self.selection_task))):
            self.statusBar().showMessage(t('Procesando localmente…') if busy else t('Listo'))

    def cancel(self):
        if self.copy_job is not None:
            self.copy_prepare_error_pending = self.preparing_engine is not None
            self.finish_copy_capture()
        self.preparation_generation = None
        self.preparing_engine = None
        self.engine.setEnabled(True)
        self.pending_copy_capture = False
        self.pending_capture_ocr = None
        timings.event("cancelled", self.capture_trace)
        self.ocr_pending = None
        self.invalidate_dictionary_lookup()
        for entry in self.import_queue:
            self.import_report.appendPlainText(Path(entry['path']).name + t(': no iniciado por cancelación.'))
        self.import_queue = []
        self.pending_external_capture = False
        self.capture_request_timer.stop()
        if self.capture_active:
            self.capture_delay.stop()
            self.capture_failed(t('Operación de captura cancelada.'))
        for task in self.tasks:
            task.cancel()

    def make_capture(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        r = row(layout)
        self.capture_btn = button(t('Seleccionar región'), lambda: self.capture_and_recognize(), r)
        button(t('Abrir imagen…'), self.open_image, r)
        self.engine_caption = plain()
        r.addWidget(self.engine_caption, 1)
        self.recognize_btn = button(t('Reconocer'), self.recognize, r)
        self.preview = ImagePreview()
        layout.addWidget(self.preview)
        self.image_caption = plain()
        layout.addWidget(self.image_caption)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        r = row(layout)
        r.addWidget(self.progress, 1)
        self.cancel_btn = button(t('Cancelar operaciones'), self.cancel, r)
        self.cancel_btn.setEnabled(False)
        self.provenance = plain()
        self.provenance.setText(t('Sin resultado OCR. Puedes escribir texto para traducirlo.'))
        layout.addWidget(self.provenance)
        splitter = QSplitter(Qt.Horizontal)
        left, right = QWidget(), QWidget()
        ll, rl = QVBoxLayout(left), QVBoxLayout(right)
        ll.addWidget(QLabel(t('Texto para revisar y traducir (editable)')))
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(t('El texto reconocido aparecerá aquí. Las correcciones no cambian el original OCR.'))
        self.editor.textChanged.connect(self.text_changed)
        ll.addWidget(self.editor)
        self.selection_action = QAction(t('Consultar selección'), self.editor)
        self.selection_action.setEnabled(False)
        self.selection_action.triggered.connect(self.lookup_selection)
        self.editor.selectionChanged.connect(self.selection_changed)
        self.editor.setContextMenuPolicy(Qt.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.selection_menu)
        self.selection_btn = button(t('Consultar selección'), self.lookup_selection, ll)
        self.selection_btn.setEnabled(False)
        self.selection_hint = plain()
        self.selection_hint.setText(t('Selecciona una palabra o expresión en el editor y pulsa Consultar selección.'))
        ll.addWidget(self.selection_hint)
        self.dictionary_setup_btn = button(t('Importar o activar diccionarios…'), self.open_dictionary_configuration, ll)
        self.dictionary_setup_btn.hide()
        r = row(ll)
        button(t('Copiar texto'), lambda: QApplication.clipboard().setText(self.editor.toPlainText()), r)
        button(t('Ver original OCR'), self.show_original, r)
        rl.addWidget(QLabel(t('Traducción de la frase — Argos local')))
        self.target = QComboBox()
        self.target.currentIndexChanged.connect(self.route_changed)
        rl.addWidget(self.target)
        self.route_caption = plain()
        rl.addWidget(self.route_caption)
        self.translation = QPlainTextEdit()
        self.translation.setReadOnly(True)
        rl.addWidget(self.translation)
        self.translate_btn = button(t('Traducir texto revisado'), self.translate, rl)
        splitter.addWidget(left)
        splitter.addWidget(right)
        layout.addWidget(splitter, 2)
        layout.addWidget(QLabel(t('Resultados de diccionario — consulta exacta OCR o selección (separados de Argos)')))
        self.selection_definitions = DictionaryView()
        self.selection_definitions.setReadOnly(True)
        layout.addWidget(self.selection_definitions, 1)
        self.translation_status = plain()
        layout.addWidget(self.translation_status)
        self.tabs.addTab(page, t('Captura y resultado'))

    def selected_term(self):
        return self.editor.textCursor().selectedText().replace('\u2029', '\n')

    def invalidate_dictionary_lookup(self):
        self.selection_generation += 1
        self.selection_pending = None
        self.selection_query_term = None
        self.dictionary_setup_btn.hide()

    def selection_changed(self):
        self.invalidate_dictionary_lookup()
        selected = bool(self.selected_term())
        self.selection_action.setEnabled(selected)
        self.selection_btn.setEnabled(selected)
        self.selection_definitions.clear()
        self.selection_hint.setText(t('Pulsa Consultar selección para consultar el texto seleccionado.') if selected
                                    else t('Selecciona una palabra o expresión en el editor y pulsa Consultar selección.'))

    def selection_menu(self, position):
        menu = self.editor.createStandardContextMenu()
        menu.addSeparator()
        menu.addAction(self.selection_action)
        menu.exec(self.editor.mapToGlobal(position))
        menu.deleteLater()

    def lookup_selection(self):
        term = self.selected_term()
        if not term:
            return
        self.lookup_dictionary_text(term, automatic=False)

    def lookup_dictionary_text(self, term, *, automatic):
        if not term.strip():
            return
        self.selection_generation += 1
        self.selection_query_term = term
        self.selection_pending = {'action': 'lookup_selection', 'term': term,
                                  'generation': self.selection_generation}
        self.selection_definitions.clear()
        self.dictionary_setup_btn.hide()
        self.selection_hint.setText(t('Consultando texto OCR completo (coincidencia exacta)…') if automatic
                                    else t('Consultando selección en los diccionarios activos…'))
        self.start_selection_lookup()

    def start_selection_lookup(self):
        if self.selection_pending is not None and not self.selection_task.busy:
            self.selection_running = self.selection_pending
            self.selection_pending = None
            self.selection_task.start(self.selection_running, 30000)

    def selection_result(self, result):
        if (not self.closing and result['generation'] == self.selection_generation
                and result['term'] == self.selection_query_term):
            self.dictionary_setup_btn.setVisible(not result['active'])
            if not result['active']:
                self.selection_definitions.setPlainText(t('No hay diccionarios activos para consultar este texto. Importa un ZIP Yomitan o activa uno de los diccionarios ya importados con «Importar o activar diccionarios…».'))
            elif not result['results']:
                self.selection_definitions.setPlainText(t('Sin coincidencias exactas en los diccionarios activos.'))
            else:
                try:
                    self.selection_definitions.setHtml(render_results(result['results']))
                except UserError as e:
                    self.selection_definitions.setPlainText(str(e))
            self.selection_hint.setText(t('Falta importar o activar un diccionario para consultar el texto.') if not result['active']
                                        else t('Consulta de diccionario terminada (máximo 100 resultados).'))
        self.start_selection_lookup()

    def selection_error(self, message):
        if self.selection_running and self.selection_running['generation'] == self.selection_generation:
            self.selection_definitions.setPlainText(t('Consulta de diccionario: ') + message)
            self.selection_hint.setText(t('Puedes volver a consultar la selección.'))
        self.start_selection_lookup()

    def open_dictionary_configuration(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.tabs.setCurrentWidget(self.dictionary_tab)
        self.dict_refresh()

    def make_dicts(self):
        page = QWidget()
        self.dictionary_tab = page
        layout = QVBoxLayout(page)
        info = plain()
        info.setText(t('Yomitan v3: términos/bilingües, gramática por consulta exacta, kanji y acento tonal. Frecuencia/IPA y medios no se consultan; la revisión informa omisiones. No se ejecuta contenido ni se modifica el ZIP original.'))
        layout.addWidget(info)
        r = row(layout)
        self.add_dict = button(t('Agregar diccionarios'), self.add_dictionary, r)
        self.remove_dict = button(t('Quitar copia administrada'), self.remove_dictionary, r)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([t('Nombre / revisión'), t('Idiomas'), t('Entradas'), t('Estado'), t('Activo'), t('Prioridad ↑')])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.import_status = plain()
        layout.addWidget(self.import_status)
        self.import_report = QPlainTextEdit()
        self.import_report.setReadOnly(True)
        self.import_report.setMaximumHeight(120)
        self.import_report.document().setMaximumBlockCount(1000)
        self.import_report.setPlaceholderText(t('Resultado individual por archivo de la última selección.'))
        layout.addWidget(self.import_report)
        r = row(layout)
        self.query = QLineEdit()
        self.query.setPlaceholderText(t('Palabra, lectura, expresión gramatical o kanji exacto; sin análisis de frases'))
        self.query.returnPressed.connect(self.lookup)
        r.addWidget(self.query)
        button(t('Consultar activos'), self.lookup, r)
        self.definitions = DictionaryView()
        self.definitions.setReadOnly(True)
        layout.addWidget(self.definitions)
        self.tabs.addTab(page, t('Diccionarios'))

    def make_ocr(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.engine = QComboBox()
        self.engine.currentIndexChanged.connect(self.engine_changed)
        layout.addWidget(self.engine)
        r = row(layout)
        r.addWidget(QLabel(t('Idioma del adaptador')))
        self.ocr_language = QComboBox()
        self.ocr_language.currentTextChanged.connect(self.language_changed)
        r.addWidget(self.ocr_language)
        self.detect_btn = button(t('Volver a detectar y probar'), self.redetect, r)
        button(t('Probar imagen…'), self.test_image, r)
        self.engine_detail = QPlainTextEdit()
        self.engine_detail.setReadOnly(True)
        layout.addWidget(self.engine_detail)
        info = plain()
        info.setText(t('Tesseract: PSM 6 e idioma seleccionable; jpn_vert usa datos verticales. MangaOCR: japonés fijo, sin controles de idioma/dirección; modelo residente en worker propio de Next, CPU y sin red. La captura prepara solo el motor elegido; Volver a detectar y probar añade una inferencia de diagnóstico. PaddleOCR sigue pendiente. No hay cambio automático de motor.'))
        layout.addWidget(info)
        self.tabs.addTab(page, t('OCR'))

    def save_auto_copy(self, enabled):
        previous = self.settings.get('auto_copy_ocr', True)
        self.settings['auto_copy_ocr'] = enabled
        try:
            save_settings(self.settings)
        except (OSError, UserError) as e:
            self.settings['auto_copy_ocr'] = previous
            self.auto_copy.blockSignals(True)
            self.auto_copy.setChecked(previous)
            self.auto_copy.blockSignals(False)
            self.fail(str(e))

    def show_setup(self):
        if self.closing:
            return
        from .setup_dialog import SetupDialog
        if not hasattr(self, "setup_dialog") or not self.setup_dialog.isVisible():
            if hasattr(self, "setup_dialog"):
                self.setup_dialog.deleteLater()
            self.setup_dialog = SetupDialog(self)
        self.setup_dialog.show()
        self.setup_dialog.raise_()

    def make_prefs(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.auto_copy = QCheckBox(t('Copiar automáticamente al terminar OCR'))
        self.auto_copy.setChecked(self.settings.get('auto_copy_ocr', True))
        self.auto_copy.toggled.connect(self.save_auto_copy)
        layout.addWidget(self.auto_copy)
        button(t('Asistente de idioma y preparación OCR…'), self.show_setup, layout)
        group = QGroupBox(t('Recursos locales de MangaOCR (uso de solo lectura)'))
        ml = QVBoxLayout(group)
        ml.addWidget(QLabel(t('Python con manga-ocr instalado:')))
        self.manga_python_field = QLineEdit(self.settings['manga_python'])
        ml.addWidget(self.manga_python_field)
        ml.addWidget(QLabel(t('Directorio del snapshot local completo:')))
        self.manga_model_field = QLineEdit(self.settings['manga_model'])
        ml.addWidget(self.manga_model_field)
        button(t('Elegir directorio del modelo…'), self.choose_manga_model, ml)
        button(t('Guardar recursos y volver a probar OCR'), self.save_manga_resources, ml)
        layout.addWidget(group)
        self.argos_detail = plain()
        from .translation_dialog import TranslationSection
        self.translation_section = TranslationSection(self)
        translation_scroll = QScrollArea(); translation_scroll.setWidgetResizable(True)
        translation_scroll.setWidget(self.translation_section)
        self.translation_tab = translation_scroll
        self.tabs.addTab(translation_scroll, t('Traducción'))
        self.tabs.currentChanged.connect(self.translation_tab_changed)
        label = plain()
        label.setText(t('Se guardan automáticamente motor e idioma OCR, ruta de traducción y activación/prioridad de diccionarios. Los asistentes OCR y Traducción descargan recursos solo con confirmación; el procesamiento de texto e imágenes es local.'))
        layout.addWidget(label)
        button(t('Actualizar diagnóstico'), self.diagnostics, layout)
        button(t('Abrir log'), self.open_log, layout)
        self.diagnostic_text = QPlainTextEdit()
        self.diagnostic_text.setReadOnly(True)
        layout.addWidget(self.diagnostic_text)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page)
        self.tabs.addTab(scroll, t('Preferencias y diagnóstico'))

    def make_integrations(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel(t('Integraciones')); title.setStyleSheet('font-size:24px;font-weight:600'); layout.addWidget(title)
        selection = row(layout); selection.addWidget(QLabel(t('Acción')))
        self.integration_action = QComboBox(); self.integration_action.setAccessibleName(t('Acción'))
        for action, title in ACTIONS.items(): self.integration_action.addItem(t(title), action)
        selection.addWidget(self.integration_action, 1)
        help_text = plain()
        help_text.setText(t('Los atajos internos funcionan mientras Next está ejecutándose, también en la bandeja.\nLos comandos, scripts y accesos directos pueden iniciar Next cerrado.'))
        layout.addWidget(help_text)

        shortcuts = QGroupBox(t('Atajo de teclado')); sl = QVBoxLayout(shortcuts)
        self.action_shortcut_fields, self.action_shortcut_status = {}, {}
        self.shortcut_pages = QStackedWidget(); sl.addWidget(self.shortcut_pages)
        for action in ACTIONS:
            entry = QWidget(); box = QVBoxLayout(entry); box.setContentsMargins(0, 0, 0, 0)
            field = QKeySequenceEdit(QKeySequence(self.settings.get(action.replace('-', '_')+'_shortcut', '')))
            field.setMaximumSequenceLength(1); field.setAccessibleName(t('Combinación: ')+t(ACTIONS[action])); box.addWidget(field)
            status = plain(); box.addWidget(status)
            self.action_shortcut_fields[action] = field; self.action_shortcut_status[action] = status
            self.shortcut_pages.addWidget(entry)
        controls = row(sl)
        button(t('Guardar'), lambda: self.save_action_shortcut(self.integration_action.currentData()), controls)
        button(t('Desactivar'), lambda: self.disable_action_shortcut(self.integration_action.currentData()), controls)
        layout.addWidget(shortcuts)

        scripts = QGroupBox(t('Script y acceso directo')); gl = QVBoxLayout(scripts)
        controls = row(gl)
        button(t('Crear script…'), lambda: self.create_action_script(self.integration_action.currentData()), controls)
        button(t('Copiar comando'), self.copy_integration_command, controls)
        button(t('Crear acceso directo…'), lambda: self.create_action_desktop(self.integration_action.currentData()), controls)
        self.script_pages = QStackedWidget(); gl.addWidget(self.script_pages)
        self.command_pages = QStackedWidget(); self.command_pages.setMaximumHeight(125)
        self.integration_fields = {}
        folder_row = row(gl)
        self.integration_open = button(t('Abrir carpeta'), lambda: self.open_action_folder(self.integration_action.currentData()), folder_row)
        self.integration_copy_path = button(t('Copiar ruta'), self.copy_integration_path, folder_row)
        self.integration_copy_path.setFlat(True)
        for action in ACTIONS:
            entry = QWidget(); box = QVBoxLayout(entry); box.setContentsMargins(0, 0, 0, 0)
            box.addWidget(QLabel(t('Ubicación del script')))
            key = 'stream_deck_script' if action == 'capture-copy' else action+'_script'
            path = QLineEdit(self.settings.get(key, '')); path.setReadOnly(True)
            path.setPlaceholderText(t('Todavía no has creado un script para esta acción.')); box.addWidget(path)
            status = plain(); box.addWidget(status)
            desktop = plain()
            if self.settings.get(action+'_desktop'): desktop.setText(t('Acceso directo: ')+self.settings[action+'_desktop'])
            box.addWidget(desktop)
            command = QPlainTextEdit(shlex.quote(path.text()) if path.text() else action_command(action)); command.setReadOnly(True); command.setMaximumHeight(125)
            self.command_pages.addWidget(command); self.script_pages.addWidget(entry)
            self.integration_fields[action] = dict(path=path, command=command, status=status, desktop=desktop,
                                                   copy=self.integration_copy_path, open=self.integration_open)
        layout.addWidget(scripts)

        details = QGroupBox(t('Detalles')); details.setCheckable(True); details.setChecked(False)
        dl = QVBoxLayout(details); body = QWidget(); db = QVBoxLayout(body); dl.addWidget(body)
        db.addWidget(QLabel(t('Comando completo · usa el script guardado si existe')))
        db.addWidget(self.command_pages)
        db.addWidget(QLabel(t('Perfil para nuevos scripts y comandos directos')))
        profile = QPlainTextEdit('\n'.join(key+'='+str(value if value is not None else t('(sin definir)')) for key,value in profile_environment().items()))
        profile.setReadOnly(True); profile.setMaximumHeight(110); db.addWidget(profile)
        legacy = QGroupBox(t('Compatibilidad: atajo anterior de capturar y reconocer')); ll = QVBoxLayout(legacy)
        note = plain(); note.setText(t('Conserva su configuración y el recorrido anterior de captura con resultado en la ventana principal.')); ll.addWidget(note)
        self.shortcut_field = QKeySequenceEdit(QKeySequence(self.settings.get('capture_shortcut', DEFAULT_SHORTCUT)))
        self.shortcut_field.setMaximumSequenceLength(1); ll.addWidget(self.shortcut_field)
        controls = row(ll); button(t('Guardar'), self.save_shortcut, controls); button(t('Desactivar'), self.disable_shortcut, controls)
        self.shortcut_status = plain(); ll.addWidget(self.shortcut_status); db.addWidget(legacy)
        details.toggled.connect(body.setVisible); body.hide(); layout.addWidget(details)
        how = QGroupBox(t('Cómo configurarlo')); how.setCheckable(True); how.setChecked(False)
        hl = QVBoxLayout(how); instructions = plain()
        instructions.setText(t('Para usar un atajo con Next cerrado, crea un acceso directo o copia el comando de esta acción. En KDE: Preferencias del sistema → Teclado → Atajos; asigna ese acceso/comando a una combinación libre.\n\nStreamController: OS → Run Command. Pega Copiar comando, activa Detached/Separado y usa repetición 0.\n\nGuardar solo registra el atajo interno de Next. No cambia atajos de KDE, botones de StreamController ni inicio automático.'))
        hl.addWidget(instructions); how.toggled.connect(instructions.setVisible); instructions.hide(); layout.addWidget(how)
        layout.addStretch()
        self.integration_action.currentIndexChanged.connect(self.integration_action_changed)
        self.integration_action_changed()
        capture = self.integration_fields['capture-copy']
        self.stream_script_path, self.stream_command = capture['path'], capture['command']
        self.stream_copy, self.stream_open, self.stream_status = capture['copy'], capture['open'], capture['status']
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page)
        self.integrations_tab = scroll
        self.tabs.addTab(scroll, t('Integraciones'))

    def integration_action_changed(self):
        index = self.integration_action.currentIndex()
        self.shortcut_pages.setCurrentIndex(index); self.script_pages.setCurrentIndex(index); self.command_pages.setCurrentIndex(index)
        has_path = bool(self.integration_fields[self.integration_action.currentData()]['path'].text())
        self.integration_open.setVisible(has_path); self.integration_copy_path.setVisible(has_path)

    def copy_integration_command(self):
        QApplication.clipboard().setText(self.integration_fields[self.integration_action.currentData()]['command'].toPlainText())

    def copy_integration_path(self):
        QApplication.clipboard().setText(self.integration_fields[self.integration_action.currentData()]['path'].text())

    def open_action_folder(self, action):
        text = self.integration_fields[action]['path'].text()
        if text and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(text).parent))):
            self.integration_fields[action]['status'].setText(t('No se pudo abrir la carpeta; copia su ruta.'))

    def create_action_script(self, action):
        fields = self.integration_fields[action]
        suggested = fields['path'].text() or str(Path.home() / ('naatik-next-'+action+'.sh'))
        filename, _ = QFileDialog.getSaveFileName(self, t('Crear script: ')+t(ACTIONS[action]), suggested,
                t('Script (*.sh)'), options=QFileDialog.DontConfirmOverwrite)
        if not filename: return
        overwrite = Path(filename).exists() or Path(filename).is_symlink()
        if not self.confirm_integration_overwrite(filename): return
        try:
            path = write_action_script(filename, action, overwrite=overwrite)
            fields['path'].setText(str(path)); fields['command'].setPlainText(shlex.quote(str(path)))
            fields['copy'].setEnabled(True); fields['open'].setEnabled(True)
            fields['status'].setText(t('Script creado para ')+t(ACTIONS[action])+t('. Asigna este comando en KDE o StreamController.'))
            self.settings['stream_deck_script' if action == 'capture-copy' else action+'_script'] = str(path); self.persist()
            self.integration_action_changed()
        except Exception as error: fields['status'].setText(t('No se creó: ')+str(error))

    def confirm_integration_overwrite(self, filename):
        path = Path(filename)
        return not (path.exists() or path.is_symlink()) or QMessageBox.question(self,
            t('Sobrescribir archivo'), t('Ya existe:\n')+str(path)+t('\n¿Reemplazarlo?'),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def create_action_desktop(self, action):
        directory = paths()['data'].parent / 'applications'
        suggested = self.settings.get(action+'_desktop') or directory / ('org.naatik.Next.'+action+'.desktop')
        filename, _ = QFileDialog.getSaveFileName(self, t('Crear acceso: ')+t(ACTIONS[action]), str(suggested),
                t('Acceso de escritorio (*.desktop)'), options=QFileDialog.DontConfirmOverwrite)
        if not filename: return
        overwrite = Path(filename).exists() or Path(filename).is_symlink()
        if not self.confirm_integration_overwrite(filename): return
        try:
            Path(filename).parent.mkdir(parents=True,exist_ok=True)
            path = write_action_desktop(filename, action, overwrite=overwrite)
            self.settings[action+'_desktop'] = str(path); self.persist()
            self.integration_fields[action]['desktop'].setText(t('Acceso directo: ')+str(path))
            self.integration_fields[action]['status'].setText(t('Acceso directo creado. Puedes asignarlo en KDE.'))
        except Exception as error: self.integration_fields[action]['status'].setText(t('No se creó: ')+str(error))

    def create_stream_script(self):
        return self.create_action_script('capture-copy')

    def copy_stream_path(self):
        QApplication.clipboard().setText(self.stream_script_path.text())

    def open_stream_folder(self):
        text = self.stream_script_path.text()
        if text and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(text).parent))):
            self.stream_status.setText(t('No se pudo abrir la carpeta. Puedes copiar la ruta del script.'))

    def persist(self):
        if self.closing:
            return
        try:
            save_settings(self.settings)
        except Exception as e:
            self.fail((t('No se pudieron guardar las preferencias: ') + f'{e}'))

    def diagnostics(self):
        import platform
        from PySide6 import __version__ as qt_version
        import shutil
        data = paths()
        lines = ['Na’atik Next 0.1.0', f'Python: {platform.python_version()} — {sys.executable}',
                 f'PySide6: {qt_version}', (t('Sesión declarada: ') + f"{os.environ.get('XDG_SESSION_TYPE', 'desconocida')}"),
                 (t('Escritorio: ') + f"{os.environ.get('XDG_CURRENT_DESKTOP', 'desconocido')}"),
                 f'DISPLAY: {os.environ.get("DISPLAY", "ausente")}',
                 f'WAYLAND_DISPLAY: {os.environ.get("WAYLAND_DISPLAY", "ausente")}',
                 f'Spectacle: {shutil.which("spectacle") or "ausente"}',
                 t('Adaptador de captura: Spectacle 6 / KDE X11; validar visualmente en la sesión del usuario.'),
                 t('Sin servicios HTTP ni unidades systemd.'),
                 *[f'{k}: {v}' for k, v in data.items()],
                 f'Log: {data["state"] / "naatik-next.log"}']
        self.diagnostic_text.setPlainText('\n'.join(lines))

    def open_log(self):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths()['state'] / 'naatik-next.log'))):
            self.fail(t('No se pudo abrir el visor de log. La ruta aparece en el diagnóstico.'))

    def open_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, t('Abrir imagen'), '', t('Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)'))
        if not filename:
            return False
        try:
            if Path(filename).stat().st_size > 40 * 1024 * 1024:
                raise UserError(t('La imagen supera 40 MiB.'))
            reader = QImageReader(filename)
            size = reader.size()
            if not size.isValid() or size.width() * size.height() > 40_000_000:
                raise UserError(t('Imagen inválida o superior a 40 megapíxeles.'))
            reader.setAutoTransform(True)
            image = reader.read()
            if image.isNull():
                raise UserError(t('No se puede decodificar la imagen: ') + reader.errorString())
            self.set_image(image, Path(filename).name)
            return True
        except Exception as e:
            self.fail(str(e))
            return False

    def set_image(self, image, description):
        # Immutable unique snapshots let a running OCR finish even if another image is opened.
        import uuid
        path = Path(self.temp.name) / (uuid.uuid4().hex + '.png')
        if not image.save(str(path), 'PNG'):
            raise UserError(t('No se pudo guardar la copia temporal privada.'))
        previous = self.image_path
        self.image_path = str(path)
        if previous and (not (self.ocr_task.busy or self.manga_task.busy) or previous != getattr(self, 'ocr_request_image', None)):
            Path(previous).unlink(missing_ok=True)
        self.preview.set_image(image)
        self.image_caption.setText((f'{description}' + ' · ' + f'{image.width()}' + ' × ' + f'{image.height()}' + t(' · resultado anterior limpiado')))
        self.raw_text = ''
        self.editor.clear()
        self.translation.clear()
        self.translation_status.clear()

    def apply_saved_shortcut(self):
        if not self.settings.get('capture_shortcut_enabled', False):
            self.shortcut_status.setText(t('Desactivado; ninguna combinación registrada.'))
            return
        try:
            text = self.settings.get('capture_shortcut', DEFAULT_SHORTCUT)
            conflict = self.shortcut_conflict('capture', text)
            if conflict: raise UserError(t('Combinación duplicada en Next: ') + conflict)
            self.shortcut.register(text)
            self.shortcut_status.setText(t('Registrado en X11: ') + self.shortcut.active + t('. Comprueba su activación desde otra aplicación.'))
        except Exception as e:
            self.shortcut_status.setText(t('Activo: ninguno. Error de registro: ') + str(e))

    def save_shortcut(self):
        try:
            text, _, _ = combination(self.shortcut_field.keySequence().toString(QKeySequence.PortableText))
        except UserError as e:
            self.shortcut_status.setText((t('Activo: ') + f"{self.shortcut.active or 'ninguno'}" + t('. No se guardó: ') + f'{e}'))
            return
        self.change_shortcut_settings(text, True)

    def change_shortcut_settings(self, text, enabled):
        conflict = self.shortcut_conflict('capture', text) if enabled else None
        if conflict:
            self.shortcut_status.setText(t('No se guardó: combinación duplicada con ') + conflict)
            return
        previous = dict(self.settings)
        self.shortcut.close()
        self.settings.update(capture_shortcut=text, capture_shortcut_enabled=enabled)
        try:
            save_settings(self.settings)
        except Exception as e:
            if not enabled:
                self.shortcut_status.setText(t('Desactivado en esta sesión. No se pudo guardar; al reabrir se leerá la preferencia anterior: ') + str(e))
                return
            self.settings = previous
            self.apply_saved_shortcut()
            self.shortcut_status.setText(self.shortcut_status.text() + t('\nNo se guardaron cambios: ') + str(e))
            return
        self.apply_saved_shortcut()

    def disable_shortcut(self):
        self.change_shortcut_settings(self.settings.get('capture_shortcut', DEFAULT_SHORTCUT), False)

    def restore_shortcut(self):
        self.shortcut_field.setKeySequence(QKeySequence(DEFAULT_SHORTCUT))
        self.shortcut_status.setText((t('Activo: ') + f"{self.shortcut.active or 'ninguno'}" + t('. Valor inicial propuesto: ') + f'{DEFAULT_SHORTCUT}' + t('; pulsa Guardar para activarlo.')))

    def shortcut_conflict(self, action, text):
        normalized = QKeySequence(text).toString(QKeySequence.PortableText)
        for other in ('capture', *ACTIONS):
            key = other.replace('-', '_') + '_shortcut'
            if other != action and self.settings.get(key+'_enabled', False):
                existing = self.settings.get(key, DEFAULT_SHORTCUT if other == 'capture' else '')
                if QKeySequence(existing).toString(QKeySequence.PortableText) == normalized:
                    return other
        return None

    def apply_action_shortcut(self, action):
        key = action.replace('-', '_') + '_shortcut'
        shortcut = self.action_shortcuts[action]
        status = self.action_shortcut_status[action]
        if not self.settings.get(key+'_enabled', False):
            status.setText(t('Desactivado; ninguna combinación registrada.')); return
        try:
            text = self.settings.get(key, '')
            conflict = self.shortcut_conflict(action, text)
            if conflict: raise UserError(t('Combinación duplicada con ') + conflict)
            shortcut.register(text)
            status.setText(t('Registrado en X11: ') + shortcut.active)
        except Exception as error:
            status.setText(t('No registrado: ') + str(error).removeprefix(t('Atajo no registrado: ')))

    def save_action_shortcut(self, action):
        key = action.replace('-', '_') + '_shortcut'
        status = self.action_shortcut_status[action]
        shortcut = self.action_shortcuts[action]
        previous = dict(self.settings)
        try:
            text, _, _ = combination(self.action_shortcut_fields[action].keySequence().toString(QKeySequence.PortableText))
            conflict = self.shortcut_conflict(action, text)
            if conflict: raise UserError(t('Combinación duplicada con ') + conflict)
            shortcut.register(text)
            self.settings.update({key: text, key+'_enabled': True})
            save_settings(self.settings)
            status.setText(t('Registrado en X11: ') + shortcut.active)
        except Exception as error:
            self.settings = previous
            shortcut.close()
            self.apply_action_shortcut(action)
            status.setText(status.text() + t('\nNo se guardó: ') + str(error))

    def disable_action_shortcut(self, action):
        key = action.replace('-', '_') + '_shortcut'
        self.action_shortcuts[action].close()
        self.settings[key+'_enabled'] = False
        try:
            save_settings(self.settings)
        except Exception as error:
            self.action_shortcut_status[action].setText(t('Desactivado en esta sesión. No se pudo guardar; al reabrir se leerá la preferencia anterior: ')+str(error))
            return
        self.action_shortcut_status[action].setText(t('Desactivado; combinación guardada para uso posterior.'))

    def global_action(self, action):
        if QApplication.activeModalWidget() or any(field.hasFocus() for field in self.action_shortcut_fields.values()) or self.shortcut_field.hasFocus():
            return 'ignored'
        return self.external_command(action)

    def global_capture(self):
        editing_shortcut = self.shortcut_field.hasFocus() or any(field.hasFocus() for field in self.action_shortcut_fields.values())
        if (self.isActiveWindow() and editing_shortcut) or QApplication.activeModalWidget():
            return
        return self.capture_and_recognize()

    def capture_and_recognize(self):
        if self.closing:
            return 'ignored'
        if QApplication.activeModalWidget():
            return 'ignored'
        if self.copy_job is not None or self.pending_capture_ocr is not None or self.capture_active or self.capture_task.busy or self.ocr_task.busy or (self.manga_task.busy and self.manga_action != 'prepare'):
            return 'ignored'
        if not self.startup_detection_started and not self.engines:
            self.pending_external_capture = True
            self.prepare_selected()
            return 'queued'
        self.capture(auto_ocr=True)
        return 'accepted' if self.capture_active else 'unavailable'

    def external_command(self, action):
        if self.closing:
            return 'ignored'
        if action in ('translator', 'phrase'):
            # Closing the last popup must not kill an owner temporarily hidden for capture.
            QApplication.instance().setQuitOnLastWindowClosed(False)
            self.resident = True
            self.ensure_tray()
            from .popups import TextPopup
            if action not in self.popups:
                self.popups[action] = TextPopup(self, action)
            self.popups[action].open_text(QApplication.clipboard().text())
            return 'shown'
        if action in ('capture','capture-copy') and self.ocr_deferred:
            self.prepare_selected()
        if action == 'show':
            was_background = self.background
            self.background = False
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
            self.show()
            self.raise_()
            self.activateWindow()
            if self.ocr_deferred:
                self.prepare_selected()
            if was_background:
                self.dict_refresh()
                self.redetect_argos()
                if self.needs_setup:
                    self.show_setup()
            return 'shown'
        if action == 'capture-copy':
            if self.copy_job is not None or self.pending_capture_ocr is not None or self.capture_active or self.capture_task.busy or self.ocr_task.busy or (self.manga_task.busy and self.manga_action not in ('detect', 'prepare')):
                return 'ignored'
            if not self.external_capture_ready():
                self.pending_copy_capture = True
                return 'queued'
            return self.start_copy_capture()
        if action != 'capture':
            raise UserError(t('Acción externa no compatible.'))
        if not self.external_capture_ready():
            self.pending_external_capture = True
            self.statusBar().showMessage(t('Captura solicitada; esperando la detección inicial del OCR seleccionado…'))
            return 'queued'
        return self.capture_and_recognize()

    def external_capture_ready(self):
        if not self.startup_detection_started:
            return False
        # The shared action excludes all OCR workers while busy. Do not consume
        # a startup request while the background MangaOCR probe still owns one.
        return self.preparing_engine is not None or (not self.detect_task.busy and not (self.manga_task.busy and self.manga_action == 'detect'))

    def flush_external_capture(self):
        if self.pending_copy_capture and self.external_capture_ready():
            self.pending_copy_capture = False
            self.start_copy_capture()
        if not self.pending_external_capture or not self.external_capture_ready():
            return
        if QApplication.activeModalWidget():
            self.capture_request_timer.start(100)
            return
        self.pending_external_capture = False
        self.capture_and_recognize()

    def ensure_tray(self):
        if self.notice is not None:
            return True
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        self.notice = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation), self)
        menu = QMenu(self)
        for action, title in ACTIONS.items():
            menu.addAction(t(title), lambda checked=False, action=action: self.external_command(action))
        menu.addSeparator()
        menu.addAction(t('Abrir Configuración'), self.open_configuration)
        menu.addAction(t('Salir de Next'), self.quit_background)
        self.notice.setContextMenu(menu)
        self.notice.setToolTip(t('Na’atik Next está ejecutándose'))
        self.notice.activated.connect(self.tray_activated)
        self.notice.messageClicked.connect(self.open_configuration)
        self.notice.show()
        return True

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.external_command('show')

    def hide_to_tray(self):
        if not self.ensure_tray():
            self.fail(t('No hay bandeja disponible en esta sesión. La ventana sigue abierta; puedes minimizarla para conservar Next ejecutándose.'))
            return False
        self.resident = True
        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.hide()
        return True

    def notify_configuration(self, message):
        logging.warning('Captura y copia: %s', message)
        self.statusBar().showMessage(message)
        if self.ensure_tray():
            self.notice.showMessage(t('Na’atik Next — Configuración OCR'),
                                    message + t('\nPulsa para abrir Configuración.'), QSystemTrayIcon.Warning, 8000)
        else:
            print('Na’atik Next: ' + message, file=sys.stderr)
            if QApplication.platformName() not in ('offscreen', 'minimal'):
                QMessageBox.warning(self if self.isVisible() else None, t('Na’atik Next — Configuración OCR'), message)

    def open_configuration(self):
        self.external_command('show')
        self.tabs.setCurrentIndex(next(i for i in range(self.tabs.count()) if self.tabs.tabText(i) == t('OCR')))
        self.show_setup()

    def quit_background(self):
        self.close()
        QApplication.instance().quit()

    def start_copy_capture(self):
        self.prepare_if_needed()
        if (self.closing or QApplication.activeModalWidget() or self.copy_job is not None or self.pending_capture_ocr is not None
                or self.capture_active or self.capture_task.busy or self.ocr_task.busy
                or (self.manga_task.busy and self.manga_action != 'prepare')):
            return 'ignored'
        engine, language = self.engine.currentData(), self.ocr_language.currentText()
        info = next((e for e in self.engines if e['id'] == engine), {})
        if (not (self.preparing_engine and self.preparing_engine == engine) and (info.get('status') != 'listo' or
                (engine == 'tesseract' and language not in info.get('languages', [])))):
            self.notify_configuration(t('El OCR seleccionado no está listo. Revisa motor, idioma y recursos.'))
            return 'unavailable'
        self.capture_trace = timings.identity()
        timings.event('request', self.capture_trace)
        self.copy_job = dict(engine=engine, language=language, visible=self.isVisible(),
                             state=self.windowState(), image=None, generation=None)
        self.capture_active = True
        self.update_capture_controls()
        self.hide()
        self.capture_delay.start(0)
        return 'accepted'

    def restore_copy_window(self):
        if self.copy_job is None or self.copy_job.get('restored'):
            return
        self.copy_job['restored'] = True
        self.capture_active = False
        self.capture_auto_ocr = False
        if self.copy_job['visible']:
            # Restore the previous state without raising, activating or unminimizing.
            previous = self.testAttribute(Qt.WA_ShowWithoutActivating)
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
            self.setWindowState(self.copy_job['state'] & ~Qt.WindowActive)
            self.show()
            self.setAttribute(Qt.WA_ShowWithoutActivating, previous)
        self.update_capture_controls()

    def finish_copy_capture(self, error=None):
        job = self.copy_job
        if job is None:
            return
        self.capture_delay.stop()
        self.restore_copy_window()
        if self.preparing_engine is not None:
            self.copy_prepare_error_pending = True
        self.copy_job = None
        if job['image']:
            Path(job['image']).unlink(missing_ok=True)
        if error:
            timings.event('cancelled' if 'cancel' in error.lower() else 'failed', self.capture_trace)
            if 'cancel' not in error.lower():
                self.notify_configuration(error)

    def captured_for_copy(self, value):
        try:
            image = QImage.fromData(base64.b64decode(value), 'PNG')
            if image.isNull():
                raise UserError(t('La región está vacía o la captura es inválida.'))
            import uuid
            path = Path(self.temp.name) / (uuid.uuid4().hex + '.png')
            if not image.save(str(path), 'PNG'):
                raise UserError(t('No se pudo guardar la región temporal.'))
            self.ocr_generation += 1
            job = self.copy_job
            job.update(image=str(path), generation=self.ocr_generation)
            self.restore_copy_window()
            self.start_copy_ocr()
        except Exception as e:
            self.finish_copy_capture(str(e))

    def start_copy_ocr(self):
        job = self.copy_job
        if job is None or not job['image'] or self.preparing_engine is not None:
            return
        info = next((e for e in self.engines if e['id'] == job['engine']), {})
        if info.get('status') != 'listo':
            self.finish_copy_capture(t('El OCR seleccionado no está listo.'))
            return
        request = dict(action='ocr', generation=job['generation'], engine=job['engine'],
                       image=job['image'], language=job['language'], trace=self.capture_trace)
        self.copy_ocr_error_pending = True
        if job['engine'] == 'mangaocr':
            self.manga_action = 'ocr'
            request.update(model=self.settings['manga_model'], language='ja')
            self.manga_task.start(request, 120000)
        else:
            self.ocr_task.start(request)

    def engine_preparation_failed(self, message):
        self.engine.setEnabled(True)
        self.preparing_engine = None
        self.preparation_generation = None
        self.pending_capture_ocr = None
        if self.copy_prepare_error_pending:
            self.copy_prepare_error_pending = False
            return
        timings.event('failed', self.capture_trace)
        self.fail(message)

    def prepare_if_needed(self):
        engine = self.engine.currentData()
        info = next((e for e in self.engines if e['id'] == engine), {})
        if self.preparing_engine is None and info.get('status') in ('detectado', 'error'):
            if engine != 'mangaocr' or manga_descriptor(self.settings)['status'] == 'detectado':
                self.prepare_selected()

    def prepare_selected(self):
        """Prepare only the chosen engine; capture may run in parallel."""
        if self.closing or self.preparing_engine or self.ocr_task.busy or self.manga_task.busy or self.detect_task.busy:
            return
        self.ocr_deferred = False
        self.startup_detection_started = True
        engine = self.settings.get('ocr_engine', 'tesseract')
        self.preparing_engine = engine
        self.preparation_generation = timings.identity()
        timings.event('engine_prepare_begin', self.capture_trace)
        stub = dict(id=engine, name=engine, status='detectado', detail=t('Preparando OCR seleccionado…'),
                    languages=[self.settings.get('ocr_language', 'jpn')] if engine == 'tesseract' else [])
        choices = {e['id']: e for e in self.engines}
        choices.setdefault('tesseract', dict(id='tesseract', name='Tesseract', status='detectado',
                           detail=t('Sin preparar; se prepara al elegirlo.'), languages=[]))
        choices.setdefault('mangaocr', manga_descriptor(self.settings))
        choices.setdefault('paddleocr', dict(id='paddleocr', name='PaddleOCR', status='incompatible',
                           detail=t('Adaptador no implementado.'), languages=[]))
        choices[engine] = stub
        if engine == 'mangaocr':
            self.manga_status = stub
        self.detected(list(choices.values()))
        self.engine.setEnabled(False)
        self.ocr_language.setEnabled(False)
        if engine == 'mangaocr':
            self.manga_action = 'prepare'
            self.manga_task.program = self.settings['manga_python']
            self.manga_task.start(dict(action='prepare', model=self.settings['manga_model'], trace=self.capture_trace, preparation=self.preparation_generation), 180000)
        else:
            self.detect_task.start(dict(action='prepare_ocr', engine=engine, trace=self.capture_trace, preparation=self.preparation_generation), 120000)
        self.capture_request_timer.start(0)

    def resume_capture_ocr(self):
        had_capture = self.copy_job is not None or self.pending_capture_ocr is not None or self.capture_active
        self.copy_prepare_error_pending = False
        if self.preparing_engine is not None:
            return
        if self.copy_job is not None:
            self.start_copy_ocr()
        if self.pending_capture_ocr is not None:
            image, engine, language = self.pending_capture_ocr
            self.pending_capture_ocr = None
            if (image, engine, language) == (self.image_path, self.engine.currentData(), self.ocr_language.currentText()):
                self.recognize()
        if not self.background and not had_capture and not self.startup_argos_started:
            self.redetect_argos()

    def capture(self, checked=False, *, auto_ocr=False):
        if self.copy_job is not None or self.pending_capture_ocr is not None or self.capture_active or self.capture_task.busy or self.ocr_task.busy or (self.manga_task.busy and self.manga_action != 'prepare'):
            return
        if auto_ocr:
            self.prepare_if_needed()
            info = next((e for e in self.engines if e['id'] == self.engine.currentData()), {})
            if not (self.preparing_engine and self.preparing_engine == self.engine.currentData()) and (self.detect_task.busy or info.get('status') != 'listo'):
                self.fail(t('No se inició captura automática: el motor seleccionado no está listo. Revisa OCR y vuelve a detectar.'))
                return
            if self.editor.toPlainText().strip() and self.editor.toPlainText() != self.raw_text:
                self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
                self.show()
                self.raise_()
                if QMessageBox.question(self, t('Reemplazar texto revisado'),
                        t('La captura y el nuevo OCR reemplazarán tus correcciones. ¿Continuar?')) != QMessageBox.Yes:
                    return
        self.capture_trace = timings.identity()
        timings.event('request', self.capture_trace)
        self.invalidate_dictionary_lookup()
        self.capture_active = True  # Includes the hide/delay interval, before QProcess exists.
        self.capture_auto_ocr = auto_ocr
        self.capture_engine = (self.engine.currentData(), self.ocr_language.currentText())
        self.capture_previous_state = self.windowState()
        self.update_capture_controls()
        self.hide()
        self.capture_delay.start(0)

    def start_capture_worker(self):
        if self.capture_active:
            self.copy_capture_error_pending = self.copy_job is not None
            timings.event('selector_prepare', self.capture_trace)
            self.capture_task.start({'action': 'capture', 'trace': self.capture_trace}, 140000)

    def update_capture_controls(self, *args):
        self.capture_btn.setEnabled(not self.capture_active and not self.capture_task.busy)

    def restore_capture_window(self):
        state = self.capture_previous_state
        self.capture_previous_state = None
        self.capture_active = False
        self.capture_auto_ocr = False
        if state is not None:
            self.setWindowState(state & ~Qt.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()
        self.update_capture_controls()

    def capture_failed(self, message):
        timings.event('cancelled' if 'cancel' in message.lower() else 'failed', self.capture_trace)
        quiet = self.copy_capture_error_pending
        self.copy_capture_error_pending = False
        if self.copy_job is not None:
            self.finish_copy_capture(message)
            return
        if quiet:
            return
        self.capture_delay.stop()
        self.restore_capture_window()
        self.statusBar().showMessage(t('Captura no completada: ') + message)
        # Includes Escape/cancel: preserve image, original, edits and dictionary panel.
        if 'cancel' not in message.lower():
            QMessageBox.warning(self, t('Captura no completada'), message)

    def captured(self, value):
        timings.event('capture_complete', self.capture_trace)
        self.copy_capture_error_pending = False
        if not self.capture_active or self.closing:
            return
        if self.copy_job is not None:
            self.captured_for_copy(value)
            return
        auto_ocr = self.capture_auto_ocr
        try:
            image = QImage.fromData(base64.b64decode(value), 'PNG')
            if image.isNull():
                raise UserError(t('Spectacle devolvió una imagen inválida.'))
            self.set_image(image, t('Región de pantalla'))
            self.restore_capture_window()
            self.tabs.setCurrentIndex(0)
            if auto_ocr:
                if self.capture_engine != (self.engine.currentData(), self.ocr_language.currentText()):
                    self.fail(t('La selección OCR cambió durante la captura. Pulsa Reconocer para usar la selección actual.'))
                    return
                self.recognize()
        except Exception as e:
            self.capture_failed(str(e))

    def update_ocr_controls(self, *args):
        busy = self.ocr_task.busy or self.manga_task.busy
        self.recognize_btn.setEnabled(not busy)
        self.detect_btn.setEnabled(not busy and not self.detect_task.busy)

    def choose_manga_model(self):
        path = QFileDialog.getExistingDirectory(self, t('Snapshot local de MangaOCR'), self.manga_model_field.text())
        if path:
            self.manga_model_field.setText(path)

    def save_manga_resources(self):
        if self.ocr_task.busy or self.manga_task.busy or self.detect_task.busy:
            self.fail(t('Cancela o espera a que termine OCR antes de cambiar sus recursos.'))
            return
        self.settings['manga_python'] = self.manga_python_field.text().strip()
        self.settings['manga_model'] = self.manga_model_field.text().strip()
        self.persist()
        self.redetect()

    def redetect(self):
        if self.closing:
            return
        if self.ocr_task.busy or self.manga_task.busy or self.detect_task.busy:
            self.fail(t('Ya hay una operación OCR en curso; espera o cancélala.'))
            return
        self.startup_detection_started = True
        if self.manga_task.program != self.settings['manga_python']:
            self.manga_task.close()
            self.manga_task.reopen()
        self.manga_status = manga_descriptor(self.settings)
        if self.engines:
            self.detected(self.engines)
        self.detect_task.start({'action': 'detect'}, 120000)
        if self.manga_status['status'] == 'detectado':
            self.manga_action = 'detect'
            self.manga_task.program = self.settings['manga_python']
            self.manga_task.start({'action': 'detect', 'model': self.settings['manga_model']}, 180000)

    def manga_result(self, result):
        if 'preparation' in result and result['preparation'] != self.preparation_generation:
            return
        if self.manga_action in ('detect', 'prepare'):
            self.manga_status = {k: v for k, v in result.items() if k != 'preparation'}
            self.detected(self.engines)
            if self.preparing_engine == 'mangaocr':
                self.preparing_engine = None
                self.engine.setEnabled(True)
                timings.event('engine_ready', self.capture_trace)
                self.resume_capture_ocr()
        else:
            self.recognized(result)

    def manga_failed(self, message):
        if self.preparing_engine == 'mangaocr':
            self.engine.setEnabled(True)
            self.preparing_engine = None
            self.pending_capture_ocr = None
        self.manga_status = dict(manga_descriptor(self.settings), status='error',
                                 detail=message + t('\nVuelve a detectar MangaOCR; no hay fallback.'))
        self.detected(self.engines)

    def detected(self, engines):
        if self.closing:
            return
        if any('preparation' in e and e['preparation'] != self.preparation_generation for e in engines):
            return
        selected_prepared = self.preparing_engine is not None and self.preparing_engine != 'mangaocr' and any(e.get('preparation') == self.preparation_generation and 'preparation' in e for e in engines)
        engines = [{k: v for k, v in e.items() if k != 'preparation'} for e in engines]
        if selected_prepared:
            choices = {e['id']: e for e in self.engines}
            choices.update({e['id']: e for e in engines})
            engines = list(choices.values())
        if self.manga_status:
            engines = [e for e in engines if e['id'] != 'mangaocr'] + [self.manga_status]
        self.engines = engines
        selected = self.settings.get('ocr_engine', 'tesseract')
        self.engine.blockSignals(True)
        self.engine.clear()
        for item in engines:
            self.engine.addItem(f'{item["name"]} — {t(item["status"])}', item['id'])
        index = self.engine.findData(selected)
        # Preserve missing selection; never silently fall back to another engine.
        if index < 0:
            self.engine.addItem((f'{selected}' + t(' — selección no disponible')), selected)
            index = self.engine.count() - 1
        self.engine.setCurrentIndex(index)
        self.engine.blockSignals(False)
        self.engine_detail.setPlainText('\n\n'.join(f'{e["name"]}: {t(e["status"])}\n{e["detail"]}' for e in engines))
        self.engine_changed()
        if selected_prepared:
            self.preparing_engine = None
            self.engine.setEnabled(True)
            timings.event('engine_ready', self.capture_trace)
            self.resume_capture_ocr()

    def engine_changed(self):
        key = self.engine.currentData()
        if not key:
            return
        self.settings['ocr_engine'] = key
        self.ocr_language.blockSignals(True)
        self.ocr_language.clear()
        info = next((e for e in self.engines if e['id'] == key), {})
        self.ocr_language.addItems(info.get('languages', []))
        previous = self.settings.get('ocr_language', 'jpn')
        index = self.ocr_language.findText(previous)
        if index < 0 and previous and info.get('languages'):
            self.ocr_language.addItem(previous)
            index = self.ocr_language.findText(previous)
        self.ocr_language.setCurrentIndex(max(0, index))
        self.ocr_language.setEnabled(bool(info.get('languages')))
        self.ocr_language.blockSignals(False)
        self.language_changed()
        if self.startup_detection_started and self.preparing_engine is None and info.get('status') == 'detectado':
            QTimer.singleShot(0, self.prepare_selected)

    def language_changed(self):
        language = self.ocr_language.currentText()
        if self.engine.currentData() == 'mangaocr':
            language = t('japonés fijo · sin selector de dirección')
        elif language:
            self.settings['ocr_language'] = language
        self.engine_caption.setText((t('Motor: ') + f'{self.engine.currentText()}' + ' · ' + f'{language}'))
        self.persist()

    def test_image(self):
        if self.open_image():
            self.tabs.setCurrentIndex(0)
            self.recognize()

    def recognize(self):
        if self.closing or self.copy_job is not None or self.capture_active:
            return
        self.prepare_if_needed()
        if self.preparing_engine and self.preparing_engine == self.engine.currentData():
            self.pending_capture_ocr = (self.image_path, self.engine.currentData(), self.ocr_language.currentText())
            return
        if self.ocr_task.busy or self.manga_task.busy:
            self.fail(t('Ya hay una operación OCR en curso.'))
            return
        if not self.image_path:
            self.fail(t('Primero selecciona una región o abre una imagen.'))
            return
        info = next((e for e in self.engines if e['id'] == self.engine.currentData()), {})
        if info.get('status') != 'listo':
            self.fail(t('El motor seleccionado no está listo. Revisa la pestaña OCR y vuelve a detectar.'))
            return
        if self.engine.currentData() == 'tesseract' and self.ocr_language.currentText() not in info.get('languages', []):
            self.fail(t('Faltan los datos de idioma elegidos: ') + self.ocr_language.currentText() + t('. Instálalos o elige explícitamente otro idioma.'))
            return
        if self.editor.toPlainText().strip() and self.editor.toPlainText() != self.raw_text:
            if QMessageBox.question(self, t('Reemplazar texto revisado'), t('El nuevo OCR reemplazará el texto corregido. ¿Continuar?')) != QMessageBox.Yes:
                return
        self.invalidate_dictionary_lookup()
        self.ocr_generation += 1
        self.ocr_pending = self.ocr_generation
        self.ocr_request_image = self.image_path
        if self.engine.currentData() == 'mangaocr':
            self.manga_action = 'ocr'
            self.manga_task.start({'action': 'ocr', 'generation': self.ocr_pending, 'engine': 'mangaocr', 'model': self.settings['manga_model'],
                                   'image': self.image_path, 'language': 'ja', 'trace': self.capture_trace}, 120000)
        else:
            self.ocr_task.start({'action': 'ocr', 'generation': self.ocr_pending, 'engine': self.engine.currentData(),
                                 'image': self.image_path, 'language': self.ocr_language.currentText(), 'trace': self.capture_trace})

    def ocr_failed(self, message):
        self.invalidate_ocr()
        quiet = self.copy_ocr_error_pending or self.copy_prepare_error_pending
        self.copy_prepare_error_pending = False
        self.copy_ocr_error_pending = False
        if self.copy_job is not None:
            self.finish_copy_capture(message)
        elif quiet:
            # A cancelled silent job may report its terminal error after cleanup.
            logging.info('Captura y copia terminada: %s', message)
        else:
            self.fail(message)

    def invalidate_ocr(self, *args):
        self.ocr_pending = None

    def recognized(self, result):
        if self.closing or self.interrupted():
            return
        if self.copy_job is not None:
            job = self.copy_job
            if (not self.closing and isinstance(result, dict) and job['generation'] is not None
                    and result.get('generation') == job['generation']):
                self.copy_ocr_error_pending = False
                text = result.get('text', '')
                if text.strip():
                    QApplication.clipboard().setText(text)
                    timings.event('clipboard', self.capture_trace)
                    self.statusBar().showMessage(t('Texto reconocido y copiado'), 5000)
                    self.finish_copy_capture()
                else:
                    self.finish_copy_capture(t('El OCR terminó sin encontrar texto.'))
            return
        # Workers echo the request identity, including the persistent MangaOCR worker.
        # Cancellation invalidates it before terminating a process.
        if (self.closing or not isinstance(result, dict) or self.ocr_pending is None
                or result.get('generation') != self.ocr_pending):
            return
        self.ocr_pending = None
        text = result['text']
        if self.ocr_request_image != self.image_path:
            Path(self.ocr_request_image).unlink(missing_ok=True)
            self.statusBar().showMessage(t('Resultado OCR descartado: la imagen cambió durante el proceso.'))
            return
        self.raw_text = text
        self.editor.setPlainText(text)
        self.translation.clear()
        if not text.strip():
            self.fail(t('El motor terminó sin encontrar texto. Prueba otra región o idioma.'))
        self.text_changed()
        if text.strip() and self.settings.get('auto_copy_ocr', True):
            # Task result slots execute on the GUI thread; never synthesize keystrokes.
            QApplication.clipboard().setText(text)
            timings.event('clipboard', self.capture_trace)
        if text.strip():
            self.lookup_dictionary_text(text, automatic=True)
            if self.settings.get('auto_copy_ocr', True):
                self.statusBar().showMessage(t('Texto reconocido y copiado'), 5000)
        if not self.background and not self.startup_argos_started:
            self.startup_argos_started = True
            QTimer.singleShot(0, self.redetect_argos)

    def show_original(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle(t('Original OCR — solo lectura'))
        dialog.setTextFormat(Qt.PlainText)
        dialog.setText(self.raw_text or t('Todavía no hay texto reconocido.'))
        dialog.exec()

    def text_changed(self):
        self.selection_changed()
        text = self.editor.toPlainText()
        self.provenance.setText(t('Texto corregido por el usuario; el original OCR se conserva.') if self.raw_text and text != self.raw_text
                                else t('Texto original OCR sin cambios.') if self.raw_text else t('Texto introducido por el usuario; sin resultado OCR.'))
        if self.translated_source is not None and text != self.translated_source:
            self.translation_status.setText(t('El texto cambió: la traducción mostrada corresponde a la versión anterior.'))

    def translation_tab_changed(self, index):
        if self.tabs.widget(index) is self.translation_tab and not self.translation_section.active:
            self.translation_section.inspect()

    def configure_translation(self):
        self.show(); self.raise_(); self.activateWindow()
        self.tabs.setCurrentWidget(self.translation_tab)
        if not self.translation_section.started:
            self.translation_section.inspect()

    def refresh_translation_models(self):
        if self.argos_task.busy:
            self.translation_refresh_pending = True
        else:
            self.redetect_argos()
        for popup in self.popups.values():
            popup.reconfigure_translation()

    def redetect_argos(self):
        if self.closing:
            return
        self.startup_argos_started = True
        if self.argos_task.busy:
            self.fail(t('Espera a que termine Argos o cancela la operación antes de revisar modelos.'))
            return
        from .translation_runtime import program as translation_program
        if self.argos_task.program != translation_program():
            self.argos_task.begin_close()
            self.argos_task=self.task(self.argos_result,persistent=True,program=translation_program())
            self.argos_task.busy_changed.connect(lambda busy:self.translate_btn.setEnabled(not busy))
        self.argos_action = 'routes'
        self.argos_task.start({'action': 'routes'}, 180000)

    def argos_result(self, result):
        if self.closing:
            return
        if self.argos_action == 'routes':
            self.routes = result['routes']
            self.argos_detail.setText(result['detail'] + '\n' + '\n'.join(result['errors']))
            selected = self.settings.get('translation_route', ['ja', 'en', 'es'])
            self.target.blockSignals(True)
            self.target.clear()
            for route_ in self.routes:
                self.target.addItem(' → '.join(route_) + (t(' (intermedio: ') + ', '.join(route_[1:-1]) + ')' if len(route_) > 2 else t(' (directa)')), route_)
            index = next((i for i, r in enumerate(self.routes) if r == selected), -1)
            if index < 0 and 'translation_route' in self.settings:
                self.target.addItem(' → '.join(selected) + t(' — no disponible'), None)
                index = self.target.count() - 1
            self.target.setCurrentIndex(max(0, index) if self.target.count() else -1)
            self.target.blockSignals(False)
            self.route_changed()
        else:
            self.translation.setPlainText(result['text'])
            self.translated_source = self.translation_input
            self.translation_status.setText(t('Traducción local: ') + ' → '.join(result['route']))
            self.text_changed()
        if getattr(self, 'translation_refresh_pending', False):
            self.translation_refresh_pending = False
            QTimer.singleShot(0, self.redetect_argos)

    def route_changed(self):
        route_ = self.target.currentData()
        if self.translation.toPlainText():
            self.translation_status.setText(t('La ruta cambió: vuelve a traducir el texto con la ruta seleccionada.'))
        if route_:
            self.settings['translation_route'] = route_
            self.persist()
            self.route_caption.setText(t('Idioma intermedio: ') + ', '.join(route_[1:-1]) if len(route_) > 2 else t('Ruta directa, sin idioma intermedio.'))
        else:
            self.route_caption.setText(t('No hay una ruta disponible seleccionada. Revisa los modelos locales en Preferencias.'))

    def translate(self):
        route_ = self.target.currentData()
        if not route_:
            self.fail(t('Faltan modelos para una ruta de traducción. Consulta Preferencias y diagnóstico.'))
            return
        if not self.editor.toPlainText().strip():
            self.fail(t('No hay texto para traducir.'))
            return
        self.translation_input = self.editor.toPlainText()
        self.argos_action = 'translate'
        self.argos_task.start({'action': 'translate', 'text': self.translation_input, 'route': route_}, 180000)

    def dict_refresh(self):
        if self.store is None:
            self.store = Store()
        dictionaries = self.store.list()
        self.table.setRowCount(len(dictionaries))
        for i, d in enumerate(dictionaries):
            metadata = json.loads(d['metadata']) if d.get('metadata') else {}
            types = ', '.join(t(NAMES.get(k,k)) for k in metadata.get('counts', {'term':d['count']}))
            warnings = metadata.get('warnings',[])
            values = [d['title'] + ' / ' + d['revision'] + ' · ' + types,
                      (d['source_language'] or '?') + ' → ' + (d['target_language'] or '?'), str(d['count']), t('Importado con avisos') if warnings else t('Importado')]
            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, d['id'])
                item.setToolTip('\n'.join(warnings))
                self.table.setItem(i, j, item)
            check = QCheckBox()
            check.setChecked(bool(d['enabled']))
            spin = QSpinBox()
            spin.setRange(-10000, 10000)
            spin.setValue(d['priority'])
            check.toggled.connect(lambda value, ident=d['id'], s=spin: self.update_dictionary(ident, value, s.value()))
            spin.valueChanged.connect(lambda value, ident=d['id'], c=check: self.update_dictionary(ident, c.isChecked(), value))
            self.table.setCellWidget(i, 4, check)
            self.table.setCellWidget(i, 5, spin)

    def update_dictionary(self, ident, enabled, priority):
        try:
            self.store.update(ident, enabled, priority)
        except Exception as e:
            self.fail(str(e))

    def dict_controls(self, busy):
        busy = self.import_task.busy or self.inspect_task.busy or self.dictionary_action_task.busy or bool(self.import_queue) or self.current_import is not None
        self.add_dict.setEnabled(not busy)
        self.remove_dict.setEnabled(not busy)
        self.table.setEnabled(not busy)
        if busy:
            self.import_status.setText(t('Inspeccionando ZIP sin importar…') if self.inspect_task.busy else t('Validando e importando transaccionalmente. Cancelar revierte la operación en curso.') if self.import_task.busy else t('Quitando copia administrada…') if self.dictionary_action_task.busy else t('Preparando siguiente diccionario…'))

    def add_dictionary(self):
        filenames, _ = QFileDialog.getOpenFileNames(self, t('Agregar diccionarios Yomitan'), '', t('Diccionario ZIP (*.zip)'))
        if filenames:
            if len(filenames) > 50:
                self.fail(t('Selecciona como máximo 50 ZIP por lote.'))
                return
            self.import_report.clear()
            self.inspect_task.start({'action':'inspect_dictionaries','paths':filenames},600000)

    def inspection_failed(self, message):
        self.import_status.setText(t('Revisión no completada: ') + message)
        self.import_report.appendPlainText(message)
        self.dict_controls(False)

    def dictionaries_inspected(self, entries):
        for entry in entries:
            state = ('ERROR: '+entry['error'] if entry.get('error') else t('Duplicado: ')+entry['duplicate']
                     if entry.get('duplicate') else (t('Validado: ') + f"{entry['title']}" + ' · ' + f"{entry['count']:,}" + t(' entradas; aún no importado')))
            self.import_report.appendPlainText(Path(entry['path']).name + ': ' + state)
            for warning in entry.get('warnings',[]):
                self.import_report.appendPlainText(warning)
        review = ImportReview(entries,self)
        if review.exec() == ImportReview.Accepted:
            self.import_queue = review.selected()
            if not self.import_queue:
                self.import_status.setText(t('No se seleccionó ningún archivo para importar.'))
            self.dict_controls(False)
            self.next_dictionary_import()
        else:
            self.import_status.setText(t('Revisión cancelada; no se importó ningún archivo.'))

    def next_dictionary_import(self):
        if self.closing:
            return
        if self.import_queue:
            self.current_import = self.import_queue.pop(0)
            entry = self.current_import
            self.import_report.appendPlainText(Path(entry['path']).name + t(': importando…'))
            self.import_task.start({'action':'import','path':entry['path'],'digest':entry['digest']},600000)
        else:
            self.current_import = None
            self.dict_controls(False)

    def imported(self, result):
        counts = ', '.join(t(NAMES.get(k,k))+': '+f'{v:,}' for k,v in result.get('counts',{}).items())
        text = (t('Importado: ') + f"{result['title']}" + ' · ' + f"{result['count']:,}" + t(' entradas. ')) + counts
        self.import_status.setText(text)
        self.import_report.appendPlainText((Path(self.current_import['path']).name + ': ' if self.current_import else '') + text)
        for warning in result.get('warnings',[]):
            self.import_report.appendPlainText(warning)
        self.current_import = None
        self.dict_refresh()
        self.dict_controls(False)
        QTimer.singleShot(0,self.next_dictionary_import)

    def import_failed(self, message):
        name = Path(self.current_import['path']).name if self.current_import else t('Importación')
        committed = self.current_import and any(d['digest'] == self.current_import['digest'] for d in self.store.list())
        self.import_report.appendPlainText(name + (t(': Ya está importado y completo. El proceso informó: ') if committed else t(': ERROR — ')) + message)
        self.current_import = None
        self.dict_refresh()
        self.dict_controls(False)
        QTimer.singleShot(0,self.next_dictionary_import)

    def remove_dictionary(self):
        selected = self.table.currentRow()
        if selected < 0:
            self.fail(t('Selecciona un diccionario de la tabla.'))
            return
        ident = self.table.item(selected, 0).data(Qt.UserRole)
        if QMessageBox.question(self, t('Quitar diccionario'), t('¿Quitar las entradas administradas? El ZIP original se conserva.')) == QMessageBox.Yes:
            try:
                self.dictionary_action_task.start({'action': 'remove', 'id': ident}, 120000)
            except Exception as e:
                self.fail(str(e))

    def dictionary_changed(self, result):
        self.dict_refresh()
        self.definitions.clear()
        self.import_status.setText(t('Copia administrada eliminada; el archivo original se conserva.'))

    def lookup(self):
        self.lookup_task.start({'action': 'lookup', 'term': self.query.text()}, 30000)

    def looked_up(self, result):
        if not result:
            self.definitions.setPlainText(t('Sin coincidencias exactas en los diccionarios activos (máximo 100 resultados).'))
            return
        try:
            self.definitions.setHtml(render_results(result))
        except UserError as e:
            self.fail(str(e))

    def shutdown(self, *, interrupted=False):
        if self.closing:
            return
        self.closing = True  # Invalidate every queued callback before touching children.
        active_capture = (self.capture_active or self.copy_job is not None or
                          self.pending_capture_ocr is not None or self.ocr_pending is not None)
        if interrupted:
            timings.event('interrupted', self.capture_trace if active_capture else None)
        elif active_capture:
            timings.event('cancelled', self.capture_trace)
        self.preparation_generation = None
        self.preparing_engine = None
        self.ocr_pending = None
        self.pending_capture_ocr = None
        self.selection_generation += 1
        self.selection_pending = None
        self.capture_request_timer.stop()
        self.capture_delay.stop()
        self.pending_external_capture = False
        self.pending_copy_capture = False
        self.capture_active = False
        self.copy_job = None
        self.shortcut.close()
        for shortcut in self.action_shortcuts.values():
            shortcut.close()
        self.translation_section.cancel()
        for popup in self.popups.values():
            popup.shutdown()
        if self.notice is not None:
            self.notice.hide()
        # Terminate all workers first, then wait; a busy stderr callback cannot
        # re-enter widgets while waitForFinished dispatches process events.
        tasks = self.tasks + self.popup_tasks
        for task in tasks:
            task.begin_close()
        if hasattr(self, 'tutorial_dialog'):
            self.tutorial_dialog.close()
        if hasattr(self, 'setup_dialog'):
            self.setup_dialog.close()
        deadline = time.monotonic() + 3
        for task in tasks:
            task.close(timeout_ms=max(0, int((deadline - time.monotonic()) * 1000)))
        if self.store is not None:
            self.store.close()
        self.temp.cleanup()

    def closeEvent(self, event):
        self.shutdown()
        event.accept()
        if self.resident:
            QApplication.instance().quit()


def main():
    parser = argparse.ArgumentParser(description=t('Na’atik Next — OCR y traducción local'))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--show', action='store_true', help=t('Abrir la ventana principal de Next.'))
    mode.add_argument('--capture-copy', action='store_true', help=t('Capturar y copiar OCR en segundo plano, sin consulta ni traducción.'))
    mode.add_argument('--translator', action='store_true', help=t('Abrir Translator con el texto del portapapeles.'))
    mode.add_argument('--phrase', action='store_true', help=t('Abrir OCR Phrase con el texto del portapapeles, sin capturar.'))
    mode.add_argument('--capture', action='store_true', help=t('Capturar una región y reconocer con el OCR seleccionado; reutiliza la instancia abierta.'))
    parser.add_argument('--timings', action='store_true', help=t('Registrar etapas y duraciones sin texto ni imágenes; también habilita diagnóstico en la instancia existente.'))
    arguments = parser.parse_args()
    if arguments.timings:
        timings.enable()
    os.umask(0o077)
    app = QApplication([sys.argv[0]])
    app.setApplicationName('Na’atik Next')
    app.setOrganizationName('NaatikNext')
    action = ('translator' if arguments.translator else 'phrase' if arguments.phrase else
              'capture-copy' if arguments.capture_copy else 'capture' if arguments.capture else 'show')
    instance = None
    window = None
    def stop_from_signal(signum):
        try:
            if window is not None:
                window.shutdown(interrupted=True)
        finally:
            app.exit(128 + signum)
    signals = ShutdownSignals(stop_from_signal)
    try:
        state = paths()['state']
        handler = RotatingFileHandler(state / 'naatik-next.log', maxBytes=2_000_000, backupCount=2)
        logging.basicConfig(handlers=[handler], level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s')
        instance = Instance(state)
        instance.interrupted = lambda: signals.received is not None
        if not (instance.acquire_or_forward(action, diagnostics=True) if arguments.timings else instance.acquire_or_forward(action)):
            return 128 + signals.received if signals.received is not None else 0
        if signals.received is not None:
            return 128 + signals.received
        if arguments.translator or arguments.phrase:
            app.setQuitOnLastWindowClosed(False)
            window = Window(background=True, popup_only=True)
        elif arguments.capture_copy:
            app.setQuitOnLastWindowClosed(False)
            window = Window(background=True)
        else:
            window = Window(startup_action=action)
        window.interrupted = lambda: signals.received is not None
        for task in window.tasks:
            task.interrupted = window.interrupted
        app.aboutToQuit.connect(window.shutdown)
        instance.server.set_handler(window.external_command)
        if action not in ('capture-copy', 'translator', 'phrase'):
            window.show()
        if action != 'show':
            window.external_command(action)
        return app.exec()
    except Exception as e:
        logging.error('Application activation failed: %s', e)
        print('Na’atik Next: ' + str(e), file=sys.stderr)
        if app.platformName() not in ('offscreen', 'minimal'):
            QMessageBox.warning(None, t('Na’atik Next — no se pudo iniciar'), str(e))
        return 1
    finally:
        try:
            if window is not None:
                window.shutdown(interrupted=signals.received is not None)
        finally:
            try:
                if instance:
                    instance.close()
            finally:
                signals.close()


if __name__ == '__main__':
    sys.exit(main())
