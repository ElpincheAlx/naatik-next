"""Validated local appearance settings and shared Qt presentation. No font downloads."""
from .i18n import t
import re
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

ROLES = {'background': 'Fondo', 'surface': 'Paneles y campos', 'text': 'Texto', 'muted': 'Texto secundario', 'accent': 'Acento', 'border': 'Bordes', 'selection': 'Selección'}
PRESETS = {
    'light': dict(background='#f7f8fa', surface='#ffffff', text='#1d2433', muted='#596579',
                  accent='#087f96', border='#cfd6df', selection='#b9d7ff'),
    'dark': dict(background='#171b24', surface='#232a36', text='#edf1f7', muted='#b0bdcf',
                 accent='#63cde0', border='#58677c', selection='#355b80'),
}
DEFAULTS = dict(theme='system', ui_font='', text_font='', ui_size=10, text_size=18, colors={})


def normalize(value):
    value = value if isinstance(value, dict) else {}
    result = dict(DEFAULTS, colors={})
    if value.get('theme') in ('system', 'light', 'dark'): result['theme'] = value['theme']
    for key, lower, upper in [('ui_size',8,24), ('text_size',10,40)]:
        number = value.get(key, result[key])
        if type(number) is int: result[key] = min(upper, max(lower, number))
    for key in ('ui_font', 'text_font'):
        name = value.get(key, '')
        if isinstance(name, str) and len(name) <= 200 and not any(ord(c) < 32 for c in name):
            result[key] = name
    colors = value.get('colors', {})
    if isinstance(colors, dict):
        result['colors'] = {key: color.lower() for key, color in colors.items()
                            if key in ROLES and isinstance(color, str) and re.fullmatch('#[a-fA-F0-9]{6}', color)}
    return result


def contrast(a, b):
    def luminance(color):
        c = QColor(color)
        values = [c.redF(), c.greenF(), c.blueF()]
        values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v*w for v,w in zip(values,(.2126,.7152,.0722)))
    x,y = sorted((luminance(a),luminance(b)))
    return (y+.05)/(x+.05)


def foreground(color):
    return '#ffffff' if contrast(color,'#ffffff') >= contrast(color,'#111827') else '#111827'


def colors_for(config):
    config = normalize(config)
    if config['theme'] == 'system':
        p = QApplication.palette()
        colors = {key:p.color(role).name() for key,role in {
            'background':QPalette.Window, 'surface':QPalette.Base, 'text':QPalette.Text,
            'muted':QPalette.PlaceholderText, 'accent':QPalette.Highlight,
            'border':QPalette.Mid, 'selection':QPalette.Highlight}.items()}
    else: colors = dict(PRESETS[config['theme']])
    colors.update(config['colors'])
    return colors


def family(config, key):
    name = config[key]
    return name if name in QFontDatabase.families() else QApplication.font().family()


def quoted(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def apply(widget, value, *, popup=False):
    config = normalize(value)
    colors = colors_for(config)
    palette = QPalette(QApplication.palette())
    for role, color in [(QPalette.Window,'background'),(QPalette.Base,'surface'),
                        (QPalette.AlternateBase,'background'),(QPalette.Button,'surface'),
                        (QPalette.WindowText,'text'),(QPalette.Text,'text'),(QPalette.ButtonText,'text'),
                        (QPalette.PlaceholderText,'muted'),(QPalette.Highlight,'selection'),
                        (QPalette.Link,'accent'),(QPalette.Mid,'border')]:
        palette.setColor(role,QColor(colors[color]))
    palette.setColor(QPalette.HighlightedText,QColor(foreground(colors['selection'])))
    for role in (QPalette.Text,QPalette.WindowText,QPalette.ButtonText):
        palette.setColor(QPalette.Disabled,role,QColor(colors['muted']))
    widget.setPalette(palette)
    font = QFont(family(config,'ui_font'),config['ui_size']); widget.setFont(font)
    if popup:
        from .popup_presentation import STYLE
        style = 'QWidget {background:transparent;color:'+colors['text']+';font-family:'+quoted(family(config,'ui_font'))+';font-size:'+str(config['ui_size'])+'pt;}\n' + STYLE
        # Map the old presentation's semantic colors; preserve geometry and hierarchy.
        mapping = {'#f7f8fa':'background','#f0f2f5':'background','#eef1f5':'background',
                   '#f5f7fa':'background','#f4f6f8':'background',
                   '#cfd6df':'border','#e2e6ec':'border','#e0e5eb':'border','#dde3ea':'border','#b9c0ca':'border',
                   '#42b9d0':'accent','#b9d7ff':'selection',
                   '#697386':'muted','#7b8495':'muted','#778195':'muted','#4f5c70':'muted','#596579':'muted','#687386':'muted'}
        style = re.sub(r'#[0-9a-fA-F]{6}',lambda match:colors[mapping.get(match[0],'text')],style)
        style = style.replace('color:white', 'color:'+foreground(colors['accent']))
        style = style.replace('background:white','background:'+colors['surface'])
        style = re.sub(r'font-family:[^;]+;', lambda match:'font-family:'+quoted(family(config,'ui_font'))+';',style)
        style = re.sub(r'font-size:(\d+)px;',lambda m:'font-size:'+str(round(int(m[1])*config['ui_size']/10))+'px;',style)
        style += '\nQTextEdit#editor {font-family:'+quoted(family(config,'text_font'))+';font-size:'+str(config['text_size'])+'pt;}'
        style += '\nQLabel#word {font-family:'+quoted(family(config,'text_font'))+';font-size:'+str(config['text_size'])+'pt;}'
        style += '\nQTextEdit#editor {selection-color:'+foreground(colors['selection'])+';}'
        for selector,scale in [('QTextBrowser#dictionary',.7),('QTextBrowser#furigana',.8),('QPlainTextEdit#translation',.85)]:
            style += '\n'+selector+' {font-family:'+quoted(family(config,'text_font'))+';font-size:'+str(round(config['text_size']*scale))+'pt;}'
    else:
        if not widget.objectName():widget.setObjectName('appearanceSurface')
        style = '#'+widget.objectName()+' {background:'+colors['background']+';} '
        style += 'QWidget {background:'+colors['background']+';color:'+colors['text']+';font-family:'+quoted(family(config,'ui_font'))+';font-size:'+str(config['ui_size'])+'pt;} '
        style += 'QPlainTextEdit, QTextEdit, QTextBrowser {background:'+colors['surface']+';color:'+colors['text']+';selection-background-color:'+colors['selection']+';selection-color:'+foreground(colors['selection'])+';font-family:'+quoted(family(config,'text_font'))+';font-size:'+str(config['text_size'])+'pt;}'
    style += '\nQPushButton, QComboBox, QSpinBox, QLineEdit {background:'+colors['surface']+';color:'+colors['text']+';border:1px solid '+colors['border']+';border-radius:4px;padding:4px;}'
    style += '\nQAbstractItemView, QTableWidget {background:'+colors['surface']+';color:'+colors['text']+';selection-background-color:'+colors['selection']+';selection-color:'+foreground(colors['selection'])+';}'
    style += '\nQTabBar::tab, QHeaderView::section {background:'+colors['surface']+';color:'+colors['text']+';border:1px solid '+colors['border']+';padding:5px;}'
    style += '\nQMenu {background:'+colors['surface']+';color:'+colors['text']+';} QMenu::item:selected {background:'+colors['selection']+';color:'+foreground(colors['selection'])+';}'
    style += '\nQPushButton:hover {background:'+colors['selection']+';color:'+foreground(colors['selection'])+';}'
    style += '\nQPushButton:focus, QComboBox:focus {border:1px solid '+colors['accent']+';} QTabBar::tab:selected {border-bottom:2px solid '+colors['accent']+';}'
    style += '\nQPushButton:disabled {color:'+colors['muted']+';}'
    widget.setStyleSheet(style)
    widget.setPalette(palette)
