"""Summarize numeric capture stages; no OCR text/images are read or exported."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from naatik_next.storage import paths


def captures(events):
    by_trace = defaultdict(list)
    for event in events:
        if event.get('trace'):
            by_trace[event['trace']].append(event)
    result = []
    first_pid = set()
    for trace, items in sorted(by_trace.items(), key=lambda pair: min(x['at_ns'] for x in pair[1])):
        stages = {e['stage']: e['at_ns'] for e in items}
        if 'request' not in stages:
            continue
        begin = stages['request']
        pid = next(e['pid'] for e in items if e['stage'] == 'request')
        row = dict(trace=trace, pid=pid, scenario='first-in-process' if pid not in first_pid else 'successive')
        first_pid.add(pid)
        def delta(a, b):
            return round((stages[b] - stages[a]) / 1e6, 3) if a in stages and b in stages else None
        for key, a, b in [('total_ms','request','clipboard'),
                          ('selector_prepare_ms','selector_prepare','selector_ready'),
                          ('selection_window_ms','selection_begin','selection_end'),
                          ('capture_complete_ms','request','capture_complete'),
                          ('drag_ms','selection_user_begin','selection_user_end'),
                          ('inference_ms','inference_begin','inference_end')]:
            row[key] = delta(a, b)
        starts = [e['at_ns'] for e in events if e['pid'] == pid and e['stage'] == 'process_start']
        row['process_to_request_ms'] = round((begin - min(starts)) / 1e6, 3) if starts else None
        # Preparation can start before the first request and overlaps the selector.
        ready = next((e for e in items if e['stage'] == 'engine_ready' and e['pid'] == pid), None)
        preparations = [e['at_ns'] for e in events if e['pid'] == pid and e['stage'] == 'engine_prepare_begin'
                        and e['at_ns'] <= (ready['at_ns'] if ready else begin)]
        row['engine_prepare_ms'] = round((ready['at_ns'] - max(preparations))/1e6, 3) if ready and preparations else None
        row['clipboard_observed'] = 'clipboard' in stages
        row['state'] = ('interrupted' if 'interrupted' in stages else 'cancelled' if 'cancelled' in stages
                        else 'failed' if 'failed' in stages else 'copied' if 'clipboard' in stages else 'incomplete')
        if row['state'] != 'copied':
            row['total_ms'] = None
        result.append(row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?', type=Path)
    parser.add_argument('--last-process', action='store_true',
                        help='Resumir solo el propietario de la petición más reciente; separar series antiguas.')
    args = parser.parse_args()
    target = args.file or paths()['state'] / 'capture-timings.jsonl'
    rows = captures([json.loads(line) for line in target.read_text().splitlines() if line.strip()])
    if args.last_process and rows:
        owner = rows[-1]['pid']
        rows = [row for row in rows if row['pid'] == owner]
    print(json.dumps(rows, indent=2))
    print('\nSummary: median [min, max] ms; overlapping stages must not be added.')
    for scenario in ('first-in-process', 'successive'):
        group = [row for row in rows if row['scenario'] == scenario and row['state'] == 'copied']
        print(scenario, 'n=' + str(len(group)))
        for key in ('total_ms','selector_prepare_ms','selection_window_ms','drag_ms','engine_prepare_ms','inference_ms'):
            values = [row[key] for row in group if row.get(key) is not None]
            if values:
                print(' ', key, f'{statistics.median(values):.1f} [{min(values):.1f}, {max(values):.1f}]')
    print('selection_window includes Spectacle startup, thinking and dragging; drag is sampled at ~10 ms. Missing values are unmeasured.')


if __name__ == '__main__':
    main()
