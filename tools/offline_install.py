"""Verify an explicit wheel directory; URLs cannot bypass offline mode."""
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from naatik_next.i18n import t
from urllib.parse import unquote


def main():
    lock, wheel_dir = map(Path, sys.argv[1:])
    if not wheel_dir.is_dir():
        raise SystemExit(t('Falta el directorio de ruedas offline: ')+str(wheel_dir)+t('. No se usa otro entorno.'))
    lines = []
    for line in lock.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        if ' @ ' in line:
            url = line.split(' @ ', 1)[1].split()[0]
            filename = unquote(url.rsplit('/', 1)[1])
            wheel = wheel_dir / filename
            expected = line.split('--hash=sha256:')[1]
            if not wheel.is_file():
                raise SystemExit(t('Falta la rueda CPU requerida: ')+filename+t('; descarga bloqueada por modo offline.'))
            if hashlib.file_digest(wheel.open('rb'), 'sha256').hexdigest() != expected:
                raise SystemExit(t('Hash incorrecto: ')+filename)
            name, version = filename.split('-')[:2]
            line = f'{name}=={version} --hash=sha256:{expected}'
        lines.append(line)
    with tempfile.TemporaryDirectory(prefix='naatik-install-') as tmp:
        requirements = Path(tmp) / 'locked.txt'
        requirements.write_text('\n'.join(lines))
        subprocess.run([sys.executable, '-m', 'pip', '--isolated', 'install', '--no-index',
                        '--find-links', str(wheel_dir), '--prefer-binary', '--no-build-isolation', '--no-deps',
                        '--require-hashes', '-r', str(requirements)], check=True)


if __name__ == '__main__':
    main()
