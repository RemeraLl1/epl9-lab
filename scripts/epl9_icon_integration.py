"""Embed the ten film badges in an offline OSD copy; no update container or camera writes."""
import argparse
import json
from pathlib import Path
from epl9_film_icons import artwork, encode_rle, TARGETS
from epl9_osd_audit import ROOT, MAIN_SHA, OSD_SHA, verified_bytes, load_decoder
from epl9_workspace_bridge import sha


def replace_spans(original,changes):
    result = bytearray(original)
    previous = 0
    for start,before,after in sorted(changes):
        if start < previous or not before or len(before) != len(after) or original[start:start+len(before)] != before:
            raise ValueError('overlapping, resized or mismatched icon span')
        result[start:start+len(before)] = after
        previous = start+len(before)
    return bytes(result)


def integrate(out):
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored local output required')
    decoded = ROOT/'local/epl9-1101-analysis/decoded'
    main,osd_path = decoded/'00_0100_406e0020.decoded.bin',decoded/'01_0101_421e0020.decoded.bin'
    verified_bytes(main,MAIN_SHA,26214336)
    original = verified_bytes(osd_path,OSD_SHA,26214336)
    decoder = load_decoder()
    old = decoder.OSD(osd_path,main)
    targets = [(str(k),old.descriptor(k),v,11) for k,v in TARGETS.items()]
    targets += [(f'A{k:03X}',old.symbol(k)[0],v,1) for k,v in ((0x76,'G200'),(0x77,'P400'))]
    changes,rows,expected = [],[],{}
    for ident,row,label,mode in targets:
        w,h,start,size = row['width'],row['height'],row['payload_offset'],row['encoded_bytes']
        ink = 3 if mode == 1 else 103 if ident in ('4420','4421') else 22 if ident in ('4556','4557') else 4
        pixels = bytes(ink if v else 0 for v in artwork(label,w,h))
        raw = encode_rle(pixels,w,h,mode)
        if len(raw)>size: raise ValueError('icon exceeds original stream allocation')
        replacement = raw.ljust(size,b'\0')
        if decoder.decode_rle(replacement,w,h)[:4] != (pixels,w,h,mode):
            raise ValueError('independent icon round-trip failed')
        before = original[start:start+size]
        changes.append((start,before,replacement))
        expected[ident] = pixels
        rows.append(dict(id=ident,recipe=label,offset=hex(start),bytes=size,encoded_bytes=len(raw),
                         before_sha256=sha(before),after_sha256=sha(replacement)))
    modified = replace_spans(original,changes)
    out.mkdir()
    path = out/'OSD-icons-OFFLINE-ONLY.decoded.bin'
    path.write_bytes(modified)
    # Original input and external decoder are pinned above. The derived copy is
    # independently reparsed with its own exact expected hash, not no-verify mode.
    decoder.COMPONENT_SHA = sha(modified)
    new = decoder.OSD(path,main)
    preview = []
    palette = next(p['entries'] for p in old.palettes() if p['address']==0x6151b980)
    for ident in range(old.bitmap_count):
        a,b = old.descriptor(ident),new.descriptor(ident)
        if a != b: raise ValueError('resource descriptor changed')
        if a['kind']=='rle':
            old_px,_,_ = old.decode_bitmap(a)
            px,_,_ = new.decode_bitmap(b)
            if px != expected.get(str(ident),old_px):
                raise ValueError(f'bitmap {ident} changed unexpectedly or aliases a target')
            if str(ident) in expected:
                preview.append((str(ident)+' '+TARGETS[ident],decoder.palette_image(px,b['width'],b['height'],palette).convert('RGBA')))
    for ident in range(old.symbol_count):
        a,old_px = old.symbol(ident)
        b,px = new.symbol(ident)
        if a != b or px != expected.get(f'A{ident:03X}',old_px):
            raise ValueError('inline symbol/alias changed unexpectedly')
    # Undo the exact replacements and require the complete original component.
    reverse = [(at,after,before) for at,before,after in changes]
    if replace_spans(modified,reverse)!=original: raise ValueError('OSD round-trip identity failed')
    if osd_path.read_bytes()!=original: raise ValueError('stock OSD changed')
    decoder.contact_sheet(preview,out/'embedded-icons.png',cols=2,cell=(240,100))
    report = dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',main_build='1101',
        original_bytes=len(original),original_osd_sha256=OSD_SHA,modified_osd_sha256=sha(modified),
        main_sha256=MAIN_SHA,changes=rows,bitmap_descriptors_checked=old.bitmap_count,
        symbols_checked=old.symbol_count,all_non_target_pixels_identical=True,descriptors_identical=True,
        stock_examples_untouched=True,camera_accessed=False,update_container_created=False,
        screen_palette_verified=False,install_ready=False)
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    report=integrate(args.out)
    print(json.dumps({k:report[k] for k in ('modified_osd_sha256','bitmap_descriptors_checked','symbols_checked','install_ready')}))
