"""Independent adapters. Presence is evidence, never a readiness assertion."""
from .i18n import t
import importlib.util
from functools import lru_cache
from . import timings
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from .storage import UserError, Cancelled

_child = None
_stopping = False


def stop(signum, frame):
    global _stopping
    if _stopping:
        return
    _stopping = True
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    # Unwind finally blocks once, including subprocess reaping and observer cleanup.
    # BaseException cannot be swallowed by an OCR adapter's error-to-status handler.
    raise SystemExit(0)


def run(args, timeout=30, env=None):
    global _child
    # Supervised workers are session leaders. Keep their tools in the same group
    # so the GUI can terminate the whole owned family even if the worker is stuck.
    supervised = os.environ.get('NAATIK_SUPERVISED') == '1' and os.getpid() == os.getpgrp()
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                         start_new_session=not supervised)
    _child = p
    def terminate(signum):
        try:
            if supervised:
                p.kill() if signum == signal.SIGKILL else p.terminate()
            else:
                os.killpg(p.pid, signum)
        except ProcessLookupError:
            pass
    try:
        out, err = p.communicate(timeout=timeout)
        if p.returncode:
            raise UserError((f'{Path(args[0]).name}' + t(' falló (') + f'{p.returncode}' + '): ' + f"{err.decode(errors='replace')[-1500:]}"))
        return out.decode(errors='replace')
    except subprocess.TimeoutExpired as e:
        raise UserError((f'{Path(args[0]).name}' + t(': se agotó el tiempo de espera (') + f'{timeout}' + 's).')) from e
    finally:
        if p.poll() is None:
            terminate(signal.SIGTERM)
            try:
                p.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                terminate(signal.SIGKILL)
                p.communicate()
        if _child is p:
            _child = None


class Tesseract:
    key = 'tesseract'

    def detect(self, *, probe=True):
        executable = shutil.which('tesseract')
        result = dict(id=self.key, name='Tesseract', status='detectado', detail=executable or '', languages=[])
        if not executable:
            return dict(result, status='recursos faltantes', detail=t('Instala tesseract y los datos de idioma con el gestor de paquetes de Fedora.'))
        try:
            version = run([executable, '--version'], 10)
            if not version.lower().startswith('tesseract '):
                return dict(result, status='incompatible', detail=t('El comando no se identifica como Tesseract.'))
            langs = [x.strip() for x in run([executable, '--list-langs'], 10).splitlines()[1:] if x.strip() and x.strip() != 'osd']
            result['languages'] = langs
            if not langs:
                return dict(result, status='recursos faltantes', detail=t('No hay datos de idioma OCR utilizables.'))
            if not probe:
                return dict(result, status='listo', detail=(f'{version.splitlines()[0]}' + t('; idiomas comprobados; sin inferencia de prueba.')))
            from PIL import Image, ImageDraw, ImageFont
            with tempfile.TemporaryDirectory(prefix='naatik-ocr-probe-') as tmp:
                path = Path(tmp) / 'probe.png'
                image = Image.new('RGB', (650, 120), 'white')
                font = ImageFont.load_default(size=52)
                ImageDraw.Draw(image).text((20, 20), 'TEST 123', fill='black', font=font)
                image.save(path)
                lang = 'eng' if 'eng' in langs else langs[0]
                text = self.recognize(str(path), lang)
                if not text.strip() or ('eng' in langs and 'TEST' not in text.upper()):
                    return dict(result, status='error', detail=t('La prueba real no devolvió el texto esperado.'))
            return dict(result, status='listo', detail=(f'{version.splitlines()[0]}' + t('; prueba OCR real correcta con ') + f'{lang}' + '.'))
        except (UserError, OSError) as e:
            return dict(result, status='error', detail=str(e))

    def recognize(self, image, language):
        if not language or not all(c.isalnum() or c in '_+' for c in language):
            raise UserError(t('Selecciona un idioma OCR válido.'))
        executable = shutil.which('tesseract')
        if not executable:
            raise UserError(t('Tesseract ya no está disponible. Vuelve a detectar.'))
        return run([executable, image, 'stdout', '-l', language, '--psm', '6'], 90).strip()


class UnsupportedPythonOCR:
    def __init__(self, key, module, label):
        self.key, self.module, self.label = key, module, label

    def detect(self):
        evidence = []
        if importlib.util.find_spec(self.module):
            evidence.append('paquete presente en este entorno')
        return dict(id=self.key, name=self.label, status='incompatible', languages=[],
                    detail=(t('Detectado: ') + '; '.join(evidence) + '. ' if evidence else t('No se encontró evidencia local. '))
                    + t('Adaptador de inferencia todavía no implementado; no se acredita disponibilidad ni se contactan servicios antiguos.'))


def detect():
    from .manga import descriptor
    return [Tesseract().detect(), descriptor(),
            UnsupportedPythonOCR('paddleocr', 'paddleocr', 'PaddleOCR').detect()]


@lru_cache(maxsize=4)
def spectacle_capability(executable, modified, size):
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    version = run([executable, '--version'], 10, env)
    help_text = run([executable, '--help'], 10, env)
    if not version.startswith('spectacle 6.') or not all(x in help_text for x in ['--region', '--background', '--output', '--new-instance', '--release-capture']):
        raise UserError(t('Versión de Spectacle no compatible con el adaptador KDE 6.'))


def capture(trace=None):
    from .platform_support import kde_x11
    if not kde_x11():
        raise UserError(t('Esta entrega integra Spectacle en KDE/X11. Para esta sesión usa Abrir imagen; captura Wayland pendiente de validación.'))
    executable = shutil.which('spectacle')
    if not executable:
        raise UserError(t('No se encontró Spectacle. Puedes abrir una imagen existente.'))
    # Cached only in the resident capture worker, invalidated when the executable changes.
    stamp = Path(executable).stat()
    spectacle_capability(executable, stamp.st_mtime_ns, stamp.st_size)
    with tempfile.TemporaryDirectory(prefix='naatik-capture-') as tmp:
        path = Path(tmp) / 'region.png'
        timings.event('selector_ready', trace)
        timings.event('selection_begin', trace)
        from .selection_timing import DragTimer
        with DragTimer(trace):
            run([executable, '--new-instance', '--region', '--release-capture', '--background', '--nonotify', '--output', str(path)], 120)
        timings.event('selection_end', trace)
        if not path.is_file() or not path.stat().st_size:
            raise Cancelled(t('Selección cancelada o Spectacle no produjo una imagen.'))
        from PIL import Image
        with Image.open(path) as im:
            if im.width <= 0 or im.height <= 0:
                raise Cancelled(t('Selección vacía.'))
            if im.width * im.height > 40_000_000:
                raise UserError(t('La captura supera los 40 megapíxeles.'))
            import base64
            return base64.b64encode(path.read_bytes()).decode('ascii')
