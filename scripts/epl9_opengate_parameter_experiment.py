"""Signal-free native-fragment experiment, not a camera or sensor emulator.

Requires a privately supplied exact decoded main and qualified reader.
Writes scalar results/traces only; no OEM instruction bytes or firmware.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from epl9_video_geometry_audit import (
    WINDOWS, ANCHORS, RATE_CLASS_TABLE, probe_geometry, probe_rate_class,
    probe_aspect_geometry, probe_received_video, probe_render_layout,
    probe_repacked_fhd_pool, probe_q_pool, probe_mov_headers,
)
from epl9_video_audit import BASE, MAIN_SHA, checked_listing
from mn103_subset import parse_listing, Machine, Memory, Region
from mn103_tooling import default_reader, verify_reader


def experiment(main, reader):
    image = main.read_bytes()
    sha = hashlib.sha256(image).hexdigest()
    if len(image) != 26214336 or sha != MAIN_SHA:
        raise ValueError('Exact E-PL9 build1101 decoded main required')
    reader_sha = verify_reader(reader)
    code, decoded = {}, {}
    for name, (start, stop) in WINDOWS.items():
        listing = subprocess.check_output([str(reader.resolve()), str(main.resolve()),
            hex(BASE), hex(start-BASE), hex(stop-BASE)], text=True)
        decoded.update(checked_listing(listing, image, start, stop))
        code.update(parse_listing(listing, image, BASE))
    for at, expected in ANCHORS.items():
        if decoded.get(at) != expected:
            raise ValueError(f'Native anchor changed at {at:#x}')
    rows=[]
    table=image[RATE_CLASS_TABLE-BASE:RATE_CLASS_TABLE-BASE+36]
    for width,height in ((1920,1080),(1920,1440),(1536,1152),(3840,2160),(1921,1441)):
        for rate in (2997,5994,6000):
            for bitrate in (30000000,60000000):
                row=probe_geometry(code,width,height,rate,bitrate)
                row['rate_class_probe']=probe_rate_class(code,table,row,row['native_class'])
                row['nominal_budget_exceeded']=row['rate_class_probe']['macroblocks_per_second']>row['rate_class_probe']['nominal_table_macroblock_rate']
                rows.append(row)
    invalid=[]
    for case in ((0,1440,6000,30000000),(1920,-1,6000,30000000),(1920,1440,0,30000000)):
        try: probe_geometry(code,*case)
        except ValueError as e: invalid.append(dict(case=case,rejected_by='host input validator',reason=str(e)))
        else: raise AssertionError('Invalid control unexpectedly accepted')
    # Concrete CPU stop: continuation is not allowed to invent a driver object.
    m=Machine(code,Memory([Region(0x10000000,bytearray(1024),True,'host stack')]),{'sp':0x10000000})
    try:
        boundary=m.run(0x6169f4ee,stops=[],limit=30)
    except Exception as e:
        boundary=dict(exception=type(e).__name__,reason=str(e))
    report=dict(schema='epl9-opengate-parameter-experiment-v1',main_sha256=sha,
        reader_sha256=reader_sha,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_windows_byte_checked=len(WINDOWS),native_anchors_checked=len(ANCHORS),
        scope='isolated original MN103 fragments on declared host objects, independently entered',
        geometry_rows=rows,invalid_controls=invalid,unprovisioned_driver_continuation=boundary,
        receiver_rows=[probe_received_video(code,h,30000000) for h in (1080,1440)],
        aspect_rows=[probe_aspect_geometry(code,image,a,full_height_shadow=s)
            for a in (1,2,3,4) for s in (False,True)],
        render_rows=[probe_render_layout(code,k,h) for k in (5,6,8) for h in (None,1440)],
        repacked_pool=probe_repacked_fhd_pool(code),
        conditional_q_rows=[probe_q_pool(code,0),probe_q_pool(code,0,4147200)],
        mov_rows=[probe_mov_headers(code,1920,h,bytes.fromhex('67640028')) for h in (1080,1440)],
        sensor_emulated=False,encoder_emulated=False,frames_generated=0,wall_time_fps_measured=False,
        full_recording_call_chain_executed=False,firmware_modified=False,camera_accessed=False,
        frozen_candidate_modified=False,install_ready=False)

    assert len(rows)==30 and len(invalid)==3
    assert all((r['configuration_width'],r['configuration_height'],r['configuration_rate']) ==
               (r['width'],r['height'],r['rate_key']) for r in rows)
    target=[r for r in rows if (r['width'],r['height'],r['rate_key'])==(1920,1440,6000)]
    assert [r['native_class'] for r in target]==[6,7]
    assert all(r['nominal_budget_exceeded'] for r in target)
    assert report['repacked_pool']['seventh_allocation_native_status']==1
    assert report['repacked_pool']['release_and_recycle_passed']
    assert [r['output_dimensions'] for r in report['aspect_rows']]==[
        [1920,1440],[1920,1440],[1920,1280],[1920,1280],
        [1920,1080],[1920,1440],[1440,1440],[1440,1440]]
    assert boundary.get('exception')=='Fault' and 'unmapped access at 0x0' in boundary['reason']
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True)
    p.add_argument('--reader',type=Path,default=default_reader())
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists(): raise ValueError('Output exists: choose new report path')
    report=experiment(a.main,a.reader)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(a.out),geometry_cases=len(report['geometry_rows']),
        boundary=report['unprovisioned_driver_continuation'],frames=0)))
if __name__=='__main__': main()
