"""Package already audited E-PL9 components as private OM-Emu memory overlays.

No update container, camera connection or upstream source copy is produced.
"""
import argparse
import base64
import json
from pathlib import Path
from epl9_workspace_bridge import ROOT, MAIN, MAIN_SHA, BASE, sha

OSD=ROOT/'local/epl9-1101-analysis/decoded/01_0101_421e0020.decoded.bin'
ICONS=ROOT/'local/epl9-embedded-icons-rowbounded-20261107'
FILMS=ROOT/'local/epl9-kind1000-integration-final-20261105'
OSD_SHA='ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e'
ICON_SHA='50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b'
FILM_SHA='29c6dceb4ecd14c0cf7ae5286aa595f48b9a548a2303986375d098fc34bb1585'
UPSTREAM='147ca89c60b24774f3145c2813d79714e0f0b7b7'
RESOURCE_PREFIX=21456352


def overlay(stock,modified,spans,block):
    """Require all differences to lie in disjoint declared nonempty spans."""
    if len(stock)!=len(modified):raise ValueError('component size changed')
    rebuilt=bytearray(stock);rows=[];previous=0
    for offset,size,label in sorted(spans):
        if not 0<=previous<=offset<offset+size<=len(stock):
            raise ValueError('invalid/overlapping overlay span')
        before,after=stock[offset:offset+size],modified[offset:offset+size]
        rows.append(dict(block=block,offset=offset,label=label,
            old=base64.b64encode(before).decode(),new=base64.b64encode(after).decode()))
        rebuilt[offset:offset+size]=after;previous=offset+size
    if rebuilt!=modified:raise ValueError('undeclared component changes')
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();out=a.out.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'local').resolve()):
        ap.error('new ignored local output directory required')
    stock=OSD.read_bytes();modified=(ICONS/'OSD-icons-OFFLINE-ONLY.decoded.bin').read_bytes()
    if sha(stock)!=OSD_SHA or sha(modified)!=ICON_SHA:raise ValueError('wrong OSD input')
    manifest=json.loads((ICONS/'manifest.json').read_text())
    spans=[(int(c['offset'],16),c['bytes'],c['recipe']+' icon '+c['id']) for c in manifest['changes']]
    if len(spans)!=10 or any(at+n>RESOURCE_PREFIX for at,n,_ in spans):
        raise ValueError('expected ten resources inside OM-Emu loaded prefix')
    icons=overlay(stock,modified,spans,'resource')
    main=MAIN.read_bytes();candidate=(FILMS/'main-with-module-OFFLINE-ONLY.decoded.bin').read_bytes()
    if sha(main)!=MAIN_SHA or sha(candidate)!=FILM_SHA:raise ValueError('wrong main input')
    module=json.loads((FILMS/'manifest.json').read_text())
    spans=[(int(module['module_base'],16)-BASE,module['module_bytes'],'film module')]
    spans += [(int(p['address'],16)-BASE,len(bytes.fromhex(p['before'])),'film hook '+p['address'])
              for p in module['candidate_patches']]
    films=overlay(main,candidate,spans,'main')
    report=dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',internal_build='1101',
        upstream_url='https://github.com/flatpanda/om-emu',upstream_commit=UPSTREAM,
        main_bytes=len(main),stock_main_sha256=sha(main),candidate_main_sha256=sha(candidate),
        osd_bytes=len(stock),stock_osd_sha256=sha(stock),candidate_osd_sha256=sha(modified),
        omemu_resource_prefix=RESOURCE_PREFIX,stock_prefix_sha256=sha(stock[:RESOURCE_PREFIX]),
        candidate_prefix_sha256=sha(modified[:RESOURCE_PREFIX]),icon_patches=len(icons),
        main_patches=len(films),firmware_container_created=False,camera_accessed=False,
        hardware_pixel_execution=False,source_sha256=sha(Path(__file__).read_bytes()))
    out.mkdir()
    for name,rows in [('icons',icons),('main',films),('combined',icons+films)]:
        (out/(name+'.json')).write_text(json.dumps(dict(patches=rows),indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
