"""Next-owned presentation, specified from the read-only JapaneseMining UI review.

No legacy code, services or resources are imported. Widgets contain only plain
text or Next's resource-blocking dictionary renderer.
"""
from .i18n import t
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QToolButton, QScrollArea, QTextEdit, QPlainTextEdit, QComboBox,
    QApplication, QSizePolicy)
from .dictionary_view import DictionaryView


def styled(widget, name):
    widget.setObjectName(name)
    return widget


def text_label(text='', name='muted'):
    widget = styled(QLabel(), name)
    widget.setTextFormat(Qt.PlainText)
    widget.setText(text)
    widget.setWordWrap(True)
    if name in ('badge','badgeMuted'): widget.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
    return widget


class Header(QWidget):
    drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self.window().windowHandle()
            if not handle or not handle.startSystemMove():
                self.drag_offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint()-self.drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_offset = None
        super().mouseReleaseEvent(event)


class WordCard(QFrame):
    def __init__(self, popup, token, row):
        super().__init__()
        self.setObjectName('wordCard')
        self.popup, self.row = popup, row
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.toggle = styled(QToolButton(), 'wordHeader')
        self.toggle.setCheckable(True); self.toggle.setArrowType(Qt.RightArrow)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setAccessibleName(token['surface'] + t(': abrir diccionarios'))
        header = QHBoxLayout(self.toggle); header.setContentsMargins(20, 10, 14, 10); header.setSpacing(8)
        header.addWidget(text_label(token['surface'], 'word'))
        header.addWidget(text_label(token['reading'], 'reading')); header.addStretch()
        header.addWidget(text_label(token['pos'], 'badgeMuted'))
        self.toggle.setMinimumHeight(54)
        self.toggle.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Minimum)
        layout.addWidget(self.toggle)
        self.body = QWidget(); body = QVBoxLayout(self.body)
        body.setContentsMargins(18, 4, 18, 16); body.setSpacing(10)
        if token['base'] != token['surface']:
            body.addWidget(text_label(t('Forma base: ')+token['base'], 'reading'))
        self.status = text_label(t('Abre esta sección para consultar el diccionario.'))
        self.definitions = styled(DictionaryView(), 'dictionary')
        self.definitions.setMinimumHeight(150)
        body.addWidget(self.status); body.addWidget(self.definitions)
        def resize_definition():
            self.definitions.setFixedHeight(min(420,max(70,int(self.definitions.document().size().height())+12)))
        self.definitions.document().documentLayout().documentSizeChanged.connect(resize_definition)
        self.body.hide(); layout.addWidget(self.body)
        self.toggle.toggled.connect(self.expand)

    def expand(self, checked):
        self.toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.body.setVisible(checked)
        if checked:
            self.popup.definitions = self.definitions
            self.popup.dictionary_status = self.status
            self.popup.lookup_token(self.row)


STYLE = '''
QDialog#popup {background:#f7f8fa; color:#1d2433; border:1px solid #cfd6df; font-family:"Noto Sans","Noto Sans JP",sans-serif;}
QWidget#content {background:#f7f8fa;}
QWidget#header {background:white; border-bottom:1px solid #e2e6ec;}
QLabel#appTitle {color:#18202d; font-size:16px; font-weight:700;}
QPushButton#close {background:transparent; border:0; border-radius:17px; color:#697386; font-size:22px;}
QPushButton#close:hover {background:#f0f2f5; color:#1d2433;}
QFrame#hero {background:white; border:1px solid #e0e5eb; border-radius:14px;}
QTextEdit#editor {background:white; border:0; color:#111827; font-family:"Noto Serif CJK JP","Noto Sans JP",sans-serif; font-size:29px; font-weight:600; selection-background-color:#b9d7ff; selection-color:#111827;}
QLabel#selectionTitle {color:#111827; font-size:20px; font-weight:700;}
QLabel#hint {color:#7b8495; font-size:12px;}
QLabel#badge, QLabel#badgeMuted {border-radius:5px; padding:3px 7px; font-size:11px; font-weight:700;}
QLabel#badge {background:#42b9d0; color:white;}
QLabel#badgeMuted {background:#eef1f5; color:#596579;}
QFrame#box {background:white; border:1px solid #e0e5eb; border-radius:12px;}
QLabel#eyebrow {color:#778195; font-size:11px; font-weight:700;}
QTextBrowser#furigana {background:white; border:0; color:#4f5c70; font-size:16px;}
QPlainTextEdit#translation {background:white; border:0; color:#222b3a; font-size:17px;}
QLabel#muted {color:#7b8495; font-size:13px;}
QLabel#section {color:#202938; font-size:15px; font-weight:700;}
QFrame#wordCard {background:white; border:1px solid #dde3ea; border-radius:10px;}
QToolButton#wordHeader {background:transparent; border:0; text-align:left;}
QToolButton#wordHeader:hover {background:#f5f7fa; border-radius:10px;}
QLabel#word {color:#111827; font-size:22px; font-weight:600;}
QLabel#reading {color:#687386; font-size:13px;}
QTextBrowser#dictionary {background:white; color:#252f3f; border:0; font-size:14px;}
QWidget#footer {background:white; border-top:1px solid #e0e5eb;}
QPushButton {min-height:28px; border-radius:8px; padding:5px 10px; font-size:13px; font-weight:700; background:white; border:1px solid #cfd6df; color:#344054;}
QPushButton:hover {background:#f4f6f8;}
QScrollArea {border:0; background:#f7f8fa;}
QScrollBar:vertical {background:transparent; width:10px; margin:2px;}
QScrollBar::handle:vertical {background:#b9c0ca; border-radius:5px; min-height:36px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
'''


def build(p):
    """Build the source-specified hierarchy; processing belongs to TextPopup."""
    p.setObjectName('popup')
    from .appearance import apply
    apply(p, p.owner.settings.get('appearance'), popup=True)
    p.resize(720, 840); p.setMinimumSize(520, 560)
    root = QVBoxLayout(p); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
    header = styled(Header(), 'header'); header.setAttribute(Qt.WA_StyledBackground); bar = QHBoxLayout(header)
    bar.setContentsMargins(18, 10, 10, 10); bar.setSpacing(8)
    bar.addWidget(text_label('Na’atik Next', 'appTitle'))
    bar.addWidget(text_label('Translator' if p.mode == 'translator' else 'OCR Phrase', 'badge'))
    bar.addStretch(); close = styled(QPushButton('×'), 'close'); close.setFixedSize(34, 34)
    close.setAccessibleName(t('Cerrar')); close.clicked.connect(p.close); bar.addWidget(close)
    root.addWidget(header)
    p.scroll = QScrollArea(); p.scroll.setWidgetResizable(True)
    p.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    content = styled(QWidget(), 'content'); column = QVBoxLayout(content)
    column.setContentsMargins(18, 16, 18, 20); column.setSpacing(14)
    p.scroll.setWidget(content); root.addWidget(p.scroll, 1)

    def box(title, hero=False):
        frame = styled(QFrame(), 'hero' if hero else 'box'); layout = QVBoxLayout(frame)
        layout.setContentsMargins(*( (18,16,18,16) if hero else (16,12,16,12)))
        layout.setSpacing(8 if hero else 4)
        if title: layout.addWidget(text_label(title, 'eyebrow'))
        column.addWidget(frame)
        return layout

    hero = box(t('OCR') if p.mode == 'translator' else '', True)
    p.editor = styled(QTextEdit(), 'editor'); p.editor.setAcceptRichText(False)
    p.editor.setPlaceholderText(t('Escribe o pega texto…')); p.editor.setMinimumHeight(180 if p.mode == 'translator' else 70)
    hero.addWidget(p.editor)
    p.furigana = styled(DictionaryView(), 'furigana')
    p.furigana.setMinimumHeight(40); p.furigana.setMaximumHeight(420)
    if p.mode == 'translator':
        hero.addWidget(text_label(t('Selecciona una palabra o varios kanji para consultar el diccionario.'), 'hint'))
        box('FURIGANA').addWidget(p.furigana)
    else:
        hero.addWidget(p.furigana)
        badges = QHBoxLayout(); badges.addWidget(text_label(t('frase'), 'badge')); badges.addStretch(); hero.addLayout(badges)
    translation_box = box(t('TRANSLATION') if p.mode == 'translator' else t('TRADUCCIÓN'))
    route_row = QHBoxLayout(); route_row.addWidget(text_label(t('Ruta Argos'), 'hint'))
    p.route = QComboBox(); p.route.setAccessibleName(t('Ruta de idiomas Argos')); route_row.addWidget(p.route, 1)
    translation_box.addLayout(route_row)
    p.translation = styled(QPlainTextEdit(), 'translation'); p.translation.setReadOnly(True)
    p.translation.setMinimumHeight(150 if p.mode == 'translator' else 40)
    if p.mode == 'phrase':
        def resize_translation():
            p.translation.setFixedHeight(min(300,max(40,p.translation.fontMetrics().lineSpacing()*max(1,p.translation.document().blockCount())+12)))
        p.translation.document().documentLayout().documentSizeChanged.connect(resize_translation)
        resize_translation()
    translation_box.addWidget(p.translation)
    p.translation_status = text_label(t('Comprobando traducción local…')); translation_box.addWidget(p.translation_status)
    p.prepare_translation = QPushButton(t('Preparar traducción')); p.prepare_translation.clicked.connect(p.owner.configure_translation)
    translation_box.addWidget(p.prepare_translation); p.prepare_translation.hide()
    p.analysis_status = text_label(); column.addWidget(p.analysis_status)
    p.word_cards, p.word_queue = [], []
    p.word_timer = QTimer(p); p.word_timer.setSingleShot(True)
    p.word_timer.timeout.connect(lambda: append_words(p))
    p.words_widget = QWidget(); p.words_layout = QVBoxLayout(p.words_widget)
    p.words_layout.setContentsMargins(0,0,0,0); p.words_layout.setSpacing(14)
    if p.mode == 'phrase': column.addWidget(text_label(t('Palabras y diccionarios'), 'section')); column.addWidget(p.words_widget)
    selection = box(t('DICCIONARIO · SELECCIÓN'))
    p.selection_box = selection.parentWidget()
    if p.mode == 'translator':
        column.removeWidget(p.selection_box)
        p.selection_box.setParent(p, Qt.ToolTip | Qt.FramelessWindowHint)
        p.selection_box.setMinimumWidth(360); p.selection_box.setMaximumWidth(540)
        p.selection_box.resize(440, 260)
    p.selection_box.hide()
    p.selection_title = text_label('', 'selectionTitle'); selection.addWidget(p.selection_title)
    p.selection_status = text_label(); p.selection_definitions = styled(DictionaryView(), 'dictionary')
    p.selection_definitions.setMinimumHeight(150)
    selection.addWidget(p.selection_status); selection.addWidget(p.selection_definitions)
    p.dictionary_status, p.definitions = p.selection_status, p.selection_definitions
    column.addStretch()
    footer = styled(QWidget(), 'footer'); buttons = QHBoxLayout(footer)
    buttons.setContentsMargins(14,10,14,10); buttons.setSpacing(8)
    settings = QPushButton(t('Opciones ▾')); buttons.addWidget(settings); buttons.addStretch()
    copy = QPushButton(t('Copiar texto') if p.mode == 'translator' else t('Copiar frase'))
    copy.clicked.connect(lambda: QApplication.clipboard().setText(p.editor.toPlainText())); buttons.addWidget(copy)
    anki = QPushButton(t('Agregar a Anki')); anki.clicked.connect(p.open_anki); buttons.addWidget(anki)
    root.addWidget(footer)
    # Actual implemented controls only, kept out of the original's reading area.
    p.options = QWidget(); controls = QVBoxLayout(p.options); controls.setContentsMargins(14,8,14,10)
    p.process_button = QPushButton(t('Traducir') if p.mode == 'translator' else t('Analizar'))
    cancel = QPushButton(t('Cancelar')); cancel.clicked.connect(p.cancel)
    row = QHBoxLayout(); row.addWidget(p.process_button); row.addWidget(cancel); controls.addLayout(row)
    for title, callback in [(t('Consultar selección'), p.lookup_selection), (t('Configuración'), lambda:p.owner.external_command('show')),
            (t('Preparar lecturas…'), p.prepare_phrase)]:
        button = QPushButton(title); button.clicked.connect(callback); controls.addWidget(button)
    p.options.hide(); root.addWidget(p.options)
    for button in p.findChildren(QPushButton): button.setAutoDefault(False)
    settings.clicked.connect(lambda:p.options.setVisible(not p.options.isVisible()))
    def resize_readings():
        p.furigana.setFixedHeight(min(420, max(40, int(p.furigana.document().size().height()) + 12)))
    p.furigana.document().documentLayout().documentSizeChanged.connect(resize_readings)
    resize_readings()
    if p.mode == 'phrase':
        def resize_editor():
            p.editor.setFixedHeight(min(300, max(70, int(p.editor.document().size().height()) + 12)))
        p.editor.document().documentLayout().documentSizeChanged.connect(resize_editor)
        resize_editor()


def clear_words(p):
    p.lookup_targets.clear()
    p.word_timer.stop(); p.word_queue.clear()
    p.definitions, p.dictionary_status = p.selection_definitions, p.selection_status
    while p.words_layout.count():
        item = p.words_layout.takeAt(0)
        if item.widget(): item.widget().hide(); item.widget().deleteLater()
    p.word_cards.clear()


def append_words(p):
    if p.closed or p.owner.closing: return
    for _ in range(min(24,len(p.word_queue))):
        row, token = p.word_queue.pop(0)
        card = WordCard(p, token, row); p.word_cards.append(card); p.words_layout.addWidget(card)
    if p.word_queue: p.word_timer.start(0)


def show_words(p):
    clear_words(p)
    if p.mode == 'phrase':
        p.word_queue = list(enumerate(p.token_data))
        if not p.word_queue: p.words_layout.addWidget(text_label(t('No hay palabras analizadas.')))
        append_words(p)


def show_selection(p):
    if p.mode == 'translator':
        pos = p.editor.viewport().mapToGlobal(p.editor.cursorRect().bottomRight()) + QPoint(14,18)
        screen = (QApplication.screenAt(pos) or p.screen()).availableGeometry()
        pos.setX(max(screen.left(), min(pos.x(), screen.right()-p.selection_box.width())))
        pos.setY(max(screen.top(), min(pos.y(), screen.bottom()-p.selection_box.height())))
        p.selection_box.move(pos)
    p.selection_box.show()
