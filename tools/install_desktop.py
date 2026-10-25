"""Install only the distinct Next menu entry. Never touches older launchers."""
import os
from pathlib import Path

project = Path(__file__).resolve().parent.parent
base = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
if not base.is_absolute():
    base = Path.home() / '.local/share'
applications = base / 'applications'
applications.mkdir(parents=True, exist_ok=True)

def quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'

content = (project / 'naatik-next.desktop.in').read_text().replace('"@LAUNCH@"', quote(project / 'launch'))
target = applications / 'org.naatik.Next.desktop'
target.write_text(content)
print(target)
