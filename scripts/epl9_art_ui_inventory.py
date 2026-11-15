"""Exact-stock ART UI inventory for V2; no firmware patch or recipe invention.

The three bounded UI tables are not the worklist hash tables. Their agreement
establishes static selection metadata, not hardware availability or rendering.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from epl9_embedded_art_inventory import BASE, MAIN_SHA

LABEL_START = 0x615724d8
LABEL_END = 0x6157264c
CHOICE_START = 0x6155d37c
CHOICE_END = 0x6155d5e8
VARIANT_START = 0x6155d648
VARIANT_END = 0x6155d8d0
SIMPLE = {0x9, 0xb, 0x10, 0x3f}


def records(image, start, end, fmt):
    size = struct.calcsize(fmt)
    if start < BASE or end < start or end - BASE > len(image) or (end-start) % size:
        raise ValueError('invalid table bounds')
    return [struct.unpack_from(fmt, image, p-BASE) for p in range(start,end,size)]


def reconcile(labels, choices, variants):
    """Validate cross-table relationships; input lengths alone are not proof."""
    if len(labels) != 31 or len(choices) != 31 or len(variants) != 27:
        raise ValueError('unexpected bounded table lengths')
    values = [r[0] for r in labels]
    if len(set(values)) != len(values) or [r[0] for r in choices] != values:
        raise ValueError('selection keys/order disagree')
    if any(kind != 4 or not string_id for _,kind,string_id,_ in labels):
        raise ValueError('not string-label rows')
    if len({r[0] for r in variants}) != 27:
        raise ValueError('duplicate variant selector')
    variant_by_key = {r[0]:r for r in variants}
    if set(values)-variant_by_key.keys() != SIMPLE or variant_by_key.keys()-set(values):
        raise ValueError('variant/simple partition disagrees')
    output=[]
    for (key,_,string_id,_),(ckey,resource,mode,variant,reserved) in zip(labels,choices):
        if reserved or (variant and key != mode*256+variant) or (not variant and key != mode):
            raise ValueError('choice decomposition mismatch')
        detail=variant_by_key.get(key)
        if detail:
            vk,vv,property_id,detail_resource,vm,zero=detail
            if (vv,detail_resource,vm,zero)!=(variant,resource,mode,0):
                raise ValueError('variant table does not match choice')
        else:
            if variant: raise ValueError('simple selection has nonzero variant')
            property_id=None
        output.append(dict(ui_value=hex(key),string_id=string_id,
            choice_resource_id=resource,base_mode=hex(mode),variant=variant,
            variant_property_id=hex(property_id) if property_id is not None else None,
            processing_key=None,embedded_recipe=None,processing_binding_proven=False))
    return output


def inventory(image):
    if hashlib.sha256(image).hexdigest()!=MAIN_SHA:
        raise ValueError('requires exact stock E-PL9 1101 decoded main')
    labels=records(image,LABEL_START,LABEL_END,'<IHHI')
    for *_,pointer in labels:
        if not BASE <= pointer < BASE+len(image) or image[pointer-BASE]!=0:
            raise ValueError('unexpected label fallback pointer')
    rows=reconcile(labels,records(image,CHOICE_START,CHOICE_END,'<5I'),
                   records(image,VARIANT_START,VARIANT_END,'<6I'))
    return dict(schema='epl9-art-ui-inventory-v1',stock_main_sha256=MAIN_SHA,
        ui_record_count=len(rows),variant_record_count=27,simple_record_count=4,
        rows=rows,camera_tested=False,processing_binding_proven=False,
        frozen_v2_created=False,install_ready=False,
        scope='31 static UI records, not 31 proved active capture/preview paths')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(inventory(args.main.read_bytes()),indent=2))

if __name__=='__main__': main()
