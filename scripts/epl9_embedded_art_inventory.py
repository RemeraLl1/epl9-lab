"""Read-only inventory for the separate embedded-31 V2 effort.

Reports worklist coverage, not the number/order of UI slots. Does not patch or
write firmware. OEM input is required locally and is never included in output.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

MAIN_SHA = '8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267'
BASE = 0x60400020
KEY_BASE = 0x01010067
TABLES = (('art', 0x608f22c0, 32), ('special', 0x608f23c0, 16))


def read_table(image, address, count):
    rows = []
    for slot in range(count):
        offset = address - BASE + slot * 8
        key, target = struct.unpack_from('<II', image, offset)
        if not key:
            continue
        rows.append(dict(slot=slot, key=hex(KEY_BASE + key), target=hex(target)))
    return rows


def inventory(image):
    if hashlib.sha256(image).hexdigest() != MAIN_SHA:
        raise ValueError('requires exact stock E-PL9 1101 decoded main')
    tables = {name: read_table(image, address, count) for name, address, count in TABLES}
    keys = sorted(set(row['key'] for rows in tables.values() for row in rows), key=lambda k:int(k,16))
    rows = []
    for key in keys:
        rows.append(dict(processing_key=key, paths={name: [r['target'] for r in values if r['key']==key]
            for name, values in tables.items()}, embedded_v2_recipe=None, ui_binding_proven=False))
    return dict(schema='epl9-embedded-v2-art-inventory-v1', stock_main_sha256=MAIN_SHA,
        target_embedded_recipe_count=31, sd_loader_in_v2=False, delete_hook_in_v2=False,
        tables=tables, table_row_count=sum(map(len,tables.values())),
        unique_processing_key_count=len(keys), mappings=rows,
        menu_slot_count=None, frozen_v2_created=False, install_ready=False,
        note='Two tables overlap. Their row sum is not a UI slot count; unlisted modes may use other/default paths.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--main',type=Path,required=True)
    args=ap.parse_args()
    print(json.dumps(inventory(args.main.read_bytes()),indent=2))


if __name__=='__main__':
    main()
