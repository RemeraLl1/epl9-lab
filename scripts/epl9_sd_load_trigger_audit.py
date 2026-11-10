"""Reproduce read-only SD-loader trigger discovery and freeze v3 hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE
from epl9_color_audit import STOCK_SHA
from epl9_tonal_drafts import READER_SHA
from mn103_subset import parse_listing

WINDOWS={
    'hls_init':(0x60ae1bb2,0x60ae1d19),
    'hls_manager':(0x60ae1a4d,0x60ae1aac),
    'hls_get':(0x60ae2073,0x60ae208c),
    'event_get':(0x606b686a,0x606b6a46),
    'media_set':(0x60aef921,0x60aef973),
    'cached_sd_status':(0x60aef812,0x60aef853),
    'registered_getter':(0x609b175e,0x609b1787),
    'section_flags':(0x60422a3c,0x60422ac1),
    'get_task_id':(0x604117be,0x6041184d),
}
PINNED={
    'local/epl9-native-film-curves-probe-20261107/main-with-module-OFFLINE-ONLY.decoded.bin':
        (26214336,'501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686'),
    'local/epl9-embedded-icons-rowbounded-20261107/OSD-icons-OFFLINE-ONLY.decoded.bin':
        (26214336,'50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b'),
    'local/epl9-v3-packages-20261107/Gold-Portra-v3-candidate.bin':
        (52428800,'8d606a028f4b533db6431f1a0271a92d8f3f1c71e08833b481dcb2310d79ef8f'),
    'local/epl9-v3-packages-20261107/Stock-1101-main-osd-restore.bin':
        (52428800,'10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387'),
}


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists() or not a.out.resolve().is_relative_to((ROOT/'local').resolve()):
        ap.error('new ignored local output required')
    image=MAIN.read_bytes()
    stock=(ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN').read_bytes()
    if (len(image),sha(image))!=(26214336,MAIN_SHA) or (len(stock),sha(stock))!=(104552480,STOCK_SHA):
        raise ValueError('requires exact E-PL9 1101 inputs')
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    if sha(reader.read_bytes())!=READER_SHA: raise ValueError('wrong GNU reader')
    protected=[]
    paths=[*(ROOT/p for p in PINNED),ROOT/'firmware_src/epl9_films_late.s.in',
           *sorted((ROOT/'recipes').glob('epl9-film-drafts-*.json')),ROOT/'recipes/epl9-native-wb-trial-v1.json']
    for p in paths:
        data=p.read_bytes();name=p.relative_to(ROOT).as_posix()
        if name in PINNED and (len(data),sha(data))!=PINNED[name]: raise ValueError('frozen input changed: '+name)
        protected.append(dict(path=name,bytes=len(data),sha256=sha(data)))
    a.out.mkdir(parents=True)
    windows={};code={}
    for name,(start,end) in WINDOWS.items():
        listing=subprocess.check_output([str(reader),str(MAIN),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        parsed=parse_listing(listing,image,BASE)
        if start not in parsed or any(not start<=pc<end for pc in parsed): raise ValueError('wrong decoder span')
        code.update(parsed)
        (a.out/(name+'.tsv')).write_text(listing)
        windows[name]=dict(start=hex(start),end=hex(end),sha256=sha(listing.encode()))
    if code[0x60ae1c6e][0].hex()!='cd05042008' or code[0x60422ab8][1:]!=('mov',['d0','(0xa2aeaa3c)']):
        raise ValueError('event/boot anchors differ')
    (a.out/'protected-before.json').write_text(json.dumps(protected,indent=2)+'\n')
    report=dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',main_build=1101,
        stock_bytes=len(stock),stock_sha256=STOCK_SHA,main_bytes=len(image),main_sha256=MAIN_SHA,
        reader_sha256=READER_SHA,windows=windows,protected_files=protected,
        script_sha256=sha(Path(__file__).read_bytes()),
        camera_accessed=False,firmware_modified=False,static_analysis_only=True)
    (a.out/'discovery.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(windows=len(windows),protected_inputs=len(protected),camera_accessed=False)))


if __name__=='__main__': main()
