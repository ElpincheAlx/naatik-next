"""Capability boundaries; opening an image uses Qt and needs no capture backend."""
from .i18n import t
import os
import sys


def kde_x11():
    return (sys.platform == 'linux' and os.environ.get('XDG_SESSION_TYPE') == 'x11'
            and 'KDE' in os.environ.get('XDG_CURRENT_DESKTOP', '').upper())


def summary():
    return (t('Abrir imagen: Qt/Pillow. Captura: adaptador Spectacle 6 en Linux KDE/X11. Atajo global: libX11 en Linux KDE/X11 con backend Qt xcb. Wayland, Windows, macOS y otras arquitecturas: sin acreditación de esta entrega.'))
