"""Diagnostic only: public Requires-Python and wheel tags, not an inference claim."""
import json
from pathlib import Path
import sys
# Use the pip seeded by venv; no extra diagnostic download needed.
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.tags import cpython_tags, compatible_tags, sys_tags
from pip._vendor.packaging.utils import parse_wheel_filename


def matrix(directory):
    platforms = sorted({tag.platform for tag in sys_tags() if tag.platform != 'any'})
    results = {}
    for minor in (11, 12, 13, 14):
        python = f'3.{minor}'
        tags = set(cpython_tags((3, minor), [f'cp3{minor}'], platforms))
        tags.update(compatible_tags((3, minor), f'cp3{minor}', platforms))
        rows = []
        for file in sorted(directory.glob('*.json')):
            data = json.loads(file.read_text())
            requirement = data['info'].get('requires_python') or ''
            accepts = SpecifierSet(requirement).contains(python)
            wheels = []
            for item in data['urls']:
                if item['packagetype'] != 'bdist_wheel' or item.get('yanked'):
                    continue
                try:
                    if parse_wheel_filename(item['filename'])[3] & tags:
                        wheels.append(item['filename'])
                except ValueError:
                    pass
            rows.append({'name':data['info']['name'],'version':data['info']['version'],
                         'requires_python':requirement,'metadata_accepts':accepts,
                         'compatible_public_wheels':wheels,
                         'sdist_available':any(x['packagetype']=='sdist' for x in data['urls'])})
        results[python] = rows
    return {'scope':'PyPI metadata/tags only. Torch official CPU index and actual load/inference on alternative Python remain separate gates. Existing locks include cp314 hashes.', 'matrix':results}


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(json.dumps(matrix(Path(sys.argv[1])),ensure_ascii=False,indent=2)+'\n')
