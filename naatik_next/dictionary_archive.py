"""Bounded, read-only Yomitan v3 archive inspection shared by preview/import."""
from .i18n import t
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile
from .storage import UserError, Cancelled

BANK = re.compile(r'(term|kanji|term_meta|kanji_meta|tag)_bank_([1-9][0-9]*)\.json')


def grammar(row):
    # DOJG is a normal term bank, not a new Yomitan bank type or sentence parser.
    return any(tag.startswith('DOJG') for tag in row[7].split()) and any(
        isinstance(m, str) and m.startswith('文法項目') for m in row[5])


def number(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def validate_term(row):
    if (not isinstance(row, list) or len(row) != 8 or not isinstance(row[0], str) or not row[0]
            or not isinstance(row[1], str) or not (row[2] is None or isinstance(row[2], str))
            or not isinstance(row[3], str) or not number(row[4])
            or not isinstance(row[5], list) or not row[5] or type(row[6]) is not int or not isinstance(row[7], str)):
        raise UserError(t('entrada inválida: se requieren ocho campos de términos v3.'))
    from .dictionary_content import validate_meanings
    validate_meanings(row[5])


def validate_kanji(row):
    if (not isinstance(row, list) or len(row) != 6
            or not all(isinstance(x, str) for x in row[:4]) or not row[0]
            or not isinstance(row[4], list) or not all(isinstance(x, str) for x in row[4])
            or not isinstance(row[5], dict) or not all(isinstance(v, str) for v in row[5].values())):
        raise UserError(t('entrada kanji inválida: carácter, on, kun, tags, significados y atributos de texto.'))


def validate_pitch(data):
    if (not isinstance(data, dict) or set(data) != {'reading', 'pitches'}
            or not isinstance(data['reading'], str) or not data['reading']
            or not isinstance(data['pitches'], list) or len(data['pitches']) > 20000):
        raise UserError(t('Metadatos pitch inválidos: reading y pitches requeridos.'))
    for pitch in data['pitches']:
        if not isinstance(pitch, dict) or 'position' not in pitch or set(pitch) - {'position', 'tags', 'nasal', 'devoice'}:
            raise UserError(t('Patrón pitch inválido o atributos no compatibles.'))
        pos = pitch['position']
        if not (type(pos) is int and pos >= 0 or isinstance(pos, str) and re.fullmatch('[HL]+', pos)):
            raise UserError(t('Posición pitch inválida: entero no negativo o patrón H/L.'))
        if 'tags' in pitch and (not isinstance(pitch['tags'], list) or not all(isinstance(t, str) for t in pitch['tags'])):
            raise UserError(t('Tags pitch inválidos.'))
        for key in ('nasal', 'devoice'):
            if key in pitch:
                positions = pitch[key] if isinstance(pitch[key], list) else [pitch[key]]
                if not all(type(p) is int and p >= 0 for p in positions):
                    raise UserError((f'{key}' + t(': posiciones inválidas.')))


class Archive:
    def __init__(self, source, cancelled=lambda: False):
        self.source = Path(source)
        self.cancelled = cancelled
        self.snapshot = None
        self.zip = None
        self.counts = {}
        self.unsupported = {}
        self.banks = []
        self.resources = []
        self.tags = []
        self.digest = ''

    def check(self):
        if self.cancelled():
            raise Cancelled(t('Importación/inspección cancelada; no se guardaron entradas parciales.'))

    def __enter__(self):
        try:
            if self.source.suffix.lower() != '.zip':
                raise UserError('Solo se admite ZIP Yomitan v3.')
            self.snapshot = tempfile.TemporaryFile()
            h = hashlib.sha256()
            total = 0
            with self.source.open('rb') as source:
                while chunk := source.read(1024 * 1024):
                    self.check()
                    total += len(chunk)
                    if total > 512 * 1024 * 1024:
                        raise UserError(t('El ZIP supera el límite de 512 MiB.'))
                    h.update(chunk)
                    self.snapshot.write(chunk)
            self.digest = h.hexdigest()
            self.snapshot.seek(0)
            self.zip = zipfile.ZipFile(self.snapshot)
            self.header()
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        if self.zip:
            self.zip.close()
        if self.snapshot:
            self.snapshot.close()

    def read(self, name):
        self.check()
        return json.loads(self.zip.read(name))

    def header(self):
        infos = self.zip.infolist()
        if len(infos) > 10000:
            raise UserError(t('Demasiados archivos en el ZIP (máximo 10 000).'))
        names, size = set(), 0
        for info in infos:
            self.check()
            name = info.filename
            path = PurePosixPath(name)
            mode = info.external_attr >> 16
            if (name in names or '\\' in name or path.is_absolute() or '..' in path.parts
                    or ':' in name or '\x00' in name or stat.S_ISLNK(mode)):
                raise UserError(f'Ruta peligrosa o duplicada dentro del ZIP: {name!r}')
            names.add(name)
            if info.flag_bits & 1:
                raise UserError(t('No se admiten ZIP cifrados.'))
            size += info.file_size
            if info.file_size > 32*1024*1024 or size > 512*1024*1024 or info.file_size/max(1, info.compress_size) > 300:
                raise UserError(t('El ZIP supera los límites: 32 MiB/archivo, 512 MiB total o relación 300:1.'))
            if name == 'index.json':
                continue
            match = BANK.fullmatch(name)
            if match:
                self.banks.append((name, match[1]))
            elif info.is_dir():
                continue
            elif path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.mp3', '.ogg', '.wav', '.txt', '.md'}:
                self.resources.append(name)
            else:
                raise UserError((t('Tipo todavía no compatible: ') + f'{name}' + t('. No se ejecuta ni se extrae.')))
        if 'index.json' not in names or not any(kind != 'tag' for _, kind in self.banks):
            raise UserError(t('Faltan index.json o bancos de datos v3 en la raíz del ZIP.'))
        self.index = self.read('index.json')
        index = self.index
        if (not isinstance(index, dict) or type(index.get('format')) is not int or index['format'] != 3
                or not isinstance(index.get('title'), str) or not index['title'].strip()
                or not isinstance(index.get('revision'), str) or not index['revision'].strip()):
            raise UserError(t('index.json requiere format: 3, title y revision no vacíos.'))
        for key in ('sourceLanguage', 'targetLanguage'):
            if key in index and not isinstance(index[key], str):
                raise UserError((f'{key}' + t(' debe ser texto.')))
        for name, kind in self.banks:
            if kind == 'tag':
                tags = self.read(name)
                if not isinstance(tags, list) or any(not isinstance(t, list) or len(t) != 5
                        or not isinstance(t[0], str) or not isinstance(t[1], str) or not number(t[2])
                        or not isinstance(t[3], str) or not number(t[4]) for t in tags):
                    raise UserError((t('Tags inválidos: ') + f'{name}'))
                self.tags.extend(tags)

    def rows(self, progress=lambda text: None):
        self.counts = {}
        self.unsupported = {}
        count = 0
        for name, kind in sorted(self.banks):
            if kind == 'tag':
                continue
            rows = self.read(name)
            if not isinstance(rows, list):
                raise UserError((f'{name}' + t(' debe contener una lista.')))
            for row in rows:
                self.check()
                count += 1
                if count > 2_000_000:
                    raise UserError(t('Se supera el máximo de 2 000 000 entradas.'))
                if kind != 'term' and len(json.dumps(row,ensure_ascii=False)) > 2_000_000:
                    raise UserError(t('Entrada superior a 2 millones de caracteres.'))
                if kind == 'term':
                    validate_term(row)
                    output = 'grammar' if grammar(row) else 'term'
                elif kind == 'kanji':
                    validate_kanji(row)
                    output = 'kanji'
                else:
                    if (not isinstance(row, list) or len(row) != 3 or not isinstance(row[0], str)
                            or not isinstance(row[1], str)):
                        raise UserError((f'{name}' + t(': metadato inválido; se requieren tres campos.')))
                    if kind == 'term_meta' and row[1] == 'pitch':
                        validate_pitch(row[2])
                        output = 'pitch'
                    else:
                        if row[1] not in ({'freq','ipa'} if kind == 'term_meta' else {'freq'}):
                            raise UserError((f'{name}' + t(': modo de metadatos desconocido ') + f'{row[1]!r}' + '.'))
                        label = kind + ':' + row[1]
                        self.unsupported[label] = self.unsupported.get(label, 0) + 1
                        continue
                self.counts[output] = self.counts.get(output, 0) + 1
                yield output, row
                if count % 1000 == 0:
                    progress(f'{self.index["title"]}: {count:,} entradas verificadas…')
            progress(f'{name}: {count:,} entradas verificadas')
        if not sum(self.counts.values()):
            raise UserError(t('El diccionario no contiene entradas compatibles (términos, kanji o pitch).'))

    def summary(self):
        warnings = [(t('No importado: ') + f'{kind}' + ' (' + f'{count}' + ' registros)') for kind, count in self.unsupported.items()]
        warnings += [t('Recurso no importado ni renderizado: ') + name for name in self.resources]
        return {'path': str(self.source), 'title': self.index['title'], 'revision': self.index['revision'],
                'digest': self.digest, 'counts': dict(self.counts), 'count': sum(self.counts.values()),
                'types': list(self.counts), 'warnings': warnings,
                'banks': [{'name': name, 'type': kind} for name, kind in self.banks]}
