"""Explicit, pinned model provisioning. Never used by inference workers."""
from .i18n import t
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from .storage import UserError, paths


def catalogue():
    return json.loads(Path(__file__).with_name('model-catalog.json').read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare_model(progress=lambda text: None, *, spec=None, opener=urllib.request.urlopen):
    spec = spec or catalogue()
    target = paths()['data'] / 'models/manga-ocr-base'
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    # A private lock prevents two setup dialogs/processes writing partial files.
    import fcntl
    with (target / '.download.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise UserError(t('Ya hay una preparación de este modelo en curso.')) from e
        for item in spec['files']:
            name = item['name']
            if Path(name).name != name or name.startswith('.'):
                raise UserError(t('Nombre de recurso inválido en el catálogo.'))
            final, partial = target / name, target / (name + '.part')
            if final.is_symlink() or partial.is_symlink():
                raise UserError(t('El destino del modelo no puede ser un enlace simbólico.'))
            if final.is_file() and final.stat().st_size == item['bytes'] and digest(final) == item['sha256']:
                progress((f'{name}' + t(': verificado, se conserva')))
                continue
            offset = partial.stat().st_size if partial.exists() else 0
            if offset > item['bytes']:
                partial.unlink(); offset = 0
            if offset != item['bytes']:
                url = f"https://huggingface.co/{spec['id']}/resolve/{spec['revision']}/{name}"
                request = urllib.request.Request(url, headers={'Range': f'bytes={offset}-'} if offset else {})
                started = time.monotonic()
                try:
                    # No cookies, tokens or authenticated Hub configuration.
                    with opener(request, timeout=20) as response:
                        if not response.geturl().startswith('https://'):
                            raise UserError(t('El recurso se redirigió fuera de HTTPS.'))
                        status = response.status
                        if status == 206:
                            content_range = response.headers.get('Content-Range', '')
                            if not content_range.startswith(f'bytes {offset}-') or not content_range.endswith(f"/{item['bytes']}"):
                                raise UserError(t('Respuesta de reanudación incoherente.'))
                        elif status == 200:
                            offset = 0
                        else:
                            raise UserError((t('HTTP inesperado: ') + f'{status}'))
                        with partial.open('ab' if offset else 'wb') as stream:
                            while True:
                                if time.monotonic() - started > 900:
                                    raise UserError(t('Se agotó el tiempo total de descarga (15 min por archivo).'))
                                block = response.read(1024 * 1024)
                                if not block:
                                    break
                                offset += len(block)
                                if offset > item['bytes']:
                                    raise UserError(t('El recurso supera el tamaño del catálogo.'))
                                stream.write(block)
                                progress(f'{name}: {offset:,} / {item["bytes"]:,} bytes')
                except (OSError, ValueError) as e:
                    raise UserError((t('Descarga interrumpida de ') + f'{name}' + ': ' + f'{e}' + t('. Reintenta para recuperar el parcial; no se usará como modelo listo.'))) from e
            if not partial.exists() or partial.stat().st_size != item['bytes']:
                raise UserError((t('Descarga incompleta de ') + f'{name}' + t('; reintenta para reanudar.')))
            if digest(partial) != item['sha256']:
                partial.unlink()
                raise UserError((t('Integridad incorrecta de ') + f'{name}' + t('; parcial descartado. No se acredita el modelo.')))
            partial.replace(final)
        (target / 'verified-manifest.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2))
    return {'model': str(target), 'detail': t('Descarga verificada. Pendiente carga e inferencia del motor.')}


def prepare_phrase_runtime():
    """One installation per project, even when both popup actions request it."""
    import fcntl
    from .ocr import run
    project = Path(__file__).resolve().parent.parent
    with (project / '.phrase-install.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise UserError(t('Ya se están preparando los recursos de frase de Next.')) from error
        return run(['bash', str(project / 'tools/install.sh'), '--phrase'], 900)
