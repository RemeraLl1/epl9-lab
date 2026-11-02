"""Read-only identity report for a local firmware file."""

import argparse
import hashlib
import json
from pathlib import Path


def inspect(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        header = source.read(64)
        digest.update(header)
        size += len(header)
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {
        "filename": path.name,
        "size_bytes": size,
        "sha256": digest.hexdigest(),
        "first_64_bytes_hex": header.hex(),
        "model": None,
        "displayed_version": None,
        "internal_build": None,
        "note": "Identity only; model, build, authenticity and compatibility are unverified.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.file.is_file():
        parser.error("input must be an existing file")
    report = json.dumps(inspect(args.file), indent=2) + "\n"
    if args.output:
        if args.output.resolve() == args.file.resolve():
            parser.error("output must not overwrite the input")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as output:
            output.write(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
