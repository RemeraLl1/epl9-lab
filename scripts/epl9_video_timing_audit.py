"""Offline clock/frame-period evidence for exact E-PL9 stock build 1101.

Checks static instructions and data only. No camera interface, firmware patches,
or invented hardware clock rates. Outputs are restricted to a new local/ path.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from epl9_video_audit import (
    ROOT, BASE, MAIN_NAME, MAIN_SHA, STOCK_SHA, verified_input,
    checked_listing, local_output,
)
from epl9_video_deep_audit import AUX_BASE, AUX_NAME, AUX_SHA, hash_target, require

MAIN_WINDOWS = {
    'main_hardware_counter': (0x60401e69, 0x60401e82),
    'main_counter_wrap_constant': (0x60451954, 0x6045195d),
    'long_exposure_period_diagnostic_fields': (0x605ef580, 0x605ef5a6),
    'sensor_hd_time_diagnostic_fields': (0x605ef633, 0x605ef659),
    'frame_period_descriptor_copy': (0x605eea39, 0x605eea5a),
    'frame_period_rate_classifier': (0x605eebc3, 0x605eebff),
    'period_scheduler_call': (0x605edd21, 0x605edd6b),
    'camera_request_timestamp': (0x605d5fcd, 0x605d5fe0),
    'video_pts_source': (0x607b9f2f, 0x607b9faf),
    'video_pts_cadence': (0x607b9faf, 0x607ba084),
    'video_pts_and_delivery_clock': (0x607ba2d6, 0x607ba366),
    'model_definition_transport_setup': (0x605e3403, 0x605e3434),
    'model_definition_receive_dispatch': (0x605e3a07, 0x605e3a27),
    'rejected_coefficient_record_copy': (0x605d91c0, 0x605d91ea),
}
AUX_WINDOWS = {
    'component_phase_counter': (0x4000b797, 0x4000b7a7),
    'component_phase_delta': (0x4000b7f5, 0x4000b808),
    'component_system_timer': (0x4001753b, 0x40017583),
    'component_roll_timer': (0x400172d6, 0x4001731d),
    'component_timer_comparator_copy': (0x4000989b, 0x400098bc),
}
MAIN_ANCHORS = {
    0x60401e69: 'call\t0x60401e71,[],0',
    0x60401e71: 'mov\t(0x9890014c),d1',
    0x60401e77: 'mov\t1073741823,d0',
    0x60401e7d: 'sub\td1,d0',
    0x60451954: 'mov\t1073741823,d0',
    0x605ef586: 'mov\t(0x625a5a10),d0',
    0x605ef599: 'mov\t(0x625a5a14),d0',
    0x605ef633: 'movhu\t(0x625a5906),d0',
    0x605ef646: 'mov\t(0x625a5908),d0',
    0x605eea3d: 'movhu\td0,(30,a0)',
    0x605eea43: 'mov\td0,(32,a0)',
    0x605eebd5: 'mov\t60,d0',
    0x605eebd7: 'cmp\t18333,d1',
    0x605edd3d: 'call\t0x605d737b,[d2,d3],20',
    0x605edd62: 'call\t0x605d7294,[d2,d3,a2,a3],20',
    0x605d5fd3: 'call\t0x60401e69,[],4',
    0x605d5fdd: 'mov\td0,(16,a2)',
    0x607b9f41: 'mov\t(104,a0),d0',
    0x607b9f8b: 'mov\td1,(d0,a0)',
    0x607b9f9e: 'mov\td1,(56,sp)',
    0x607b9fb1: 'add\t-2396,a2',
    0x607b9fbd: 'add\t1620077260,d0',
    0x607ba01c: 'mov\t1502,d3',
    0x607ba027: 'cmp\t1,d1',
    0x607ba02b: 'mov\t1501,d3',
    0x607ba05e: 'mov\t9000000,d3',
    0x607ba077: 'mov\td0,(d1,a3)',
    0x607ba2e4: 'mov\t(56,sp),d0',
    0x607ba308: 'call\t0x60401e69,[],4',
    0x607ba30f: 'mov\td0,(28,sp)',
    0x607ba34a: 'calls\t(a2)',
    0x605e341c: 'mov\t1616787395,d0',
    0x605e3422: 'mov\td0,(8,a0)',
    0x605e3a07: 'cmp\t32,d1',
    0x605e3a0e: 'call\t0x605d8971,[d2,d3,a2,a3],168',
    0x605e3a1e: 'call\t0x605d8c7a,[d2,d3,a2,a3],160',
    0x605d91c8: 'add\t8244,d0',
    0x605d91d6: 'mov\t(8,a3),d0',
}
AUX_ANCHORS = {
    0x4000b797: 'movhu\t(0x9c050010),d0',
    0x4000b7fc: 'mov\t50000,d0',
    0x4001753f: 'movbu\td0,(5,sp)',
    0x40017545: 'mov\t50000,d0',
    0x4001754b: 'movhu\td0,(8,sp)',
    0x40017559: 'clr\td0',
    0x4001755c: 'call\t0x400097d1,[d2,d3,a2,a3],24',
    0x40017566: 'call\t0x40009884,[d2,d3,a2,a3],20',
    0x400172eb: 'movbu\td1,(5,sp)',
    0x400172f1: 'mov\t12500,d1',
    0x400172f4: 'movhu\td1,(8,sp)',
    0x400098b4: 'movhu\t(4,a0),d0',
    0x400098ba: 'movhu\td0,(a1)',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reader', type=Path, default=default_reader())
    args = parser.parse_args()
    out = local_output(args.out)
    verified_input(ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN',104552480,STOCK_SHA)
    decoded_dir = ROOT/'local/epl9-1101-analysis/decoded'
    main_path, aux_path = decoded_dir/MAIN_NAME, decoded_dir/AUX_NAME
    data = verified_input(main_path,26214336,MAIN_SHA)
    aux = verified_input(aux_path,219104,AUX_SHA)
    # Register metadata is data, not an executable initialization routine.
    timer27 = struct.unpack_from('<5I',data,0x604a0700-BASE+27*20)
    require(timer27 == (0x9890006c,0x989000dc,0x9890014c,0,0),'main timer table changed')
    timer0 = struct.unpack_from('<8I',aux,0x4000ecb8-AUX_BASE)
    timer2 = struct.unpack_from('<8I',aux,0x4000ecb8-AUX_BASE+2*32)
    require(timer0[3] == 0x9c050008 and timer0[5] == 0x9c050010,
            'component timer-0 metadata changed')
    require(timer2[3] == 0x9c050048,'component timer-2 metadata changed')
    require(hash_target(data,BASE,0x60906acc,16,5994-2396) == 0x607ba01c,
            '5994 PTS branch changed')
    for address,text in [(0x605fe1da,b'VDcycle   '),(0x605fe1e5,b'LSEXPcycle'),
                         (0x605fe23d,b'vd_hd     '),(0x605fe248,b'vd_time   '),
                         (0x60905512,b'[Vid] ID:%d PTS:%d Addr:%X Switch:%01d timecode:%d time:%d')]:
        off=address-BASE
        require(data[off:off+len(text)+1] == text+b'\0',f'string changed: {address:#x}')
    # Reject the tempting 36-byte record lead: the selected ROM data consists
    # of coefficient bit patterns. No conversion to pixel/line time is claimed.
    coefficient_index = [struct.unpack_from('<4I',data,0x605744f0-BASE+i*16) for i in range(19)]
    require(coefficient_index[0] == (0x15,32,0x60570d78,0x60571178),
            'coefficient index changed')
    listings={}; count=0
    for path,image,base,windows,anchors in [
        (main_path,data,BASE,MAIN_WINDOWS,MAIN_ANCHORS),
        (aux_path,aux,AUX_BASE,AUX_WINDOWS,AUX_ANCHORS)]:
        decoded={}
        for name,(start,stop) in windows.items():
            verify_reader(args.reader)
            listing=subprocess.check_output([str(args.reader.resolve()),str(path.resolve()),
                                             hex(base),hex(start-base),hex(stop-base)],text=True)
            decoded.update(checked_listing(listing,image,start,stop,base=base))
            listings[name]=listing
        for address,expected in anchors.items():
            require(decoded.get(address)==expected,
                    f'anchor {address:#x}: expected {expected!r}, got {decoded.get(address)!r}')
        count+=len(anchors)
    report=dict(model='Olympus PEN E-PL9',model_id='1330',displayed_version='1.1',
                internal_main_build='1101',stock_bytes=104552480,stock_sha256=STOCK_SHA,
                inputs=[dict(name=MAIN_NAME,bytes=len(data),sha256=MAIN_SHA,base=hex(BASE)),
                        dict(name=AUX_NAME,bytes=len(aux),sha256=AUX_SHA,base=hex(AUX_BASE))],
                reader_sha256=verify_reader(args.reader),
                main_counter=dict(register='0x9890014c',subtract_from='0x3fffffff',
                                  absolute_tick_rate_verified=False),
                component_counters=dict(timer0=list(timer0),timer2=list(timer2),
                                        period_values=[50000,12500],absolute_tick_rate_verified=False),
                video_pts=dict(rate_key=5994,increments=[1501,1502],
                               generation='cadence accumulator',exposure_clock_mapping_verified=False),
                full_field_60_timing_verified=False,camera_commands_sent=False,
                checked_instruction_anchors=count,windows=len(listings))
    out.mkdir(parents=True)
    for name,listing in listings.items():
        (out/(name+'.tsv')).write_text(listing,encoding='utf-8')
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(out=str(out),anchors=count,windows=len(listings))))


if __name__=='__main__':
    main()
