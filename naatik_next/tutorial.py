"""Per-profile onboarding. Progress never certifies resource readiness."""
from .i18n import t
from copy import deepcopy
from .storage import paths, save_settings

KEY = 'tutorial'
STEPS = (('Bienvenida', 'Next permite capturar texto, reconocerlo con OCR, consultar diccionarios locales, traducir y enviar tarjetas a Anki.'), ('OCR', 'Elige motor e idioma en el asistente, prepara sus recursos y pulsa Comprobar. Descargar requiere tu confirmación; el asistente muestra el tamaño conocido.'), ('Traducción', 'Elige idiomas en Configuración de traducción. Consulta el plan y confirma los modelos que quieras descargar. Si el tamaño no está disponible, se indica como desconocido.'), ('Diccionarios', 'Importa tus ZIP Yomitan, revisa la selección y confirma. Después escribe una palabra en Diccionarios y pulsa Consultar.'), ('Anki (opcional)', 'Configura AnkiConnect y comprueba la conexión desde Anki, o continúa para saltar este paso.'), ('Primera prueba guiada', '1. Abre Captura y resultado y selecciona una región con Capturar.\n2. Reconoce el texto con OCR.\n3. Selecciona una palabra para consultar su diccionario.\n4. Abre Traducción y traduce el texto reconocido.\nPuedes volver a cualquier configuración si faltan recursos. Completar solo registra tu recorrido.'))


def initial_state(settings):
    value = settings.get(KEY)
    if isinstance(value, dict) and value.get('status') in ('pending', 'in_progress', 'skipped', 'completed'):
        try:
            step = int(value.get('step', 0))
        except (TypeError, ValueError):
            step = 0
        return {'status': value['status'], 'step': max(0, min(len(STEPS)-1, step))}
    # Even an empty pre-existing settings file is a legacy profile.
    if (paths()['config'] / 'settings.json').exists() or settings:
        return {'status': 'skipped', 'step': 0}
    return {'status': 'pending', 'step': 0}


def automatic(state, *, background=False, popup_only=False):
    return not background and not popup_only and state['status'] in ('pending', 'in_progress')


def persist(owner, status, step):
    candidate = deepcopy(owner.settings)
    candidate[KEY] = {'status': status, 'step': step}
    try:
        save_settings(candidate)
    except Exception as error:
        owner.fail((t('No se pudo guardar el progreso del tutorial: ') + f'{error}' + t('. Puedes seguir usando Next; al reiniciar se conserva el último paso guardado.')))
        return False
    owner.settings[KEY] = candidate[KEY]
    return True


def open_tutorial(owner):
    from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
    existing = getattr(owner, 'tutorial_dialog', None)
    if existing and existing.isVisible():
        existing.raise_()
        return

    class Tutorial(QDialog):
        def __init__(self):
            super().__init__(owner)
            self.setWindowTitle(t('Tutorial y configuración inicial'))
            self.resize(620, 380)
            state = owner.settings[KEY]
            self.step = state['step'] if state['status'] != 'completed' else 0
            layout = QVBoxLayout(self)
            self.title = QLabel(); layout.addWidget(self.title)
            self.text = QLabel(); self.text.setWordWrap(True); layout.addWidget(self.text)
            self.action = QPushButton(); self.action.clicked.connect(self.launch); layout.addWidget(self.action)
            self.practice = []
            for title, callback in ((t('1. Capturar región'), lambda: owner.capture()), (t('2. Reconocer imagen'), lambda: owner.recognize()), (t('3. Consultar palabra'), self.consult), (t('4. Traducir texto'), lambda: owner.translate())):
                control = QPushButton(title)
                control.clicked.connect(lambda checked=False, callback=callback: callback())
                layout.addWidget(control)
                self.practice.append(control)
            self.notice = QLabel(t('Puedes continuar sin preparar una función y configurarla después. No se descarga nada al avanzar.')); self.notice.setWordWrap(True); layout.addWidget(self.notice)
            row = QHBoxLayout(); layout.addLayout(row)
            self.back = QPushButton(t('Volver')); self.back.clicked.connect(lambda: self.move(-1)); row.addWidget(self.back)
            self.next = QPushButton(); self.next.clicked.connect(self.advance); row.addWidget(self.next)
            skip = QPushButton(t('Omitir por ahora')); skip.clicked.connect(self.skip); row.addWidget(skip)
            restart = QPushButton(t('Reiniciar tutorial')); restart.clicked.connect(self.restart); row.addWidget(restart)
            self.render()
            persist(owner, 'in_progress', self.step)

        def render(self):
            title, text = STEPS[self.step]
            self.title.setText(f'{self.step+1} / {len(STEPS)} — {t(title)}')
            self.text.setText(t(text))
            self.back.setEnabled(self.step > 0)
            for control in self.practice:
                control.setVisible(self.step == len(STEPS)-1)
            self.next.setText(t('Completar tutorial') if self.step == len(STEPS)-1 else t('Continuar / saltar este paso'))
            self.action.setText((t('Explorar Next'), t('Abrir asistente OCR'), t('Configurar traducción'), t('Importar ZIP y consultar'), t('Configurar Anki'), t('Abrir captura para la prueba'))[self.step])

        def restart(self):
            if persist(owner, 'in_progress', 0):
                self.step = 0
                self.render()

        def move(self, delta):
            target = self.step + delta
            if persist(owner, 'in_progress', target):
                self.step = target
                self.render()

        def advance(self):
            if self.step < len(STEPS)-1:
                self.move(1)
            elif persist(owner, 'completed', self.step):
                self.accept()

        def skip(self):
            if persist(owner, 'skipped', self.step):
                self.accept()

        def consult(self):
            owner.tabs.setCurrentIndex(0)
            owner.editor.setFocus()
            owner.statusBar().showMessage(t('Selecciona una palabra del texto reconocido para consultar el diccionario.'))

        def launch(self):
            owner.show(); owner.raise_()
            if self.step == 1:
                owner.show_setup()
            elif self.step == 2:
                owner.configure_translation()
            elif self.step == 3:
                owner.tabs.setCurrentIndex(1)
                owner.add_dictionary()
            elif self.step == 4:
                owner.tabs.setCurrentIndex(owner.tabs.indexOf(owner.anki_section.parent_scroll))
            else:
                owner.tabs.setCurrentIndex(0)
            # Nonmodal: the tutorial stays available while the user tries the app.

    owner.tutorial_dialog = Tutorial()
    owner.tutorial_dialog.show()
