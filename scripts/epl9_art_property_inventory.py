"""Stock UI-property backing slots; no assumption that stored == active variant."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from epl9_art_ui_inventory import inventory,BASE,MAIN_SHA

TABLE=0x608aca18
COUNT=1620


def backing_slot(image,property_id):
    if not 0<=property_id<COUNT:
        raise ValueError('outside confirmed primary property range')
    if TABLE-BASE+4*COUNT>len(image):
        raise ValueError('truncated property table')
    key,index=struct.unpack_from('<HH',image,TABLE-BASE+4*property_id)
    return dict(property_id=hex(property_id),storage_id=hex(key),element_index=index)


def audit(image):
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:
        raise ValueError('requires exact stock main')
    ui=inventory(image)
    properties=sorted({int(r['variant_property_id'],16) for r in ui['rows']
                       if r['variant_property_id'] is not None})
    slots=[backing_slot(image,p) for p in properties]
    if len(slots)!=12 or any(r['storage_id']!='0x44c1' for r in slots):
        raise ValueError('variant storage family differs')
    if [r['element_index'] for r in slots]!=list(range(1,13)):
        raise ValueError('variant slot order differs')
    if backing_slot(image,0x6f)!=dict(property_id='0x6f',storage_id='0x9481',element_index=0):
        raise ValueError('mode backing differs')
    return dict(schema='epl9-art-property-inventory-v1',stock_main_sha256=MAIN_SHA,
        variant_slots=slots,mode_property_candidate=backing_slot(image,0x6f),
        capture_variant_read=dict(storage_id='0x44c1',element_index=0,config_offset=23688),
        capture_mode_read=dict(storage_id='0x9481',element_index=0,config_offset=22955),
        active_variant_copy_proven=False,ui_mode_conversion_proven=False,
        ui_to_capture_join_proven=False,install_ready=False,
        scope='Exact static backing inventory; property dispatch and active-slot lifecycle remain open')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True)
    print(json.dumps(audit(p.parse_args().main.read_bytes()),indent=2))
