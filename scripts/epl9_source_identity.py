"""Verify pinned text source with only uniform LF/CRLF equivalence.

Mixed endings and bare CR are rejected. No decoding, whitespace stripping,
Unicode normalization or semantic rewriting is performed. Not for binary inputs.
"""
import hashlib
from pathlib import Path


def verified_source(path, canonical_lf_sha256, legacy_raw_sha256):
    """Return the verified LF source snapshot and its actual/raw provenance."""
    raw = Path(path).read_bytes()
    canonical = raw.replace(b'\r\n', b'\n')
    if b'\r' in canonical:
        raise ValueError(f'bare CR in pinned source: {Path(path).name}')
    crlf_count = raw.count(b'\r\n')
    if crlf_count and raw.count(b'\n') != crlf_count:
        raise ValueError(f'mixed line endings in pinned source: {Path(path).name}')
    raw_sha = hashlib.sha256(raw).hexdigest()
    canonical_sha = hashlib.sha256(canonical).hexdigest()
    if canonical_sha != canonical_lf_sha256:
        raise ValueError(f'source identity mismatch: {Path(path).name}')
    return canonical, dict(raw_sha256=raw_sha, canonical_lf_sha256=canonical_sha,
        legacy_raw_sha256=legacy_raw_sha256, legacy_raw_match=raw_sha == legacy_raw_sha256,
        raw_bytes=len(raw), canonical_lf_bytes=len(canonical),
        line_endings='CRLF' if crlf_count else 'LF',
        normalization='uniform-LF-or-CRLF-only; mixed-and-bare-CR-rejected')
