#!/usr/bin/env python3
"""Isolated UI capture and optional transient real X11 registration/conflict probe.

No KDE/StreamController settings are changed. Never synthesizes key events.
Use QT_QPA_PLATFORM=xcb from the desktop to exercise Qt's actual registration.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def probe_x11(text):
    from naatik_next.hotkey import X11Grab, combination
    result = dict(display=os.environ.get('DISPLAY'), registration=False, conflict=False, released=False,
                  activation=False, kind='real libX11; two independent connections, no key injection')
    first = second = None
    try:
        _, name, modifiers = combination(text)
        first = X11Grab(); first.register(name, modifiers); result['registration'] = True
        second = X11Grab()
        try: second.register(name, modifiers)
        except Exception as error:
            result['conflict'] = 'Conflicto X11' in str(error); result['conflict_detail'] = str(error)
    except Exception as error: result['error'] = str(error)
    finally:
        if second: second.close()
        if first: first.close(); result['released'] = True
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--probe-x11', action='store_true', help='Briefly register/release an internal shortcut; never changes KDE bindings.')
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    combination = 'Ctrl+Alt+Shift+F12'
    probe = probe_x11(combination) if args.probe_x11 else {'kind':'not requested', 'registration':False}
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    if os.environ['QT_QPA_PLATFORM'] == 'xcb' and args.probe_x11 and not probe['registration']:
        failure = dict(qt_platform='xcb requested; UI not opened', probe=probe, qt_global_registered=False, activation_verified=False)
        (output/'evidence.json').write_text(json.dumps(failure, ensure_ascii=False, indent=2)+'\n')
        raise SystemExit('Cannot verify desktop registration: '+probe.get('error','unknown error'))
    authority = Path.home()/'.Xauthority'
    if authority.is_file(): os.environ.setdefault('XAUTHORITY', str(authority))
    profile = Path(tempfile.mkdtemp(prefix='next-integrations-review-'))
    for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
        value = profile/key; value.mkdir(mode=0o700); os.environ[key] = str(value)
    from PySide6.QtWidgets import QApplication, QGroupBox
    from naatik_next.integrations import write_action_script
    from naatik_next.storage import save_settings
    from naatik_next.app import Window
    app = QApplication.instance() or QApplication([])
    script = write_action_script(profile/'translator.sh', 'translator')
    save_settings(dict(setup_completed=True, translator_script=str(script), translator_shortcut=combination,
                       translator_shortcut_enabled=args.probe_x11))
    with patch('naatik_next.app.QTimer.singleShot'):
        window = Window(background=True, popup_only=True)
    window.resize(1100, 800); window.tabs.setCurrentWidget(window.integrations_tab)
    window.integration_action.setCurrentIndex(window.integration_action.findData('translator'))
    window.show(); app.processEvents()
    window.grab().save(str(output/'integrations.png'))
    details = next(g for g in window.findChildren(QGroupBox) if g.title()=='Detalles')
    details.setChecked(True); window.resize(1100, 1200)
    app.processEvents(); window.grab().save(str(output/'integrations-details.png'))
    evidence = dict(profile=str(profile), qt_platform=app.platformName(), probe=probe,
                    shortcut_requested=combination if args.probe_x11 else None,
                    qt_global_registered=bool(window.action_shortcuts['translator'].active),
                    qt_registration_status=window.action_shortcut_status['translator'].text(),
                    activation_verified=False, kde_configuration_changed=False, streamcontroller_changed=False,
                    script_generated=True, script=str(script))
    window.close(); app.processEvents()
    evidence['qt_released_on_close'] = not bool(window.action_shortcuts['translator'].active)
    (output/'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
