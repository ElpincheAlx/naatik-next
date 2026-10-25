"""Generate a single-action POSIX script, without interpolating shell code."""
from .i18n import t
import os
from pathlib import Path
import shlex
import stat
import tempfile
from .storage import UserError, paths


def launcher_path():
    return Path(__file__).resolve().parent.parent / 'launch'


ACTIONS = {'capture-copy': 'Capturar y copiar', 'translator': 'Translator', 'phrase': 'OCR Phrase', 'show': 'Abrir ventana principal'}


def profile_environment():
    data = paths()
    values = {variable:str(data[key].parent) for variable,key in
              (('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state'))}
    cache = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home()/'.cache')))
    values['XDG_CACHE_HOME'] = str(cache if cache.is_absolute() else Path.home()/'.cache')
    values['XDG_RUNTIME_DIR'] = os.environ.get('XDG_RUNTIME_DIR') or None
    return values


def action_script(action, launcher=None):
    if action not in ACTIONS: raise UserError(t('Acción de integración desconocida.'))
    launcher = Path(launcher or launcher_path()).absolute()
    lines = ['#!/bin/sh', '# Na’atik Next: ' + ACTIONS[action]]
    # Target this GUI's XDG profile, even if a runner supplies its own XDG roots.
    for variable, value in profile_environment().items():
        lines.append('unset ' + variable if value is None else 'export '+variable+'='+shlex.quote(value))
    lines.append('exec ' + shlex.quote(str(launcher)) + ' --' + action)
    return '\n'.join(lines) + '\n'


def capture_script(launcher=None):
    return action_script('capture-copy', launcher)


def write_capture_script(path, *, overwrite=False):
    return write_action_script(path, 'capture-copy', overwrite=overwrite)


def write_action_script(path, action, *, overwrite=False):
    return write_artifact(path, action_script(action), overwrite=overwrite)


def write_artifact(path, content, *, overwrite=False):
    """Atomic replace of a user-confirmed regular file; no symlink traversal."""
    path = Path(path).absolute()
    if path == launcher_path() or path.resolve() == launcher_path().resolve():
        raise UserError(t('Elige otra ruta: no se puede reemplazar el lanzador de Next.'))
    if path.is_symlink():
        raise UserError(t('No se sobrescriben enlaces simbólicos. Elige otro archivo.'))
    if path.exists():
        if not stat.S_ISREG(path.stat().st_mode):
            raise UserError(t('La ruta seleccionada no es un archivo normal.'))
        if not overwrite:
            raise FileExistsError(str(path))
    fd, temporary = tempfile.mkstemp(prefix='.naatik-script-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            output.write(content)
            output.flush()
            os.fchmod(output.fileno(), 0o700)
            os.fsync(output.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            # No-clobber creation, even if a file appeared after the save dialog.
            os.link(temporary, path)
        return path
    finally:
        Path(temporary).unlink(missing_ok=True)


def action_command(action):
    if action not in ACTIONS: raise UserError(t('Acción de integración desconocida.'))
    values = profile_environment()
    unset = ''.join('-u '+key+' ' for key,value in values.items() if value is None)
    return ('env ' + unset + ' '.join(key+'='+shlex.quote(value) for key,value in values.items() if value is not None)
            + ' ' + shlex.quote(str(launcher_path())) + ' --' + action)


def desktop_quote(value):
    # Exec argument quoting, then desktop-entry string escaping (two separate layers).
    quoted = ''.join('\\' + c if c in '\\"`$' else c for c in str(value).replace('%','%%'))
    return '"' + quoted.replace('\\','\\\\').replace('\n','\\n').replace('\r','\\r').replace('\t','\\t') + '"'


def desktop_entry(action):
    if action not in ACTIONS: raise UserError(t('Acción de integración desconocida.'))
    # Let sh parse only our generated, shell-escaped fixed command. No clipboard data.
    command = '/bin/sh -c ' + desktop_quote('exec ' + action_command(action))
    return ('[Desktop Entry]\nType=Application\nVersion=1.0\nName=Na’atik Next — ' + ACTIONS[action] +
            '\nExec=' + command + '\nTerminal=false\nIcon=accessories-dictionary\nCategories=Education;\n')


def write_action_desktop(path, action, *, overwrite=False):
    main = paths()['data'].parent / 'applications/org.naatik.Next.desktop'
    if Path(path).resolve() == main.resolve():
        raise UserError(t('No se reemplaza el acceso principal de Next.'))
    return write_artifact(path, desktop_entry(action), overwrite=overwrite)
