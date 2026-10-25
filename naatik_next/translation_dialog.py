"""Single translation journey embedded in the main window; work runs in workers."""
from .i18n import t
from PySide6.QtCore import Qt, QLocale
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QPlainTextEdit, QProgressBar, QFileDialog, QMessageBox, QGroupBox)
from .processes import Task
from .translation_runtime import program
from .translation_setup import plans


class TranslationSection(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.task = None
        self.serial = 0
        self.active = False
        self.flow = False
        self.report = dict(installed=[], routes=[], errors=[], runtime_error='')
        self.cache = dict(items=[], sha256=None)
        self.proposal = None
        self.started = False
        self.ready_pair = None
        layout = QVBoxLayout(self)
        title = QLabel(t('Traducción')); title.setStyleSheet('font-size:24px;font-weight:600')
        layout.addWidget(title)
        self.state = QLabel(); self.state.setTextFormat(Qt.PlainText); layout.addWidget(self.state)
        self.hint = QLabel(t('Elige los idiomas y prepara la traducción local CPU. Se conservan tus modelos.')); self.hint.setTextFormat(Qt.PlainText); self.hint.setWordWrap(True); layout.addWidget(self.hint)
        languages = QHBoxLayout(); layout.addLayout(languages)
        self.source = QComboBox(); self.destination = QComboBox()
        self.source.setAccessibleName(t('Idioma de origen')); self.destination.setAccessibleName(t('Idioma de destino'))
        self.populate_languages()
        for label, combo in ((t('Origen'), self.source), (t('Destino'), self.destination)):
            combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(18)
            languages.addWidget(QLabel(label)); languages.addWidget(combo, 1)
            combo.currentIndexChanged.connect(self.languages_changed)
        self.primary = QPushButton(); self.primary.clicked.connect(self.activate); layout.addWidget(self.primary)
        self.progress = QProgressBar(); self.progress.setRange(0, 1); layout.addWidget(self.progress)
        self.details = QPlainTextEdit(); self.details.setReadOnly(True); self.details.setMaximumHeight(190); layout.addWidget(self.details)
        self.details.textChanged.connect(lambda: self.details.setVisible(bool(self.details.toPlainText())))
        self.details.hide()
        self.advanced = QGroupBox(t('Opciones avanzadas')); self.advanced.setCheckable(True); self.advanced.setChecked(False)
        advanced = QVBoxLayout(self.advanced)
        self.advanced_body = QWidget(); body = QVBoxLayout(self.advanced_body); advanced.addWidget(self.advanced_body)
        local = QPushButton(t('Importar modelo local')); local.clicked.connect(self.import_file); body.addWidget(local)
        self.installed = QPlainTextEdit(); self.installed.setReadOnly(True); self.installed.setMaximumHeight(100); body.addWidget(self.installed)
        body.addWidget(QLabel(t('Diagnóstico')))
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(150); body.addWidget(self.log)
        self.advanced.toggled.connect(self.advanced_body.setVisible); self.advanced_body.hide(); layout.addWidget(self.advanced)
        layout.addStretch()
        self.set_state(t('Sin configurar'))

    def populate_languages(self):
        selected = self.owner.settings.get('translation_route', ['ja', 'en', 'es'])
        names = {locale.name().split('_')[0]: locale.nativeLanguageName()
                 for locale in QLocale.matchingLocales(QLocale.AnyLanguage, QLocale.AnyScript, QLocale.AnyCountry)
                 if locale.language() != QLocale.C and locale.nativeLanguageName()}
        names.update({'ja':t('Japonés'), 'es':t('Español'), 'en':t('Inglés'), 'fr':t('Francés'), 'de':t('Alemán'), 'pt':t('Portugués'), 'it':t('Italiano'), 'zh':t('Chino'), 'ko':t('Coreano'), 'ru':t('Ruso'), 'ar':t('Árabe')})
        for item in self.cache['items']:
            names[item['from_code']] = item['from_name']; names[item['to_code']] = item['to_name']
        for model in self.report['installed']:
            for key in ('from_code', 'to_code'): names.setdefault(model[key], model[key])
        for combo, fallback in ((self.source, selected[0]), (self.destination, selected[-1])):
            previous = combo.currentData() or fallback
            names.setdefault(previous, previous)
            combo.blockSignals(True); combo.clear()
            for code, name in sorted(names.items()): combo.addItem(f'{name} ({code})', code)
            combo.setCurrentIndex(combo.findData(previous)); combo.blockSignals(False)

    def pair(self): return (self.source.currentData(), self.destination.currentData())

    def set_state(self, state, detail=None):
        self.state.setText(state)
        self.state.setStyleSheet('font-size:18px;font-weight:600')
        if detail is not None: self.hint.setText(detail)
        self.primary.setText(t('Cancelar') if self.active else (t('Reparar') if state == t('Requiere atención') else t('Preparar traducción')))
        self.primary.setEnabled(self.active or state != t('Listo'))
        self.source.setEnabled(not self.active); self.destination.setEnabled(not self.active)
        self.advanced_body.setEnabled(not self.active)
        self.progress.setRange(0, 0 if self.active else 1)
        self.progress.setVisible(self.active)

    def languages_changed(self):
        self.ready_pair = None
        self.set_state(t('Sin configurar'), t('Pulsa Preparar traducción para comprobar los recursos de estos idiomas.'))
        self.details.clear()

    def inspect(self):
        if self.active: return
        self.started = True; self.flow = False
        self.start('translation_status')

    def activate(self):
        if self.active: self.cancel(); return
        if self.pair()[0] == self.pair()[1]:
            self.set_state(t('Requiere atención'), t('Elige idiomas de origen y destino diferentes.')); return
        self.flow = True; self.proposal = None
        self.start('translation_status')

    def start(self, action, **payload):
        if self.owner.closing: return
        self.serial += 1; serial = self.serial
        self.active = True
        self.set_state(t('Preparando'), t('Comprobando recursos…') if action == 'translation_status' else t('Preparando traducción; puedes cancelar.'))
        task = Task(self, program=program()); self.task = task
        task.interrupted = lambda: self.owner.closing or self.owner.interrupted()
        self.owner.popup_tasks.append(task)
        task.progress.connect(lambda text: self.log.appendPlainText(text) if serial == self.serial else None)
        task.result.connect(lambda value: self.finished(serial, action, value))
        task.error.connect(lambda text: self.failed(serial, text))
        task.start(dict(action=action, **payload), 1800000)

    def failed(self, serial, text):
        if serial != self.serial or self.owner.closing: return
        self.active = False; self.flow = False
        self.log.appendPlainText(text)
        self.set_state(t('Requiere atención'), text + t('\nPulsa Reparar para reintentar. Se conservan los modelos existentes.'))
        self.owner.refresh_translation_models()

    def finished(self, serial, action, value):
        if serial != self.serial or self.owner.closing: return
        self.active = False
        if action == 'translation_status':
            self.report = value; self.cache = value['catalogue']; self.populate_languages()
            self.installed.setPlainText(t('Modelos instalados en Next:\n') + ('\n'.join(f"{p['from_code']} → {p['to_code']} · {p['version']}" for p in value['installed']) or t('Ninguno')))
            self.log.setPlainText(value.get('detail', '') + '\n' + '\n'.join(value['errors']))
            routes = [r for r in value['routes'] if (r[0], r[-1]) == self.pair()]
            preferred = self.owner.settings.get('translation_route')
            if routes:
                route = preferred if preferred in routes else routes[0]
                self.start('translation_validate', route=route)
            elif self.flow:
                self.start('translation_catalogue')
            else:
                self.set_state(t('Requiere atención') if value['errors'] and value['installed'] else t('Sin configurar'), t('Pulsa Preparar traducción para detectar y preparar los componentes necesarios.'))
        elif action == 'translation_catalogue':
            self.cache = value; self.populate_languages()
            proposals = plans(value['items'], *self.pair())
            if not proposals:
                self.failed(serial, t('No hay una ruta compatible en el catálogo. Puedes importar modelos desde Opciones avanzadas.')); return
            proposal = proposals[0]
            self.start('translation_details', keys=proposal['keys'], catalogue_sha256=value['sha256'])
        elif action == 'translation_details':
            self.proposal = value
            edges = {(p['from_code'], p['to_code']) for p in self.report['installed']}
            self.missing = [i for i in value['items'] if (i['from_code'], i['to_code']) not in edges]
            text = t('Ruta: ') + ' → '.join(value['route'])
            if len(value['route']) > 2:
                text += t('\nIdioma intermedio: ') + ', '.join(t('inglés (en)') if code == 'en' else code for code in value['route'][1:-1]) + t('. La calidad depende de ambas etapas.')
            text += t('\n\nComponentes necesarios:')
            text += (t('\n• Motor Argos CPU y dependencias desde PyPI (tamaño total no publicado; versiones y hashes fijados).') if self.report['runtime_error'] else t('\n• Motor CPU ya disponible; se conserva.'))
            for item in self.missing:
                size = f"{item['bytes']:,} bytes" if item.get('bytes') else t('tamaño no publicado')
                text += (t('\n• Modelo ') + f"{item['from_code']}" + ' → ' + f"{item['to_code']}" + t(' · versión ') + f"{item['version']}" + ' (' + f'{size}' + ')')
                text += t('\n  Origen: ') + item['url'] + t('\n  Licencia: ') + item['license']
            text += t('\n\nLos modelos ya instalados se conservan. Se comprobará inferencia real antes de indicar Listo.')
            self.log.appendPlainText(self.describe(value))
            self.details.setPlainText(text)
            self.active = True
            self.set_state(t('Preparando'), t('Revisa la ruta y los componentes antes de confirmar.'))
            if QMessageBox.question(self, t('Preparar traducción'), text + t('\n\n¿Descargar los componentes necesarios, instalar y comprobar inferencia?'), QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                self.cancel(); return
            if self.owner.closing: return
            if self.report['runtime_error']: self.start('translation_runtime')
            else: self.install_missing()
        elif action == 'translation_runtime': self.install_missing()
        elif action == 'install_argos':
            self.owner.refresh_translation_models(); self.flow = False; self.start('translation_status')
        elif action in ('translation_download', 'translation_validate'):
            if not value.get('offline_checked') or not value.get('output', '').strip():
                self.failed(serial, t('No se obtuvo una comprobación de inferencia real.')); return
            route = value['route']; self.ready_pair = self.pair()
            # Only the explicit preparation journey changes the main default.
            if self.flow:
                self.owner.settings['translation_route'] = route; self.owner.persist()
            self.flow = False
            self.details.setPlainText(t('Ruta: ') + ' → '.join(route) + t('\nInferencia CPU comprobada sin red:\n') + value['input'] + '\n' + value['output'])
            self.installed.setPlainText(t('Modelos instalados en Next:\n') + '\n'.join(f"{m['from_code']} → {m['to_code']} · {m['version']}" for m in value.get('installed', [])))
            self.set_state(t('Listo'), t('Ruta comprobada: ') + ' → '.join(route) + t('. Abre Acciones → Translator para traducir.'))
            self.owner.refresh_translation_models()

    def install_missing(self):
        if self.missing:
            self.start('translation_download', keys=[i['key'] for i in self.proposal['items']], catalogue_sha256=self.proposal['sha256'], preserve_installed=True, download_keys=[i['key'] for i in self.missing])
        else: self.start('translation_validate', route=self.proposal['route'])

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, t('Importar modelo local'), '', t('Argos (*.argosmodel)'))
        if path and QMessageBox.question(self, t('Importar modelo local'), t('¿Importar este archivo en Next y comprobar las rutas? Su licencia no queda acreditada.\n') + path, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.flow = False; self.start('install_argos', path=path)

    def cancel(self):
        self.serial += 1
        if self.task: self.task.cancel()
        self.active = False; self.flow = False; self.ready_pair = None
        self.set_state(t('Sin configurar'), t('Preparación cancelada. Puedes reintentar; se conservan los modelos y los parciales recuperables.'))
        if not self.owner.closing: self.owner.refresh_translation_models()

    @staticmethod
    def describe(proposal):
        lines=[t('Ruta propuesta: ')+' → '.join(proposal['route'])]
        if len(proposal['route'])==3:lines.append(t('Idioma intermedio: inglés (en). La calidad depende de ambos modelos.'))
        for item in proposal['items']:
            size=f"{item['bytes']:,} bytes" if item.get('bytes') else t('no publicado / no disponible; máximo admitido 1 GiB')
            lines.extend([('\n' + f"{item['from_name']}" + ' (' + f"{item['from_code']}" + ') → ' + f"{item['to_name']}" + ' (' + f"{item['to_code']}" + t(') · modelo ') + f"{item['version']}" + t(' · Argos ≥ ') + f"{item['requires']}"),
                          t('Origen: ')+item['url'],t('Tamaño: ')+size,t('Licencia: ')+item['license']])
            if item.get('size_detail'):lines.append(item['size_detail'])
        lines.append(t('\nSe comprobarán ZIP, carga e inferencia CPU. El catálogo no publica SHA-256: se registra el hash recibido por HTTPS, sin atribuirle verificación contra un hash oficial.'))
        return '\n'.join(lines)
