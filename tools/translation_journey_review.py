#!/usr/bin/env python3
"""Capture an isolated real GUI journey with explicitly supplied local model files.

Uses this checkout's Next venv; no network, no personal caches, no model discovery
outside the isolated profile. Not a fresh-runtime installation or clean VM test.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', action='append', default=[], type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    models = [p.resolve(strict=True) for p in args.model]
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix='next-translation-review-'))
    authority = Path.home()/'.Xauthority'
    if authority.exists(): os.environ.setdefault('XAUTHORITY', str(authority))
    for key in list(os.environ):
        if key.startswith(('ARGOS_', 'NAATIK_NEXT_')): os.environ.pop(key)
    for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME'):
        directory = profile/key; directory.mkdir(mode=0o700); os.environ[key] = str(directory)
    from PySide6.QtWidgets import QApplication
    from naatik_next.app import Window
    app = QApplication.instance() or QApplication([])
    with patch('naatik_next.app.QTimer.singleShot'):
        window = Window(background=True, popup_only=True)
    window.resize(1100, 900)
    section = window.translation_section
    def wait(predicate, timeout=180):
        deadline = time.monotonic()+timeout
        while not predicate():
            app.processEvents(); time.sleep(.01)
            if time.monotonic()>deadline: raise RuntimeError('Timed out: '+section.hint.text())
    def capture(name):
        app.processEvents(); window.grab().save(str(output/name))
    from naatik_next.popups import TextPopup
    empty_popup = TextPopup(window, 'translator'); window.popups['translator'] = empty_popup
    empty_popup.open_text('')
    wait(lambda: not empty_popup.translate_task.busy)
    empty_popup.grab().save(str(output/'translator-empty-real.png'))
    empty_popup.prepare_translation.click()
    empty_popup.close()
    wait(lambda: not section.active)
    assert section.state.text() == 'Sin configurar', section.hint.text()
    capture('translation-empty-real.png')
    # Exercise real supervisor cancellation; no network action is dispatched.
    section.start('translation_status'); capture('translation-preparing-real.png'); section.cancel()
    capture('translation-cancelled-real.png')
    # A deliberately injected failure documents only the recoverable UI state.
    section.failed(section.serial, 'Error de conexión simulado para revisión visual.')
    capture('translation-error-simulated.png')
    section.cancel()
    # Proposal rendering is injected; no catalogue request/download is made.
    from naatik_next.translation_setup import normalize
    from PySide6.QtWidgets import QMessageBox
    items = normalize([dict(from_code=a, to_code=b, package_version='1.0',
                       links=[f'https://argos-net.com/{a}_{b}.argosmodel'])
                       for a,b in [('ja','en'),('en','es')]])
    section.report['runtime_error'] = 'simulated missing runtime'
    def review_only(*args):
        capture('translation-proposal-simulated.png')
        return QMessageBox.No
    with patch.object(QMessageBox, 'question', side_effect=review_only):
        section.finished(section.serial, 'translation_details', dict(items=[dict(i, bytes=None) for i in items], route=['ja','en','es'], sha256='fixture'))
    for model in models:
        section.start('install_argos', path=str(model))
        wait(lambda: not section.active)
        if section.state.text() == 'Requiere atención': raise RuntimeError(section.hint.text())
    report = dict(profile=str(profile), platform=os.environ.get('QT_QPA_PLATFORM','desktop'),
                  runtime='existing Next venv, isolated HOME/XDG; not a fresh venv or clean VM',
                  runtime_versions={name:importlib.metadata.version(name) for name in ('argostranslate','ctranslate2','sentencepiece','PySide6')},
                  lock_sha256=hashlib.sha256((PROJECT/'requirements-translation.lock').read_bytes()).hexdigest(),
                  network_downloads=False, local_models=[dict(file=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), provenance='explicit local input; original download and individual license not verified by this run') for p in models],
                  state=section.state.text(), evidence=section.details.toPlainText())
    if models:
        assert section.state.text() == 'Listo', section.hint.text()
        wait(lambda: not any(task.busy for task in window.tasks + window.popup_tasks))
        capture('translation-ready-real.png')
        section.advanced.setChecked(True); capture('translation-advanced-real.png')
        window.external_command('translator')
        popup = window.popups['translator']
        popup.editor.setPlainText('私は毎日日本語を勉強しています。')
        wait(lambda: popup.route.count()>0 and not popup.translate_task.busy)
        popup.route.setCurrentIndex(popup.route.findData(['ja','en','es']))
        popup.process()
        wait(lambda: bool(popup.translation.toPlainText()))
        popup.grab().save(str(output/'translator-ready-real.png'))
        report['popup_output'] = popup.translation.toPlainText()
    window.close(); app.processEvents()
    (output/'evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
