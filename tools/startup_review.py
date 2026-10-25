#!/usr/bin/env python3
"""Real isolated launcher/script/desktop probes; never treats offscreen as desktop proof.

Uses this checkout's existing Qt venv. No model/resource downloads, private user
clipboard dump, global shortcuts, KDE edits or lock removal. Each observed owner
is stopped only after verifying its isolated state environment in /proc.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import resource
import signal
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
KEYS = ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','XDG_RUNTIME_DIR')


def isolated(root):
    env = dict(os.environ, PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    env.setdefault('QT_QPA_PLATFORM','offscreen')
    for key in list(env):
        if key.startswith(('ARGOS_', 'NAATIK_')) or key in ('PYTHONPATH','PYTHONHOME'):
            env.pop(key)
    authority = Path.home()/'.Xauthority'
    if authority.is_file(): env.setdefault('XAUTHORITY',str(authority))
    for index,key in enumerate(KEYS):
        directory = root/str(index); directory.mkdir(parents=True,mode=0o700);env[key]=str(directory)
    return env


def stop_owned(env):
    lock = Path(env['XDG_STATE_HOME'])/'naatik-next/application.lock'
    try:
        pid = int(lock.read_text().splitlines()[0])
        entries = Path('/proc',str(pid),'environ').read_bytes().split(b'\0')
        if os.fsencode('XDG_STATE_HOME='+env['XDG_STATE_HOME']) not in entries:
            return False
        os.kill(pid,signal.SIGTERM)
        return True
    except (FileNotFoundError, ValueError, ProcessLookupError): return False


def invoke(command, env, profile_env):
    process = subprocess.Popen(command, cwd='/', env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    stopped = False
    try:
        out,err = process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        stopped = stop_owned(profile_env)
        if not stopped:
            # Only our foreground launcher group, never an existing instance.
            os.killpg(process.pid,signal.SIGTERM)
        try: out,err = process.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);out,err=process.communicate(timeout=3)
    state=Path(profile_env['XDG_STATE_HOME'])/'naatik-next'
    startup_log=(state/'naatik-next.log').read_text()[-2500:] if (state/'naatik-next.log').exists() else ''
    return dict(exit=process.returncode,observer_stopped_owner=stopped,
                observed_app_startup_failure='ERROR Application activation failed:' in startup_log,
                stderr=err.decode(errors='replace')[-2500:],
                startup_log=startup_log,
                lock_remains=(state/'application.lock').exists(),locator_remains=(state/'application.endpoint').exists())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--normal-before',type=Path,help='Optional private hash snapshot produced before review; no user file contents are copied')
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    work=Path(tempfile.mkdtemp(prefix='ns-review-'))
    source=work/"Next con espacios '日本' $()";source.mkdir()
    shutil.copytree(ROOT/'naatik_next',source/'naatik_next',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(ROOT/'launch',source/'launch')
    runtime=source/'.venv/bin';runtime.mkdir(parents=True)
    python=runtime/'python';python.write_text('#!/bin/sh\nexec '+shlex.quote(str(ROOT/'.venv/bin/python'))+' "$@"\n');python.chmod(0o700)
    probe=socket.socket(socket.AF_UNIX)
    try:probe.bind(str(work/'probe.sock'));bind=dict(available=True)
    except OSError as error:bind=dict(available=False,error=str(error),errno=error.errno)
    finally:probe.close()
    gio=subprocess.run(['/usr/bin/python3','-c','from gi.repository import Gio'],capture_output=True).returncode==0
    result=dict(kind='real launch/artifact execution, isolated HOME/XDG before Next imports',
                qt_platform=os.environ.get('QT_QPA_PLATFORM','offscreen'),existing_next_venv=True,
                clean_runtime_install=False,unix_bind=bind,source_copy=str(source),entries=[],
                desktop_action_verified=False,capture_selector_ocr_clipboard_verified=False)
    for index,action in enumerate(('show','capture-copy','translator','phrase')):
        env=isolated(work/('p'+str(index)))
        folder=work/('artifacts'+str(index));folder.mkdir();script=folder/(action+" '日本' $().sh");desktop=folder/(action+'.desktop')
        # This interpreter starts after the profile is set and imports the copied sources.
        generation=subprocess.run([str(ROOT/'.venv/bin/python'),'-c',
            'from naatik_next.integrations import write_action_script,write_action_desktop; import sys; write_action_script(sys.argv[2],sys.argv[1]);write_action_desktop(sys.argv[3],sys.argv[1])',
            action,str(script),str(desktop)],cwd=source,env=env,capture_output=True,text=True,timeout=5)
        if generation.returncode: raise RuntimeError(generation.stderr)
        if shutil.which('desktop-file-validate'):
            subprocess.run(['desktop-file-validate',str(desktop)],check=True,capture_output=True)
        direct=invoke([str(source/'launch')]+([] if action=='show' else ['--'+action]),env,env)
        wrong=dict(env,**{key:str(work/'wrong-profile'/key) for key in KEYS[1:]})
        scripted=invoke([str(script)],wrong,env)
        launched=invoke(['/usr/bin/python3','-c',
            'from gi.repository import Gio; import sys; a=Gio.DesktopAppInfo.new_from_filename(sys.argv[1]);assert a;assert a.launch([],None)',str(desktop)],wrong,env) if gio else dict(status='NOT TESTED: system Gio unavailable')
        result['entries'].append(dict(action=action,direct=direct,script=scripted,desktop=launched,
                                      intended_profile_log_exists=(Path(env['XDG_STATE_HOME'])/'naatik-next/naatik-next.log').exists(),
                                      wrong_profile_created=(work/'wrong-profile').exists()))
    if args.normal_before:
        before=json.loads(args.normal_before.read_text());changed=[]
        for filename,digest in before.items():
            file=Path(filename)
            if not file.is_file(): changed.append(filename);continue
            with file.open('rb') as stream: actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual!=digest:changed.append(filename)
        extra=set()
        for directory in (Path.home()/'.config/naatik-next',Path.home()/'.local/state/naatik-next',Path.home()/'.local/share/naatik-next'):
            extra.update(str(path) for path in directory.rglob('*') if path.is_file() and not path.is_symlink() and str(path) not in before)
        result['normal_profile_and_script']=dict(files_checked=len(before),changed_count=len(changed),new_file_count=len(extra),unchanged=not changed and not extra,
                                                existing_script_sha256=before.get(str(ROOT/'naatik-next-capturar.sh')))
    result['scope']='Exit/diagnostics and selected profile are observed; bind denial blocks successful cold/reuse cycles. Offscreen never validates global clipboard/selector/tray.'
    (output/'real-launches.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
