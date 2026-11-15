"""Build authored 31-look assets; never modify or emit camera firmware.

Catalog positions preserve the recovered authoring order, NOT native ART IDs.
Palette/resource assignment remains the responsibility of the native integrator.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from epl9_film_icons import FONT, artwork, encode_rle, svg

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'recipes/epl9-library31-ui-v1.json'


def load_catalog(path=CATALOG):
    data = json.loads(Path(path).read_text())
    rows = data['recipes']
    if len(rows) != 31 or [r['position'] for r in rows] != list(range(1, 32)):
        raise ValueError('expected exactly 31 ordered design positions')
    if [r['id'] for r in rows[:2]] != ['gold-200', 'portra-400']:
        raise ValueError('Gold 200 and Portra 400 must remain first')
    for key in ('id', 'badge'):
        if len({r[key] for r in rows}) != 31:
            raise ValueError(f'duplicate {key}')
    for row in rows:
        if not row['id'] or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in row['id']):
            raise ValueError('unsafe recipe identifier')
        if not 1 <= len(row['badge']) <= 4 or any(c not in FONT for c in row['badge']):
            raise ValueError('badge must contain 1–4 supported glyphs')
        if row.get('native_art_id') is not None:
            raise ValueError('UI asset catalog cannot assign unqualified native ART IDs')
    return data


def build(catalog, output):
    """Write a new asset folder, with no OEM assets or firmware inputs."""
    data = load_catalog(catalog)
    output = Path(output)
    if output.exists():
        raise ValueError('output already exists; do not overwrite a frozen generation')
    output.mkdir(parents=True)
    sheet = Image.new('RGB', (5 * 270, 7 * 120), '#19232d')
    draw = ImageDraw.Draw(sheet)
    assets = []
    for index, row in enumerate(data['recipes']):
        pixels = artwork(row['badge'])
        asset = output / f"{row['id']}.svg"
        asset.write_text(svg(pixels,44,32))
        # Two supported encodings, abstract index 1. Native palettes not assigned.
        sizes = {str(mode): len(encode_rle(pixels,44,32,mode)) for mode in (1,11)}
        assets.append(dict(id=row['id'],position=row['position'],badge=row['badge'],
                           svg=asset.name,pixel_sha256=hashlib.sha256(pixels).hexdigest(),
                           rle_bytes_at_44x32=sizes,native_resource_id=None))
        x,y=(index%5)*270,(index//5)*120
        icon = Image.frombytes('L',(44,32),bytes(v*255 for v in pixels)).resize((88,64),Image.Resampling.NEAREST)
        sheet.paste('#fefefe',(x+8,y+8,x+96,y+72),icon)
        draw.text((x+8,y+82),f"{row['position']:02d} {row['title']}",fill='#fefefe')
    sheet.save(output/'contact-sheet.png')
    report = dict(schema='epl9-library31-assets-v1',assets=assets,
                  source_catalog_sha256=hashlib.sha256(Path(catalog).read_bytes()).hexdigest(),
                  firmware_modified=False,install_ready=False,
                  native_palette_and_resource_binding_proven=False,
                  order_is_native_art_id=False)
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,default=CATALOG)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    build(args.catalog,args.out)
