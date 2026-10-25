"""Own, pinned CPU runtime provisioning. Usable before Qt/Argos is installed."""
from .i18n import t
import hashlib
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
from .storage import UserError

PROJECT=Path(__file__).resolve().parent.parent


def run_progress(args, progress, *, env=None, timeout=900):
    # In a supervised worker children remain in its group; a bootstrap subprocess
    # is itself started in a new group by the GUI. Never invoke a shell string.
    process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
    started=time.monotonic();tail=''
    try:
        while selector.get_map():
            if time.monotonic()-started>timeout:raise UserError(t('Se agotó el tiempo de preparación; puedes reintentar.'))
            for key,_ in selector.select(0.2):
                block=os.read(key.fileobj.fileno(),8192)
                if not block:selector.unregister(key.fileobj);continue
                value=block.decode(errors='replace');tail=(tail+value)[-4000:];progress(value[-2000:])
        process.wait(timeout=5)
        if process.returncode:
            detail=t('No se pudo conectar con PyPI (red/DNS). Revisa tu conexión y reintenta.') if any(word in tail for word in ('name resolution','Name or service not known','Network is unreachable','Connection refused')) else t('No se pudo completar la instalación. Puedes reintentar.')
            raise UserError(detail+t(' No se marcará como lista.\n')+tail)
    finally:
        selector.close();process.stdout.close()
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:process.kill();process.wait()


def runtime_directory():
    from .translation_setup import root
    return root()/'runtime'


def program():
    python=runtime_directory()/'bin/python'
    return str(python) if python.is_file() and (runtime_directory()/'next-runtime.json').is_file() and not runtime_directory().is_symlink() else sys.executable


def compatible():
    import platform,sysconfig
    if sys.version_info[:2]!=(3,14) or sys.platform!='linux' or platform.machine()!='x86_64' or sysconfig.get_config_var('Py_GIL_DISABLED'):
        raise UserError(t('Esta preparación admite Python 3.14 estándar, Linux x86_64. Plataforma aún no compatible.'))


def prepare(progress=lambda text:None):
    from .translation_setup import locked,atomic_json
    compatible()
    target=runtime_directory();lock=PROJECT/'requirements-translation.lock'
    env=dict(os.environ,PYTHONNOUSERSITE='1',PIP_CONFIG_FILE=os.devnull)
    for key in ('PYTHONPATH','PYTHONHOME','NAATIK_NEXT_WHEELHOUSE'):env.pop(key,None)
    with locked('.provision.lock'):
        if target.is_dir() and not target.is_symlink(): (target/'next-runtime.json').unlink(missing_ok=True)
        if target.is_symlink():raise UserError(t('El entorno de traducción no puede ser un enlace a otra instalación.'))
        python=target/'bin/python'
        if not python.is_file():
            progress(t('Creando el entorno privado de traducción de Next…'))
            run_progress([sys._base_executable,'-m','venv',str(target)],progress,env=env)
        run_progress([str(python),'-c','import sys,pathlib; assert sys.prefix!=sys.base_prefix; assert "include-system-site-packages = false" in (pathlib.Path(sys.prefix)/"pyvenv.cfg").read_text().lower()'],progress,env=env)
        # Recovery always re-runs a hash-pinned installation. No user pip cache,
        # developer wheelhouse or global site-packages are read.
        progress(t('Instalando motor CPU con versiones y hashes fijados desde PyPI…'))
        run_progress([str(python),'-m','pip','--isolated','install','--index-url','https://pypi.org/simple',
            '--no-cache-dir','--only-binary=:all:','--no-deps','--require-hashes','--timeout','15','--retries','1',
            '-r',str(lock)],progress,env=env)
        run_progress([str(python),'-c',
            'import sys,pathlib; assert sys.prefix!=sys.base_prefix; assert "include-system-site-packages = false" in (pathlib.Path(sys.prefix)/"pyvenv.cfg").read_text().lower(); from naatik_next.translation import package_api; package_api(); import ctranslate2,sentencepiece; print("Motor CPU importado; falta probar modelos")'],progress,env=env)
        atomic_json(target/'next-runtime.json',dict(lock_sha256=hashlib.sha256(lock.read_bytes()).hexdigest(),cpu=True))
    return dict(detail=t('Entorno preparado. Los modelos aún deben pasar carga e inferencia.'),program=str(python))


def prepare_base(progress=lambda text:None):
    compatible()
    from .translation_setup import locked
    env=dict(os.environ,NAATIK_NEXT_ONLINE='1',NAATIK_NEXT_SKIP_DESKTOP='1',PYTHONNOUSERSITE='1',PIP_CONFIG_FILE=os.devnull)
    for key in ('PYTHONPATH','PYTHONHOME','NAATIK_NEXT_WHEELHOUSE','NAATIK_NEXT_OFFLINE'):env.pop(key,None)
    with locked('.base.lock'):
        run_progress(['bash',str(PROJECT/'tools/install.sh')],progress,env=env)
    return dict(detail=t('Interfaz y adaptador propios preparados; abre la sección Traducción de la ventana principal.'))
