"""Compare local, manual Workspace TIFF exports without treating them as ISP proof."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_tiff(path):
    with Image.open(path) as image:
        if image.format != 'TIFF' or image.mode != 'RGB' or tuple(image.tag_v2.get(258, ())) != (8, 8, 8):
            raise ValueError('requires an 8-bit RGB TIFF; no implicit profile/depth conversion')
        profile = image.info.get('icc_profile')
        if not profile:
            raise ValueError('embedded ICC profile required for a controlled comparison')
        array = np.array(image)
        metadata = dict(file=path.name, file_sha256=sha(path.read_bytes()),
            pixel_sha256=sha(array.tobytes()), size=list(image.size), mode=image.mode,
            bits_per_sample=[8, 8, 8], icc_sha256=sha(profile), software=image.tag_v2.get(305))
    return array, metadata


def pixel_metrics(array):
    if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] != 3 or not array.size:
        raise ValueError('requires nonempty uint8 RGB pixels')
    # Channel range is a simple numerical chroma proxy, not calibrated saturation.
    ranges = array.max(axis=2).astype(np.float64)-array.min(axis=2)
    return dict(mean_rgb=array.mean(axis=(0, 1)).tolist(), mean_channel_range=float(ranges.mean()),
                zero_channel_fraction=float((array == 0).mean()),
                full_scale_channel_fraction=float((array == 255).mean()))


def compare(before, after, before_meta, after_meta):
    if before.shape != after.shape:
        raise ValueError('image geometry differs; registration/resampling is not implicit')
    if before_meta['icc_sha256'] != after_meta['icc_sha256']:
        raise ValueError('ICC profiles differ; RGB differences would be ambiguous')
    pixel_metrics(before)
    pixel_metrics(after)
    delta = after.astype(np.int16)-before.astype(np.int16)
    changed = np.any(delta != 0, axis=2)
    return dict(before=before_meta['file'], after=after_meta['file'],
                different_pixels=int(changed.sum()), different_fraction=float(changed.mean()),
                mean_abs_rgb_difference=float(np.abs(delta).mean()),
                maximum_abs_difference=int(np.abs(delta).max()),
                pixel_identical=not bool(changed.any()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reference', type=Path, required=True)
    ap.add_argument('--images', type=Path, nargs='+', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT/'local').resolve()):
        ap.error('output must be a new ignored directory under local/')
    paths = [args.reference, *args.images]
    loaded = [load_tiff(p) for p in paths]
    if loaded[0][1]['size'] != [4608, 3456]:
        raise ValueError('expected the full-size E-PL9 reference')
    comparisons = []
    for i in range(len(loaded)):
        for j in range(i+1, len(loaded)):
            a, am = loaded[i]
            b, bm = loaded[j]
            comparisons.append(compare(a, b, am, bm))
    report = dict(scope='Actual manual Workspace exports; not modified-camera ISP output',
        images=[dict(meta, **pixel_metrics(array)) for array, meta in loaded],
        comparisons=comparisons, modified_camera_pixel_cycle_verified=False)
    canvas = Image.new('RGB', (500*len(paths), 420), '#15191f')
    draw = ImageDraw.Draw(canvas)
    for i, (array, meta) in enumerate(loaded):
        preview = Image.fromarray(array)
        preview.thumbnail((492, 385))
        canvas.paste(preview, (500*i, 34))
        draw.text((500*i+8, 10), meta['file'], fill='white')
    args.out.mkdir()
    canvas.save(args.out/'comparison.jpg', quality=95)
    (args.out/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(out=str(args.out), comparisons=comparisons), indent=2))


if __name__ == '__main__':
    main()
