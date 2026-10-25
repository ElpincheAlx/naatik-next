"""Build a Fedora source distribution without user scripts, environments or resources."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parents[1]
NAME='Naatik-Next-Fedora-es-en'


def digest(path):
    with path.open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--validation',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='next-fedora-package-') as temporary:
        source=Path(temporary)/NAME;source.mkdir()
        for folder in ('naatik_next','tools','tests','docs','examples'):
            shutil.copytree(ROOT/folder,source/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for filename in ('AGENTS.md','README.md','launch','naatik-next.desktop.in'):
            shutil.copy2(ROOT/filename,source/filename)
        for path in ROOT.glob('requirements*.lock'):shutil.copy2(path,source/path.name)
        for filename in ('.gitignore', 'LICENSE-STATUS.md', 'PUBLICATION_REPORT.md', 'SOURCE_MANIFEST.json', 'LICENSE', 'COPYING', 'NOTICE'):
            if (ROOT/filename).is_file(): shutil.copy2(ROOT/filename, source/filename)
        instructions = (ROOT/'README.md').read_text()
        # This copy lives one level above docs; keep its evidence links usable.
        (source/'INSTALACION.md').write_text(instructions.replace('](evidence/', '](docs/evidence/'))
        shutil.copy2(args.validation,source/'VALIDACION.txt')
        files=sorted(path for path in source.rglob('*') if path.is_file())
        (source/'SHA256.txt').write_text(''.join(digest(path)+'  '+str(path.relative_to(source))+'\n' for path in files))
        archive=args.output/(NAME+'.tar.gz')
        with tarfile.open(archive,'w:gz') as packed:packed.add(source,arcname=NAME)
        shutil.copy2(source/'INSTALACION.md',args.output/'INSTALACION.md')
        shutil.copy2(source/'VALIDACION.txt',args.output/'VALIDACION.txt')
        (args.output/'SHA256.txt').write_text(''.join(digest(path)+'  '+path.name+'\n' for path in
            (archive,args.output/'INSTALACION.md',args.output/'VALIDACION.txt')))
    print(archive)


if __name__=='__main__':main()
