#!/usr/bin/env python3
"""One desktop check: fresh sources, environments and caches; GUI setup only.

No dependency or model is downloaded by this driver. The user confirms each
preparation in Next's GUI. Leaves its isolated directory and machine-readable
report for review; never reads/writes the normal user profile.
"""
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from public_install_validation import copy_source


def main():
    workspace=Path(tempfile.mkdtemp(prefix='next-translation-desktop-'))
    source=workspace/'source';project=Path(__file__).resolve().parents[1];copy_source(project,source)
    (source/'docs').mkdir()
    for name in ('THIRD_PARTY_DEPENDENCIES.md','TRANSLATION-SETUP.md','INSTALLATION.md'):
        shutil.copy2(project/'docs'/name,source/'docs'/name)
    env=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
    # Authentication belongs to the running display, not the new data profile.
    authority=Path.home()/'.Xauthority'
    if not env.get('XAUTHORITY') and authority.is_file():env['XAUTHORITY']=str(authority)
    for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR'):
        env[key]=str(workspace/key);Path(env[key]).mkdir(mode=0o700)
    for key in list(env):
        if key.startswith(('ARGOS_','PIP_','NAATIK_NEXT_')) or key in ('PYTHONPATH','PYTHONHOME'):env.pop(key,None)
    print('Perfil nuevo, sin entornos/cachés/modelos: '+str(workspace),flush=True)
    print('En el popup pulsa Preparar traducción. Elige idiomas en Traducción, pulsa Preparar traducción y confirma los componentes. Espera Listo y vuelve mediante Acciones → Translator. Cierra Next desde la ventana principal para terminar el informe.',flush=True)
    process=subprocess.run([str(source/'launch'),'--translator'],cwd=source,env=env)
    validation=Path(env['XDG_DATA_HOME'])/'naatik-next/argos/validation.json'
    value=json.loads(validation.read_text()) if validation.is_file() else None
    report=dict(kind='fresh HOME/XDG/source/venvs/caches on existing system; not a clean VM',returncode=process.returncode,
                real_inference='PASS' if value and value.get('route') in (['ja','es'],['ja','en','es']) and value.get('offline_checked') and value.get('output','').strip() else 'NOT VALIDATED',
                validation=value,source=str(source),profile=str(workspace))
    (workspace/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['real_inference']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
