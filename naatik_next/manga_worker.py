"""Next-owned persistent MangaOCR process, executed by an explicit local Python.

No HTTP. All heavy libraries and model instances stay out of the Qt process.
"""
from .i18n import t
import os
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                  TOKENIZERS_PARALLELISM='false', PYTHONDONTWRITEBYTECODE='1')
import contextlib
import importlib.metadata
import json
from pathlib import Path
import signal
import socket
import sys
from .manga import complete_model
from .storage import UserError
from . import timings


def blocked(*args, **kwargs):
    raise UserError(t('La red está deshabilitada en el worker MangaOCR de Next.'))


socket.getaddrinfo = blocked
socket.socket.connect = blocked
socket.socket.connect_ex = blocked


_stopping = False


def stop(signum, frame):
    global _stopping
    if _stopping:
        return
    _stopping = True
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise SystemExit(0)


def emit(key, value):
    print(json.dumps({key: value}, ensure_ascii=False), flush=True)


class Engine:
    def __init__(self):
        self.model = None
        self.path = None
        self.ready = None
        self.stamp = None

    @staticmethod
    def model_stamp(path):
        files = [Path(path) / name for name in ('config.json', 'preprocessor_config.json',
                 'tokenizer_config.json', 'vocab.txt', 'model.safetensors', 'pytorch_model.bin')]
        return tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.is_file())

    def detect(self, path, *, probe=True):
        stamp = self.model_stamp(path)
        if not probe and self.model is not None and self.path == path and self.stamp == stamp and self.ready is not None:
            return self.ready
        self.ready = None
        result = dict(id='mangaocr', name='MangaOCR', languages=[], fixed_language='ja', status='detectado')
        if not complete_model(path):
            return dict(result, status='recursos faltantes', detail=t('Falta un snapshot MangaOCR local completo; no se descarga automáticamente.'))
        try:
            config = json.loads((Path(path) / 'config.json').read_text())
            if config.get('model_type') != 'vision-encoder-decoder' or 'auto_map' in json.dumps(config):
                return dict(result, status='incompatible', detail=t('El modelo no se identifica como vision-encoder-decoder local sin código remoto.'))
            version = importlib.metadata.version('manga-ocr')
            import torch
            torch.set_num_threads(2)
            from manga_ocr import MangaOcr
            if self.model is None or self.path != path or self.stamp != stamp:
                self.model = None
                self.model = MangaOcr(path, force_cpu=True)
                self.path = path
                self.stamp = stamp
            text = None
            if probe:
                # Explicit diagnostics retain the known-sample test; capture needs no extra inference.
                sample = Path(__file__).resolve().parent.parent / 'examples/nihon.png'
                text = self.model(sample)
                if text != '日本':
                    self.model = None
                    return dict(result, status='error', detail=t('Prueba OCR real no superada.'))
            self.ready = dict(result, status='listo', detail=('MangaOCR ' + f'{version}' + t('; CPU; modelo local cargado.'))
                              + (' Prueba real correcta.' if probe else t(' Sin inferencia de prueba redundante.')))
            if probe:
                self.ready['probe_text'] = text
            return self.ready
        except importlib.metadata.PackageNotFoundError:
            return dict(result, status='recursos faltantes', detail=t('El Python seleccionado no contiene manga-ocr.'))
        except Exception as e:
            self.model = None
            return dict(result, status='error', detail=(t('No se pudo cargar/probar MangaOCR: ') + f'{type(e).__name__}' + ': ' + f'{e}'))

    def recognize(self, request):
        if self.model is None or self.path != request['model'] or self.ready is None:
            raise UserError(t('MangaOCR no está listo en este worker. Vuelve a detectar; no se cambiará de motor.'))
        if request.get('engine') != 'mangaocr' or request.get('language') != 'ja':
            raise UserError(t('MangaOCR solo admite japonés fijo, sin selector de dirección.'))
        from PIL import Image
        with Image.open(request['image']) as image:
            if image.width * image.height > 40_000_000:
                raise UserError(t('La imagen supera los 40 megapíxeles.'))
            image.load()
            text = self.model(image)
        if not text.strip():
            raise UserError(t('MangaOCR no devolvió texto.'))
        return text


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    engine = Engine()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            from .i18n import set_language
            import os
            code = request.get('ui_language', os.environ.get('NAATIK_NEXT_UI_LANGUAGE', 'es'))
            set_language(code)
            os.environ['NAATIK_NEXT_UI_LANGUAGE'] = code
            if request.get('timings') is True:
                timings.enable()
            with contextlib.redirect_stdout(sys.stderr):
                if request['action'] == 'detect':
                    result = engine.detect(request['model'])
                elif request['action'] == 'prepare':
                    timings.event('engine_prepare_begin', request.get('trace'))
                    result = engine.detect(request['model'], probe=False)
                    result = dict(result, preparation=request.get('preparation'))
                    timings.event('engine_ready', request.get('trace'))
                elif request['action'] == 'ocr':
                    timings.event('inference_begin', request.get('trace'))
                    result = engine.recognize(request)
                    timings.event('inference_end', request.get('trace'))
                else:
                    raise UserError(t('Acción MangaOCR no admitida.'))
            if request['action'] == 'ocr' and 'generation' in request:
                result = {'generation': request['generation'], 'text': result}
            emit('result', result)
        except Exception as e:
            emit('error', f'MangaOCR: {type(e).__name__}: {e}')


if __name__ == '__main__':
    main()
