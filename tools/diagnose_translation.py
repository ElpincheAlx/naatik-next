"""Explicit local inference diagnostic. Prints only the texts supplied by the caller.

No OCR, capture, dictionary lookup, preference writes, or model downloads.
Use --official-python to opt into the official API in an existing Python environment.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys


def offline():
    def blocked(*args, **kwargs):
        raise RuntimeError('Network disabled in translation diagnostic')
    socket.getaddrinfo = blocked
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'


def fingerprint(pkg):
    base = pkg.package_path
    files = [base / 'metadata.json', base / 'sentencepiece.model', base / 'bpe.model']
    files += sorted((base / 'model').rglob('*'))
    hashes = {}
    for file in files:
        if file.is_file():
            digest = hashlib.sha256()
            with file.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            hashes[str(file.relative_to(base))] = digest.hexdigest()
    return {'path': str(base), 'version': pkg.package_version, 'files_sha256': hashes}


def versions():
    return {n: importlib.metadata.version(n) for n in ['argostranslate', 'ctranslate2', 'sentencepiece']}


def adapter_report(texts):
    from naatik_next.translation import Argos

    class TracedArgos(Argos):
        tracing = False

        def _translate_edge(self, text, key):
            if not self.tracing:
                return super()._translate_edge(text, key)
            model = self.models[key]
            record = {'route': list(key), 'input': text,
                      'target_prefix': self.packages[key].target_prefix}

            class Observer:
                def translate_batch(self, tokens, **kwargs):
                    record['input_tokens'] = tokens
                    record['inference_options'] = kwargs
                    result = model.translate_batch(tokens, **kwargs)
                    record['output_tokens'] = [r.hypotheses for r in result]
                    return result

            self.models[key] = Observer()
            try:
                result = super()._translate_edge(text, key)
                record['output'] = result
                self.stages.append(record)
                return result
            finally:
                self.models[key] = model

    engine = TracedArgos()
    discovery = engine.discover()
    engine.tracing = True
    packages = {f'{a}→{b}': fingerprint(p) for (a, b), p in engine.packages.items()}
    cases = []
    for text in texts:
        for route in [['ja', 'en'], ['ja', 'en', 'es']]:
            if route not in discovery['routes']:
                continue
            engine.stages = []
            result = engine.translate(text, route)
            cases.append({'input': text, **result, 'stages': engine.stages})
    return {'versions': versions(), 'packages': packages, 'discovery': discovery, 'cases': cases}


def official_report(texts):
    # Official Stanza wrapper defaults to refreshing resources.json. Disable that
    # explicitly; keep the installed tokenizer/models and the official algorithms.
    import stanza
    constructor = stanza.Pipeline

    def local_pipeline(*args, **kwargs):
        kwargs['download_method'] = None
        return constructor(*args, **kwargs)

    stanza.Pipeline = local_pipeline
    from argostranslate import package, settings, translate
    import ctranslate2

    installed = {(p.from_code, p.to_code): p for p in package.get_installed_packages()
                 if p.type == 'translate'}
    report = {'versions': versions(), 'packages': {f'{a}→{b}': fingerprint(p)
              for (a, b), p in installed.items()},
              'stanza_download_method': 'NONE', 'cases': [],
              'beam_size': settings.beam_size, 'device': settings.device}
    for text in texts:
        for route in [['ja', 'en'], ['ja', 'en', 'es']]:
            if not all((a, b) in installed for a, b in zip(route, route[1:])):
                continue
            case = {'input': text, 'route': route, 'stages': []}
            value = text
            try:
                for a, b in zip(route, route[1:]):
                    output = translate.translate(value, a, b)
                    pkg = installed[a, b]
                    case['stages'].append({'route': [a, b], 'input': value,
                                           'input_tokens': pkg.tokenizer.encode(value), 'output': output})
                    value = output
                case['text'] = translate.translate(text, route[0], route[-1])
            except Exception as e:
                case['error'] = f'{type(e).__name__}: {e}'
            report['cases'].append(case)
    # Also exercise the unmodified official tokenization/inference/decoding routine,
    # with an explicitly single-line segmenter to match the Next adapter's unit.
    class OneLine:
        def split_sentences(self, text):
            return [text]
    pkg = installed.get(('ja', 'en'))
    if pkg:
        model = ctranslate2.Translator(str(pkg.package_path / 'model'), device='cpu',
                                      intra_threads=2, inter_threads=1)
        report['official_single_line'] = [{'input': text, 'hypotheses': [
            {'text': h.value, 'score': h.score} for h in translate.apply_packaged_translation(
                pkg, text, model, OneLine(), 1)]} for text in texts]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', action='append', help='Explicit input; repeat to compare contexts')
    parser.add_argument('--official-python', help='Existing Python executable with full Argos dependencies')
    parser.add_argument('--official-worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    texts = args.text or ['日本', '日本語', '日本に行きます。']
    offline()
    if args.official_worker:
        report = official_report(texts)
    else:
        report = {'adapter': adapter_report(texts)}
        if args.official_python:
            command = [args.official_python, str(Path(__file__).resolve()), '--official-worker']
            for text in texts:
                command += ['--text', text]
            env = dict(os.environ, ARGOS_DEVICE_TYPE='cpu', ARGOS_CHUNK_TYPE='STANZA',
                       ARGOS_INTER_THREADS='1', ARGOS_INTRA_THREADS='2')
            try:
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=120)
                if result.returncode:
                    report['official_error'] = result.stderr[-3000:]
                else:
                    report['official'] = json.loads(result.stdout)
                    report['same_package_files'] = report['adapter']['packages'] == report['official']['packages']
                    report['same_outputs'] = [(c['input'], c['route'], c['text']) for c in report['adapter']['cases']] == [
                        (c['input'], c['route'], c.get('text')) for c in report['official']['cases']]
            except (OSError, subprocess.TimeoutExpired, ValueError) as e:
                report['official_error'] = str(e)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
