"""Offline BOOT-source evidence and candidate identification for E-PL9.

Reads saved catalogs/inventories and local files only. Never downloads, extracts
an installable image, talks to a camera or treats a BOOT tag as reset validation.
"""
import argparse
from array import array
import json
from pathlib import Path
import re
import struct
import sys
import urllib.parse
import xml.etree.ElementTree as ET

from epl9_ok_entry_audit import ROOT, STOCK_SHA, sha, verified_input, local_output
from epl9_recovery_audit import decoded_payload


def nested_BOOT_tags(raw):
    """Find bounded, checksum-valid OE/1330/BOOT envelopes, not bare boot code."""
    accepted=[];rejected=[]
    for match in re.finditer(re.escape(b'OE\x13\x30'),raw):
        start=match.start()
        if len(raw)-start < 64 or raw[start+20] != 0x10:continue
        size=struct.unpack_from('<I',raw,start+12)[0]
        end=start+size+64
        if not size or size%16 or end>len(raw):
            rejected.append(dict(offset=start,reason='invalid nested extent'));continue
        try:
            result=inspect_candidate(raw[start:end],scan_nested=False)
        except ValueError as exc:
            rejected.append(dict(offset=start,reason=str(exc)));continue
        accepted.append(dict(offset=start,bytes=end-start,sha256=result['sha256'],
                             components=result['components'],independently_bootable=False))
    return dict(accepted=accepted,rejected=rejected,
                limitation='envelope scan cannot exclude bare, compressed or differently wrapped loader code')


def inspect_candidate(raw,scan_nested=True):
    identity=dict(bytes=len(raw),sha256=sha(raw),ready_to_install=False,
                  independently_bootable=False,model_proven_for_raw_dump=False)
    if not raw:
        raise ValueError('empty input')
    if raw[:2] != b'OE':
        return dict(**identity,classification='unidentified raw/non-OE input',components=[],
                    nested_BOOT_scan=nested_BOOT_tags(raw) if scan_nested else None,
                    note='model, board, address mapping and dump layout need independent provenance')
    rows=[];offset=0;kinds=set()
    while offset < len(raw):
        if len(raw)-offset < 64:
            raise ValueError('truncated component envelope')
        header=raw[offset:offset+32]
        address,size=struct.unpack_from('<II',header,8)
        kind=struct.unpack_from('<H',header,20)[0]
        if header[:4] != b'OE\x13\x30':
            raise ValueError('not an E-PL9 model-1330 component')
        if not size or size%16 or kind in kinds or header[28:] != bytes(4):
            raise ValueError('unqualified size/duplicate/header form')
        end=offset+size+64
        if end > len(raw):
            raise ValueError('component exceeds input')
        trailer=raw[end-32:end]
        if header[:28] != trailer[:28]:
            raise ValueError('header/trailer disagreement')
        decoded=decoded_payload(raw[offset+32:end-32])
        words=array('I');words.frombytes(header+decoded+trailer)
        if words.itemsize != 4:raise ValueError('unexpected host word size')
        if sys.byteorder != 'little':words.byteswap()
        if sum(words)&0xffffffff:raise ValueError('bad component checksum')
        rows.append(dict(offset=offset,model_bytes='1330',kind=hex(kind),
            header_build=f'{struct.unpack_from("<H",header,16)[0]:04x}',
            destination=hex(address),payload_bytes=size,component_bytes=size+64,
            decoded_sha256=sha(decoded),BOOT_tag_candidate=kind&0xff==0x10,
            nested_BOOT_scan=nested_BOOT_tags(decoded) if scan_nested else None))
        offset=end;kinds.add(kind)
    return dict(**identity,classification='model-1330 OE container; structural checks only',
                components=rows,BOOT_tag_present=any(r['BOOT_tag_candidate'] for r in rows))


def catalog_record(xml):
    root=ET.fromstring(xml)
    entries=root.findall('./firmwares/firmware_info')
    if root.tag != 'firmware_result' or len(entries) != 1:
        raise ValueError('unexpected saved catalog shape')
    row={n.tag:n.text or '' for n in entries[0]}
    if row.get('model_name') != 'E-PL9' or row.get('model_id') != '1330':
        raise ValueError('saved catalog is not for E-PL9')
    url=urllib.parse.urlsplit(row.pop('url',''))
    row['url_without_temporary_signature']=urllib.parse.urlunsplit(url._replace(query='',fragment=''))
    row['temporary_query_keys']=list(urllib.parse.parse_qs(url.query))
    return row


def epl9_inventory(records):
    found=[]
    def visit(value):
        if isinstance(value,dict):
            if value.get('model') == 'E-PL9':
                components=value.get('components',[])
                if not components or any(c.get('model_bytes') != '1330' for c in components):
                    raise ValueError('inconsistent E-PL9 inventory row')
                found.append(dict(role=value.get('role'),bytes=value.get('bytes'),
                    sha256=value.get('sha256'),filenames=value.get('filenames',[]),
                    source_urls=value.get('source_urls',[]),
                    component_kinds=[c['kind'] for c in components],
                    BOOT_tag_reported=any(int(c['kind'],16)&0xff==0x10 for c in components),
                    evidence='pinned inventory report; availability/content not independently fetched'))
                return
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(records)
    return found


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,action='append',default=[])
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if not __debug__:p.error('assertions required')
    out=local_output(args.out)
    stock_path=ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN'
    stock=verified_input(stock_path,104552480,STOCK_SHA)
    catalog_path=ROOT/'local/epl9-vendor-catalog-20261102/response.xml'
    xml=catalog_path.read_bytes();catalog=catalog_record(xml)
    if (catalog['file_name'] != stock_path.name or catalog['version'] != '1101'
            or int(catalog['file_size']) != len(stock)):
        raise ValueError('saved offer differs from pinned stock input')
    inventory_path=ROOT/'references/oly_fw_analysis/provenance/firmware-inventory.json'
    inventory_raw=inventory_path.read_bytes();inventory=epl9_inventory(json.loads(inventory_raw))
    candidates=[dict(path=str(stock_path),**inspect_candidate(stock))]
    seen={stock_path.resolve()}
    for path in args.candidate:
        path=path.resolve()
        if path in seen:continue
        if not path.is_file() or not 0 < path.stat().st_size <= 1024**3:
            raise ValueError('candidate must be a nonempty local file <=1 GiB')
        candidates.append(dict(path=str(path),**inspect_candidate(path.read_bytes())))
        seen.add(path)
    report=dict(model='Olympus PEN E-PL9',model_bytes='1330',
        displayed_version='1.1 (owner report)',downloaded_main_build='1101',
        saved_catalog_date='2026-11-02',saved_catalog_sha256=sha(xml),catalog=catalog,
        inventory_sha256=sha(inventory_raw),inventory_records=inventory,
        reference_revision='539fcf1fa9eda5fdef8ede4deeab94a4691d94c3',candidates=candidates,
        BOOT_source_confirmed=False,source_sha256=sha(Path(__file__).read_bytes()),
        dependencies={n:sha((ROOT/'scripts'/n).read_bytes()) for n in (
            'epl9_ok_entry_audit.py','epl9_recovery_audit.py','epl9_video_audit.py','epl9_color_audit.py')},
        camera_accessed=False,media_accessed=False,network_accessed=False,
        firmware_modified=False,installable_image_written=False)
    out.mkdir();(out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(catalog_model=catalog['model_name'],offered=catalog['file_name'],
        stock_BOOT_tag_present=candidates[0]['BOOT_tag_present'],
        known_EPL9_inventory_records=len(inventory),
        inventory_BOOT_tags=[r['BOOT_tag_reported'] for r in inventory],
        BOOT_source_confirmed=False,network_accessed=False),indent=2))


if __name__=='__main__':main()
