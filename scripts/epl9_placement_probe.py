"""Verify the early loader request and local module-to-loaded-buffer identity."""
import argparse,json,struct,subprocess
from pathlib import Path
from epl9_workspace_bridge import ROOT,MAIN,MAIN_SHA,BASE,sha
from epl9_placement import CANDIDATE,MODULE_SIZE,EARLY_START,EARLY_END,check_slot
from mn103_subset import Machine,Memory,Region,parse_listing


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate-main',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):raise ValueError('new ignored output required')
    image=MAIN.read_bytes();check_slot(image,CANDIDATE,MODULE_SIZE)
    if sha(image)!=MAIN_SHA:raise ValueError('exact E-PL9 1101 main required')
    candidate=args.candidate_main.read_bytes()
    if len(candidate)!=len(image):raise ValueError('candidate main changed length')
    manifest=json.loads((args.candidate_main.parent/'manifest.json').read_text())
    module=(args.candidate_main.parent/'epl9-films-native.bin').read_bytes()
    if (manifest['main_sha256']!=MAIN_SHA or int(manifest['module_base'],0)!=CANDIDATE or
            len(module)!=MODULE_SIZE or sha(module)!=manifest['module_sha256']):
        raise ValueError('candidate module identity mismatch')
    expected=bytearray(image)
    expected[CANDIDATE-BASE:CANDIDATE-BASE+MODULE_SIZE]=module
    for patch in manifest['candidate_patches']:
        at=int(patch['address'],0)-BASE;before=bytes.fromhex(patch['before']);after=bytes.fromhex(patch['after'])
        if len(before)!=len(after) or expected[at:at+len(before)]!=before:raise ValueError('candidate hook identity mismatch')
        expected[at:at+len(after)]=after
    if candidate!=expected:raise ValueError('candidate changed bytes beyond module and declared hooks')
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    listing=subprocess.check_output([str(reader),str(MAIN),hex(BASE),hex(0x604001a4-BASE),hex(0x604001d0-BASE)],text=True)
    code=parse_listing(listing,image,BASE)
    m=Machine(code,Memory([Region(BASE,image),Region(0x6257d800,bytearray(4),True),
        Region(0x10000000,bytearray(4096),True)]),dict(sp=0x10000800))
    result=m.run(0x604001a4,[0x604001cb])
    assert result['pc']==0x604001cb
    source,destination,length=m.r['a0'],m.r['a1'],m.r['d1']
    assert (source,destination,length)==(0x406f0000,0xa0410000,0xa0800)
    # This emulates copying declared storage bytes, not a physical read.
    source_offset=source-0x406e0020
    loaded=candidate[source_offset:source_offset+length]
    at=CANDIDATE-EARLY_START
    assert loaded[at:at+MODULE_SIZE]==candidate[CANDIDATE-BASE:CANDIDATE-BASE+MODULE_SIZE]
    references=[]
    for lo in (CANDIDATE,(CANDIDATE&0x3fffffff)|0x80000000):
        p=image.find(b'\xfc')
        while 0<=p<=len(image)-6:
            value=struct.unpack_from('<I',image,p+2)[0]
            if lo<=value<lo+MODULE_SIZE:references.append(dict(address=hex(BASE+p),bytes=image[p:p+6].hex()))
            p=image.find(b'\xfc',p+1)
    report=dict(main_sha256=sha(image),candidate_main_sha256=sha(candidate),module_base=hex(CANDIDATE),
        module_bytes=MODULE_SIZE,early_load=dict(source=hex(source),destination=hex(destination),bytes=length,
        cached_start=hex(EARLY_START),cached_end=hex(EARLY_END)),module_load_bytes_identical=True,
        only_declared_module_and_hooks_changed=True,
        absolute_fc_reference_candidates=references,computed_references_excluded=False,
        physical_read_verified=False,install_ready=False)
    args.out.mkdir();(args.out/'placement.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.out/'early-loader.tsv').write_text(listing)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
