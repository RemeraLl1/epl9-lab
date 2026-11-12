"""Local-only reproduction of the frozen native-source-v1 research pair.

No camera, SD-card preparation, firmware download or external code execution.
Every output must match the already frozen full-file identity.
"""
import argparse
import json
from pathlib import Path
import sys

from epl9_color_audit import STOCK_SHA
from epl9_workspace_bridge import ROOT, sha, MAIN_SHA
from epl9_workspace_gamma_probe import native_curve_document
from epl9_film_late_module import build_late_module
from epl9_film_icons import artwork, encode_rle
from epl9_recovery_audit import inspect_package, decoded_payload
from epl9_v3_package import pair, KINDS
from epl9_native_source_package import (
    GENERATION, MAIN_HASH, MODULE_HASH, OSD_HASH, STOCK_OSD_HASH, RGB_HASH,
    RESTORE_HASH, MODULE_BASE, PAIR_BYTES, CANDIDATE_NAME, RESTORE_NAME,
    RECIPE_HASHES, module_main, verify_protected, require,
)

CANDIDATE_HASH = '10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421'
STOCK_BYTES = 104552480
LAYOUT = ROOT/'releases/native-source-v1/icon-layout.json'
NOTICE = '''Experimental E-PL9 native-source-v1 research files

These files reproduce the frozen Gold/Portra candidate and exact stock main/OSD
return package. This is NOT a qualified installation procedure. The builder
neither connects to a camera nor prepares a card. Do not infer a DCOLYMP filename,
button sequence, LED pattern or safe timeout from another camera's instructions.

Physical E-PL9 installation, early-boot recovery and TruePic output have not been
qualified. The return file is not a complete camera backup and cannot guarantee
recovery of an unbootable camera. Video support is not established. No SD recipe
loader or Delete remapping is included. Watercolor I/II labels remain unchanged.

Use SHA256SUMS to identify the files. manifest.json is written last only after
reading back both firmware files; a directory without it is incomplete. Files are
private and ignored by Git. Never publish manufacturer firmware in this repo.
'''


def identified(data, digest, size=None, name='input'):
    require((size is None or len(data) == size) and sha(data) == digest,
            name+' identity mismatch')
    return data


def load_stock(path):
    # Check length before reading; never admit a similar model/build or bypass SHA.
    require(path.is_file() and path.stat().st_size == STOCK_BYTES,
            'stock must be the exact 104552480-byte E-PL9 build 1101 file')
    return identified(path.read_bytes(), STOCK_SHA, STOCK_BYTES, 'stock')


def extract_components(stock):
    rows = inspect_package(stock)
    require([int(r['kind'],16) for r in rows] == [0x100,0x101,0x106,0x10e,0x102],
            'unexpected stock component inventory')
    result = {}
    for row in rows:
        kind = int(row['kind'],16)
        if kind in KINDS:
            at = int(row['offset'],16)
            result[kind] = decoded_payload(stock[at+32:at+row['package_bytes']-32])
    identified(result[0x100], MAIN_SHA, 26214336, 'stock main')
    identified(result[0x101], STOCK_OSD_HASH, 26214336, 'stock OSD')
    return result


def make_icons(original, layout):
    """Original authored badges at measured, hash-guarded E-PL9 offsets.

    Only numeric metadata/digests are published, never original icon streams.
    """
    output = bytearray(original)
    require(len(layout) == 10 and len({r['id'] for r in layout}) == 10,
            'expected ten unique icon records')
    end = 0
    for row in sorted(layout,key=lambda r:r['offset']):
        at, size = row['offset'], row['bytes']
        require(type(at) is int and type(size) is int and at >= end and size > 0
                and at+size <= len(original), 'invalid/overlapping icon span')
        identified(original[at:at+size],row['before_sha256'],size,'original icon')
        w,h = row['width'],row['height']
        pixels = bytes(row['ink'] if x else 0 for x in artwork(row['label'],w,h))
        encoded = encode_rle(pixels,w,h,row['mode'])
        require(len(encoded) <= size,'authored icon exceeds existing allocation')
        data = encoded.ljust(size,b'\0')
        identified(data,row['after_sha256'],size,'authored icon')
        output[at:at+size] = data
        end = at+size
    return identified(bytes(output),OSD_HASH,len(original),'candidate OSD')


def build_bytes(stock):
    identified(stock,STOCK_SHA,STOCK_BYTES,'stock')
    components = extract_components(stock)
    for name,digest in RECIPE_HASHES.items():
        identified((ROOT/name).read_bytes(),digest,name=name)
    tone = json.loads((ROOT/'recipes/epl9-film-drafts-v1.json').read_text(encoding='utf-8'))
    rgb,_ = native_curve_document(components[0x100],tone)
    identified((json.dumps(rgb,indent=2)+'\n').encode(),RGB_HASH,name='derived RGB')
    wb = json.loads((ROOT/'recipes/epl9-native-wb-trial-v1.json').read_text(encoding='utf-8'))
    module = build_late_module(components[0x100],base=MODULE_BASE,rgb_document=rgb,
                              wb_document=wb,private_color=True,native_source_gate=True)
    identified(module['data'],MODULE_HASH,15360,'module')
    main = identified(module_main(components[0x100],module),MAIN_HASH,26214336,'candidate main')
    protected = verify_protected(components[0x100],main)
    icons = json.loads(LAYOUT.read_text(encoding='utf-8'))
    osd = make_icons(components[0x101],icons)
    candidate, restore = pair(stock,{0x100:main,0x101:osd})
    identified(candidate,CANDIDATE_HASH,PAIR_BYTES,'candidate package')
    identified(restore,RESTORE_HASH,PAIR_BYTES,'stock-return package')
    # Strict reparse, including decoded checksums, of both final files.
    for blob,expected in ((candidate,(MAIN_HASH,OSD_HASH)),(restore,(MAIN_SHA,STOCK_OSD_HASH))):
        rows = inspect_package(blob)
        require(tuple(int(r['kind'],16) for r in rows) == KINDS and
                tuple(r['decoded_sha256'] for r in rows) == expected,
                'final decoded component identity mismatch')
    evidence = dict(schema='epl9-local-build-v1',generation=GENERATION,
        stock_sha256=STOCK_SHA,model='E-PL9 / IM008',downloaded_build='1101',
        install_ready=False,physical_installation_tested=False,
        physical_recovery_tested=False,video_support_confirmed=False,
        camera_accessed=False,source_only_reproduction=True,
        module_sha256=MODULE_HASH,main_sha256=MAIN_HASH,osd_sha256=OSD_HASH,
        derived_rgb_sha256=RGB_HASH,protected_ranges=protected,
        files={CANDIDATE_NAME:dict(bytes=len(candidate),sha256=sha(candidate)),
               RESTORE_NAME:dict(bytes=len(restore),sha256=sha(restore))})
    return {CANDIDATE_NAME:candidate,RESTORE_NAME:restore},evidence


def write_outputs(out, files, evidence):
    require(out.resolve().is_relative_to((ROOT/'local').resolve()) and
            out.resolve() != (ROOT/'local').resolve(),
            'output must be a new directory under this checkout local/')
    require(not out.exists(),'output already exists; choose a new directory')
    # Files are fully qualified in memory before claiming the destination.
    out.parent.mkdir(parents=True,exist_ok=True)
    out.mkdir()  # Exclusive: do not overwrite an existing result or user files.
    for name,data in files.items():
        with (out/name).open('xb') as f:
            f.write(data)
    for name,data in files.items():
        identified((out/name).read_bytes(),sha(data),len(data),'written '+name)
    (out/'SHA256SUMS').write_text(''.join(sha(data)+'  '+name+'\n' for name,data in files.items()),encoding='utf-8')
    (out/'READ-ME-FIRST.txt').write_text(NOTICE,encoding='utf-8')
    evidence = dict(evidence,output_readback_verified=True)
    (out/'manifest.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['build','check-stock'])
    parser.add_argument('--stock',type=Path,required=True,
                        help='Original official E-PL9 build 1101 BIN; never a patched or E-P7/PEN-F file')
    parser.add_argument('--out',type=Path,default=ROOT/'local/volunteer-native-source-v1')
    args = parser.parse_args(argv)
    try:
        stock = load_stock(args.stock)
        if args.command == 'check-stock':
            extract_components(stock)
            print('Exact E-PL9 build 1101 input verified. No output files created.')
            return 0
        require(not args.out.exists(),'output already exists; choose a new directory')
        files,evidence = build_bytes(stock)
        write_outputs(args.out,files,evidence)
        print('Frozen native-source-v1 pair reproduced and read back: '+str(args.out))
        print('Not installation-qualified. Read READ-ME-FIRST.txt. No camera was accessed.')
        return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('Build refused: '+str(exc),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
