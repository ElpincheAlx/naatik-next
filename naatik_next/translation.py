"""Offline Argos package adapter, CTranslate2 inference, no network or SBD downloads.

Uses Argos package discovery/tokenizers. Short lines are translation units. Deliberately
avoids argostranslate.translate, whose SBD backends may download resources on import.
"""
from .i18n import t
from collections import deque
from .storage import UserError


class Argos:
    def __init__(self):
        self.packages = {}
        self.models = {}
        self.errors = []

    def discover(self):
        try:
            package, directory = package_api()
            installed = package.get_installed_packages(path=[directory])
        except Exception as e:
            raise UserError((t('No se puede inspeccionar Argos local: ') + f'{e}')) from e
        self.packages.clear()
        self.models.clear()
        self.errors.clear()
        for pkg in installed:
            if getattr(pkg, 'type', 'translate') != 'translate':
                continue
            key = (pkg.from_code, pkg.to_code)
            try:
                self.packages[key] = pkg
                # Loading model + actual inference, not merely metadata/files.
                self._translate_edge('日本語です。' if key[0] == 'ja' else 'Hello.', key)
            except Exception as e:
                self.packages.pop(key, None)
                self.errors.append((f'{key[0]}' + '→' + f'{key[1]}' + t(' no listo: ') + f'{e}'))
        routes = []
        origins = sorted({a for a, b in self.packages})
        for source in origins:
            queue = deque([[source]])
            visited = {source}
            while queue:
                route = queue.popleft()
                for a, b in sorted(self.packages):
                    if a == route[-1] and b not in visited:
                        visited.add(b)
                        next_route = route + [b]
                        queue.append(next_route)
                        routes.append(next_route)
        return {'routes': routes, 'errors': self.errors,
                'detail': t('Modelos Argos locales probados mediante inferencia. Traducción por líneas (máximo 1 000 caracteres por línea).')
                if routes else t('Faltan modelos Argos utilizables. Instala explícitamente paquetes .argosmodel para el origen y destino; pulsa Preparar traducción para abrir la sección Traducción.')}

    def _translate_edge(self, text, key):
        import ctranslate2
        pkg = self.packages[key]
        if key not in self.models:
            self.models[key] = ctranslate2.Translator(str(pkg.package_path / 'model'), device='cpu', intra_threads=2, inter_threads=1)
        tokens = pkg.tokenizer.encode(text)
        if len(tokens) > 512:
            raise UserError(t('La línea supera 512 tokens; divídela antes de traducir.'))
        prefix = getattr(pkg, 'target_prefix', '')
        result = self.models[key].translate_batch([tokens], target_prefix=[[prefix]] if prefix else None,
                    beam_size=4, replace_unknowns=True, max_decoding_length=1024, length_penalty=0.2)
        value = pkg.tokenizer.decode(result[0].hypotheses[0])
        if prefix and value.startswith(prefix):
            value = value[len(prefix):]
        if not value.strip():
            raise UserError(t('El modelo devolvió una traducción vacía.'))
        return value.strip()

    def translate(self, text, route):
        if not text.strip():
            raise UserError(t('No hay texto para traducir.'))
        if len(text) > 10000 or any(len(line) > 1000 for line in text.splitlines()):
            raise UserError(t('Máximo 10 000 caracteres y 1 000 por línea. Divide el texto.'))
        if len(route) < 2 or any((a, b) not in self.packages for a, b in zip(route, route[1:])):
            raise UserError(t('La ruta elegida ya no está disponible. Abre Preparar traducción para reparar la ruta.'))
        for a, b in zip(route, route[1:]):
            text = '\n'.join(self._translate_edge(line, (a, b)) if line.strip() else '' for line in text.splitlines())
        return {'text': text, 'route': route}



def package_api():
    """Constrain package discovery/config to Next, including first Argos import."""
    import os
    from pathlib import Path
    from .storage import paths
    roots = paths()
    directory = roots['data'] / 'argos/packages'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home()/'.cache')))
    if not cache.is_absolute(): cache = Path.home()/'.cache'
    updates = dict(XDG_CONFIG_HOME=str(roots['config']), XDG_DATA_HOME=str(roots['data']),
                   XDG_CACHE_HOME=str(cache/'naatik-next'), ARGOS_PACKAGES_DIR=str(directory),
                   ARGOS_TRANSLATE_PACKAGE_DIR=str(directory))
    saved = {key:os.environ.get(key) for key in (*updates, 'SNAP')}
    try:
        os.environ.update(updates); os.environ.pop('SNAP',None)
        from argostranslate import package
    finally:
        for key, value in saved.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key] = value
    # Discovery explicitly receives only this directory; no SNAP/system extras.
    return package, directory


def install_package(path, expected=None):
    """Validated local import; avoid Argos install's translate/SBD import side effects."""
    from pathlib import Path
    import hashlib
    import json
    import re
    import tempfile
    import zipfile
    import stat
    from .storage import paths
    path = Path(path)
    if path.suffix != '.argosmodel' or path.stat().st_size > 1024**3:
        raise UserError(t('Selecciona un paquete .argosmodel local de hasta 1 GiB.'))
    parent = paths()['data']/'argos'
    directory = parent/'packages'
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    with path.open('rb') as stream: digest = hashlib.file_digest(stream,'sha256').hexdigest()
    target = directory/('model-'+digest)
    with zipfile.ZipFile(path) as archive:
        total, roots = 0, set()
        for info in archive.infolist():
            parts = info.filename.replace('\\', '/').split('/')
            total += info.file_size
            if (not parts[0] or '..' in parts or ':' in parts[0] or
                    stat.S_ISLNK(info.external_attr >> 16) or total > 2*1024**3):
                raise UserError(t('El paquete contiene rutas o tamaños no admitidos.'))
            roots.add(parts[0])
        if len(roots) != 1: raise UserError(t('Se requiere un paquete con un solo directorio raíz.'))
        root = next(iter(roots))
        metadata_name = root+'/metadata.json'
        if archive.getinfo(metadata_name).file_size > 65536: raise UserError(t('Metadatos demasiado grandes.'))
        metadata = json.loads(archive.read(metadata_name))
        if metadata.get('type','translate') != 'translate' or not all(
                isinstance(metadata.get(key),str) and re.fullmatch('[A-Za-z0-9_-]{1,20}',metadata[key])
                for key in ('from_code','to_code')):
            raise UserError(t('El paquete no declara una traducción con idiomas válidos.'))
        if expected and tuple(metadata.get(key) for key in ('from_code','to_code')) != tuple(expected):
            raise UserError(t('Los idiomas del paquete no coinciden con la propuesta confirmada.'))
        if target.is_dir(): return {'detail':t('Este paquete ya está importado en Next.'), 'model':str(target)}
        with tempfile.TemporaryDirectory(prefix='.import-',dir=parent) as tmp:
            # No symlinks/path traversal; extract to staging outside the discovered directory.
            archive.extractall(tmp)
            staged = Path(tmp)/root
            if not (staged/'model').is_dir() or not any((staged/name).is_file() for name in ('sentencepiece.model','bpe.model')):
                raise UserError(t('Faltan modelo CTranslate2 o tokenizador local.'))
            # Import provenance contains no source path or text; does not assert a model license.
            (staged/'naatik-import.json').write_text(json.dumps(dict(sha256=digest,license=t('No verificada; paquete aportado por el usuario'))))
            try: staged.rename(target)
            except OSError:
                if not target.is_dir(): raise
    return {'detail':t('Modelo importado en Next. Revisa las rutas para comprobar inferencia local.'), 'model':str(target)}
