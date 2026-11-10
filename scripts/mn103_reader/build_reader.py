"""Build a local reader from pinned, unmodified GNU sources on Windows/Linux.

This does not download dependencies, read firmware or access a camera.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import platform
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from mn103_tooling import (BUILD_SCHEMA, checked_upstream, checked_validation,
                           source_fingerprints)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT / 'references/binutils-2.45-mn103')
    p.add_argument('--compiler', type=Path, help='Windows: pinned TinyCC; Linux: local C compiler (default cc)')
    p.add_argument('--out', type=Path, default=ROOT / 'local/mn103-tooling')
    args = p.parse_args()
    if sys.platform not in ('win32', 'linux'):
        p.error('supported build hosts are Windows and Linux')
    if not args.out.resolve().is_relative_to((ROOT / 'local').resolve()):
        p.error('build output must be below ignored local/')
    try:
        manifest = checked_upstream(args.source)
    except (OSError, ValueError) as error:
        p.error(str(error))
    if args.compiler is None:
        args.compiler = ROOT / 'tools/tinycc/tcc/tcc.exe' if sys.platform == 'win32' else Path(shutil.which('cc') or '')
    if not args.compiler.is_file():
        p.error('local C compiler not found; supply --compiler')
    if sys.platform == 'win32' and digest(args.compiler) != manifest['compiler']['executable_sha256']:
        p.error('compiler differs from pinned TinyCC executable')
    adapter_sources = source_fingerprints()
    compiler_sha = digest(args.compiler)
    args.out.mkdir(parents=True, exist_ok=True)
    executable = args.out.resolve() / ('mn103-reader.exe' if sys.platform == 'win32' else 'mn103-reader')
    # A failed rebuild must not leave a previously successful receipt usable.
    (args.out / 'build.json').unlink(missing_ok=True)
    command = [str(args.compiler.resolve()), *([] if sys.platform == 'win32' else ['-std=c99', '-O2']), '-I', str(HERE), '-I',
               str(args.source.resolve() / 'include'), '-o', str(executable),
               str(HERE / 'reader.c'), str(args.source.resolve() / 'opcodes/m10300-dis.c'),
               str(args.source.resolve() / 'opcodes/m10300-opc.c')]
    subprocess.run(command, check=True)
    subprocess.run([sys.executable, str(HERE / 'check_reader.py'), '--reader', str(executable),
                    '--vectors', str(args.source / 'gas/testsuite/gas/mn10300/am33-2.d'),
                    '--out', str(args.out / 'validation')], check=True)
    validation_path = args.out / 'validation/validation.json'
    validation = json.loads(validation_path.read_text(encoding='utf-8'))
    checked_validation(validation, digest(args.source / 'gas/testsuite/gas/mn10300/am33-2.d'))
    compiler = dict(path=str(args.compiler.resolve()), sha256=compiler_sha,
                    version=subprocess.check_output([str(args.compiler.resolve()), '-v'], stderr=subprocess.STDOUT, text=True).strip())
    # Do not attest post-build source bytes for an executable compiled before a
    # concurrent edit. The receipt identifies the inputs checked before build.
    if source_fingerprints() != adapter_sources or digest(args.compiler) != compiler_sha:
        raise ValueError('adapter source or compiler changed during build; no receipt written')
    checked_upstream(args.source)
    if sys.platform == 'win32':
        compiler['pinned_tinycc'] = manifest['compiler']
    report = {'schema': BUILD_SCHEMA, 'platform': sys.platform, 'machine': platform.machine(),
              'upstream_commit': manifest['commit'], 'upstream_files': manifest['files'],
              'source_directory': str(args.source.resolve()), 'compiler': compiler, 'command': command,
              'reader_filename': executable.name, 'reader_bytes': executable.stat().st_size,
              'reader_sha256': digest(executable), 'adapter_sources': adapter_sources,
              'validation_sha256': digest(validation_path), 'validation': validation}
    (args.out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Built and validated:', executable)


if __name__ == '__main__':
    main()
