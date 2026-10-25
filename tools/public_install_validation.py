"""Controller for the single public-source validation entry point (stdlib only).

Never imports Next in the controller; all runtime imports use newly created venvs.
The seeded pip/its vendored packaging are diagnostic tooling, not product deps.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class Blocked(Exception):
    pass


class Failed(Exception):
    pass


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            body = response.read(12 * 1024 * 1024 + 1)
        if len(body) > 12 * 1024 * 1024:
            raise Failed('Metadatos públicos superan 12 MiB')
        return body
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            raise Failed(f'Recurso público inexistente: {url} (HTTP {e.code})') from e
        raise Blocked(f'Proveedor no disponible: {url} (HTTP {e.code})') from e
    except OSError as e:
        raise Blocked(f'Red/DNS/TLS bloquea {url}: {e}') from e


def parse_lock(path):
    result = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip() or line.startswith('#'):
            continue
        chunks = line.split(' --hash=sha256:')
        if len(chunks) < 2 or any(not re.fullmatch('[0-9a-f]{64}', s) for s in chunks[1:]):
            raise Failed(f'Lock sin hash cerrado: {path.name}:{number}')
        pin = chunks[0]
        if ' @ ' in pin:
            name, url = pin.split(' @ ', 1)
            if name != 'torch' or not url.startswith('https://download-r2.pytorch.org/whl/cpu/torch-'):
                raise Failed('Solo se admite la URL CPU oficial fijada para torch')
            result.append(dict(name=name, url=url, hashes=chunks[1:]))
        else:
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9.+_-]+)', pin)
            if not match:
                raise Failed(f'Especificación no cerrada: {pin}')
            result.append(dict(name=match[1], version=match[2], hashes=chunks[1:]))
    return result


def audit_locks(source, metadata_dir):
    """Every accepted hash must exist publicly, not merely one alternative hash."""
    records, seen = [], {}
    for lock in ['requirements.lock', 'requirements-manga-build.lock', 'requirements-manga-cpu.lock', 'requirements-phrase.lock', 'requirements-translation.lock']:
        for item in parse_lock(source / lock):
            if 'url' in item:
                index = fetch('https://download.pytorch.org/whl/cpu/torch/').decode()
                urls = [urllib.parse.unquote(s) for s in re.findall(r'href=["\x27]([^"\x27]+)', index)]
                for digest in item['hashes']:
                    wanted = urllib.parse.unquote(item['url']) + '#sha256=' + digest
                    if wanted not in urls:
                        raise Failed('El hash/archivo CPU fijado no aparece en el índice público PyTorch')
                records.append(dict(item, lock=lock, source='official CPU index', verified=True))
                continue
            key = (item['name'], item['version'])
            if key not in seen:
                raw = fetch(f'https://pypi.org/pypi/{key[0]}/{key[1]}/json')
                (metadata_dir / f'{key[0]}-{key[1]}.json').write_bytes(raw)
                seen[key] = json.loads(raw)
            release = seen[key]
            public = {f['digests']['sha256']: f for f in release['urls']}
            matches = []
            for digest in item['hashes']:
                if digest not in public:
                    raise Failed(f'{key[0]} {key[1]}: hash {digest} no publicado en PyPI')
                file = public[digest]
                parsed = urllib.parse.urlsplit(file['url'])
                if parsed.scheme != 'https' or parsed.hostname != 'files.pythonhosted.org':
                    raise Failed('La distribución no procede del almacén oficial de PyPI')
                if file.get('yanked'):
                    raise Failed(f'Archivo retirado por el publicador: {file["filename"]}')
                matches.append({k: file[k] for k in ['filename', 'url', 'size', 'digests', 'packagetype']})
            records.append(dict(item, lock=lock, verified=True, requires_python=release['info'].get('requires_python'), files=matches))
    return records


def copy_source(source, destination):
    destination.mkdir()
    for name in ['naatik_next', 'tools', 'tests']:
        shutil.copytree(source / name, destination / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.log', '*.sqlite*'))
    (destination / 'examples').mkdir()
    for name in ['hello.png', 'nihon.png']:
        shutil.copy2(source / 'examples' / name, destination / 'examples' / name)
    for name in ['requirements.lock', 'requirements-manga-build.lock', 'requirements-manga-cpu.lock', 'requirements-phrase.lock', 'requirements-translation.lock', 'launch', 'naatik-next.desktop.in']:
        shutil.copy2(source / name, destination / name)
    if any(p.name in ('.venv', '.wheelhouse', '.venv-mangaocr', '.venv-phrase', '.wheelhouse-phrase') for p in destination.iterdir()):
        raise Failed('La copia incluyó artefactos locales')


def snapshot(config, data):
    files = {'settings':config/'naatik-next/settings.json',
             'dictionary':data/'naatik-next/dictionaries.sqlite3',
             'dictionary_wal':data/'naatik-next/dictionaries.sqlite3-wal',
             'menu':data/'applications/org.naatik.Next.desktop'}
    return {name:sha(path) if path.is_file() else None for name,path in files.items()}


def command(args, cwd, log, timeout=1800):
    with log.open('w') as stream:
        p = subprocess.Popen([str(a) for a in args], cwd=cwd, stdout=stream,
                             stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = p.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(p.pid, signal.SIGTERM)
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL); p.wait()
            raise Failed(f'Timeout/interrupción; consulta {log.name}')
    if code:
        text = log.read_text(errors='replace')
        # Only classify explicit transport failures as BLOCKED, not missing hashes/versions.
        if any(marker in text for marker in ['Temporary failure in name resolution', 'ConnectionError', 'Network is unreachable', 'CERTIFICATE_VERIFY_FAILED', 'ReadTimeoutError', 'HTTP Error 403', 'HTTP Error 429', 'HTTP Error 500', 'HTTP Error 502', 'HTTP Error 503', 'HTTP Error 504', 'ConnectionRefusedError', 'NameResolutionError']):
            raise Blocked(f'Fallo de red; consulta {log.name}')
        raise Failed(f'Etapa terminó con código {code}; consulta {log.name}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--normal-config', type=Path, required=True)
    parser.add_argument('--normal-data', type=Path, required=True)
    args = parser.parse_args()
    out, source = args.output.resolve(), args.source.resolve()
    if out == source or not Path.home().resolve().is_relative_to(out):
        raise SystemExit('La ejecución requiere HOME aislado bajo el directorio de revisión')
    logs = out / 'logs'; logs.mkdir()
    metadata = out / 'public-metadata'; metadata.mkdir()
    result = {'status':'RUNNING','started':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
              'host':{'platform':platform.platform(),'python':sys.version,'executable':sys.executable},
              'isolation':'new HOME/XDG/venvs/caches, host executables and native libraries retained; NOT a clean VM',
              'steps':[], 'interactive_capture_validated':False}
    before = snapshot(args.normal_config, args.normal_data)
    code = 1
    def step(name, callback):
        result['current_step'] = name
        print(name, flush=True)
        value = callback()
        result['steps'].append({'step':name,'status':'PASS'})
        (out/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return value
    try:
        print('Se instalarán dependencias públicas y se descargará el modelo fijado (~444 MB, Apache-2.0 según su ficha). Solo en esta revisión aislada.', flush=True)
        dest = out / 'Next con espacios'
        step('copy source without caches/resources', lambda:copy_source(source, dest))
        if not shutil.which('tesseract'):
            raise Blocked('Falta Tesseract del sistema. Fedora 44: sudo dnf install tesseract tesseract-langpack-eng tesseract-langpack-jpn')
        command(['tesseract','--version'],dest,logs/'tesseract-version.log',20)
        command(['tesseract','--list-langs'],dest,logs/'tesseract-languages.log',20)
        if 'eng' not in (logs/'tesseract-languages.log').read_text().splitlines():
            raise Blocked('Faltan datos Tesseract eng para la prueba real; instala tesseract-langpack-eng')
        # A seeded pip is needed only for standards-compliant compatibility analysis.
        bootstrap = out/'bootstrap'
        step('create isolated bootstrap', lambda:command([sys.executable,'-m','venv',bootstrap],out,logs/'bootstrap.log',120))
        records = step('audit all lock hashes against public sources',lambda:audit_locks(dest,metadata))
        (out/'public-lock-audit.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
        # Install only the audited public URLs. Index config cannot choose another file.
        # The original locks remain recorded by SHA-256; rewriting is review-copy only.
        result['original_lock_sha256'] = {name:sha(source/name) for name in
            ['requirements.lock','requirements-manga-build.lock','requirements-manga-cpu.lock', 'requirements-phrase.lock', 'requirements-translation.lock']}
        for lock in result['original_lock_sha256']:
            entries = []
            for record in records:
                if record['lock'] != lock: continue
                url = record.get('url') or record['files'][0]['url']
                entries.append(record['name']+' @ '+url+' '+' '.join('--hash=sha256:'+h for h in record['hashes']))
            (dest/lock).write_text('\n'.join(entries)+'\n')

        step('public Python compatibility matrix',lambda:command([bootstrap/'bin/python',dest/'tools/python_compatibility.py',metadata,out/'python-matrix.json'],dest,logs/'python-matrix.log',60))
        # All caches are new; prohibit inherited tool switches and cached indexes.
        os.environ.update(NAATIK_NEXT_PYTHON=sys.executable, NAATIK_NEXT_ONLINE='1',
                          PIP_NO_CACHE_DIR='1', PIP_CONFIG_FILE=os.devnull,
                          HF_HOME=str(out/'hf-cache'), NAATIK_PUBLIC_REVIEW='1',
                          NAATIK_ISOLATED_REVIEW='1', NAATIK_REVIEW_OUTPUT=str(out))
        step('install base from public sources',lambda:command(['bash',dest/'tools/install.sh','--language','es'],dest,logs/'base-install.log'))
        # Host OCR is independently checked; no default text is substituted.
        step('native libraries required for KDE/X11',lambda:command([dest/'.venv/bin/python','-c', 'import ctypes; [ctypes.CDLL(n) for n in ["libX11.so.6","libxcb.so.1","libxkbcommon-x11.so.0","libxcb-cursor.so.0","libGL.so.1"]]; print("Native libraries loaded; actual display interaction remains untested")'],dest,logs/'native-libraries.log',30))
        step('base GUI first/second start and real Tesseract',lambda:command([dest/'.venv/bin/python','-m','tools.independent_smoke'],dest,logs/'base-smoke.log',240))
        step('install own CPU runtime from public sources',lambda:command(['bash',dest/'tools/install.sh','--manga-cpu'],dest,logs/'cpu-install.log',1800))
        step('install own phrase runtime from public sources',lambda:command(['bash',dest/'tools/install.sh','--phrase'],dest,logs/'phrase-install.log',900))
        step('download full pinned model and verify every SHA-256',lambda:command([dest/'.venv/bin/python','-m','tools.public_model_smoke','download'],dest,logs/'model-download.log',1800))
        step('own CPU worker real load/inference/cancel/reload',lambda:command([dest/'.venv/bin/python','-m','tools.public_model_smoke','inference'],dest,logs/'cpu-inference.log',900))
        step('offline model reuse',lambda:command([dest/'.venv/bin/python','-m','tools.public_model_smoke','reuse'],dest,logs/'offline-reuse.log',120))
        result.update(status='PASS',reason='Public locks, independent install, full download and actual CPU inference passed; interactive and clean-machine gates remain.')
        code=0
    except Blocked as e:
        result.update(status='BLOCKED',reason=str(e)); code=2
    except (Failed, OSError, ValueError, AssertionError) as e:
        result.update(status='FAIL',reason=str(e)); code=1
    except KeyboardInterrupt:
        result.update(status='BLOCKED',reason='Interrupted by user');code=2
    except Exception as e:
        import traceback
        traceback.print_exc()
        result.update(status='FAIL',reason=f'Unexpected {type(e).__name__}: {e}; see console.log');code=1
    finally:
        try:
            result['normal_profile_unchanged'] = before == snapshot(args.normal_config,args.normal_data)
        except OSError as e:
            result['normal_profile_unchanged'] = False
            print(f'Cannot read final profile fingerprint: {e}',flush=True)
        if not result['normal_profile_unchanged']:
            result.update(status='FAIL',reason='Normal profile changed during review (may be concurrent user activity); investigate, no automatic restore.');code=1
        result['finished']=time.strftime('%Y-%m-%dT%H:%M:%S%z')
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        summary=f"{result['status']}: {result['reason']}\nEtapa: {result.get('current_step')}\nPerfil normal sin cambios: {result['normal_profile_unchanged']}\n"
        (out/'summary.txt').write_text(summary);print(summary,flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
