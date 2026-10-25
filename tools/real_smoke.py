"""Real local inference; does not assert that GUI capture has been validated."""
import json
from pathlib import Path
import tempfile
from PIL import Image, ImageDraw, ImageFont
from naatik_next.ocr import detect, Tesseract
from naatik_next.translation import Argos

engines = detect()
print(json.dumps(engines, ensure_ascii=False, indent=2))
assert engines[0]['status'] == 'listo', engines[0]
with tempfile.TemporaryDirectory(prefix='naatik-real-smoke-') as tmp:
    p = Path(tmp) / 'english.png'
    image = Image.new('RGB', (900, 160), 'white')
    ImageDraw.Draw(image).text((20, 25), 'Hello world', font=ImageFont.load_default(size=70), fill='black')
    image.save(p)
    recognized = Tesseract().recognize(str(p), 'eng')
    print('REAL OCR:', repr(recognized))
    assert 'hello' in recognized.lower() and 'world' in recognized.lower()
    argos = Argos()
    discovery = argos.discover()
    print('REAL ARGOS ROUTES:', discovery)
    assert ['en', 'es'] in discovery['routes']
    direct = argos.translate(recognized, ['en', 'es'])
    print('REAL OCR → TRANSLATION:', direct)
    assert direct['text'].strip()
    if ['ja', 'en', 'es'] in discovery['routes']:
        print('REAL ARGOS PIVOT:', argos.translate('こんにちは。', ['ja', 'en', 'es']))
