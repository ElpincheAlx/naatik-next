"""Private line-delimited JSON over managed process pipes; never a service."""
from .i18n import t
import json
import logging
import signal
import sys
from .storage import Store, paths, Cancelled
from .ocr import stop
from . import timings


def emit(kind, value):
    sys.stdout.write(json.dumps({kind: value}, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    logging.basicConfig(filename=paths()['state'] / 'naatik-next.log', level=logging.INFO)
    argos = None
    for line in sys.stdin:
        try:
            request = json.loads(line)
            from .i18n import set_language
            import os
            code = request.get('ui_language', os.environ.get('NAATIK_NEXT_UI_LANGUAGE', 'es'))
            set_language(code)
            os.environ['NAATIK_NEXT_UI_LANGUAGE'] = code
            if request.get('timings') is True:
                timings.enable()
            action = request['action']
            if action == 'anki':
                from .anki import execute
                result = execute(request)
            elif action == 'prepare_model':
                from .resources import prepare_model
                result = prepare_model(progress=lambda value: emit('progress', value))
            elif action == 'prepare_runtime':
                from pathlib import Path
                from .ocr import run
                result = run(['bash', str(Path(__file__).resolve().parent.parent / 'tools/install.sh'), '--manga-cpu'], 900)
            elif action in ('translation_status','translation_catalogue','translation_details', 'translation_download',
                             'translation_validate','translation_runtime','prepare_base_runtime'):
                from . import translation_setup as setup
                progress=lambda value: emit('progress',value)
                if action == 'translation_status': result=setup.status()
                elif action == 'translation_catalogue': result=setup.catalogue(online=True,progress=progress)
                elif action == 'translation_details': result=setup.details(request['keys'],request['catalogue_sha256'],progress=progress)
                elif action == 'translation_download': result=setup.install_models(request['keys'],request['catalogue_sha256'],progress=progress,preserve_installed=request.get('preserve_installed',False),download_keys=request.get('download_keys'))
                elif action == 'translation_validate': result=setup.validate(request['route'])
                else:
                    from .translation_runtime import prepare,prepare_base
                    result=(prepare_base if action=='prepare_base_runtime' else prepare)(progress)
            elif action == 'detect':
                from .ocr import detect
                result = detect()
            elif action == 'prepare_ocr':
                timings.event('engine_prepare_begin', request.get('trace'))
                from .ocr import Tesseract
                if request['engine'] != 'tesseract':
                    result = dict(id=request['engine'], name=request['engine'], status='incompatible', languages=[], detail=t('Motor sin adaptador funcional.'))
                else:
                    result = Tesseract().detect(probe=False)
                result = [dict(result, preparation=request.get('preparation'))]
                timings.event('engine_ready', request.get('trace'))
            elif action == 'ocr':
                from .ocr import Tesseract
                if request['engine'] != 'tesseract':
                    raise ValueError(t('Motor sin integración funcional; elige Tesseract.'))
                timings.event('inference_begin', request.get('trace'))
                result = Tesseract().recognize(request['image'], request['language'])
                timings.event('inference_end', request.get('trace'))
            elif action == 'capture':
                from .ocr import capture
                result = capture(request.get('trace'))
            elif action == 'prepare_phrase_runtime':
                from .resources import prepare_phrase_runtime
                result = prepare_phrase_runtime()
            elif action == 'install_argos':
                from .translation import install_package
                result = install_package(request['path'])
                argos = None
            elif action in ('routes', 'translate'):
                from .translation import Argos
                if argos is None:
                    argos = Argos()
                result = argos.discover() if action == 'routes' else argos.translate(request['text'], request['route'])
            elif action in ('import', 'inspect_dictionaries', 'lookup', 'lookup_selection', 'popup_lookup', 'remove'):
                store = Store()
                try:
                    if action == 'import':
                        result = store.import_zip(request['path'], progress=lambda x: emit('progress', x), expected_digest=request.get('digest'))
                    elif action == 'inspect_dictionaries':
                        result = []
                        seen_digests, seen_titles = set(), set()
                        for path in request['paths']:
                            try:
                                entry = store.inspect_zip(path, progress=lambda x: emit('progress', x))
                                key = (entry['title'],entry['revision'])
                                if entry['digest'] in seen_digests or key in seen_titles:
                                    entry['duplicate'] = t('repetido dentro de la selección')
                                seen_digests.add(entry['digest'])
                                seen_titles.add(key)
                                result.append(entry)
                            except Exception as e:
                                if isinstance(e, Cancelled):
                                    raise
                                result.append(dict(getattr(e,'preview',{}),path=path,error=str(e)))
                    elif action == 'remove':
                        store.remove(request['id'])
                        result = {'removed': request['id']}
                    elif action == 'popup_lookup':
                        results = store.lookup(request['term'], exact=True)
                        if not results and request['surface'] != request['term']:
                            results = store.lookup(request['surface'], exact=True)
                        result = {'active': sum(bool(d['enabled']) for d in store.list()), 'results': results}
                    elif action == 'lookup_selection':
                        result = {'generation': request['generation'], 'term': request['term'],
                                  'active': sum(bool(d['enabled']) for d in store.list()),
                                  'results': store.lookup(request['term'], exact=True)}
                    else:
                        result = store.lookup(request['term'])
                finally:
                    store.close()
            else:
                raise ValueError(t('Operación desconocida.'))
            if request['action'] == 'ocr' and 'generation' in request:
                result = {'generation': request['generation'], 'text': result}
            if 'popup_generation' in request:
                result = {'popup_generation': request['popup_generation'], 'value': result}
            emit('result', result)
        except Cancelled as e:
            emit('error', str(e))
            break  # A cancelled resident worker must exit rather than wait for another line.
        except Exception as e:
            if request.get('action') != 'anki':
                logging.exception('Worker operation failed')
            emit('error', str(e))
        if '--persistent' not in sys.argv:
            break


if __name__ == '__main__':
    main()
