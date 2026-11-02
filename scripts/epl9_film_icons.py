"""Author small film badges and round-trip their RLE; never patch firmware."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from epl9_osd_audit import ROOT, load_decoder, verified_bytes, MAIN_SHA, OSD_SHA

FONT = {
    'G': ('01110','10000','10000','10111','10001','10001','01110'),
    'P': ('11110','10001','10001','11110','10000','10000','10000'),
    '2': ('01110','10001','00001','00010','00100','01000','11111'),
    '4': ('00010','00110','01010','10010','11111','00010','00010'),
    '0': ('01110','10001','10001','10001','10001','10001','01110'),
}
TARGETS = {4387: 'G200', 4388: 'P400', 4420: 'G200', 4421: 'P400',
           4458: 'G200', 4459: 'P400', 4556: 'G200', 4557: 'P400'}


def artwork(label, width=44, height=32):
    """Original grid drawing: cassette, spindle and four hand-built glyphs."""
    canvas = Image.new('L', (44, 32))
    d = ImageDraw.Draw(canvas)
    d.rectangle((9, 3, 26, 5), fill=1)
    d.rectangle((4, 6, 32, 27), outline=1, width=2)
    d.rectangle((6, 8, 30, 9), fill=1)
    d.rectangle((6, 24, 30, 25), fill=1)
    d.line([(33, 12),(39, 12),(39, 25),(33,25)], fill=1, width=2)
    for y in (15, 20):
        d.rectangle((35, y, 36, y+1), fill=1)
    for char_index, char in enumerate(label):
        for y, row in enumerate(FONT[char]):
            for x, value in enumerate(row):
                if value == '1':
                    canvas.putpixel((7+char_index*6+x, 13+y), 1)
    return canvas.resize((width, height), Image.Resampling.NEAREST).tobytes()


def svg(pixels, width, height, color='#fefefe'):
    rows = []
    for y in range(height):
        x = 0
        while x < width:
            if not pixels[y*width+x]:
                x += 1
                continue
            end = x+1
            while end < width and pixels[y*width+end]:
                end += 1
            rows.append(f'<rect x="{x}" y="{y}" width="{end-x}" height="1"/>')
            x = end
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" shape-rendering="crispEdges">\n'
            f'<g fill="{color}">\n'+'\n'.join(rows)+'\n</g>\n</svg>\n')


def encode_rle(pixels, width, height, mode=11):
    """Own encoder from documented bit layout; cross-checked by pinned decoder."""
    if not 1 <= width <= 1024 or not 1 <= height <= 1024 or len(pixels) != width*height:
        raise ValueError('invalid pixel extent')
    ibits, rbits, tbits = {1: (2,2,4), 11: (8,4,12)}[mode]
    if max(pixels) >= 1 << ibits:
        raise ValueError('palette index does not fit mode')
    tokens, pos = [], 0
    while pos < len(pixels):
        value, end = pixels[pos], pos+1
        while end < min(len(pixels), pos+(1 << rbits)) and pixels[end] == value:
            end += 1
        tokens.append((value << rbits) | (end-pos-1))
        pos = end
    w, h = width-1, height-1
    result = bytearray([h & 255, (h >> 8) | ((w & 15) << 4), w >> 4, mode])
    per = 64 // tbits
    for start in range(0, len(tokens), per):
        group = tokens[start:start+per]
        word = sum(t << (i*tbits) for i,t in enumerate(group))
        size = 8 if len(group) == per else (len(group)*tbits+7)//8
        result.extend(word.to_bytes(size, 'little'))
    return bytes(result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        p.error('output must be new and under ignored local/')
    decoded = ROOT/'local/epl9-1101-analysis/decoded'
    main_path, osd_path = decoded/'00_0100_406e0020.decoded.bin', decoded/'01_0101_421e0020.decoded.bin'
    verified_bytes(main_path, MAIN_SHA, 26214336)
    verified_bytes(osd_path, OSD_SHA, 26214336)
    decoder = load_decoder()
    osd = decoder.OSD(osd_path, main_path)
    palette = next(p['entries'] for p in osd.palettes() if p['address'] == 0x6151b980)
    args.out.mkdir(parents=True)
    rows, preview = [], []
    targets = [(str(i), osd.descriptor(i), label, 11) for i, label in TARGETS.items()]
    targets += [(f'A{i:03X}', osd.symbol(i)[0], label, 1)
                for i, label in [(0x76,'G200'), (0x77,'P400')]]
    for ident, row, label, mode in targets:
        w, h = row['width'], row['height']
        ink = 3 if mode == 1 else 103 if ident in ('4420','4421') else 22 if ident in ('4556','4557') else 4
        pixels = bytes(ink if v else 0 for v in artwork(label,w,h))
        encoded = encode_rle(pixels,w,h,mode)
        capacity = row['encoded_bytes']
        fits = len(encoded) <= capacity
        payload = encoded.ljust(capacity, b'\0') if fits else encoded
        back, dw, dh, dm, used = decoder.decode_rle(payload,w,h)
        assert (back,dw,dh,dm) == (pixels,w,h,mode)
        assert used <= len(encoded)
        (args.out/f'{ident}-{label}.rle').write_bytes(payload)
        pal = decoder.level_palette(palette) if mode == 1 else palette
        im = decoder.rgba_image(pixels,w,h,pal) if mode == 1 else decoder.palette_image(pixels,w,h,pal)
        im.save(args.out/f'{ident}-{label}.png')
        preview.append((f'{ident}  {label}  {len(encoded)}/{capacity}',im.convert('RGBA')))
        rows.append(dict(resource=ident,recipe=label,width=w,height=h,mode=mode,
            encoded_bytes=len(encoded),capacity=capacity,fits=fits,roundtrip=True,
            candidate_palette_index=ink,sha256=hashlib.sha256(payload).hexdigest()))
    decoder.contact_sheet(preview,args.out/'film-icons.png',cols=2,cell=(300,112))
    for label in ('G200','P400'):
        (args.out/f'{label}.svg').write_text(svg(artwork(label),44,32),encoding='utf-8')
    report = dict(model='E-PL9',displayed_version='1.1 (owner report)',main_build='1101',
        main=dict(bytes=26214336,sha256=MAIN_SHA),osd=dict(bytes=26214336,sha256=OSD_SHA),
        camera_accessed=False,firmware_modified=False,assets=rows,
        limits=['Candidate palette; runtime palette/screen bindings not fully traced.',
                'Standalone encoded candidates only; no firmware payload changed.',
                'Generic ART12 assets and shared Roman numerals intentionally untouched.'])
    (args.out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
