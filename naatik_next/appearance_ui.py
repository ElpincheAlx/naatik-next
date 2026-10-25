"""Draft appearance controls with a scoped preview; saving is explicit."""
from .i18n import t
import copy
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
    QApplication,QComboBox,QFontComboBox,QSpinBox,QCheckBox,QColorDialog,QGroupBox,QPlainTextEdit)
from . import appearance
from .storage import save_settings


class AppearanceSection(QWidget):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner = owner
        self.saved = appearance.normalize(owner.settings.get('appearance'))
        self.draft = copy.deepcopy(self.saved)
        self.loading = False
        layout = QVBoxLayout(self)
        heading=QLabel(t('Apariencia')); heading.setStyleSheet('font-size:22px;font-weight:600'); layout.addWidget(heading)
        help=QLabel(t('Prueba los cambios aquí y pulsa Guardar y aplicar para usarlos en Next y en ambos popups.\nSolo se utilizan fuentes instaladas en este equipo.'));help.setWordWrap(True);layout.addWidget(help)
        form=QFormLayout();layout.addLayout(form)
        self.theme=QComboBox()
        for text,key in [(t('Sistema'),'system'),(t('Claro'),'light'),(t('Oscuro'),'dark')]:self.theme.addItem(text,key)
        form.addRow(t('Tema'),self.theme)
        self.fonts={};self.system_fonts={};self.sizes={}
        for key,label,size_key,minimum,maximum in [('ui_font',t('Fuente de interfaz'),'ui_size',8,24),('text_font',t('Fuente de lectura'),'text_size',10,40)]:
            row=QWidget();rl=QHBoxLayout(row);rl.setContentsMargins(0,0,0,0)
            use_system=QCheckBox(t('Del sistema'));picker=QFontComboBox();size=QSpinBox();size.setRange(minimum,maximum);size.setSuffix(' pt')
            rl.addWidget(use_system);rl.addWidget(picker,1);rl.addWidget(size)
            self.fonts[key]=picker;self.system_fonts[key]=use_system;self.sizes[size_key]=size
            form.addRow(label,row)
            use_system.toggled.connect(self.controls_changed);picker.currentFontChanged.connect(self.controls_changed);size.valueChanged.connect(self.controls_changed)
        group=QGroupBox(t('Colores personalizados'));gl=QFormLayout(group);layout.addWidget(group)
        self.color_buttons={}
        for key,label in appearance.ROLES.items():
            label = t(label)
            row=QWidget();rl=QHBoxLayout(row);rl.setContentsMargins(0,0,0,0)
            choose=QPushButton();choose.setAccessibleName(t('Elegir color: ')+label)
            reset=QPushButton(t('Del tema'));reset.setAccessibleName(t('Restablecer color: ')+label)
            choose.clicked.connect(lambda checked=False,key=key:self.choose_color(key))
            reset.clicked.connect(lambda checked=False,key=key:self.reset_color(key))
            rl.addWidget(choose);rl.addWidget(reset);gl.addRow(label,row);self.color_buttons[key]=choose
        note=QLabel(t('Cambiar de tema restablece sus colores en esta vista previa. Los tamaños se expresan en puntos y respetan el escalado de pantalla.'));note.setWordWrap(True);layout.addWidget(note)
        self.preview=QGroupBox(t('Vista previa · contenido de muestra'));pl=QVBoxLayout(self.preview)
        pl.addWidget(QLabel('Na’atik Next · Translator · OCR Phrase'))
        self.sample=QPlainTextEdit(t('日本語の文字を読みます。\nTexto de muestra: áéíóú · ñ · 日本 · にほん'));self.sample.setReadOnly(True);self.sample.setMaximumHeight(125);pl.addWidget(self.sample)
        self.secondary=QLabel(t('Lectura, traducción y diccionario · texto secundario'));pl.addWidget(self.secondary)
        self.accent=QLabel(t('Color de acento · selecciona texto de la muestra para probar el resaltado'));pl.addWidget(self.accent)
        buttons=QHBoxLayout();pl.addLayout(buttons)
        buttons.addWidget(QPushButton(t('Acción de muestra')));disabled=QPushButton(t('No disponible'));disabled.setEnabled(False);buttons.addWidget(disabled)
        layout.addWidget(self.preview)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        actions=QHBoxLayout();layout.addLayout(actions)
        for title,callback in [(t('Guardar y aplicar'),self.save),(t('Cancelar cambios'),self.cancel),(t('Restablecer valores'),self.defaults)]:
            button=QPushButton(title);button.clicked.connect(callback);actions.addWidget(button)
        layout.addStretch()
        self.theme.currentIndexChanged.connect(self.theme_changed)
        self.load_controls()
        QApplication.instance().paletteChanged.connect(self.system_changed)
        QApplication.instance().fontChanged.connect(self.system_changed)

    def system_changed(self,*args):
        if self.owner.closing:return
        if self.saved['theme']=='system' or not self.saved['ui_font'] or not self.saved['text_font']:
            self.apply_saved()
        self.refresh()

    def load_controls(self):
        self.loading=True
        self.theme.setCurrentIndex(self.theme.findData(self.draft['theme']))
        for key,picker in self.fonts.items():
            self.system_fonts[key].setChecked(not bool(self.draft[key]))
            picker.setCurrentFont(QFont(appearance.family(self.draft,key)))
            picker.setEnabled(bool(self.draft[key]))
        for key,spin in self.sizes.items():spin.setValue(self.draft[key])
        self.loading=False;self.refresh()

    def controls_changed(self,*args):
        if self.loading:return
        for key,picker in self.fonts.items():
            system=self.system_fonts[key].isChecked();picker.setEnabled(not system)
            self.draft[key]='' if system else picker.currentFont().family()
        for key,spin in self.sizes.items():self.draft[key]=spin.value()
        self.refresh()

    def theme_changed(self):
        if self.loading:return
        self.draft['theme']=self.theme.currentData();self.draft['colors']={};self.refresh()

    def choose_color(self,key):
        color=QColorDialog.getColor(QColor(appearance.colors_for(self.draft)[key]),self,t('Elegir ')+t(appearance.ROLES[key]).lower())
        if color.isValid():self.draft['colors'][key]=color.name();self.refresh()

    def reset_color(self,key):
        self.draft['colors'].pop(key,None);self.refresh()

    def refresh(self):
        colors=appearance.colors_for(self.draft)
        for key,button in self.color_buttons.items():
            color=colors[key];button.setText(color.upper())
            button.setStyleSheet('background:'+color+';color:'+appearance.foreground(color)+';border:1px solid '+colors['border']+';padding:5px;')
        appearance.apply(self.preview,self.draft)
        self.preview.setAutoFillBackground(True)
        self.secondary.setStyleSheet('color:'+colors['muted']+';')
        self.accent.setStyleSheet('background:'+colors['accent']+';color:'+appearance.foreground(colors['accent'])+';padding:6px;border-radius:4px;')
        ratios=[appearance.contrast(colors['text'],colors['surface']),appearance.contrast(colors['text'],colors['background']),appearance.contrast(colors['muted'],colors['surface'])]
        missing=[self.draft[key] for key in self.fonts if self.draft[key] and appearance.family(self.draft,key)!=self.draft[key]]
        message=t('Cambios sin guardar. Solo afectan a esta muestra.') if self.draft!=self.saved else t('Configuración guardada. La muestra no ejecuta acciones ni modifica tu texto.')
        if min(ratios)<4.5:message+=t(' Contraste bajo para texto pequeño; prueba otros colores.')
        if missing:message+=t(' Fuente no disponible: ')+', '.join(missing)+t('. Se muestra la fuente del sistema.')
        self.status.setText(message)

    def save(self):
        settings=dict(self.owner.settings,appearance=appearance.normalize(self.draft))
        try:save_settings(settings)
        except Exception:
            self.status.setText(t('No se pudo guardar Apariencia. Tus cambios se conservan en la vista previa.'));return
        self.owner.settings['appearance']=settings['appearance']
        self.saved=copy.deepcopy(settings['appearance']);self.draft=copy.deepcopy(self.saved)
        self.apply_saved();self.refresh();self.status.setText(t('Apariencia guardada y aplicada. También se usará al volver a abrir Next.'))

    def apply_saved(self):
        appearance.apply(self.owner,self.saved)
        for popup in self.owner.popups.values():appearance.apply(popup,self.saved,popup=True)

    def cancel(self):
        self.draft=copy.deepcopy(self.saved);self.load_controls()

    def defaults(self):
        self.draft=appearance.normalize({});self.load_controls()
