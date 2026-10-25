"""XDG state and a private dictionary database. Never writes to source archives."""
from .i18n import t
import json
import os
from pathlib import Path
import sqlite3
import zipfile


class UserError(Exception):
    pass


class Cancelled(UserError):
    pass


def paths():
    home = Path.home()
    def root(key, fallback):
        value = Path(os.environ.get(key, str(home / fallback)))
        return value if value.is_absolute() else home / fallback
    result = {
        'config': root('XDG_CONFIG_HOME', '.config') / 'naatik-next',
        'data': root('XDG_DATA_HOME', '.local/share') / 'naatik-next',
        'state': root('XDG_STATE_HOME', '.local/state') / 'naatik-next',
    }
    for p in result.values():
        p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return result


def load_settings():
    p = paths()['config'] / 'settings.json'
    try:
        obj = json.loads(p.read_text())
        if not isinstance(obj, dict):
            raise ValueError(t('Se esperaba un objeto JSON'))
        return obj
    except FileNotFoundError:
        return {}
    except (ValueError, OSError) as e:
        raise UserError((t('No se pueden leer las preferencias ') + f'{p}' + ': ' + f'{e}')) from e


def save_settings(data):
    import tempfile
    p = paths()['config'] / 'settings.json'
    fd, name = tempfile.mkstemp(prefix='.settings-', dir=p.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, p)
    finally:
        Path(name).unlink(missing_ok=True)


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else paths()['data'] / 'dictionaries.sqlite3'
        self.conn = sqlite3.connect(self.path, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        try:
            self._migrate()
        except Exception:
            self.conn.rollback()
            self.conn.close()
            raise

    def _migrate(self):
        version = self.conn.execute('PRAGMA user_version').fetchone()[0]
        if version > 2:
            raise UserError(t('La base usa un esquema más reciente que esta versión de Next.'))
        if version == 2:
            return
        self.conn.executescript('''BEGIN;
            CREATE TABLE IF NOT EXISTS dictionaries (
                id INTEGER PRIMARY KEY, digest TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL, revision TEXT NOT NULL,
                source_language TEXT, target_language TEXT,
                enabled INTEGER NOT NULL DEFAULT 1, priority INTEGER NOT NULL DEFAULT 0,
                count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(title, revision));
            CREATE TABLE IF NOT EXISTS terms (
                dictionary_id INTEGER NOT NULL REFERENCES dictionaries(id) ON DELETE CASCADE,
                expression TEXT NOT NULL, reading TEXT NOT NULL, meanings TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS kanji (
                dictionary_id INTEGER NOT NULL REFERENCES dictionaries(id) ON DELETE CASCADE,
                character TEXT NOT NULL, onyomi TEXT NOT NULL, kunyomi TEXT NOT NULL,
                tags TEXT NOT NULL, meanings TEXT NOT NULL, attributes TEXT NOT NULL, source_row TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pitches (
                dictionary_id INTEGER NOT NULL REFERENCES dictionaries(id) ON DELETE CASCADE,
                expression TEXT NOT NULL, reading TEXT NOT NULL, pitches TEXT NOT NULL, source_row TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS kanji_character ON kanji(character);
            CREATE INDEX IF NOT EXISTS pitches_expression_reading ON pitches(expression,reading);
            CREATE INDEX IF NOT EXISTS pitches_reading ON pitches(reading);
            CREATE INDEX IF NOT EXISTS terms_expression ON terms(expression);
            CREATE INDEX IF NOT EXISTS terms_reading ON terms(reading);
        ''')

        # Additive migration: old plain-text rows remain usable, never rebuilt.
        for table, column in [('terms', 'source_row'), ('dictionaries', 'metadata')]:
            if column not in {r[1] for r in self.conn.execute(f'PRAGMA table_info({table})')}:
                self.conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} TEXT')
        self.conn.execute('PRAGMA user_version=2')
        self.conn.commit()

    def close(self):
        self.conn.close()

    def list(self):
        return [dict(r) for r in self.conn.execute(
            'SELECT * FROM dictionaries ORDER BY priority DESC, title')]

    def update(self, ident, enabled, priority):
        with self.conn:
            self.conn.execute('UPDATE dictionaries SET enabled=?, priority=? WHERE id=?',
                              (int(enabled), int(priority), ident))

    def remove(self, ident):
        # The managed representation is SQLite rows. No original pathname is stored.
        with self.conn:
            self.conn.execute('DELETE FROM dictionaries WHERE id=?', (ident,))

    def lookup(self, term, *, exact=False):
        term = term if exact else term.strip()
        if not term:
            raise UserError(t('Escribe una palabra o lectura para consultar.'))
        results = []
        for table, expression, reading, where, args in [
                ('terms','t.expression','t.reading','t.expression=? OR t.reading=?',(term,term)),
                ('kanji','t.character',"''",'t.character=?',(term,)),
                ('pitches','t.expression','t.reading','t.expression=? OR t.reading=?',(term,term))]:
            rows = self.conn.execute(f'''SELECT t.*, d.title, d.revision, d.priority,
                    {expression} AS expression, {reading} AS reading
                    FROM {table} t JOIN dictionaries d ON d.id=t.dictionary_id
                    WHERE d.enabled=1 AND ({where}) ORDER BY d.priority DESC,d.title,t.rowid LIMIT 100''',args)
            for value in rows:
                row = dict(value)
                row['kind'] = {'terms':'term','kanji':'kanji','pitches':'pitch'}[table]
                if table == 'terms' and row.get('source_row'):
                    from .dictionary_archive import grammar
                    if grammar(json.loads(row['source_row'])):
                        row['kind'] = 'grammar'
                results.append(row)
        results.sort(key=lambda row: (-row['priority'],row['title']))
        results = results[:100]
        cache = {}
        for row in results:
            if row['kind'] not in ('term','grammar') or not row['reading']:
                continue
            pair = (row['expression'],row['reading'])
            if pair not in cache:
                cache[pair] = [dict(r) for r in self.conn.execute('''SELECT p.*, d.title, d.revision FROM pitches p
                    JOIN dictionaries d ON d.id=p.dictionary_id WHERE d.enabled=1 AND p.expression=? AND p.reading=?
                    ORDER BY d.priority DESC,d.title LIMIT 100''',pair)]
            row['accents'] = cache[pair]
        return results

    def inspect_zip(self, source, cancelled=lambda: False, progress=lambda text: None):
        return self._archive(source, False, cancelled, progress)

    def import_zip(self, source, cancelled=lambda: False, progress=lambda text: None, expected_digest=None):
        return self._archive(source, True, cancelled, progress, expected_digest)

    def _archive(self, source, importing, cancelled, progress, expected_digest=None):
        from .dictionary_archive import Archive
        archive = Archive(source, cancelled)
        try:
            with archive:
                if expected_digest and archive.digest != expected_digest:
                    raise UserError(t('El ZIP cambió después de la revisión. Selecciónalo de nuevo.'))
                duplicate = self.conn.execute('SELECT title FROM dictionaries WHERE digest=?', (archive.digest,)).fetchone()
                same = self.conn.execute('SELECT title FROM dictionaries WHERE title=? AND revision=?',
                                         (archive.index['title'], archive.index['revision'])).fetchone()
                if importing and duplicate:
                    raise UserError(t('Este archivo ya está importado (SHA-256 idéntico).'))
                if importing and same:
                    raise UserError(t('Diccionario duplicado: ya existe el mismo nombre y revisión.'))
                with self.conn:
                    if importing:
                        index = archive.index
                        ident = self.conn.execute('''INSERT INTO dictionaries
                            (digest,title,revision,source_language,target_language) VALUES (?,?,?,?,?)''',
                            (archive.digest,index['title'],index['revision'],index.get('sourceLanguage'),index.get('targetLanguage'))).lastrowid
                    for kind, row in archive.rows(progress):
                        if not importing:
                            continue
                        source_row = json.dumps(row, ensure_ascii=False)
                        if kind in ('term', 'grammar'):
                            self.conn.execute('INSERT INTO terms (dictionary_id,expression,reading,meanings,source_row) VALUES (?,?,?,?,?)',
                                              (ident,row[0],row[1],json.dumps(row[5],ensure_ascii=False),source_row))
                        elif kind == 'kanji':
                            self.conn.execute('INSERT INTO kanji (dictionary_id,character,onyomi,kunyomi,tags,meanings,attributes,source_row) VALUES (?,?,?,?,?,?,?,?)',
                                (ident,*row[:4],json.dumps(row[4],ensure_ascii=False),json.dumps(row[5],ensure_ascii=False),source_row))
                        else:
                            self.conn.execute('INSERT INTO pitches (dictionary_id,expression,reading,pitches,source_row) VALUES (?,?,?,?,?)',
                                (ident,row[0],row[2]['reading'],json.dumps(row[2]['pitches'],ensure_ascii=False),source_row))
                    archive.check()
                    result = archive.summary()
                    result['duplicate'] = 'SHA-256 idéntico' if duplicate else t('mismo título y revisión') if same else ''
                    if importing:
                        metadata = {'index': archive.index, 'tags': archive.tags, 'counts': result['counts'],
                                    'warnings': result['warnings'], 'banks': result['banks']}
                        self.conn.execute('UPDATE dictionaries SET count=?, metadata=? WHERE id=?',
                                          (result['count'],json.dumps(metadata,ensure_ascii=False),ident))
                    return result
        except UserError as e:
            index = getattr(archive,'index',{})
            if isinstance(index,dict):
                e.preview = {key:index[key] for key in ('title','revision') if isinstance(index.get(key),str)}
                e.preview['types'] = list(archive.counts) or list(dict.fromkeys(kind for _,kind in archive.banks if kind != 'tag'))
            raise
        except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError, RecursionError) as e:
            raise UserError((t('ZIP o JSON inválido: ') + f'{e}')) from e
        except sqlite3.IntegrityError as e:
            raise UserError(t('Diccionario duplicado o datos con integridad inválida.')) from e
