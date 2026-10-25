"""MangaOCR runtime configuration. Inspect files only in the GUI environment."""
from .i18n import t
from pathlib import Path


def defaults():
    # No discovery of another project's environments or global model caches.
    from .storage import paths
    project = Path(__file__).resolve().parent.parent
    return {'manga_python': str(project / '.venv-mangaocr/bin/python'),
            'manga_model': str(paths()['data'] / 'models/manga-ocr-base')}


def complete_model(path):
    path = Path(path)
    return all((path / n).is_file() for n in ['config.json', 'preprocessor_config.json',
        'tokenizer_config.json', 'vocab.txt']) and any((path / n).is_file() for n in ['model.safetensors', 'pytorch_model.bin'])


def descriptor(config=None):
    config = config or defaults()
    missing = []
    if not Path(config['manga_python']).is_file():
        missing.append(t('intérprete Python MangaOCR'))
    if not complete_model(config['manga_model']):
        missing.append(t('snapshot local completo de manga-ocr-base'))
    return dict(id='mangaocr', name='MangaOCR', languages=[], fixed_language='ja',
                status='recursos faltantes' if missing else 'detectado',
                detail=(t('Falta: ') + ', '.join(missing) if missing else t('Recursos encontrados; pendiente de carga y prueba real.'))
                + ('\nPython: ' + f"{config['manga_python']}" + t('\nModelo: ') + f"{config['manga_model']}"))
