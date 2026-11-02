"""Build a local reader from pinned, unmodified GNU sources and TinyCC.

This does not download dependencies, read firmware or access a camera.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT / 'references/binutils-2.45-mn103')
    p.add_argument('--compiler', type=Path, default=ROOT / 'tools/tinycc/tcc/tcc.exe')
    p.add_argument('--out', type=Path, default=ROOT / 'local/mn103-tooling')
    args = p.parse_args()
    manifest = json.loads((HERE / 'upstream.json').read_text())
    if sys.platform != 'win32':
        p.error('this build recipe is validated for Windows with the pinned TinyCC only')
    if not args.out.resolve().is_relative_to(ROOT / 'local'):
        p.error('build output must be below ignored local/')
    for entry in manifest['files']:
        path = args.source / entry['path']
        if not path.is_file() or digest(path) != entry['sha256']:
            p.error(f'missing or changed upstream source: {entry["path"]}')
    if digest(args.compiler) != manifest['compiler']['executable_sha256']:
        p.error('compiler differs from pinned TinyCC executable')
    args.out.mkdir(parents=True, exist_ok=True)
    executable = args.out.resolve() / 'mn103-reader.exe'
    command = [str(args.compiler.resolve()), '-I', str(HERE), '-I',
               str(args.source.resolve() / 'include'), '-o', str(executable),
               str(HERE / 'reader.c'), str(args.source.resolve() / 'opcodes/m10300-dis.c'),
               str(args.source.resolve() / 'opcodes/m10300-opc.c')]
    subprocess.run(command, check=True)
    subprocess.run([sys.executable, str(HERE / 'check_reader.py'), '--reader', str(executable),
                    '--vectors', str(args.source / 'gas/testsuite/gas/mn10300/am33-2.d'),
                    '--out', str(args.out / 'validation')], check=True)
    report = {'upstream_commit': manifest['commit'], 'compiler': manifest['compiler'],
              'reader_sha256': digest(executable),
              'adapter_sources': {f.name: digest(f) for f in HERE.iterdir()
                                  if f.suffix in {'.c', '.h', '.py', '.json'}},
              'validation': json.loads((args.out / 'validation/validation.json').read_text())}
    (args.out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Built and validated:', executable)


if __name__ == '__main__':
    main()
