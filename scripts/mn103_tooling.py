"""Resolve and qualify the local GNU MN103 reader without camera inputs.

The historical Windows binary keeps its exact byte identity. A different host
build needs a matching build receipt, unchanged pinned sources, and a fresh
upstream-vector check once per process. Receipts are local provenance, not a
publisher signature or firmware/hardware qualification.
"""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'scripts/mn103_reader'
LEGACY_READER_SHA = 'e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae'
BUILD_SCHEMA = 'epl9-mn103-reader-build-v2'
VECTOR_COUNT, VECTOR_BYTES = 1294, 5694
NEGATIVE_CASES = ['truncated instruction', 'outside image', 'mapping overflow',
                  'negative offset', 'invalid machine']
_validated = set()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def default_reader():
    """Choose only our ignored-local host path; do not inspect it while parsing CLI."""
    name = 'mn103-reader.exe' if sys.platform == 'win32' else 'mn103-reader'
    return ROOT / 'local/mn103-tooling' / name


def source_fingerprints():
    paths = [HERE / n for n in ('reader.c', 'disassemble.h', 'sysdep.h', 'opintl.h',
             'upstream.json', 'build_reader.py', 'check_reader.py')]
    paths.append(Path(__file__).resolve())
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def checked_upstream(source):
    manifest = json.loads((HERE / 'upstream.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path = Path(source) / row['path']
        if not path.is_file() or path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError('missing or changed upstream source: ' + row['path'])
    return manifest


def checked_validation(report, vector_sha):
    if (report.get('upstream_opcode_vectors_passed') != VECTOR_COUNT or
            report.get('fixture_bytes') != VECTOR_BYTES or
            report.get('negative_cases_passed') != NEGATIVE_CASES or
            report.get('vectors_sha256') != vector_sha or report.get('camera_accessed') is not False):
        raise ValueError('incomplete GNU reader validation')


def reader_provenance(reader=None):
    """Fail closed for a missing, altered, stale, foreign-host or unvalidated build."""
    path = Path(reader) if reader is not None else default_reader()
    actual = digest(path)
    if actual == LEGACY_READER_SHA:
        return dict(kind='legacy-windows-pinned', reader_sha256=actual,
                    legacy_windows_sha256=LEGACY_READER_SHA)
    try:
        receipt_path = path.parent / 'build.json'
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if (receipt.get('schema') != BUILD_SCHEMA or receipt.get('platform') != sys.platform or
                receipt.get('machine') != platform.machine() or
                receipt.get('reader_filename') != path.name or
                receipt.get('reader_sha256') != actual or
                receipt.get('reader_bytes') != path.stat().st_size or
                receipt.get('adapter_sources') != source_fingerprints()):
            raise ValueError('reader build receipt is stale or does not identify this binary/host')
        compiler = receipt['compiler']
        if (not isinstance(compiler, dict) or
                any(not isinstance(compiler.get(k), str) or not compiler[k] for k in ('path', 'sha256', 'version')) or
                len(compiler['sha256']) != 64 or any(c not in '0123456789abcdef' for c in compiler['sha256'])):
            raise ValueError('missing compiler provenance')
        source = Path(receipt['source_directory'])
        manifest = checked_upstream(source)
        if (receipt.get('upstream_commit') != manifest['commit'] or
                receipt.get('upstream_files') != manifest['files']):
            raise ValueError('reader build receipt has different upstream identities')
        vectors = source / 'gas/testsuite/gas/mn10300/am33-2.d'
        vector_sha = digest(vectors)
        checked_validation(receipt['validation'], vector_sha)
        validation_path = path.parent / 'validation/validation.json'
        if (digest(validation_path) != receipt.get('validation_sha256') or
                json.loads(validation_path.read_text(encoding='utf-8')) != receipt['validation']):
            raise ValueError('reader validation receipt changed')
        # Do not accept self-asserted JSON as a substitute for executing the
        # decoder against the pinned independent corpus and rejection cases.
        key = (actual, digest(receipt_path), tuple(source_fingerprints().items()), vector_sha)
        if key not in _validated:
            with tempfile.TemporaryDirectory(prefix='mn103-qualify-', dir=ROOT / 'local') as tmp:
                subprocess.run([sys.executable, str(HERE / 'check_reader.py'),
                    '--reader', str(path.resolve()), '--vectors', str(vectors.resolve()),
                    '--out', tmp], check=True, capture_output=True, text=True)
                fresh = json.loads((Path(tmp) / 'validation.json').read_text(encoding='utf-8'))
                checked_validation(fresh, vector_sha)
                if fresh != receipt['validation']:
                    raise ValueError('fresh GNU reader validation differs from build receipt')
            if digest(path) != actual or source_fingerprints() != receipt['adapter_sources']:
                raise ValueError('reader or adapter changed during validation')
            _validated.add(key)
        return dict(kind='source-built-vector-validated', reader_sha256=actual,
                    platform=receipt['platform'], compiler=receipt['compiler'],
                    upstream_commit=manifest['commit'], validation=receipt['validation'],
                    build_receipt_sha256=digest(receipt_path),
                    legacy_windows_sha256=LEGACY_READER_SHA)
    except (KeyError, OSError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise ValueError('requires inspected GNU reader with valid build provenance') from exc


def verify_reader(reader=None):
    """Return the actual, qualified digest for checks and new evidence reports."""
    return reader_provenance(reader)['reader_sha256']
