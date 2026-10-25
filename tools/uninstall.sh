#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$project_dir"
# Only remove our menu entry if it still belongs to this installation.
"$project_dir/.venv/bin/python" - <<'PY'
import os
from pathlib import Path
project=Path.cwd()
base=Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))
if not base.is_absolute(): base=Path.home()/'.local/share'
p=base/'applications/org.naatik.Next.desktop'
if p.is_file():
    # Installation-specific path is escaped in Exec; compare via installer quote rules.
    quoted=str(project/'launch').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
    if f'Exec="{quoted}"' in p.read_text(): p.unlink(); print('Entrada de menú eliminada.')
    else: print('La entrada pertenece a otra instalación; se conserva.')
print('Datos, preferencias, modelos, diccionarios y entornos conservados. Cierra Next antes de borrar manualmente su carpeta.')
PY
