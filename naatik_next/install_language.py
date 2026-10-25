"""Dependency-free Fedora installation language gate; cancellation has no writes."""
import argparse
import json
import os
from pathlib import Path
import sys


def existing_settings():
    base = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))
    if not base.is_absolute(): base = Path.home()/'.config'
    path = base/'naatik-next/settings.json'
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict): raise ValueError('Expected JSON object / Se esperaba un objeto JSON')
        return value, True
    except FileNotFoundError:
        return {}, False


def select(explicit=None, *, ask=True):
    settings, exists = existing_settings()
    current = settings.get('ui_language', 'es')
    if current not in ('es', 'en'): current = 'es'
    if explicit:
        if explicit not in ('es', 'en'): raise ValueError('Idioma / Language: es | en')
        return explicit
    if not ask: return current
    if not sys.stdin.isatty():
        if exists and settings.get('ui_language') in ('es', 'en'):
            return current
        print('Elige idioma antes de instalar / Choose language before installing:\n  bash tools/install.sh --language es|en\nCancelar / Cancel: Ctrl+C', file=sys.stderr)
        return None
    print('Idioma / Language: 1 Español · 2 English · c Cancelar / Cancel\n' +
          f'Actual / Current: {current}. Enter = conservar / keep.', file=sys.stderr)
    while True:
        print('> ', end='', file=sys.stderr, flush=True)
        try: value = input().strip().lower()
        except (EOFError, KeyboardInterrupt): return None
        if value in ('c', 'cancel', 'cancelar'): return None
        if value in ('1', 'es'): return 'es'
        if value in ('2', 'en'): return 'en'
        if value == '': return current


def persist(code):
    from .storage import save_settings
    # Read immediately before merging, so setup/repair never replaces other preferences.
    settings, exists = existing_settings()
    settings['ui_language'] = code
    if not exists:
        settings['tutorial'] = {'status': 'pending', 'step': 0}
    save_settings(settings)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', choices=('es', 'en'))
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--message')
    parser.add_argument('--suffix', default='')
    args = parser.parse_args()
    code = select(args.language or os.environ.get('NAATIK_NEXT_UI_LANGUAGE'))
    if code is None: return 130
    if args.message is not None:
        from .i18n import set_language, t
        set_language(code)
        print(t(args.message) + args.suffix)
    elif args.save: persist(code)
    else: print(code)
    return 0


if __name__ == '__main__': raise SystemExit(main())
