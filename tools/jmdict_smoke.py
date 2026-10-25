"""Real local JMdict import, lookup and full row roundtrip, always in a temporary DB."""
import hashlib
import json
from pathlib import Path
import tempfile
import time
import zipfile
from naatik_next.storage import Store, UserError
from naatik_next.dictionary_content import render_results


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dictionary', required=True, type=Path, help='Explicit JMdict v3 ZIP fixture; never discovered automatically')
    source = parser.parse_args().dictionary.resolve()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='naatik-jmdict-smoke-') as tmp:
        store = Store(Path(tmp) / 'dictionary.sqlite')
        result = store.import_zip(source)
        rows = store.lookup('日本')
        assert len(rows) == 4
        html = render_results(rows)
        assert all(text in html for text in ['Japan', 'にほん', 'にっぽん', '<table', 'Japan is to the east of China.'])
        # Compare every original term row, not just flattened meanings.
        cursor = iter(store.conn.execute('SELECT source_row FROM terms ORDER BY rowid'))
        compared = 0
        with zipfile.ZipFile(source) as archive:
            for bank in sorted(n for n in archive.namelist() if n.startswith('term_bank_')):
                for original in json.loads(archive.read(bank)):
                    assert json.loads(next(cursor)[0]) == original
                    compared += 1
        assert next(cursor, None) is None
        try:
            store.import_zip(source)
            raise AssertionError('Duplicate accepted')
        except UserError as e:
            assert 'SHA-256' in str(e)
        ident = store.list()[0]['id']
        store.update(ident, False, 20)
        assert not store.lookup('日本')
        store.update(ident, True, 20)
        assert store.lookup('にほん')
        store.close()
        store = Store(Path(tmp) / 'dictionary.sqlite')
        assert store.list()[0]['priority'] == 20
        store.remove(ident)
        assert not store.lookup('日本')
        store.close()
    assert before == hashlib.sha256(source.read_bytes()).hexdigest()
    print(json.dumps({'import': result, 'rows_compared_losslessly': compared,
        '日本': [{'reading': r['reading'], 'meanings': json.loads(r['meanings'])} for r in rows],
        'duplicate_activation_priority_reopen_remove': 'passed', 'original_sha256': before,
        'original_unchanged': True, 'seconds': round(time.monotonic() - start, 2)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
