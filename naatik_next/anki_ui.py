"""One guided configuration section and a memory-only editable composer."""
from .i18n import t
import copy
import html
from datetime import datetime
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFormLayout, QGroupBox, QDialog, QPlainTextEdit, QCheckBox,
    QScrollArea)
from .processes import Task
from .anki import Journal, validate

SOURCES = {'word': 'Palabra / selección', 'reading': 'Lectura', 'sentence': 'Frase', 'translation': 'Traducción automática', 'definitions': 'Definiciones con origen', 'ocr': 'OCR original', 'corrected': 'Texto corregido', 'manual': 'Texto manual'}


class AnkiSection(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.checked = False
        self.fields = []
        self.mapping = {}
        self.drafts = []
        self.operation = None
        self.record = None
        self.layout = QVBoxLayout(self)
        self.status = QLabel(t('Sin configurar. Abre Anki con el perfil que quieres usar y prepara AnkiConnect.\nNo se enviará nada al comprobar.')); self.status.setWordWrap(True)
        self.layout.addWidget(self.status)
        check = QPushButton(t('Comprobar conexión')); check.clicked.connect(self.check); self.layout.addWidget(check)
        self.check_button = check
        guide = QGroupBox(t('No tengo Anki / Cómo preparar AnkiConnect')); guide.setCheckable(True); guide.setChecked(False)
        gl = QVBoxLayout(guide)
        self.guide_body = QWidget(); body = QVBoxLayout(self.guide_body)
        explanation = QLabel(t('1. Instala Anki para escritorio desde su sitio oficial y ábrelo.\n2. Herramientas → Complementos → Obtener complementos: 2055492159.\n3. Reinicia Anki, abre el perfil deseado y vuelve a comprobar aquí.\nNo necesitas AnkiWeb ni sincronizar. Next no instala ni cambia tu perfil.'))
        explanation.setWordWrap(True); body.addWidget(explanation)
        for title, url in [(t('Ver instalación oficial'), 'https://apps.ankiweb.net/'), (t('Ficha oficial AnkiConnect'), 'https://ankiweb.net/shared/info/2055492159')]:
            button = QPushButton(title); button.clicked.connect(lambda checked=False, url=url: QDesktopServices.openUrl(QUrl(url))); body.addWidget(button)
        gl.addWidget(self.guide_body); self.guide_body.hide(); guide.toggled.connect(self.guide_body.setVisible); self.layout.addWidget(guide)
        self.destination = QWidget(); dl = QFormLayout(self.destination)
        self.deck, self.model = QComboBox(), QComboBox()
        dl.addRow(t('Mazo'), self.deck); dl.addRow(t('Tipo de nota'), self.model)
        self.model.currentIndexChanged.connect(self.model_changed)
        self.layout.addWidget(self.destination); self.destination.hide()
        self.map_box = QWidget(); self.map_layout = QFormLayout(self.map_box); self.layout.addWidget(self.map_box); self.map_box.hide()
        self.save = QPushButton(t('Guardar configuración')); self.save.clicked.connect(self.save_config); self.layout.addWidget(self.save); self.save.hide()
        cancel = QPushButton(t('Cancelar cambios de configuración')); cancel.clicked.connect(self.cancel_config); self.layout.addWidget(cancel)
        back = QPushButton(t('Volver a la previsualización — tu texto se conserva')); back.clicked.connect(self.return_draft); self.layout.addWidget(back)
        advanced = QGroupBox(t('Opciones avanzadas / Diagnóstico')); advanced.setCheckable(True); advanced.setChecked(False)
        al = QVBoxLayout(advanced); self.advanced_body = QWidget(); form = QFormLayout(self.advanced_body)
        self.endpoint = QLineEdit(owner.settings.get('anki_endpoint', 'http://127.0.0.1:8765'))
        self.key = QLineEdit(); self.key.setEchoMode(QLineEdit.Password)
        form.addRow(t('Dirección local · API 6 · espera 8 s'), self.endpoint); form.addRow(t('Clave solo para esta sesión'), self.key)
        self.endpoint.textChanged.connect(self.invalidate); self.key.textChanged.connect(self.invalidate)
        al.addWidget(self.advanced_body); self.advanced_body.hide(); advanced.toggled.connect(self.advanced_body.setVisible); self.layout.addWidget(advanced)
        self.recovery_profile = QCheckBox(t('Para recuperar: he verificado que Anki tiene abierto el mismo perfil del intento'))
        self.layout.addWidget(self.recovery_profile)
        self.recovery = QWidget(); self.recovery_layout = QVBoxLayout(self.recovery); self.layout.addWidget(self.recovery)
        self.layout.addStretch()
        self.task = Task(owner)
        self.task.interrupted = lambda: owner.closing or owner.interrupted()
        owner.tasks.append(self.task)
        self.task.result.connect(self.completed); self.task.error.connect(self.failed)
        self.task.busy_changed.connect(self.busy)
        self.refresh_recovery()
        config = owner.settings.get('anki')
        if config: self.status.setText(t('Configuración guardada: ') + config['deck'] + ' · ' + config['model'] + t('\nComprueba conexión y confirma el perfil abierto antes de enviar.'))

    def refresh_recovery(self):
        while self.recovery_layout.count():
            item = self.recovery_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        try:
            for record in Journal().records():
                if record['state'] != 'uncertain': continue
                label = QLabel(t('Envío sin confirmar · ') + record['deck'] + ' · ' + record['uuid'][:8]); self.recovery_layout.addWidget(label)
                button = QPushButton(t('Comprobar resultado (confirma primero el perfil abierto)'))
                button.clicked.connect(lambda checked=False, record=record: self.reconcile(record)); self.recovery_layout.addWidget(button)
        except Exception:
            self.status.setText(t('No se puede leer el registro de recuperación. El envío permanecerá bloqueado.'))

    def invalidate(self):
        self.recovery_profile.setChecked(False)
        self.checked = False; self.destination.hide(); self.map_box.hide(); self.save.hide()
        self.status.setText(t('Conexión sin verificar. Vuelve a comprobar antes de elegir destino o enviar.'))

    def busy(self, busy):
        self.check_button.setEnabled(not busy); self.destination.setEnabled(not busy)
        self.endpoint.setEnabled(not busy); self.key.setEnabled(not busy); self.save.setEnabled(not busy)
        for draft in self.drafts: draft.update_send()

    def run(self, operation, **kwargs):
        if self.task.busy: return False
        self.operation = operation
        self.task.start(dict(action='anki', operation=operation, endpoint=self.endpoint.text(), key=self.key.text(), **kwargs), 60000)
        return True

    def check(self):
        if self.task.busy: return
        for draft in self.drafts: draft.profile.setChecked(False)
        self.invalidate(); self.status.setText(t('Comprobando conexión y acceso; no se crean notas…'))
        self.run('check')

    def completed(self, result):
        if self.operation == 'check':
            self.checked = True
            config = self.owner.settings.get('anki', {})
            for combo, values, saved in [(self.deck, result['decks'], config.get('deck')), (self.model, result['models'], config.get('model'))]:
                combo.blockSignals(True); combo.clear(); combo.addItem(t('Elige un destino…'), None)
                for value in values: combo.addItem(value, value)
                combo.setCurrentIndex(max(0, combo.findData(saved))); combo.blockSignals(False)
            self.destination.show()
            self.status.setText(t('Conectado. Opera sobre el perfil ya abierto en Anki; verifica que sea el deseado.\nElige mazo y tipo. Si faltan, créalos manualmente en Anki y vuelve a comprobar.'))
            self.model_changed()
        elif self.operation == 'fields':
            self.fields = result['fields']; self.show_mapping()
        else:
            record = result['record']
            self.status.setText(t('Validación rechazada antes de enviar. Revisa duplicados, destino, campos y plantillas; tu edición se conserva.') if result['state'] == 'rejected' else t('Nota agregada · ID ') + str(record['note_id']) if result['state'] == 'confirmed' else t('Envío sin confirmar. No sabemos si Anki recibió la nota. No la enviaremos otra vez. Revisa el perfil y comprueba el resultado.'))
            for draft in self.drafts:
                if draft.record and draft.record['uuid'] == record['uuid']:
                    draft.status.setText(self.status.text())
                    if result['state'] == 'rejected': draft.record = None
                    draft.update_send()
            self.refresh_recovery()

    def failed(self, message):
        if self.operation in ('send', 'reconcile'):
            message = t('Envío sin confirmar. No se reenviará. Comprueba el resultado en el mismo perfil de Anki.')
            self.refresh_recovery()
        else: self.invalidate()
        self.status.setText(message)
        for draft in self.drafts:
            if draft.record: draft.status.setText(message)
            draft.update_send()

    def model_changed(self):
        self.map_box.hide(); self.save.hide(); self.fields = []
        if self.model.currentData() and self.checked:
            self.run('fields', model=self.model.currentData())

    def show_mapping(self):
        while self.map_layout.count():
            item = self.map_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        config = self.owner.settings.get('anki', {})
        saved = config.get('mapping', {}) if config.get('model') == self.model.currentData() and config.get('fields') == self.fields else {}
        self.mapping = {}
        self.compositions = {}
        for name in self.fields:
            combo = QComboBox(); combo.addItem(t('No incluir'), '')
            for key, title in SOURCES.items(): combo.addItem(t(title), key)
            combo.addItem(t('Combinar bloques con rótulos…'), 'compose')
            selected = saved.get(name, '')
            combo.setCurrentIndex(max(0, combo.findData('compose' if isinstance(selected, list) else selected)))
            self.mapping[name] = combo
            row = QWidget(); layout = QVBoxLayout(row); layout.addWidget(combo)
            composition = QWidget(); blocks = QVBoxLayout(composition); checks = {}
            for key, title in SOURCES.items():
                check = QCheckBox(t(title)); check.setChecked(isinstance(selected, list) and key in selected)
                blocks.addWidget(check); checks[key] = check
            self.compositions[name] = checks
            layout.addWidget(composition); composition.setVisible(combo.currentData() == 'compose')
            combo.currentIndexChanged.connect(lambda index, combo=combo, widget=composition: widget.setVisible(combo.currentData() == 'compose'))
            self.map_layout.addRow(name + t(' · qué recibirá'), row)
        example = QLabel(t('Ejemplo sintético de ayuda: Frase = 日本を読む。 · Palabra = 日本\nLas fuentes ausentes quedan vacías. La muestra nunca se envía.\nSin recursos puedes mapear Texto manual y editar los campos en la previsualización.')); example.setWordWrap(True)
        self.map_layout.addRow(example); self.map_box.show(); self.save.show()

    def save_config(self):
        if not self.checked or not self.deck.currentData() or not self.fields:
            self.status.setText(t('Elige mazo y tipo y comprueba la conexión.')); return
        mapping = {name: ([key for key, check in self.compositions[name].items() if check.isChecked()]
                          if combo.currentData() == 'compose' else combo.currentData()) for name, combo in self.mapping.items()}
        if not mapping.get(self.fields[0]):
            self.status.setText(t('Elige una fuente para el primer campo; podrás editar su contenido antes de enviar.')); return
        self.owner.settings['anki'] = dict(deck=self.deck.currentData(), model=self.model.currentData(), fields=list(self.fields), mapping=mapping, checked=datetime.now().isoformat(timespec='seconds'))
        self.owner.settings['anki_endpoint'] = self.endpoint.text(); self.owner.persist()
        self.status.setText(t('Configurado · ') + self.deck.currentData() + ' · ' + self.model.currentData() + t('\nListo para previsualizar. Anki debe permanecer abierto. No se ha enviado ninguna nota.'))
        for draft in self.drafts: draft.update_send()

    def cancel_config(self):
        if self.task.busy: return
        self.invalidate(); self.return_draft()

    def open_draft(self, sources):
        draft = Composer(self, copy.deepcopy(sources)); self.drafts.append(draft)
        if self.owner.settings.get('anki'):
            draft.show(); draft.raise_()
        else: self.configure()

    def configure(self):
        self.owner.show(); self.owner.raise_(); self.owner.tabs.setCurrentWidget(self.parent_scroll)
        self.status.setText(self.status.text() + t('\nTu texto se conserva en la previsualización.'))

    def return_draft(self):
        if self.drafts:
            draft = self.drafts[-1]
            if draft.config is None and self.owner.settings.get('anki'): draft.adopt()
            draft.show(); draft.raise_(); draft.update_send()

    def reconcile(self, record):
        if not self.checked or not self.recovery_profile.isChecked():
            self.status.setText(t('Comprueba conexión y verifica el mismo perfil de Anki antes de consultar la etiqueta del intento.')); return
        self.run('reconcile', record=record)


class Composer(QDialog):
    def __init__(self, section, sources):
        super().__init__(section.owner)
        self.section, self.sources = section, sources
        self.record = None
        self.setWindowTitle(t('Previsualizar contenido de la nota')); self.resize(720, 720)
        layout = QVBoxLayout(self)
        self.summary = QLabel(); self.summary.setWordWrap(True); layout.addWidget(self.summary)
        layout.addWidget(QLabel(t('Vista previa del contenido de campos; no reproduce las plantillas de Anki.\nUn tipo de nota puede generar varias tarjetas. Cloze no está habilitado.')))
        scroll = QScrollArea(); scroll.setWidgetResizable(True); content = QWidget(); self.form = QFormLayout(content); scroll.setWidget(content); layout.addWidget(scroll)
        self.blocks = {}
        entries = sources.get('definition_entries', [])
        if entries:
            choice = QComboBox(); choice.addItem(t('Elige una entrada de diccionario para revisar…'), None)
            for entry in entries:
                choice.addItem(entry['title'] + t(' · revisión ') + entry['revision'] + ' · ' + entry.get('reading', ''), entry)
            self.form.addRow(t('Definición y procedencia'), choice)
            def choose_definition():
                entry = choice.currentData()
                value = (entry['text'] + t('\nDiccionario: ') + entry['title'] + t(' · revisión ') + entry['revision']) if entry else ''
                self.blocks['definitions'][1].setPlainText(value)
                self.blocks['definitions'][0].setChecked(False)
            choice.currentIndexChanged.connect(choose_definition)
        for key, title in SOURCES.items():
            value = sources.get(key, '')
            row = QWidget(); rl = QVBoxLayout(row)
            include = QCheckBox(t(title) + (t(' · disponible') if value else t(' · no disponible; edición manual posible')))
            include.setChecked(key in ('sentence', 'word', 'reading') and bool(value))
            editor = QPlainTextEdit(value); editor.setMaximumHeight(75)
            origin = QLabel(sources.get(key + '_origin', t('Instantánea del popup')) if value else t('Sin datos acreditados'))
            editor.textChanged.connect(lambda origin=origin: origin.setText(t('Editado por el usuario')))
            rl.addWidget(include); rl.addWidget(editor); rl.addWidget(origin)
            self.form.addRow(row); self.blocks[key] = (include, editor)
            if not value and key in ('ocr', 'corrected'):
                row.hide()
        adopt = QPushButton(t('Aplicar fuentes incluidas a los campos (reemplaza la edición de campos)')); adopt.clicked.connect(self.adopt); layout.addWidget(adopt)
        self.final_box = QWidget(); self.final_form = QFormLayout(self.final_box); self.form.insertRow(0, self.final_box)
        self.editors = {}; self.config = None
        self.profile = QCheckBox(t('He comprobado el perfil abierto en Anki y revisado este destino y contenido')); layout.addWidget(self.profile)
        self.status = QLabel(t('Traducción y definiciones requieren inclusión explícita. Sin audio ni imagen.')); self.status.setWordWrap(True); layout.addWidget(self.status)
        layout.addWidget(QLabel(t('No se permiten duplicados deliberados. Anki compara según tipo y primer campo.\nSe añadirá una etiqueta técnica naatik_tx_<uuid> para recuperar este intento.')))
        row = QHBoxLayout(); layout.addLayout(row)
        configure = QPushButton(t('Configurar Anki')); configure.clicked.connect(self.configure); row.addWidget(configure)
        close = QPushButton(t('Volver / conservar borrador')); close.clicked.connect(self.hide); row.addWidget(close)
        self.send_button = QPushButton(t('Agregar a Anki')); self.send_button.clicked.connect(self.send); row.addWidget(self.send_button)
        for button in self.findChildren(QPushButton): button.setAutoDefault(False)
        self.profile.toggled.connect(self.update_send)
        self.adopt()

    def configure(self):
        self.hide(); self.section.configure()

    def adopt(self):
        if self.record: return
        config = self.section.owner.settings.get('anki')
        if not config:
            self.summary.setText(t('Sin configurar · tu texto se conserva. Abre Configurar Anki.')); return
        self.config = copy.deepcopy(config)
        while self.final_form.count():
            item = self.final_form.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.editors = {}
        self.final_form.addRow(QLabel(t('Campos finales editables · se enviarán exactamente estos valores')))
        for name in config['fields']:
            key = config['mapping'].get(name)
            if isinstance(key, list):
                value = '\n\n'.join(t(SOURCES[source]) + ':\n' + self.blocks[source][1].toPlainText()
                    for source in key if source in self.blocks and self.blocks[source][0].isChecked())
            else:
                block = self.blocks.get(key)
                value = block[1].toPlainText() if block and block[0].isChecked() else ''
            editor = QPlainTextEdit(value); editor.setMaximumHeight(90)
            self.editors[name] = editor; self.final_form.addRow(name + t(' · texto literal'), editor)
        self.summary.setText(t('Destino: ') + config['deck'] + ' · ' + config['model'] + '\nModo: ' + (t('Palabra') if self.sources.get('word') else t('Frase')))
        self.profile.setChecked(False); self.update_send()

    def update_send(self):
        if not hasattr(self, 'send_button'): return
        matches = self.config == self.section.owner.settings.get('anki')
        self.send_button.setEnabled(bool(matches and self.config and self.section.checked and not self.section.task.busy and not self.record and self.profile.isChecked()))
        if self.config and not matches:
            self.status.setText(t('La configuración cambió. Pulsa Aplicar fuentes para revisar el nuevo destino; tus bloques se conservan.'))

    def send(self):
        if not self.send_button.isEnabled(): return
        config = self.config
        note = dict(deckName=config['deck'], modelName=config['model'], fields={name: html.escape(editor.toPlainText()).replace('\n', '<br>') for name, editor in self.editors.items()})
        try:
            validate(note, config['fields'])
            self.record = Journal().reserve(note)
        except Exception as exc:
            self.status.setText(str(exc)); return
        self.update_send()
        self.status.setText(t('Enviando una sola vez; no cierres Anki…'))
        self.section.run('send', note=note, record=self.record)
