"""One passive X11 key grab, on a dedicated connection; no keyboard monitoring.

Official API references and platform limits: docs/GLOBAL-HOTKEY.md.
"""
from .i18n import t
import ctypes as C
import os
from PySide6.QtCore import QObject, QSocketNotifier, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence
from .storage import UserError

DEFAULT_SHORTCUT = 'Ctrl+Alt+Shift+R'


class KeyEvent(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', C.c_ulong), ('send_event', C.c_int),
                ('display', C.c_void_p), ('window', C.c_ulong), ('root', C.c_ulong),
                ('subwindow', C.c_ulong), ('time', C.c_ulong),
                ('x', C.c_int), ('y', C.c_int), ('x_root', C.c_int), ('y_root', C.c_int),
                ('state', C.c_uint), ('keycode', C.c_uint), ('same_screen', C.c_int)]


class Event(C.Union):
    _fields_ = [('type', C.c_int), ('key', KeyEvent), ('pad', C.c_long * 24)]


class ErrorEvent(C.Structure):
    _fields_ = [('type', C.c_int), ('display', C.c_void_p), ('resourceid', C.c_ulong),
                ('serial', C.c_ulong), ('error_code', C.c_ubyte),
                ('request_code', C.c_ubyte), ('minor_code', C.c_ubyte)]


class ModifierMap(C.Structure):
    _fields_ = [('max_keypermod', C.c_int), ('modifiermap', C.POINTER(C.c_ubyte))]


def combination(text):
    sequence = QKeySequence.fromString(text, QKeySequence.PortableText)
    if sequence.count() != 1 or sequence.isEmpty():
        raise UserError(t('Pulsa una sola combinación de teclas.'))
    key = sequence[0]
    modifiers = key.keyboardModifiers()
    supported = Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier
    if modifiers & ~supported or not modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
        raise UserError(t('Incluye Ctrl, Alt o Meta junto con una tecla (Shift solo no basta).'))
    code = key.key()
    if Qt.Key_A <= code <= Qt.Key_Z:
        name = chr(code).lower()
    elif Qt.Key_0 <= code <= Qt.Key_9:
        name = chr(code)
    elif Qt.Key_F1 <= code <= Qt.Key_F35:
        name = f'F{code - Qt.Key_F1 + 1}'
    else:
        name = {Qt.Key_Space: 'space', Qt.Key_Print: 'Print', Qt.Key_Pause: 'Pause',
                Qt.Key_Home: 'Home', Qt.Key_End: 'End', Qt.Key_Insert: 'Insert',
                Qt.Key_Delete: 'Delete', Qt.Key_PageUp: 'Prior', Qt.Key_PageDown: 'Next',
                Qt.Key_Left: 'Left', Qt.Key_Right: 'Right', Qt.Key_Up: 'Up',
                Qt.Key_Down: 'Down'}.get(code)
    if not name:
        raise UserError(t('Tecla no compatible: usa una letra, número, F1–F35, espacio, Impr Pant o navegación.'))
    return sequence.toString(QKeySequence.PortableText), name, modifiers


class X11Grab:
    """All methods run on the Qt main thread. X errors are checked synchronously."""
    def __init__(self):
        self.display = None
        self.grabs = []
        self.down = False
        try:
            self.lib = C.CDLL('libX11.so.6')
        except OSError as e:
            raise UserError(t('Falta libX11.so.6 del sistema: ') + str(e)) from e
        signatures = {
            'XOpenDisplay': (C.c_void_p, [C.c_char_p]),
            'XCloseDisplay': (C.c_int, [C.c_void_p]),
            'XDefaultRootWindow': (C.c_ulong, [C.c_void_p]),
            'XConnectionNumber': (C.c_int, [C.c_void_p]),
            'XStringToKeysym': (C.c_ulong, [C.c_char_p]),
            'XKeysymToKeycode': (C.c_ubyte, [C.c_void_p, C.c_ulong]),
            'XGetModifierMapping': (C.POINTER(ModifierMap), [C.c_void_p]),
            'XFreeModifiermap': (C.c_int, [C.POINTER(ModifierMap)]),
            'XGrabKey': (C.c_int, [C.c_void_p, C.c_int, C.c_uint, C.c_ulong, C.c_int, C.c_int, C.c_int]),
            'XUngrabKey': (C.c_int, [C.c_void_p, C.c_int, C.c_uint, C.c_ulong]),
            'XSync': (C.c_int, [C.c_void_p, C.c_int]),
            'XPending': (C.c_int, [C.c_void_p]),
            'XNextEvent': (C.c_int, [C.c_void_p, C.POINTER(Event)]),
            'XPeekEvent': (C.c_int, [C.c_void_p, C.POINTER(Event)]),
            'XSetErrorHandler': (C.c_void_p, [C.c_void_p]),
        }
        for name, (restype, args) in signatures.items():
            function = getattr(self.lib, name)
            function.restype, function.argtypes = restype, args
        self.display = self.lib.XOpenDisplay(None)
        if not self.display:
            raise UserError(t('No se puede abrir el display X11. El atajo no está registrado.'))
        self.root = self.lib.XDefaultRootWindow(self.display)
        self.fd = self.lib.XConnectionNumber(self.display)

    def code(self, name):
        return self.lib.XKeysymToKeycode(self.display, self.lib.XStringToKeysym(name.encode('ascii')))

    def modifier_masks(self):
        mapping = self.lib.XGetModifierMapping(self.display)
        if not mapping:
            raise UserError(t('No se pudo leer el mapa de modificadores X11.'))
        try:
            data = mapping.contents
            def mask(names):
                keys = {self.code(name) for name in names} - {0}
                return sum(1 << slot for slot in range(8) if any(
                    data.modifiermap[slot * data.max_keypermod + offset] in keys
                    for offset in range(data.max_keypermod)))
            return {'ctrl': mask(['Control_L', 'Control_R']), 'alt': mask(['Alt_L', 'Alt_R']),
                    'shift': mask(['Shift_L', 'Shift_R']), 'meta': mask(['Super_L', 'Super_R']),
                    'locks': mask(['Caps_Lock', 'Num_Lock', 'Scroll_Lock'])}
        finally:
            self.lib.XFreeModifiermap(mapping)

    def register(self, name, modifiers):
        code = self.code(name)
        if not code:
            raise UserError(t('La tecla no tiene código en el mapa X11 actual.'))
        masks = self.modifier_masks()
        required = 0
        for qt, label in ((Qt.ControlModifier, 'ctrl'), (Qt.AltModifier, 'alt'),
                          (Qt.ShiftModifier, 'shift'), (Qt.MetaModifier, 'meta')):
            if modifiers & qt:
                if not masks[label]:
                    raise UserError(t('El mapa X11 no contiene el modificador ') + label)
                required |= masks[label]
        locks = masks['locks'] & ~required
        variants = [mask for mask in range(256) if mask & ~locks == 0]
        errors = []
        callback_type = C.CFUNCTYPE(C.c_int, C.c_void_p, C.POINTER(ErrorEvent))
        @callback_type
        def handler(display, error):
            errors.append(error.contents.error_code)
            return 0
        self.lib.XSync(self.display, False)
        previous = self.lib.XSetErrorHandler(C.cast(handler, C.c_void_p))
        try:
            for extra in variants:
                # Never AnyKey/AnyModifier; owner_events=False, both modes async.
                self.lib.XGrabKey(self.display, code, required | extra, self.root, False, 1, 1)
                self.grabs.append((code, required | extra))
            self.lib.XSync(self.display, False)
        finally:
            self.lib.XSetErrorHandler(previous)
        if errors:
            self.clear()
            if 10 in errors:  # BadAccess
                raise UserError(t('Conflicto X11: otra aplicación ya tiene esa combinación. No se ha sustituido su atajo.'))
            raise UserError(t('X11 rechazó el registro (códigos ') + ', '.join(map(str, errors)) + ').')
        self.down = False
        self.keycode = code

    def drain(self):
        triggered = False
        while self.lib.XPending(self.display):
            event = Event()
            self.lib.XNextEvent(self.display, C.byref(event))
            if event.type not in (2, 3) or event.key.keycode != self.keycode or event.key.send_event:
                continue
            if event.type == 2:
                if not self.down:
                    triggered = True
                self.down = True
            else:
                # Traditional X11 autorepeat emits Release+Press with identical timestamps.
                if self.lib.XPending(self.display):
                    following = Event()
                    self.lib.XPeekEvent(self.display, C.byref(following))
                    if following.type == 2 and following.key.keycode == event.key.keycode and following.key.time == event.key.time:
                        continue
                self.down = False
        return triggered

    def clear(self):
        for code, mask in self.grabs:
            self.lib.XUngrabKey(self.display, code, mask, self.root)
        self.grabs.clear()
        self.lib.XSync(self.display, False)
        self.down = False

    def close(self):
        if self.display:
            self.clear()
            self.lib.XCloseDisplay(self.display)
            self.display = None


class GlobalShortcut(QObject):
    activated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backend = None
        self.notifier = None
        self.active = ''

    def register(self, text):
        normalized, name, modifiers = combination(text)
        self.close()
        from .platform_support import kde_x11
        if (not kde_x11()
                or QGuiApplication.platformName() != 'xcb'):
            raise UserError(t('Atajo no registrado: esta integración requiere KDE/X11 y Qt xcb. Wayland y offscreen no están implementados.'))
        try:
            self.backend = X11Grab()
            self.backend.register(name, modifiers)
            self.notifier = QSocketNotifier(self.backend.fd, QSocketNotifier.Read, self)
            self.notifier.activated.connect(self.read)
            self.active = normalized
        except Exception:
            self.close()
            raise
        return normalized

    def read(self, *args):
        if self.backend and self.backend.drain():
            self.activated.emit()

    def close(self):
        if self.notifier:
            self.notifier.setEnabled(False)
            self.notifier.deleteLater()
            self.notifier = None
        if self.backend:
            self.backend.close()
            self.backend = None
        self.active = ''
