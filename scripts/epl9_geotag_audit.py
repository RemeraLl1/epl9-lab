"""Offline audit of explicit BLE/location experiment records. No device/network IO."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

STATUSES = {'fix', 'null', 'timeout', 'error', 'cancelled', 'interrupted'}

def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be finite and nonnegative')
    return value

def text(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError(f'{name} must be a nonempty string')
    return value

def stats(values):
    values = sorted(values)
    return {'n': len(values), 'min': values[0] if values else None,
            'median': (values[(len(values)-1)//2] + values[len(values)//2])/2 if values else None,
            'max': values[-1] if values else None}

def audit(data, max_age_ms=2000, max_accuracy_m=25):
    """Thresholds are experiment choices, not promises of shutter geotag accuracy."""
    number(max_age_ms, 'max_age_ms'); number(max_accuracy_m, 'max_accuracy_m')
    if data.get('schema') != 1 or data.get('units') != 'elapsed_realtime_ms':
        raise ValueError('schema 1 and elapsed_realtime_ms units required')
    events, requests = data.get('events'), data.get('requests')
    if not isinstance(events, list) or not isinstance(requests, list):
        raise ValueError('events and requests must be lists')
    event_map = {}
    for e in events:
        key = (text(e.get('boot'), 'event boot'), text(e.get('event_id'), 'event id'))
        if key in event_map:
            raise ValueError('duplicate event identity; deduplicate notifications explicitly')
        number(e.get('received_ms'), 'received_ms')
        event_map[key] = e
    ground = data.get('ground_truth_shots')
    mapped = set()
    if ground is not None:
        if not isinstance(ground, list) or len(set(ground)) != len(ground):
            raise ValueError('ground truth must contain unique shot IDs')
        for shot in ground: text(shot, 'shot ID')
        for e in events:
            shot = e.get('shot_id')
            if shot is not None:
                if shot not in ground or shot in mapped:
                    raise ValueError('shot association must be explicitly unique and in ground truth')
                mapped.add(shot)
    elif any(e.get('shot_id') is not None for e in events):
        raise ValueError('shot association requires ground truth')
    counts, seen, attached, good_events = Counter(), set(), set(), set()
    latency, ages, offsets, rejection_counts = [], [], [], Counter()
    for r in requests:
        rid = text(r.get('request_id'), 'request ID')
        if rid in seen: raise ValueError('duplicate request ID')
        seen.add(rid)
        key = (text(r.get('boot'), 'request boot'), text(r.get('event_id'), 'request event'))
        if key not in event_map: raise ValueError('unknown event or mismatched boot')
        attached.add(key)
        received = event_map[key]['received_ms']
        start, end = number(r.get('start_ms'), 'start_ms'), number(r.get('end_ms'), 'end_ms')
        if not received <= start <= end: raise ValueError('event/start/end ordering invalid')
        status = r.get('status')
        if status not in STATUSES: raise ValueError('unknown terminal status')
        counts[status] += 1
        latency.append(end-start)
        if status != 'fix':
            if any(k in r for k in ['fix_ms', 'accuracy_m', 'fix_boot']):
                raise ValueError('non-fix record must not contain fix fields')
            continue
        fix = number(r.get('fix_ms'), 'fix_ms')
        accuracy = number(r.get('accuracy_m'), 'accuracy_m')
        if r.get('fix_boot') != key[0] or fix > end:
            raise ValueError('location time belongs to another boot or the future')
        age = end-fix
        ages.append(age)
        offsets.append(fix-received)
        rejected = False
        for reason, condition in [('stale', age > max_age_ms), ('inaccurate', accuracy > max_accuracy_m)]:
            if condition: rejection_counts[reason] += 1; rejected = True
        if not rejected: good_events.add(key); counts['usable_fix'] += 1
    usable_shots = {event_map[k].get('shot_id') for k in good_events} - {None}
    total = len(requests)
    return {'schema': 1, 'scope': 'offline records only; no proof of E-PL9 shutter events or EXIF writes',
            'thresholds': {'max_fix_age_at_callback_ms': max_age_ms, 'max_accuracy_m': max_accuracy_m},
            'events': len(events), 'requests': total, 'outcomes': dict(counts),
            'null_fraction_of_requests': counts['null']/total if total else None,
            'events_without_request': len(event_map.keys()-attached),
            'events_with_usable_fix': len(good_events), 'fix_rejections': dict(rejection_counts),
            'request_latency_ms': stats(latency), 'fix_age_at_callback_ms': stats(ages),
            'fix_offset_from_ble_receipt_ms': stats(offsets),
            'ground_truth_shots': len(ground) if ground is not None else None,
            'shots_without_associated_event': len(ground)-len(mapped) if ground is not None else None,
            'shots_without_usable_fix': len(ground)-len(usable_shots) if ground is not None else None,
            'limits': ['BLE receipt is not exposure time', 'No inferred shot matching',
                       'Usable means selected metadata thresholds, not guaranteed location at shutter',
                       'No battery or missed-shot claim without an independent physical experiment']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--max-age-ms', type=float, default=2000)
    p.add_argument('--max-accuracy-m', type=float, default=25)
    args=p.parse_args()
    print(json.dumps(audit(json.loads(args.input.read_text()),args.max_age_ms,args.max_accuracy_m),indent=2,allow_nan=False))

if __name__ == '__main__': main()
