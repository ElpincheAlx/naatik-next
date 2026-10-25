"""Next-owned MeCab/UniDic analysis. No OCR, HTTP, grammar/JLPT guesses or translation."""
from .i18n import t
import json
from pathlib import Path
import shlex
import signal
import sys
from .ocr import stop


def hiragana(value):
    return ''.join(chr(ord(c)-0x60) if '\u30a1' <= c <= '\u30f6' else c for c in value)


class Analyzer:
    def __init__(self):
        import fugashi
        import unidic_lite
        # Explicit dictionary and empty system rc: never discover global MeCab config.
        self.tagger = fugashi.Tagger('-r /dev/null -d ' + shlex.quote(unidic_lite.DICDIR))

    def analyze(self, text):
        if not text.strip() or len(text) > 10000:
            raise ValueError(t('Escribe entre 1 y 10 000 caracteres.'))
        tokens, cursor = [], 0
        for word in self.tagger(text):
            if len(tokens) >= 1000:
                raise ValueError(t('Máximo 1 000 palabras por análisis; divide la frase.'))
            surface, feature = word.surface, word.feature
            start = text.find(surface, cursor)
            if start < cursor:
                raise ValueError(t('No se pudo asociar el análisis al texto original.'))
            reading = getattr(feature, 'kana', '') or ''
            if word.is_unk or reading == '*':
                reading = ''
            base = getattr(feature, 'orthBase', '') or surface
            if base == '*': base = surface
            tokens.append(dict(surface=surface, base=base, reading=hiragana(reading),
                               pos=getattr(feature, 'pos1', '') or '', start=start, end=start+len(surface),
                               unknown=bool(word.is_unk)))
            cursor = start + len(surface)
        return dict(sentence=text, tokens=tokens, resource='Fugashi 1.5.2 / UniDic Lite 1.0.8 (UniDic 2.1.2)')


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    analyzer = None
    for line in sys.stdin:
        try:
            request = json.loads(line)
            from .i18n import set_language
            import os
            code = request.get('ui_language', os.environ.get('NAATIK_NEXT_UI_LANGUAGE', 'es'))
            set_language(code)
            os.environ['NAATIK_NEXT_UI_LANGUAGE'] = code
            if request['action'] != 'phrase': raise ValueError(t('Acción desconocida.'))
            if analyzer is None: analyzer = Analyzer()
            result = analyzer.analyze(request['text'])
            print(json.dumps({'result': {'popup_generation': request['popup_generation'], 'value': result}}, ensure_ascii=False), flush=True)
        except Exception as error:
            print(json.dumps({'error': (t('Análisis no disponible: ') + f'{error}' + t('. Prepara los recursos lingüísticos de Next.'))}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
