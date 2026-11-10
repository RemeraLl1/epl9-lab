"""Offline analysis of bounded camera TCP captures and application read timing.

Input: TShark tab-separated fields listed in the live Wi-Fi report. No sockets,
camera commands, packet payload export or firmware access. Outputs stay local.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import statistics

from epl9_wifi_bench import FILES, ROOT

CAMERA = '192.168.0.10'
RETRY_FIELDS = ('tcp.analysis.retransmission', 'tcp.analysis.fast_retransmission',
                'tcp.analysis.spurious_retransmission')


def distribution(values):
    values = sorted(values)
    if not values:
        return dict(n=0)
    return dict(n=len(values), median=statistics.median(values),
                p95=values[int((len(values)-1)*.95)], p99=values[int((len(values)-1)*.99)],
                maximum=values[-1], total=sum(values),
                at_least_20ms=sum(x >= 20 for x in values),
                at_least_50ms=sum(x >= 50 for x in values),
                at_least_100ms=sum(x >= 100 for x in values))


def merged_ranges(ranges):
    merged = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged


def analyze_stream(rows):
    def number(row, key):
        return int(row.get(key) or 0, 0)

    request = None
    for row in rows:
        if row.get('ip.dst') == CAMERA and row.get('tcp.payload'):
            payload = bytes.fromhex(row['tcp.payload'].replace(':', ''))
            if payload.startswith(b'GET '):
                request = payload.split(b' ')[1].decode('ascii', errors='replace')
                break
    name = request.rsplit('/', 1)[-1] if request else None
    expected_size = FILES.get(name)
    data = [row for row in rows if row.get('ip.src') == CAMERA and number(row, 'tcp.len') > 0]
    if not data:
        return dict(path=request, captured_camera_data_packets=0)
    ranges = merged_ranges((number(r, 'tcp.seq'), number(r, 'tcp.seq')+number(r, 'tcp.len')) for r in data)
    unique_bytes = sum(end-start for start, end in ranges)
    fins = [r for r in rows if r.get('ip.src') == CAMERA and number(r, 'tcp.flags') & 1]
    complete = bool(len(ranges) == 1 and fins and
                    any(number(r, 'tcp.seq')+number(r, 'tcp.len') == ranges[-1][1] for r in fins))
    header_bytes = unique_bytes-expected_size if expected_size is not None and complete else None
    if header_bytes is not None and not 0 < header_bytes < 4096:
        header_bytes, complete = None, False
    # Repeated exact sequence intervals must not create false pause samples.
    # Overlap, out-of-order and loss flags remain in the report for review.
    new_data, seen = [], set()
    for row in data:
        key = number(row, 'tcp.seq'), number(row, 'tcp.len')
        if key not in seen:
            new_data.append(row)
            seen.add(key)
    all_gaps, boundary_gaps, inside_gaps = [], [], []
    for previous, current in zip(new_data, new_data[1:]):
        gap = (float(current['frame.time_epoch'])-float(previous['frame.time_epoch']))*1000
        all_gaps.append(gap)
        if header_bytes is not None:
            body_end = number(previous, 'tcp.seq')+number(previous, 'tcp.len')-ranges[0][0]-header_bytes
            if 0 < body_end < expected_size:
                (boundary_gaps if body_end % 16384 == 0 else inside_gaps).append(gap)
    data_retries = [r for r in data if any(r.get(field) for field in RETRY_FIELDS)]
    control_retries = [r for r in rows if number(r, 'tcp.len') == 0 and any(r.get(field) for field in RETRY_FIELDS)]
    host_windows = [number(r, 'tcp.window_size') for r in rows
                    if r.get('ip.dst') == CAMERA and r.get('tcp.window_size')]
    flights = [number(r, 'tcp.analysis.bytes_in_flight') for r in data if r.get('tcp.analysis.bytes_in_flight')]
    event_counts = {field: sum(bool(r.get(field)) for r in rows) for field in (
        'tcp.analysis.duplicate_ack', 'tcp.analysis.window_full', 'tcp.analysis.zero_window',
        'tcp.analysis.lost_segment', 'tcp.analysis.out_of_order', 'tcp.analysis.ack_lost_segment')}
    first, last = float(data[0]['frame.time_epoch']), float(data[-1]['frame.time_epoch'])
    return dict(path=request, name=name, expected_file_bytes=expected_size,
                first_data_epoch=first, last_data_epoch=last, response_data_span_s=last-first,
                captured_camera_data_packets=len(data), captured_unique_response_bytes=unique_bytes,
                captured_response_seq_ranges=ranges, response_capture_complete=complete,
                inferred_header_bytes=header_bytes,
                data_retry_frames=len(data_retries), control_only_retry_frames=len(control_retries),
                duplicate_captured_payload_bytes=sum(number(r, 'tcp.len') for r in data)-unique_bytes,
                tcp_events=event_counts, packet_arrival_gap_ms=distribution(all_gaps),
                after_16k_boundary_gap_ms=distribution(boundary_gaps),
                other_body_packet_gap_ms=distribution(inside_gaps),
                tcp_payload_length_counts=dict(collections.Counter(number(r, 'tcp.len') for r in new_data)),
                host_advertised_window_min=min(host_windows) if host_windows else None,
                host_advertised_window_max=max(host_windows) if host_windows else None,
                tshark_bytes_in_flight_max=max(flights) if flights else None,
                timing_limit='PC receive timestamps include Wi-Fi/driver delivery effects; not internal ISC/SD timings')


def analyze_capture(path):
    groups = collections.defaultdict(list)
    with path.open(encoding='utf-8-sig', newline='') as source:
        for row in csv.DictReader(source, delimiter='\t'):
            if row.get('tcp.stream'):
                groups[row['tcp.stream']].append(row)
    return [dict(stream=int(key), **analyze_stream(rows)) for key, rows in groups.items()]


def app_trial(row, group):
    points = row['read_events']
    gaps = [(b[0]-a[0])*1000 for a, b in zip(points, points[1:])]
    return dict(group=group, name=row['name'], tag=row.get('tag'), read_size=row['read_size'],
                bytes=row['bytes'], elapsed_s=row['elapsed_s'], mib_s=row['mib_s'], mbps=row['mbps'],
                ttfb_ms=row['ttfb_s']*1000, read_gap_ms=distribution(gaps),
                valid=row['valid'], sha256=row['sha256'], sha1=row['sha1'],
                verified_against_card_reader=row['verified_against_card_reader'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('output must be a new directory under ignored local/')
    baseline = json.loads((args.session/'baseline/measurements.json').read_text())
    trials = [app_trial(t, 'baseline') for t in baseline['trials']]
    for group in ['client-read-size', 'mov-client-check']:
        trials.extend(app_trial(t, group) for t in json.loads((args.session/group/'measurements.json').read_text()))
    traces = {}
    for name in ['tcp-packets.tsv', 'client-check-packets.tsv']:
        traces[name] = analyze_capture(args.session/name)
    identity = {}
    for name in FILES:
        rows = [t for t in trials if t['name'] == name]
        identity[name] = dict(copies=len(rows), all_valid=all(t['valid'] for t in rows),
                              unique_sha256=sorted({t['sha256'] for t in rows}),
                              verified_against_card_reader=any(t['verified_against_card_reader'] for t in rows))
    evidence = {}
    for pattern in ['*.pcapng', '*packets.tsv']:
        for path in args.session.glob(pattern):
            evidence[path.name] = dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    report = dict(camera=CAMERA, camera_modified=False, app_trials=trials, captures=traces,
                  identity=identity, evidence=evidence,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    out.mkdir(parents=True)
    (out/'analysis.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    with (out/'transfers.csv').open('w', newline='', encoding='utf-8') as target:
        keys = ['group', 'name', 'tag', 'read_size', 'bytes', 'elapsed_s', 'mib_s', 'mbps', 'ttfb_ms', 'valid', 'sha256']
        writer = csv.DictWriter(target, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(trials)
    print(json.dumps(dict(out=str(out), trials=len(trials), bytes=sum(t['bytes'] for t in trials), identity=identity), indent=2))


if __name__ == '__main__':
    main()
