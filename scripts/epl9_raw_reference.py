"""Decode an owner's ORF/JPEG pair to ignored reference artifacts, not ART output."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def input_identity(path):
    return dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def decode_pair(raw_path,jpeg_path,out):
    import numpy as np
    import rawpy

    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('a new ignored local output directory is required')
    if raw_path.suffix.lower()!='.orf' or jpeg_path.suffix.lower() not in ('.jpg','.jpeg'):
        raise ValueError('ORF and JPEG input files required')
    with Image.open(jpeg_path) as jpeg:
        exif=jpeg.getexif()
        if str(exif.get(272,'')).strip()!='E-PL9':
            raise ValueError('JPEG must identify the E-PL9')
        jpeg.load()
        camera_size=list(jpeg.size)
        camera_preview=jpeg.copy()
        camera_preview.thumbnail((1536,1152))
    with rawpy.imread(str(raw_path)) as raw:
        pixels=raw.raw_image_visible.copy()
        if pixels.dtype!=np.uint16 or pixels.ndim!=2:
            raise ValueError('expected decoded two-dimensional uint16 mosaic')
        result=dict(rawpy_version=rawpy.__version__,numpy_version=np.__version__,
            libraw_version=rawpy.libraw_version,
            raw_size=[raw.sizes.raw_width,raw.sizes.raw_height],
            visible_size=[raw.sizes.width,raw.sizes.height],
            margins=[raw.sizes.left_margin,raw.sizes.top_margin],
            decoded_dtype=str(pixels.dtype),white_level=int(raw.white_level),
            black_levels=list(raw.black_level_per_channel),
            cfa_index_pattern=raw.raw_pattern.tolist(),color_desc=raw.color_desc.decode('ascii'),
            sample_min=int(pixels.min()),sample_max=int(pixels.max()),
            camera_whitebalance=list(raw.camera_whitebalance),
            camera_jpeg_size=camera_size,
            input_identity={'raw':input_identity(raw_path),'jpeg':input_identity(jpeg_path)},
            pairing='owner-supplied filenames; scene inspected separately, timestamps not checked',
            input_files_modified=False,camera_accessed=False,firmware_modified=False,
            host_libraw_development=True,modified_art_output=False,full_pixel_cycle_passed=False,
            processing={'use_camera_wb':True,'no_auto_bright':True,'output_bps':8},
            limitations=['decoded mosaic is not a verified firmware memory layout',
                         'RAW/JPEG dimensions differ; no crop alignment is assumed',
                         'LibRaw output is not stock TruePic rendering or a calibrated film recipe'])
        rgb=raw.postprocess(use_camera_wb=True,no_auto_bright=True,output_bps=8)
        result['host_rgb_shape']=list(rgb.shape)
    out.mkdir(parents=True)
    np.save(out/'decoded-mosaic.npy',pixels)
    Image.fromarray(rgb).save(out/'libraw-reference.png')
    preview=Image.fromarray(rgb); preview.thumbnail((1536,1152))
    preview.save(out/'libraw-preview.jpg',quality=93)
    camera_preview.save(out/'camera-jpeg-preview.jpg',quality=93)
    (out/'metadata.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,required=True)
    parser.add_argument('--jpeg',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=decode_pair(args.raw,args.jpeg,args.out)
    print(json.dumps({k:result[k] for k in ('raw_size','camera_jpeg_size','white_level',
                     'host_rgb_shape','full_pixel_cycle_passed')}))


if __name__=='__main__':
    main()
