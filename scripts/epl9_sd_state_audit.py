"""Reproduce offline HLS singleton lifetime/allocation discovery, no writes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE
from epl9_sd_load_trigger_audit import PINNED, sha
from epl9_color_audit import STOCK_SHA
from epl9_tonal_drafts import READER_SHA
from mn103_subset import parse_listing

WINDOWS={
    'manager_ctor':(0x60ae187f,0x60ae1a3e),
    'manager_getter':(0x60ae1a4d,0x60ae1aac),
    'debug_alloc':(0x60dba05e,0x60dba0c9),
    'base_ctor':(0x60dba100,0x60dba185),
    'base_subobjects':(0x60dbabc1,0x60dbac95),
    'small_base':(0x60db8592,0x60db86a2),
    'parent_get_set':(0x60dba4e4,0x60dba52e),
    'parent_leaf':(0x60dbaafb,0x60dbabc1),
    'owner_factory':(0x60db86a2,0x60db86ee),
    'base_methods':(0x60dba52e,0x60dba5b0),
    'manager_vectors':(0x60ae2099,0x60ae226f),
    'task_create_manager':(0x60ae1bb2,0x60ae1c12),
    'ordinary_allocate':(0x60402373,0x6040240f),
    'root_users':(0x60ada380,0x60ada3e2),
}
PRIVATE={
    'local/epl9-v3-private-packages-20261107/Gold-Portra-v3-private-color-candidate.bin':
        (52428800,'230c4853b41d069da2a4fb22ace1eb043b28b71c9fa5b634cdc8baa037170256'),
    'local/epl9-v3-private-color-v2-20261107/private/main-with-module-OFFLINE-ONLY.decoded.bin':
        (26214336,'72cc1e48e6b42ab02b9911bdb841fe2c5b0cb34f2c08893f6b78be8a6871beee'),
}


def raw_call_candidates(image,target):
    result=[]
    for at,opcode in enumerate(image):
        width={0xcd:2,0xdd:4}.get(opcode)
        if width and at+width+3<=len(image):
            dest=(BASE+at+int.from_bytes(image[at+1:at+1+width],'little',signed=True))&0xffffffff
            if dest==target:result.append(hex(BASE+at))
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists() or not a.out.resolve().is_relative_to((ROOT/'local').resolve()):ap.error('new ignored local output required')
    image=MAIN.read_bytes();package=(ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN').read_bytes()
    if (len(image),sha(image))!=(26214336,MAIN_SHA) or (len(package),sha(package))!=(104552480,STOCK_SHA):
        raise ValueError('wrong E-PL9 1101 input')
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    if sha(reader.read_bytes())!=READER_SHA:raise ValueError('wrong GNU reader')
    pinned={**PINNED,**PRIVATE};protected=[]
    paths=[*(ROOT/p for p in pinned),ROOT/'firmware_src/epl9_films_late.s.in',
           ROOT/'firmware_src/epl9_sd_loader.s.in',ROOT/'scripts/epl9_sd_loader.py',
           *sorted((ROOT/'recipes').glob('epl9-film-drafts-*.json')),ROOT/'recipes/epl9-native-wb-trial-v1.json']
    for p in paths:
        name=p.relative_to(ROOT).as_posix();data=p.read_bytes()
        if name in pinned and (len(data),sha(data))!=pinned[name]:raise ValueError('protected generation changed: '+name)
        protected.append(dict(path=name,bytes=len(data),sha256=sha(data)))
    a.out.mkdir(parents=True);windows={};code={}
    for name,(start,end) in WINDOWS.items():
        text=subprocess.check_output([str(reader),str(MAIN),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        parsed=parse_listing(text,image,BASE)
        if start not in parsed or any(not start<=pc<end for pc in parsed):raise ValueError('decoder span mismatch')
        code.update(parsed);p=a.out/(name+'.tsv');p.write_text(text)
        windows[name]=dict(start=hex(start),end=hex(end),sha256=sha(p.read_bytes()))
    anchors={0x60ae1a6f:'2cb400',0x60ae1a8a:'cdf5fdf020',0x60ae1a8f:'fc800c793962'}
    for pc,raw in anchors.items():
        if code[pc][0].hex()!=raw:raise ValueError('singleton anchor differs')
    candidates={hex(target):raw_call_candidates(image,target) for target in (0x60ae187f,0x60ae1a4d)}
    root=(0x6239790c).to_bytes(4,'little');literals=[];at=image.find(root)
    while at>=0:literals.append(hex(BASE+at));at=image.find(root,at+1)
    report=dict(model='Olympus E-PL9 / IM008',displayed_version='1.1 (owner)',build=1101,
        package_bytes=len(package),package_sha256=STOCK_SHA,main_bytes=len(image),main_sha256=MAIN_SHA,
        reader_sha256=READER_SHA,windows=windows,raw_call_candidates=candidates,root_literal_occurrences=literals,
        scan_limit='raw encoded candidates, not a complete indirect-reference or lifetime proof',
        original_object_bytes=180,proposed_object_bytes=288,ordinary_pool_id='0x10002',ordinary_pool_block_bytes=2048,
        protected_inputs=protected,camera_accessed=False,firmware_modified=False,
        source_sha256=sha(Path(__file__).read_bytes()))
    (a.out/'discovery.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.out/'protected-before.json').write_text(json.dumps(protected,indent=2)+'\n')
    print(json.dumps(dict(windows=len(windows),ctor_candidates=len(candidates['0x60ae187f']),protected=len(protected))))


if __name__=='__main__':main()
