"""Real pinned model/CPU worker checks, only in the public validation directory."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from naatik_next.manga import defaults
from naatik_next.resources import prepare_model, catalogue, digest


def runtime_root(cpu, out):
    # venv/bin/python normally links to /usr/bin/python: validate its environment,
    # not the resolved binary. sys.prefix is independently checked in that process.
    root = cpu.parent.parent.resolve()
    assert root.is_relative_to(out.resolve())
    assert (root / 'pyvenv.cfg').is_file()
    return root


def main():
    out = Path(os.environ['NAATIK_REVIEW_OUTPUT']).resolve()
    assert os.environ.get('NAATIK_PUBLIC_REVIEW') == '1'
    assert Path.home().resolve().is_relative_to(out)
    assert Path.cwd().resolve().is_relative_to(out)
    mode = sys.argv[1]
    if mode in ('download','reuse'):
        def offline(*args, **kwargs):
            raise AssertionError('Verified resource reuse attempted network access')
        kwargs = {'opener':offline} if mode=='reuse' else {}
        result = prepare_model(progress=lambda text:print(text,flush=True),**kwargs)
        model = Path(result['model'])
        verified = []
        for item in catalogue()['files']:
            path = model / item['name']
            assert path.stat().st_size == item['bytes']
            assert digest(path) == item['sha256']
            verified.append(item)
        (out/f'model-{mode}.json').write_text(json.dumps({'status':'PASS','source':'pinned public Hugging Face revision','files':verified,'no_network_reuse':mode=='reuse'},ensure_ascii=False,indent=2))
        return
    assert mode == 'inference'
    from PySide6.QtCore import QTimer, QProcess
    from PySide6.QtWidgets import QApplication
    from naatik_next.processes import Task
    app = QApplication([])
    cpu = Path(defaults()['manga_python'])
    runtime_root(cpu, out)
    identity = subprocess.run([str(cpu),'-c',
        'import torch,sys,json,site; assert torch.version.cuda is None and "+cpu" in torch.__version__; assert not site.ENABLE_USER_SITE; print(json.dumps(dict(torch=torch.__version__,cuda=torch.version.cuda,prefix=sys.prefix)))'],check=True,capture_output=True,text=True,timeout=90)
    cpu_identity = json.loads(identity.stdout)
    assert Path(cpu_identity['prefix']).resolve().is_relative_to(out)
    beats=[]; timer=QTimer();timer.timeout.connect(lambda:beats.append(time.monotonic()));timer.start(10)
    task=Task(program=str(cpu),module='naatik_next.manga_worker',persistent=True)
    answers=[];errors=[]
    task.result.connect(answers.append);task.error.connect(errors.append)
    def wait(predicate, timeout=240):
        until=time.monotonic()+timeout
        while not predicate():
            app.processEvents()
            if time.monotonic()>until: raise TimeoutError('CPU worker real validation timed out')
            time.sleep(.01)
    config=defaults()
    try:
        task.start({'action':'detect','model':config['manga_model']},240000)
        wait(lambda:not task.busy)
        assert not errors,errors
        assert answers[-1]['status']=='listo' and answers[-1]['probe_text']=='日本',answers
        descriptor=answers[-1]
        request={'action':'ocr','engine':'mangaocr','language':'ja','model':config['manga_model'],
                 'image':str(Path('examples/nihon.png').resolve())}
        task.start(request,120000);wait(lambda:not task.busy)
        assert not errors and answers[-1]=='日本',(errors,answers)
        recognized=answers[-1]
        task.start(request,120000);task.cancel()
        wait(lambda:not task.busy)
        wait(lambda:task.process.state()==QProcess.NotRunning)
        assert errors and 'cancel' in errors[-1].lower(),errors
        task.close();errors.clear()
        task.start({'action':'detect','model':config['manga_model']},240000)
        wait(lambda:not task.busy)
        assert not errors and answers[-1]['status']=='listo',(errors,answers)
        assert beats
        result={'status':'PASS','cpu_identity':cpu_identity,'descriptor':descriptor,
                'actual_ocr':recognized,'original_sample':'examples/nihon.png; no edited text',
                'cancel_and_reload':True,'qt_event_beats':len(beats),'display':'offscreen, not interactive capture'}
        (out/'cpu-inference.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False),flush=True)
    finally:
        task.close()


if __name__=='__main__': main()
