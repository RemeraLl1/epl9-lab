"""Prepare the two E-PL9 v3 ORF trials and compare owner-exported scene TIFFs.

This automates byte validation and pixel comparisons, not Olympus RAW rendering.
Existing neutral ORFs/TIFFs are read-only controls. All new files stay in local/.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageCms, ImageDraw

from epl9_workspace_bridge import (ROOT, MAIN, MAIN_SHA, LAUREL, Epl9Orf,
                                  library_key, prepare, sha, verify_copy)
from epl9_tonal_drafts import prepare_tonal, raw_checks
from epl9_workspace_gamma_probe import apply_active_curve
from epl9_workspace_pixels import load_tiff, compare, pixel_metrics


def natural_copy(source):
    """Normalize the qualified PictureMode halfword; preserve all source bytes else."""
    layout = Epl9Orf(source)
    maker = layout.ifd(layout.maker_base+12, layout.maker_base)
    camera = layout.ifd(layout.maker_base+layout.integers(maker[0x2020])[0], layout.maker_base)
    entry = camera[0x520]
    mode = layout.integers(entry)
    if (entry['type'], entry['count']) != (3, 2) or mode not in ((2, 2), (4, 2), (5, 2)):
        raise ValueError('unqualified source PictureMode')
    for tag in (0x521, 0x523, 0x524):
        if layout.integers(camera[tag]) != (0, -2, 2):
            raise ValueError('nonzero source saturation/contrast/sharpness needs separate qualification')
    if any(layout.integers(camera[tag]) != (0,) for tag in (0x525, 0x526)):
        raise ValueError('source filter/tone metadata is not neutral')
    result = bytearray(source)
    struct.pack_into('<H', result, entry['offset'], 2)
    verify_copy(source, result, [(entry['offset'], 2)], layout.strips)
    return bytes(result), list(mode)


def new_output(path):
    path = path.resolve()
    if path.exists() or not path.is_relative_to((ROOT/'local').resolve()):
        raise ValueError('output must be a new directory under ignored local/')
    return path


def json_write(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


def prepare_batch(raw_dir, neutral_manifest, out):
    out = new_output(out)
    image, key = MAIN.read_bytes(), library_key(LAUREL)
    if sha(image) != MAIN_SHA:
        raise ValueError('requires exact E-PL9 build 1101 main')
    documents = {str(v): json.loads((ROOT/f'recipes/epl9-film-drafts-v{v}.json').read_text())
                 for v in (0, 1, 2)}
    knots = {row['watercolor_key']: row['tone_knots'] for row in documents['1']['recipes']}
    neutral = json.loads(neutral_manifest.read_text(encoding='utf-8'))
    refs = {Path(row['source_file']).name: row for row in neutral['files']}
    paths = sorted(raw_dir.glob('*.ORF'))
    if not paths or len(refs) != len(neutral['files']) or {p.name for p in paths} != set(refs):
        raise ValueError('source batch must match the neutral manifest exactly')
    rows, pending = [], {}
    for path in paths:
        source = path.read_bytes()
        ref = refs[path.name]
        if sha(source) != ref['source_sha256'] or len(source) != ref['source_bytes']:
            raise ValueError(f'source provenance mismatch: {path.name}')
        natural, old_mode = natural_copy(source)
        # Reproduce the neutral control, rather than trust only a matching filename.
        _, neutral_cases = prepare(natural, image, key)
        control = next(data for name, data, _ in neutral_cases if name == 'epl9-cmio-neutral')
        neutral_orf = Path(ref['neutral_file'])
        if sha(control) != ref['neutral_sha256'] or neutral_orf.read_bytes() != control:
            raise ValueError(f'neutral control cannot be reproduced: {path.name}')
        neutral_tiff = neutral_manifest.parent/'NEUTRAL-TIFF'/f'{path.stem}__NEUTRAL.tif'
        _, neutral_meta = load_tiff(neutral_tiff)
        _, cases = prepare_tonal(natural, image, key, documents['0'], documents['2'],
                                 allow_distinct_wb=True)
        final_cases, outputs = [], []
        for recipe, data, _, detail in cases:
            result, curve = apply_active_curve(data, image, key, knots[recipe['watercolor_key']])
            curve_bytes = struct.pack('<256H', *curve)
            name = recipe['name'].replace('-draft-v2', '-v3')
            filename = f'{path.stem}__{name}.ORF'
            final_cases.append((recipe, result, curve_bytes, detail))
            pending[filename] = result
            outputs.append(dict(file=filename, sha256=sha(result), bytes=len(result),
                watercolor_key=recipe['watercolor_key'], active_cmio_t_offset='0xde6',
                curve_sha256=sha(curve_bytes), tone_knots=knots[recipe['watercolor_key']],
                inherited_v2_metadata=detail))
        checks = raw_checks(source, final_cases)
        if path.read_bytes() != source:
            raise ValueError('original changed during preparation')
        rows.append(dict(source_file=str(path.resolve()), source_sha256=sha(source),
            source_bytes=len(source), original_picture_mode=old_mode,
            normalized_picture_mode=[2, 2], neutral_orf=str(neutral_orf),
            neutral_sha256=sha(control), neutral_tiff=str(neutral_tiff.resolve()),
            neutral_tiff_metadata=neutral_meta, raw_checks=checks, outputs=outputs))
        print(json.dumps(dict(prepared=path.name, recipes=len(outputs),
                              raw_mosaics_unchanged=True)), flush=True)
    report = dict(schema='epl9-film-scene-batch-v3',
        scope='Uncalibrated two-recipe Workspace trials; manual export required; no TruePic execution',
        model='E-PL9', owner_body_version='1.1', downloaded_main_build='1101',
        main_bytes=len(image), main_sha256=MAIN_SHA, recipe_documents=documents,
        source_count=len(rows), output_count=len(pending), camera_accessed=False,
        firmware_written=False, workspace_exports_verified=False, scenes=rows)
    out.mkdir(parents=True)
    for name, data in pending.items():
        with (out/name).open('xb') as stream:
            stream.write(data)
    json_write(out/'manifest.json', report)
    print(json.dumps(dict(out=str(out), files=len(pending), total_bytes=sum(map(len, pending.values())))))


def detailed_comparison(before, after, before_meta, after_meta):
    result = compare(before, after, before_meta, after_meta)
    code = before @ np.array([0.2126, 0.7152, 0.0722])
    after_code = after @ np.array([0.2126, 0.7152, 0.0722])
    bands = []
    for low, high in zip((0, 32, 64, 128, 192, 224), (32, 64, 128, 192, 224, 256)):
        mask = (code >= low) & (code < high)
        count = int(mask.sum())
        bands.append(dict(low=low, high=high, pixels=count,
            mean_before=float(code[mask].mean()) if count else None,
            mean_after=float(after_code[mask].mean()) if count else None))
    return dict(result, new_zero_channels=int(((before > 0) & (after == 0)).sum()),
        new_full_scale_channels=int(((before < 255) & (after == 255)).sum()),
        channels=int(after.size), bands=bands,
        band_units='Weighted RGB code values in the common ICC space, not linear luminance')


def display_preview(path):
    # Metrics retain native ICC values. Only the review JPEG converts to display sRGB.
    import io
    with Image.open(path) as im:
        profile = im.info.get('icc_profile')
        if not profile:
            raise ValueError('missing preview ICC')
        preview = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                                            ImageCms.createProfile('sRGB'), outputMode='RGB')
    preview.thumbnail((480, 440))
    return preview


def compare_batch(batch, out):
    out = new_output(out)
    manifest = json.loads((batch/'manifest.json').read_text(encoding='utf-8'))
    if manifest['schema'] != 'epl9-film-scene-batch-v3':
        raise ValueError('unexpected batch manifest')
    rows, previews = [], []
    for scene in manifest['scenes']:
        reference = Path(scene['neutral_tiff'])
        before, before_meta = load_tiff(reference)
        if before_meta != scene['neutral_tiff_metadata']:
            raise ValueError('neutral TIFF changed after preparation')
        comparisons, image_paths = [], [reference]
        for output in scene['outputs']:
            path = batch/output['file']
            if sha(path.read_bytes()) != output['sha256']:
                raise ValueError('trial ORF changed after preparation')
            export = path.with_suffix('.tif')
            after, after_meta = load_tiff(export)
            comparisons.append(dict(metadata=after_meta, metrics=pixel_metrics(after),
                versus_neutral=detailed_comparison(before, after, before_meta, after_meta)))
            image_paths.append(export)
        rows.append(dict(source_sha256=scene['source_sha256'], reference=before_meta,
                         reference_metrics=pixel_metrics(before), recipes=comparisons))
        panel = Image.new('RGB', (1500, 500), '#181b20')
        draw = ImageDraw.Draw(panel)
        for index, path in enumerate(image_paths):
            panel.paste(display_preview(path), (index*500+10, 40))
            draw.text((index*500+10, 10), path.stem, fill='white')
        previews.append((Path(scene['source_file']).stem+'.jpg', panel))
        print(json.dumps(dict(compared=Path(scene['source_file']).name)), flush=True)
    out.mkdir(parents=True)
    for name, panel in previews:
        panel.save(out/name, quality=94, icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes())
    json_write(out/'results.json', dict(schema='epl9-film-scene-review-v3',
        scope='Measured Workspace pixels versus COLOR-neutral, not modified-camera output',
        batch_manifest_sha256=sha((batch/'manifest.json').read_bytes()), scenes=rows))
    print(json.dumps(dict(out=str(out), compared=len(rows))))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--raw-dir', type=Path, required=True)
    prep.add_argument('--neutral-manifest', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    review = sub.add_parser('compare')
    review.add_argument('--batch', type=Path, required=True)
    review.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.command == 'prepare':
        prepare_batch(args.raw_dir, args.neutral_manifest, args.out)
    else:
        compare_batch(args.batch, args.out)


if __name__ == '__main__':
    main()
