"""Read-only extraction of the exact E-PL9 0x102 picture directory."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SHA = 'a0d6a08e79f8a1c731959695ada1f26d52ea1e1c0fc9f234618f795ced061c0f'
BASE = 0x468e0020


def jpeg_end(blob):
    """Walk segments and entropy markers; ignore embedded thumbnails in APPs."""
    if blob[:2] != b'\xff\xd8':
        raise ValueError('missing JPEG SOI')
    pos = 2
    entropy = False
    while pos < len(blob):
        if entropy:
            pos = blob.find(b'\xff', pos)
            if pos < 0:
                break
        elif blob[pos] != 255:
            raise ValueError('missing marker prefix')
        while pos < len(blob) and blob[pos] == 255:
            pos += 1
        if pos >= len(blob):
            break
        marker = blob[pos]
        pos += 1
        if entropy and (marker == 0 or 0xd0 <= marker <= 0xd7):
            continue
        if marker == 0xd9:
            return pos
        entropy = False
        if marker in (0, 0xd8) or 0xd0 <= marker <= 0xd7:
            raise ValueError('unexpected standalone marker')
        if marker == 1:
            continue
        if pos+2 > len(blob):
            break
        size = int.from_bytes(blob[pos:pos+2], 'big')
        if size < 2 or pos+size > len(blob):
            raise ValueError('truncated JPEG segment')
        pos += size
        entropy = marker == 0xda
    raise ValueError('missing JPEG EOI')


def directory(data):
    first = struct.unpack_from('<I', data)[0]-BASE
    if not 16 <= first <= len(data) or first % 16:
        raise ValueError('bad directory extent')
    rows = []
    end = first
    for i in range(first//16):
        ptr, size, a, b = struct.unpack_from('<4I', data, i*16)
        if not size and not (a or b) and (not ptr or BASE+first <= ptr <= BASE+len(data)):
            continue
        offset = ptr-BASE
        if a or b or size <= 0 or offset < end or offset+size > len(data):
            raise ValueError(f'invalid/overlapping picture allocation {i}')
        blob = data[offset:offset+size]
        count = jpeg_end(blob) if blob.startswith(b'\xff\xd8') else len(blob)
        rows.append((i, offset, size, blob[:count]))
        end = offset+size
    return first//16, rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    data = (ROOT/'local/epl9-1101-analysis/decoded/04_0102_468e0020.decoded.bin').read_bytes()
    if len(data) != 13107136 or hashlib.sha256(data).hexdigest() != SHA:
        p.error('exact E-PL9 1.1/build 1101 picture component required')
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        p.error('output must be a new ignored local directory')
    slots, entries = directory(data)
    from PIL import Image, ImageDraw
    rows, images = [], []
    for i, offset, size, blob in entries:
        im = Image.open(io.BytesIO(blob))
        im.load()
        rows.append(dict(id=i, offset=hex(offset), allocation=size, format=im.format,
                         payload_bytes=len(blob),
                         size=im.size, sha256=hashlib.sha256(blob).hexdigest()))
        images.append((i, im.convert('RGB')))
    args.out.mkdir(parents=True)
    for (i, _, _, blob) in entries:
        suffix = '.jpg' if blob.startswith(b'\xff\xd8') else '.ico' if blob[:4] == b'\0\0\1\0' else '.bin'
        (args.out/f'p{i:03}{suffix}').write_bytes(blob)
    for start in range(0, len(images), 48):
        sheet = Image.new('RGB', (1280, 732), (30, 30, 30))
        draw = ImageDraw.Draw(sheet)
        for k, (i, im) in enumerate(images[start:start+48]):
            im.thumbnail((156, 104))
            x, y = (k % 8)*160, (k//8)*122
            sheet.paste(im, (x, y+16))
            draw.text((x, y), str(i), fill='yellow')
        sheet.save(args.out/f'sheet-{start//48}.png')
    report = dict(model='E-PL9', displayed_version='1.1', main_build='1101',
                  component=0x102, component_header_version='0100', bytes=len(data),
                  sha256=SHA, directory_base=hex(BASE), directory_slots=slots, pictures=rows,
                  formats={fmt: sum(r['format'] == fmt for r in rows) for fmt in sorted({r['format'] for r in rows})},
                  visual_watercolor_candidates=[360, 361],
                  visual_assignment_only=True,
                  camera_accessed=False, firmware_modified=False)
    (args.out/'catalog.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(slots=slots, pictures=len(rows), formats=report['formats'],
                          dimensions=sorted(set(tuple(r['size']) for r in rows)))))


if __name__ == '__main__':
    main()
