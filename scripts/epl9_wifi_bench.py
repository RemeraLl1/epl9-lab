"""Bounded read-only E-PL9 HTTP measurements. Never sends vendor write commands.

Uses direct sockets (no proxy), a fixed request allowlist and new ignored local
output directories. Originals must be supplied from a card reader, never USB
Storage through the camera. No camera access occurs on import or in unit tests.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import re
import statistics
import time

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'PB020001.ORF': 14692005,
    'PB020001.JPG': 3249056,
    'PB020002.MOV': 8105416,
}
METADATA = (
    '/get_commandlist.cgi', '/get_connectmode.cgi',
    '/get_imglist.cgi?DIR=/DCIM', '/get_imglist.cgi?DIR=/DCIM/100OLYMP',
)
MEDIA = {f'/DCIM/100OLYMP/{name}': size for name, size in FILES.items()}
USER_AGENT = 'OI.Share v2'
OWNER_HASH_TEXT = '2adb950f5ae41bf92fa01f921fb8ca06056ee8094e'


def hashes(body):
    return dict(sha1=hashlib.sha1(body).hexdigest(), sha256=hashlib.sha256(body).hexdigest())


def validate_target(path):
    if path not in MEDIA and path not in METADATA:
        raise ValueError('request outside the fixed read-only allowlist')


def classify(status, headers, body, *, expected_size=None, byte_range=None,
             reference=None, complete=True, error=None):
    """Reject ignored/wrong Range responses and truncated originals explicitly."""
    headers = {k.lower(): v for k, v in headers.items()}
    issues = []
    if error:
        issues.append(error)
    if not complete:
        issues.append('body_incomplete_or_capped')
    if headers.get('content-encoding', 'identity').lower() != 'identity':
        issues.append('unexpected_content_encoding')
    length = headers.get('content-length')
    if length is not None:
        try:
            if int(length) != len(body):
                issues.append('content_length_mismatch')
        except ValueError:
            issues.append('invalid_content_length')
    if byte_range is None:
        if status != 200:
            issues.append('expected_status_200')
        if expected_size is not None and len(body) != expected_size:
            issues.append('original_size_mismatch')
        if reference is not None and hashes(body)['sha256'] != hashes(reference)['sha256']:
            issues.append('reference_hash_mismatch')
    else:
        start, end = byte_range
        if status != 206:
            issues.append('range_ignored' if status == 200 else 'range_not_206')
        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', headers.get('content-range', ''))
        if not match or tuple(map(int, match.groups())) != (start, end, expected_size):
            issues.append('content_range_mismatch')
        if len(body) != end-start+1:
            issues.append('range_size_mismatch')
        if reference is not None and body != reference[start:end+1]:
            issues.append('range_reference_mismatch')
    return dict(valid=not issues, issues=issues, **hashes(body))


def fetch(host, port, path, *, read_size=65536, byte_range=None,
          connection_factory=http.client.HTTPConnection, max_seconds=180):
    validate_target(path)
    if not 1024 <= read_size <= 1024*1024:
        raise ValueError('read size outside 1 KiB..1 MiB')
    if byte_range is not None and (path not in MEDIA or
            not 0 <= byte_range[0] <= byte_range[1] < MEDIA[path]):
        raise ValueError('invalid media byte range')
    headers = {'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity', 'Connection': 'close'}
    if byte_range is not None:
        headers['Range'] = f'bytes={byte_range[0]}-{byte_range[1]}'
    # A Range-ignoring camera must not silently transfer a whole file per range.
    limit = (byte_range[1]-byte_range[0]+1 if byte_range else MEDIA.get(path, 1024*1024))
    cap = limit+1
    start = time.perf_counter()
    points, parts, total = [], [], 0
    connected = requested = received_headers = first_byte = ended = None
    status, response_headers, error, complete = None, {}, None, False
    conn = connection_factory(host, port, timeout=5)
    try:
        conn.connect()
        connected = time.perf_counter()
        if conn.sock:
            conn.sock.settimeout(20)
        conn.request('GET', path, headers=headers)
        requested = time.perf_counter()
        response = conn.getresponse()
        received_headers = time.perf_counter()
        status = response.status
        response_headers = dict(response.getheaders())
        while total < cap:
            if time.perf_counter()-start > max_seconds:
                raise TimeoutError('per-request deadline exceeded')
            chunk = response.read1(min(read_size, cap-total))
            now = time.perf_counter()
            if not chunk:
                complete = True
                break
            if first_byte is None:
                first_byte = now
            parts.append(chunk)
            total += len(chunk)
            points.append([round(now-start, 6), len(chunk), total])
        ended = time.perf_counter()
    except (OSError, http.client.HTTPException, TimeoutError) as exc:
        ended = time.perf_counter()
        error = f'{type(exc).__name__}: {exc}'
    finally:
        conn.close()
    # Hashing and disk writes occur after the network timer.
    body = b''.join(parts)
    elapsed = ended-start
    report = dict(path=path, requested_range=byte_range, status=status, headers=response_headers,
                  read_size=read_size, bytes=len(body), complete=complete, error=error,
                  elapsed_s=elapsed, started_perf_s=start, finished_perf_s=ended,
                  connect_s=None if connected is None else connected-start,
                  headers_s=None if received_headers is None else received_headers-start,
                  ttfb_s=None if first_byte is None else first_byte-start,
                  body_wait_s=None if received_headers is None else ended-received_headers,
                  request_sent_s=None if requested is None else requested-start,
                  mib_s=len(body)/1048576/elapsed if elapsed else None,
                  mbps=len(body)*8/1000000/elapsed if elapsed else None,
                  read_events=points,
                  read_events_note='application read completion times; not TCP packet or camera block timestamps')
    return report, body


def run(args):
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('output must be a new directory under ignored local/')
    if not 1 <= args.repeats <= 5 or not 1 <= args.parallel <= 3:
        raise ValueError('repeats 1..5 and parallel 1..3 required')
    out.mkdir(parents=True)
    # Manifest remains available even if the connection fails.
    report = dict(started_utc=datetime.now(timezone.utc).isoformat(), model='Olympus PEN E-PL9',
                  displayed_version='1.1 (owner report)', protocol_version_is_not_firmware=True,
                  host='192.168.0.10', user_agent=USER_AGENT, read_only=True,
                  owner_hash_text=OWNER_HASH_TEXT, owner_hash_text_length=len(OWNER_HASH_TEXT),
                  owner_hash_note='42 hex characters: neither standard SHA-1 nor SHA-256; not an integrity reference',
                  original_references={}, metadata=[], trials=[], parallel_groups=[])

    def save_manifest():
        (out/'measurements.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')

    save_manifest()
    for index, path in enumerate(METADATA):
        result, body = fetch('192.168.0.10', 80, path, max_seconds=30)
        result.update(classify(result['status'], result['headers'], body,
                               complete=result['complete'], error=result['error']))
        report['metadata'].append(result)
        (out/f'metadata-{index}.body').write_bytes(body)
        save_manifest()
        if not result['valid']:
            raise RuntimeError('metadata request failed; see local measurements.json')
    references = {}
    if args.original_root:
        for name, size in FILES.items():
            path = args.original_root/name
            body = path.read_bytes()
            if len(body) != size:
                raise ValueError(f'card-reader original size mismatch: {name}')
            references[name] = body
            report['original_references'][name] = dict(bytes=size, **hashes(body))
        save_manifest()

    def trial(name, tag, byte_range=None):
        result, body = fetch('192.168.0.10', 80, f'/DCIM/100OLYMP/{name}',
                             read_size=args.read_size, byte_range=byte_range)
        result.update(classify(result['status'], result['headers'], body,
                               expected_size=FILES[name], byte_range=byte_range,
                               reference=references.get(name), complete=result['complete'], error=result['error']))
        result.update(name=name, tag=tag, verified_against_card_reader=name in report['original_references'])
        result['reference_source'] = ('card_reader' if name in report['original_references'] else
                                      'first_complete_camera_copy' if name in references else None)
        suffix = '.range' if byte_range else ''
        destination = out/f'{tag}-{name}{suffix}'
        if not result['valid']:
            destination = destination.with_name(destination.name+'.incomplete')
        destination.write_bytes(body)
        return result, body

    for repeat in range(args.repeats):
        for name in FILES:
            result, body = trial(name, f'serial-{repeat}')
            report['trials'].append(result)
            save_manifest()
            if not result['valid']:
                raise RuntimeError('original transfer failed; stopping to preserve evidence')
            # Camera-copy consistency remains distinct from card-reader identity.
            references.setdefault(name, body)
    if args.range_probe:
        for name in FILES:
            for index, interval in enumerate([(0, 65535), (65536, 131071)]):
                result, _ = trial(name, f'range-{index}', interval)
                report['trials'].append(result)
                save_manifest()
    if args.parallel > 1:
        # Different whole files only. Never pretends an ignored Range is partial.
        names = ['PB020001.ORF', 'PB020002.MOV', 'PB020001.JPG'][:args.parallel]
        for repeat in range(args.repeats):
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=args.parallel) as pool:
                results = list(pool.map(lambda name: trial(name, f'parallel-{repeat}'), names))
            elapsed = time.perf_counter()-started
            # Group wall time includes scheduling, validation/hashing and disk output;
            # individual network-only times are recorded in the member trials.
            group = dict(repeat=repeat, names=names, wall_s_including_local_processing=elapsed,
                         all_valid=all(r['valid'] for r, _ in results),
                         network_span_s=max(r['finished_perf_s'] for r, _ in results)
                                        - min(r['started_perf_s'] for r, _ in results),
                         bytes=sum(r['bytes'] for r, _ in results))
            report['parallel_groups'].append(group)
            report['trials'].extend(r for r, _ in results)
            save_manifest()
            if not group['all_valid']:
                raise RuntimeError('parallel transfer failed; stopping')
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    report['serial_summary'] = {}
    for name in FILES:
        rows = [r for r in report['trials'] if r['name'] == name and
                r['tag'].startswith('serial-') and r['valid']]
        report['serial_summary'][name] = dict(
            valid_trials=len(rows), median_elapsed_s=statistics.median(r['elapsed_s'] for r in rows),
            median_mib_s=statistics.median(r['mib_s'] for r in rows),
            all_sha256_equal=len({r['sha256'] for r in rows}) == 1)
    for group in report['parallel_groups']:
        if group['all_valid']:
            serial_seconds = sum(r['elapsed_s'] for r in report['trials'] if
                                 r['tag'] == f"serial-{group['repeat']}" and r['name'] in group['names'])
            group['serial_same_files_s'] = serial_seconds
            group['aggregate_mbps'] = group['bytes']*8/1000000/group['network_span_s']
            group['paired_wall_speedup'] = serial_seconds/group['network_span_s']
    report['comparison_limits'] = [
        'All serial trials precede parallel trials; storage cache, RF drift and camera state can confound comparisons.',
        'Parallel comparisons concern different whole files, not faster transfer of one original.',
        'Read events are application observations, not TCP segment sizes or firmware timings.',
    ]
    save_manifest()
    print(json.dumps(dict(out=str(out), trials=len(report['trials']),
                          card_reader_references=len(report['original_references'])), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--original-root', type=Path, help='directory of the three originals copied using a card reader')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--read-size', type=int, default=65536)
    parser.add_argument('--parallel', type=int, default=1, help='opt-in different whole files, max 3')
    parser.add_argument('--range-probe', action='store_true', help='bounded verification of two ranges per file')
    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()
