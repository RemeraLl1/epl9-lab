"""Map a real ORF mosaic into native configuration; no TruePic pixel model."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from epl9_job_probe import (load, experiment, assert_hardware_boundary,
                            ROOT, BASE, MAIN_SHA, STOCK_SHA, RECIPES)
from epl9_completion_audit import extend_code, machine
from epl9_job_probe import invoke, RETURN, SP
from epl9_hardware_audit import RegisterReplay
from mn103_subset import Region, parse_listing


def make_source(mosaic):
    import numpy as np
    if mosaic.ndim!=2 or mosaic.dtype!=np.uint16 or mosaic.shape!=(3472,4640):
        raise ValueError('this audit requires the measured 4640x3472 uint16 mosaic')
    if int(mosaic.max())>4095:
        raise ValueError('decoded samples exceed the declared 12-bit range')
    padded=np.zeros((3472,4672),dtype='<u2')
    padded[:,:4640]=mosaic
    return dict(data=padded.tobytes(),width=4640,height=3472,stride=4672)


def format_evidence(image,code):
    # Execute the exact label lookup through the declared logging sink.
    rows=[]
    for fmt in (0x107,0x108,0x109):
        m,_,_=machine(image,code)
        result=invoke(m,0x6176799f,0x20,12,{'d0':fmt,'a0':0x10040000})
        assert result.get('pc')==RETURN and m.r['sp']==SP,result
        labels=[e['text'].strip() for e in m.events if 'text' in e]
        assert labels==['BayerBit : 12'],(fmt,labels)
        factor=image[0x608bb2fc-BASE+(fmt&255)]
        rows.append(dict(format=hex(fmt),label=labels[0],native_group_factor=factor,
            measured_stride_for_4672=(4672//factor)*64,
            physical_bit_alignment_verified=False))
    return rows


def upload_evidence(image,code,words):
    """Native register transfer only; no pixel execution or ready response."""
    path=ROOT/'local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin'
    reader=ROOT/'local/mn103-tooling/mn103-reader.exe'
    listing=subprocess.check_output([str(reader),str(path),hex(BASE),
        hex(0x60740cad-BASE),hex(0x60740cc0-BASE)],text=True)
    code=dict(code);code.update(parse_listing(listing,image,BASE))
    m,_,_=machine(image,code)
    address=0x1d000000; device=0x9f000200
    m.memory=RegisterReplay([*m.memory.regions,Region(address,struct.pack('<24I',*words))],{},
                           [device+108+4*i for i in range(24)])
    result=invoke(m,0x60740cad,0xb0,12,{'a0':device,'a1':address})
    assert result.get('pc')==RETURN and m.r['sp']==SP,result
    expected=[dict(operation='write',address=hex(device+108+4*i),value=hex(word))
              for i,word in enumerate(words)]
    assert m.memory.transactions==expected
    return dict(result=result,register_writes=expected,pixels_processed=False)


def audit(raw_path,out):
    import rawpy
    if out.exists() or not out.resolve().is_relative_to((ROOT/'local').resolve()):
        raise ValueError('new ignored local output directory required')
    with rawpy.imread(str(raw_path)) as raw:
        mosaic=raw.raw_image_visible.copy()
        if raw.white_level!=4095:
            raise ValueError('unexpected decoder white level')
        cfa=raw.raw_pattern.tolist()
        color_desc=raw.color_desc.decode('ascii')
    source=make_source(mosaic)
    image,code=load();code=extend_code(image,code)
    evidence=format_evidence(image,code)
    cases=[]
    for key in RECIPES:
        for selector in (0,2):
            for fmt in (0x108,0x109):
                case=experiment(image,code,key,0x100,selector,source_fixture=source,
                                input_format=fmt,attach_table=True)
                assert_hardware_boundary(case)
                assert case['input_configuration']['112']==hex(4672*2)
                assert not case['cpu_source_reads']
                assert case['connected_color']['bytes_checked']==5200
                case['truepic_pixels_produced']=False
                case['color_parameters']='existing diagnostic marker, uncalibrated film slot'
                cases.append(case)
    zero_source=dict(source,data=bytes(len(source['data'])))
    controls=[]
    for key in RECIPES:
        zero=experiment(image,code,key,0x100,0,source_fixture=zero_source,
                        input_format=0x108,attach_table=True)
        assert_hardware_boundary(zero)
        real=next(case for case in cases if case['key']==hex(key) and case['selector']==0
                  and case['input_format']=='0x108')
        assert zero['source_fixture']['sha256']!=real['source_fixture']['sha256']
        assert zero['connected_color']['output_sha256']==real['connected_color']['output_sha256']
        assert zero['input_register_words']==real['input_register_words']
        assert not zero['cpu_source_reads'] and not zero['output_changed']
        controls.append(dict(key=hex(key),zero_payload_sha256=zero['source_fixture']['sha256'],
            same_configuration=True,zero_cpu_source_reads=True,output_unchanged=True))
    report=dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',main_build='1101',
        stock_bytes=104552480,stock_sha256=STOCK_SHA,main_bytes=len(image),main_sha256=MAIN_SHA,
        input_bytes=raw_path.stat().st_size,input_sha256=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        decoded_cfa_indices=cfa,decoded_color_desc=color_desc,source_sha256=hashlib.sha256(source['data']).hexdigest(),
        source_bytes=len(source['data']),source_geometry=[4640,3472],source_stride=4672,
        declared_active_window=[0,0,4608,3456],camera_crop_verified=False,
        candidate_formats=evidence,cases=cases,source_samples_present=True,
        zero_payload_controls=controls,register_upload=upload_evidence(image,code,cases[0]['input_register_words']),
        camera_accessed=False,firmware_modified=False,full_pixel_cycle_passed=False,
        limitations=['no physical TruePic executor or verified pixel backend',
                     'expanded 12-bit hardware bit alignment remains a candidate contract',
                     'CFA/WB/black-level/crop mapping to real firmware caller remains unqualified',
                     'Gold/Portra numerical recipes remain uncalibrated diagnostic markers'],
        source_code_sha256={name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in
            ('epl9_raw_input_audit.py','epl9_job_probe.py','epl9_completion_audit.py','mn103_subset.py','mn103_calls.py')})
    out.mkdir(parents=True)
    (out/'expanded-bayer-candidate.bin').write_bytes(source['data'])
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not __debug__:
        parser.error('assertions required')
    report=audit(args.raw,args.out)
    print(json.dumps(dict(cases=len(report['cases']),source_bytes=report['source_bytes'],
                          candidate_formats=report['candidate_formats'],cpu_source_reads=0,
                          full_pixel_cycle_passed=False)))


if __name__=='__main__':
    main()
