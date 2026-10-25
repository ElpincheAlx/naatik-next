"""Private loopback AnkiConnect client. No implicit writes or HTTP retries."""
from .i18n import t
import hashlib
import html
import http.client
import json
import os
import re
import tempfile
import uuid
from urllib.parse import urlsplit
from .storage import paths

LIMIT = 2 * 1024 * 1024


class AnkiError(Exception):
    pass


def digest(note):
    value = {k: note[k] for k in ('deckName', 'modelName', 'fields')}
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def validate(note, fields):
    if list(note['fields']) != fields or not fields:
        raise AnkiError(t('Los campos cambiaron; vuelve a configurar el destino.'))
    if any(not isinstance(v, str) or len(v) > 100000 for v in note['fields'].values()):
        raise AnkiError('Cada campo admite hasta 100 000 caracteres.')
    if not html.unescape(re.sub('<[^>]*>', '', note['fields'][fields[0]])).strip():
        raise AnkiError(t('El primer campo debe contener texto.'))
    if any('{{c' in v for v in note['fields'].values()):
        raise AnkiError(t('Los tipos cloze requieren validación manual; no están habilitados en esta entrega.'))


class Client:
    def __init__(self, endpoint='http://127.0.0.1:8765', key='', timeout=8):
        url = urlsplit(endpoint)
        if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', '::1', 'localhost')
                or url.username or url.password or url.path not in ('', '/') or url.query or url.fragment):
            raise AnkiError(t('Usa una dirección HTTP local de AnkiConnect.'))
        self.host, self.port = url.hostname, url.port or 8765
        self.key, self.timeout = key, min(30, max(1, timeout))

    def call(self, action, **params):
        body = dict(action=action, version=6, params=params)
        if self.key: body['key'] = self.key
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            connection.request('POST', '/', json.dumps(body).encode(), {'Content-Type': 'application/json'})
            response = connection.getresponse()
            data = response.read(LIMIT + 1)
            if response.status != 200 or len(data) > LIMIT:
                raise AnkiError('Respuesta HTTP incompatible o demasiado grande.')
            result = json.loads(data)
            if not isinstance(result, dict) or set(result) != {'result', 'error'}:
                raise AnkiError(t('El servicio no devuelve una respuesta AnkiConnect válida.'))
            if result['error'] is not None:
                # Never echo server messages: they may contain card text or credentials.
                raise AnkiError(t('Anki rechazó la operación. Revisa acceso, duplicados y plantillas en Anki.'))
            return result['result']
        except (OSError, ValueError, http.client.HTTPException) as exc:
            raise AnkiError(t('No responde Anki o su respuesta no es válida. Abre el perfil deseado y comprueba el acceso.')) from exc
        finally:
            connection.close()

    def check(self):
        permission = self.call('requestPermission')
        if not isinstance(permission, dict) or permission.get('permission') != 'granted':
            raise AnkiError('Acceso pendiente o denegado. Revisa el permiso en Anki y vuelve a comprobar.')
        if permission.get('requireApiKey') and not self.key:
            raise AnkiError(t('Anki requiere una clave: introdúcela en Opciones avanzadas, solo para esta sesión.'))
        version = self.call('version')
        if type(version) is not int or version < 6:
            raise AnkiError(t('Se requiere AnkiConnect compatible con API 6.'))
        decks, models = self.call('deckNames'), self.call('modelNames')
        for values in (decks, models):
            if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
                raise AnkiError(t('Listas de destinos incompatibles.'))
        return dict(decks=decks, models=models, version=version)

    def fields(self, model):
        value = self.call('modelFieldNames', modelName=model)
        if not isinstance(value, list) or not value or any(not isinstance(v, str) for v in value) or len(set(value)) != len(value):
            raise AnkiError(t('Firma de campos incompatible.'))
        return value


class Journal:
    def __init__(self):
        self.directory = paths()['state'] / 'anki-attempts'
        self.directory.mkdir(mode=0o700, exist_ok=True)

    def records(self):
        # Corruption fails closed; never discard protection for an unknown attempt.
        return [json.loads(p.read_text()) for p in self.directory.glob('*.json')]

    def write(self, record):
        fd, name = tempfile.mkstemp(dir=self.directory)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(record, stream); stream.flush(); os.fsync(stream.fileno())
            os.replace(name, self.directory / (record['uuid'] + '.json'))
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try: os.fsync(directory_fd)
            finally: os.close(directory_fd)
        finally:
            if os.path.exists(name): os.unlink(name)

    def reserve(self, note):
        import fcntl
        with (self.directory / 'reserve.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return self._reserve(note)

    def _reserve(self, note):
        value = digest(note)
        if any(r['digest'] == value and r['state'] != 'rejected' for r in self.records()):
            raise AnkiError(t('Este contenido ya tiene un intento registrado. Comprueba su resultado; no se reenviará.'))
        record = dict(uuid=uuid.uuid4().hex, digest=value, deck=note['deckName'], model=note['modelName'], state='uncertain')
        self.write(record)
        return record


def execute(request):
    """Used only by a supervised worker; reserve is done by the shared GUI first."""
    client = Client(request['endpoint'], request.get('key', ''))
    action = request['operation']
    if action == 'check': return client.check()
    if action == 'fields': return dict(fields=client.fields(request['model']))
    record = request['record']
    journal = Journal()
    if action == 'send':
        note = request['note']
        try:
            # Read-only validation before the single mutating call.
            fields = client.fields(note['modelName'])
            validate(note, fields)
            if note['deckName'] not in client.call('deckNames'):
                raise AnkiError(t('El mazo ya no está disponible.'))
            templates = client.call('modelTemplates', modelName=note['modelName'])
            if not isinstance(templates, dict) or not templates:
                raise AnkiError(t('No se pudieron validar las plantillas.'))
            if any('{{cloze:' in str(t).lower() for t in templates.values()):
                raise AnkiError(t('Los tipos cloze aún no están habilitados.'))
            note['tags'] = ['naatik_tx_' + record['uuid']]
            note['options'] = {'allowDuplicate': False}
            allowed = client.call('canAddNotes', notes=[note])
            if not isinstance(allowed, list) or len(allowed) != 1 or allowed[0] is not True:
                raise AnkiError(t('Anki rechazó la validación: revisa duplicados, campos y plantillas.'))
        except Exception:
            record = dict(record, state='rejected')
            journal.write(record)
            return dict(state='rejected', record=record)
        try:
            value = client.call('addNote', note=note)
            if type(value) is not int or value <= 0: raise AnkiError(t('ID inválido.'))
        except Exception:
            return dict(state='uncertain', record=record)
    elif action == 'reconcile':
        ids = client.call('findNotes', query='tag:naatik_tx_' + record['uuid'])
        if not isinstance(ids, list) or len(ids) != 1 or type(ids[0]) is not int or ids[0] <= 0:
            return dict(state='uncertain', record=record)
        notes = client.call('notesInfo', notes=ids)
        if not isinstance(notes, list) or len(notes) != 1:
            return dict(state='uncertain', record=record)
        info = notes[0]
        candidate = dict(deckName=record['deck'], modelName=info.get('modelName'),
                         fields={k: v['value'] for k, v in info.get('fields', {}).items()})
        if digest(candidate) != record['digest'] or info.get('noteId') != ids[0] or 'naatik_tx_' + record['uuid'] not in info.get('tags', []):
            return dict(state='uncertain', record=record)
        cards = info.get('cards')
        if not isinstance(cards, list) or not cards or any(type(i) is not int or i <= 0 for i in cards):
            return dict(state='uncertain', record=record)
        card_info = client.call('cardsInfo', cards=cards)
        if not isinstance(card_info, list) or len(card_info) != len(cards) or any(c.get('deckName') != record['deck'] or c.get('note') != ids[0] for c in card_info):
            return dict(state='uncertain', record=record)
        value = ids[0]
    else:
        raise AnkiError(t('Operación no admitida.'))
    record = dict(record, state='confirmed', note_id=value)
    journal.write(record)
    return dict(state='confirmed', record=record)
