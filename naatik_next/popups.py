"""Two reusable, editable clipboard actions; all expensive work stays in supervised processes."""
from .i18n import t
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QMessageBox
from .processes import Task
from .dictionary_content import render_results


class TextPopup(QDialog):
    def __init__(self, owner, mode):
        super().__init__(owner, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.owner, self.mode = owner, mode
        self.setWindowTitle('Translator' if mode == 'translator' else 'OCR Phrase')
        self.revision = 0
        self.session = 0
        self.lookup_revision = 0
        self.closed = False
        self.pending, self.running = {}, {}
        self.token_data = []
        self.lookup_targets = {}
        self.anki_lookup = None
        self.anki_token = None
        from .popup_presentation import build
        build(self)
        from .translation_runtime import program
        self.translate_task = self.task('translate',program=program())
        self.lookup_task = self.task('lookup')
        self.phrase_task = self.task('phrase', program=str(Path(__file__).resolve().parent.parent / '.venv-phrase/bin/python'),
                                     module='naatik_next.phrase_worker')
        self.resource_task = self.task('resources')
        self.debounce = QTimer(self); self.debounce.setSingleShot(True); self.debounce.setInterval(420)
        self.debounce.timeout.connect(self.process)
        self.flush_timer = QTimer(self); self.flush_timer.setSingleShot(True)
        self.flush_timer.timeout.connect(self.flush)
        self.selection_timer = QTimer(self); self.selection_timer.setSingleShot(True); self.selection_timer.setInterval(180)
        self.selection_timer.timeout.connect(self.lookup_selection)
        self.editor.textChanged.connect(self.edited)
        self.editor.selectionChanged.connect(self.selection_changed)
        self.route.currentIndexChanged.connect(self.route_changed)
        self.process_button.clicked.connect(self.process)
        self.models_fingerprint = self.model_fingerprint()
        self.models_timer = QTimer(self); self.models_timer.setInterval(2000)
        self.models_timer.timeout.connect(self.check_models); self.models_timer.start()
        self.refresh_routes()

    def open_anki(self):
        selection = self.editor.textCursor().selectedText().replace('\u2029', '\n')
        token = self.anki_token
        word = selection or (token['surface'] if token else '')
        reading = token.get('reading', '') if token and token['surface'] == word else ''
        definitions = []
        lookup = self.anki_lookup
        if lookup and lookup['revision'] == self.revision and lookup['term'] == word:
            for row in lookup['results']:
                if row.get('kind') not in ('term', 'grammar'): continue
                # Never extract tooltip HTML. Keep typed rows and literal safe text.
                import json
                meanings = row.get('meanings', '')
                try:
                    meanings = json.loads(meanings) if isinstance(meanings, str) else meanings
                except ValueError: pass
                definitions.append(dict(text=str(meanings), title=row['title'], revision=row['revision'],
                                        reading=row.get('reading', '')))
        self.owner.anki_section.open_draft(dict(sentence=self.editor.toPlainText(), word=word,
            reading=reading, translation=self.translation.toPlainText(), definition_entries=definitions,
            reading_origin=t('Fugashi / UniDic · lectura léxica de la revisión actual') if reading else '',
            translation_origin=t('Traducción automática local · ruta ') + ' → '.join(self.route.currentData() or [])))

    def model_fingerprint(self):
        from .storage import paths
        directory = paths()['data'] / 'argos/packages'
        try:
            return tuple(sorted((str(p.relative_to(directory)), p.stat().st_mtime_ns, p.stat().st_size)
                                for p in directory.glob('**/*') if p.is_file()))
        except OSError: return None

    def check_models(self):
        if self.closed or not self.isVisible() or self.translate_task.busy: return
        fingerprint = self.model_fingerprint()
        if fingerprint != self.models_fingerprint:
            self.models_fingerprint = fingerprint
            self.reconfigure_translation()

    def task(self, channel, **kwargs):
        task = Task(self, persistent=True, **kwargs)
        task.interrupted = lambda: self.owner.closing or self.owner.interrupted()
        self.owner.popup_tasks.append(task)
        task.result.connect(lambda result: self.completed(task, channel, result))
        task.error.connect(lambda message: self.failed(task, channel, message))
        return task

    def stamp(self, task):
        return f'{self.session}:{self.revision}:{self.lookup_revision}' if task is self.lookup_task else f'{self.session}:{self.revision}'

    def send(self, task, request):
        if self.closed or self.owner.closing or self.owner.interrupted(): return
        self.pending[task] = dict(request, popup_generation=self.stamp(task), popup_session=self.session)
        self.flush()

    def flush(self):
        if self.closed or self.owner.closing or self.owner.interrupted(): return
        for task, request in list(self.pending.items()):
            if not task.busy:
                del self.pending[task]
                self.running[task] = request
                task.start(request, 960000 if request['action']=='prepare_phrase_runtime' else 180000)

    def open_text(self, text):
        self.show(); self.raise_(); self.activateWindow()
        self.editor.setPlainText(text)
        self.editor.setFocus()
        # setPlainText emits even for empty text; make repeated empty actions explicit.
        if not text.strip(): self.translation_status.setText(t('Portapapeles vacío: escribe o pega texto.'))
        if self.route.count() == 0 and (not self.translate_task.busy or self.running.get(self.translate_task,{}).get('popup_session') != self.session): self.refresh_routes()

    def edited(self):
        self.revision += 1
        self.lookup_revision += 1
        self.pending.clear()
        from .popup_presentation import clear_words
        clear_words(self)
        self.selection_box.hide()
        self.translation.clear(); self.furigana.clear(); self.definitions.clear()
        self.token_data = []
        self.anki_lookup = None
        self.anki_token = None
        self.dictionary_status.clear()
        self.selection_timer.stop()
        self.debounce.start()

    def selection_changed(self):
        for _, status in self.lookup_targets.values(): status.setText(t('Consulta sustituida por una nueva selección.'))
        self.lookup_targets.clear()
        self.anki_token = None
        self.anki_lookup = None
        self.lookup_revision += 1
        self.pending.pop(self.lookup_task, None)
        self.definitions.clear()
        if not self.editor.textCursor().hasSelection(): self.selection_box.hide()
        self.selection_timer.start()

    def route_changed(self):
        if self.route.currentData():
            self.owner.settings[self.mode + '_route'] = self.route.currentData()
            self.owner.persist()
        self.prepare_translation.setVisible(not bool(self.route.currentData()))
        self.edited()

    def refresh_routes(self):
        self.translation_status.setText(t('Comprobando modelos Argos locales…'))
        self.send(self.translate_task, {'action': 'routes'})

    def process(self):
        self.debounce.stop()
        if self.closed or not self.isVisible(): return
        text = self.editor.toPlainText()
        if not text.strip():
            self.translation_status.setText(t('Escribe o pega texto para procesar.')); return
        if len(text) > 10000:
            self.translation_status.setText(t('Máximo 10 000 caracteres; divide el texto.')); return
        route = self.route.currentData()
        if route:
            self.translation_status.setText(t('Traduciendo localmente: ') + ' → '.join(route))
            self.send(self.translate_task, dict(action='translate', text=text, route=route))
        elif not self.translate_task.busy:
            self.translation_status.setText(t('Faltan modelos: pulsa Preparar traducción para abrir la sección Traducción.'))
        if Path(self.phrase_task.program).is_file():
            self.analysis_status.setText(t('Analizando palabras y lecturas locales…'))
            self.send(self.phrase_task, dict(action='phrase', text=text))
        else:
            self.analysis_status.setText(t('Faltan recursos de lecturas. Abre Opciones → Preparar lecturas…; no se descargan automáticamente.'))
            if self.mode == 'phrase':
                self.selection_box.show()
                self.definitions, self.dictionary_status = self.selection_definitions, self.selection_status
                self.lookup(text)

    def completed(self, task, channel, result):
        request = self.running.pop(task, {})
        if self.closed or self.owner.closing or self.owner.interrupted(): return
        if request.get('popup_session') != self.session:
            self.flush_timer.start(0); return
        action = request.get('action')
        value = result.get('value', {})
        current = result.get('popup_generation') == self.stamp(task)
        if action == 'routes':
            self.route.blockSignals(True); self.route.clear()
            routes = value.get('routes', [])
            for route in routes: self.route.addItem(' → '.join(route), route)
            selected = self.owner.settings.get(self.mode + '_route', self.owner.settings.get('translation_route'))
            index = next((i for i, route in enumerate(routes) if route == selected), -1)
            if index < 0 and (self.mode + '_route' in self.owner.settings or 'translation_route' in self.owner.settings):
                self.route.addItem(' → '.join(selected) + t(' — no disponible'), None); index = self.route.count()-1
            if selected is None and routes:
                self.route.insertItem(0,t('Elige una ruta de traducción…'),None);index=0
            self.route.setCurrentIndex(max(0,index) if self.route.count() else -1); self.route.blockSignals(False)
            self.prepare_translation.setVisible(not bool(self.route.currentData()))
            self.translation_status.setText(value.get('detail','') + '\n' + '\n'.join(value.get('errors',[])))
            if self.isVisible(): self.debounce.start()
        elif channel == 'resources':
            self.analysis_status.setText(t('Preparación terminada. Pulsa Analizar/Traducir para reintentar.'))
            if action == 'install_argos': self.refresh_routes()
        elif channel == 'lookup':
            target = self.lookup_targets.pop(result.get('popup_generation'), None)
            if target and self.isVisible():
                if request.get('popup_generation') == self.stamp(task):
                    self.anki_lookup = dict(revision=self.revision, term=request['surface'], results=value['results'])
                definitions, status = target
                status.setText(t('Consulta exacta terminada.') if value['active'] else t('No hay diccionarios activos; impórtalos o actívalos en Configuración.'))
                definitions.setHtml(render_results(value['results'])) if value['results'] else definitions.setPlainText(t('Sin coincidencias exactas.') if value['active'] else t('Sin diccionarios activos.'))
        elif current and self.isVisible():
            if channel == 'translate':
                self.translation.setPlainText(value['text'])
                self.translation_status.setText(t('Traducción local: ') + ' → '.join(value['route']))
            elif channel == 'phrase': self.show_analysis(value)
        self.flush_timer.start(0)

    def failed(self, task, channel, message):
        request = self.running.pop(task, {})
        if self.closed or self.owner.closing: return
        lookup_target = self.lookup_targets.pop(request.get('popup_generation'), None) if channel == 'lookup' else None
        if lookup_target and self.isVisible(): lookup_target[1].setText(message)
        elif request.get('popup_generation') == self.stamp(task) and self.isVisible():
            target = {'translate': self.translation_status, 'phrase': self.analysis_status,
                      'lookup': self.dictionary_status, 'resources': self.analysis_status}[channel]
            target.setText(message)
            if channel == 'translate': self.prepare_translation.show()
        self.flush_timer.start(0)

    def show_analysis(self, value):
        self.lookup_revision += 1
        self.pending.pop(self.lookup_task, None)
        self.analysis_status.setText(value['resource'] + t(' · lecturas léxicas contextuales, no verificadas por el usuario. Gramática/JLPT no disponibles.'))
        text, parts, cursor = value['sentence'], [], 0
        self.token_data = value['tokens']
        for token in self.token_data:
            parts.append(text[cursor:token['start']])
            surface, reading = token['surface'], token['reading']
            has_kanji = any('\u3400' <= c <= '\u9fff' or '\U00020000' <= c <= '\U0002fa1f' for c in surface)
            # Word annotations match the reference's readable surface(reading) form;
            # do not infer an alignment between individual kanji and kana.
            parts.append(surface + ('('+reading+')' if reading and has_kanji and reading != surface else ''))
            cursor = token['end']
        parts.append(text[cursor:])
        self.furigana.setPlainText(''.join(parts))
        from .popup_presentation import show_words
        show_words(self)

    def lookup_token(self, row):
        if 0 <= row < len(self.token_data):
            token = self.token_data[row]
            self.anki_token = dict(token)
            self.anki_lookup = None
            self.lookup(token['base'], token['surface'])

    def lookup_selection(self):
        text = self.editor.textCursor().selectedText().replace('\u2029', '\n')
        if text.strip():
            from .popup_presentation import show_selection
            self.selection_title.setText(text)
            show_selection(self)
            self.definitions, self.dictionary_status = self.selection_definitions, self.selection_status
            self.lookup(text)

    def lookup(self, term, surface=None):
        # A busy lookup may finish into its own still-live card, never another
        # card. Only one pending request is retained; mark one displaced by a
        # newer request explicitly instead of leaving a perpetual loading state.
        pending = self.pending.get(self.lookup_task, {})
        target = self.lookup_targets.pop(pending.get('popup_generation'), None)
        if target: target[1].setText(t('Consulta sustituida; vuelve a abrir la palabra para consultar.'))
        self.lookup_targets = {key:value for key,value in self.lookup_targets.items() if value[0] is not self.definitions}
        self.lookup_revision += 1
        self.lookup_targets[self.stamp(self.lookup_task)] = (self.definitions, self.dictionary_status)
        self.definitions.clear()
        self.dictionary_status.setText(t('Consultando diccionarios activos…'))
        self.send(self.lookup_task, dict(action='popup_lookup', term=term, surface=surface or term))

    def cancel(self):
        self.anki_token = None
        self.anki_lookup = None
        self.session += 1; self.revision += 1; self.lookup_revision += 1
        self.pending.clear()
        for _, status in self.lookup_targets.values(): status.setText(t('Consulta cancelada; vuelve a abrir la palabra para consultar.'))
        self.lookup_targets.clear()
        self.selection_box.hide()
        self.word_timer.stop(); self.word_queue.clear()
        self.debounce.stop(); self.selection_timer.stop(); self.flush_timer.stop()
        for task in (self.translate_task, self.phrase_task, self.lookup_task, self.resource_task): task.cancel()
        self.translation_status.setText(t('Operación cancelada; puedes editar y volver a procesar.'))

    def reject(self):
        self.cancel()
        super().reject()

    def closeEvent(self, event):
        self.cancel(); event.accept()  # QDialog hides; owner remains resident with cached idle workers.

    def shutdown(self):
        self.models_timer.stop()
        self.cancel(); self.closed = True; self.hide()

    def reconfigure_translation(self):
        from .translation_runtime import program
        self.models_fingerprint = self.model_fingerprint()
        self.edited()
        self.translate_task.begin_close()
        self.translate_task=self.task('translate',program=program())
        self.refresh_routes()

    def prepare_phrase(self):
        if self.resource_task.busy: return
        if QMessageBox.question(self, t('Preparar recursos de Next'),
                t('Instalar Fugashi 1.5.2 y UniDic Lite 1.0.8 (léxico de ~47 MB) en .venv-phrase, con versiones/hashes fijados. Puede acceder a PyPI. ¿Continuar?'),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        self.send(self.resource_task, {'action': 'prepare_phrase_runtime'})
        self.analysis_status.setText(t('Preparando recursos propios; puedes cancelar. No se usa otro proyecto.'))
