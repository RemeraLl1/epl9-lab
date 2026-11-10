"""Offline E-PL9 update/recovery evidence. No camera, network or flash interface.

Native validation uses small RAM-only fixtures and explicit diagnostic/backend
boundaries. No installable update, stock-restore BIN or patched firmware is saved.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_color_audit import MAIN_SHA, STOCK_SHA
from epl9_video_audit import ROOT, BASE, MAIN_NAME, verified_input, checked_listing, local_output
from mn103_subset import Memory, Region, Fault, parse_listing
from mn103_calls import CallMachine

# Historical Windows identity, not the digest of a portable build.
READER_SHA='e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae'
WINDOWS={
    'shared_updater':(0x6100440a,0x610051ab),
    'checksum_and_descrambler':(0x61003869,0x610039fd),
    'header_helpers':(0x604d54c0,0x604d55c5),
    'address_translation':(0x60445069,0x604450ad),
    'prefix_compare':(0x604bb098,0x604bb0cc),
}
STATIC_WINDOWS={
    'sd_client':(0x610039fd,0x61003c01),
    'sd_file_reader':(0x61003c01,0x61003e85),
    'update_service':(0x61003e85,0x6100440a),
    'write_selector':(0x604a0f8b,0x604a11a5),
    'access_mode':(0x604a0c14,0x604a0c1d),
    'program_readback_wrapper':(0x6043a0d9,0x6043a13d),
    'low_level_writer':(0x604014c6,0x604016cc),
    'no_file_fallback':(0x605c9ae6,0x605c9b0f),
    'usb_application_start':(0x6105c1a8,0x6105c1ee),
    'message_to_task_89':(0x60f59c8e,0x60f59ca9),
}
BUFFER,STACK,SP,RESULT,RETURN=0x10000000,0x18000000,0x18008000,0x19000000,0x1a000000
ORDER=(1,3,0,2,6,4,7,5,11,10,9,8,13,14,12,15)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decoded_payload(encoded):
    if not encoded or len(encoded)%16:
        raise ValueError('invalid encoded span')
    plain=bytearray(len(encoded))
    for i,j in enumerate(ORDER):
        plain[i::16]=encoded[j::16].translate(bytes(x^255 for x in range(256)))
    return bytes(plain)


def inspect_package(raw):
    """Strict host metadata/integrity check; never a camera acceptance claim."""
    if not raw:
        raise ValueError('empty package')
    rows=[];offset=0;kinds=set()
    while offset<len(raw):
        if len(raw)-offset<64:
            raise ValueError('truncated header/trailer')
        h=raw[offset:offset+32]
        size=struct.unpack_from('<I',h,12)[0]
        kind=struct.unpack_from('<H',h,20)[0]
        if (h[:4]!=b'OE\x13\x30' or not size or size%16 or
                kind not in (0x100,0x101,0x106,0x10e,0x102) or kind in kinds):
            raise ValueError('unexpected model/size/component')
        end=offset+size+64
        if end>len(raw):
            raise ValueError('component exceeds package')
        trailer=raw[end-32:end]
        if h[:28]!=trailer[:28] or h[28:32]!=bytes(4):
            raise ValueError('header/trailer mismatch')
        plain=decoded_payload(raw[offset+32:end-32])
        # Independent host arithmetic, checked against native fixture cases.
        from array import array
        import sys
        words=array('I');words.frombytes(h+plain+trailer)
        if sys.byteorder!='little':words.byteswap()
        if sum(words)&0xffffffff:
            raise ValueError('bad checksum')
        rows.append(dict(offset=hex(offset),kind=hex(kind),model='1330',
            header_build=f'{struct.unpack_from("<H",h,16)[0]:04x}',
            destination=hex(struct.unpack_from('<I',h,8)[0]),
            package_bytes=size+64,payload_bytes=size,decoded_sha256=sha(plain)))
        offset=end;kinds.add(kind)
    return rows


def fixture(kind=0x100,model=0x1330,address=0x406e0000,build=0x1101,size=256):
    """Nonfunctional synthetic component; its bytes remain in host RAM only."""
    if size<16 or size%16:
        raise ValueError('fixture payload must be positive and 16-byte aligned')
    header=bytearray(32);header[:2]=b'OE'
    struct.pack_into('>H',header,2,model)
    struct.pack_into('<IIHHH',header,8,address,size,build,0,kind)
    plain=bytes((i*17+3)&255 for i in range(size))
    trailer=bytearray(header)
    total=sum(struct.unpack('<'+str((size+64)//4)+'I',header+plain+trailer))
    struct.pack_into('<I',trailer,28,(-total)&0xffffffff)
    encoded=bytearray(size)
    for decoded_index,encoded_index in enumerate(ORDER):
        encoded[encoded_index::16]=bytes(x^255 for x in plain[decoded_index::16])
    return bytes(header+encoded+trailer)


class Boundary:
    def __init__(self,name,abis,backend_result=0):
        self.name,self.abis,self.backend_result=name,set(abis),backend_result

    def validate(self,m,mask,frame):
        if (mask,frame) not in self.abis:
            raise Fault(f'undeclared {self.name} ABI {mask:#x}/{frame}')

    def apply(self,m):
        if self.name=='flash-request-trap':
            source,length=m.r['a1'],m.r['d0']
            if not BUFFER<=source<source+length<=BUFFER+len(m.package):
                raise Fault('backend request outside fixture')
            raw=bytes(m.memory.read(source+i,1) for i in range(length))
            detail=dict(destination=hex(m.r['a0']),source=hex(source),bytes=length,
                        mode=m.r['d1'],decoded_sha256=sha(raw),injected_result=self.backend_result)
            m.r['d0']=self.backend_result
            return detail
        m.r['d0']=0
        return dict(effect='diagnostic/notification suppressed; no validation result supplied')


def load_code(image,out,reader):
    verify_reader(reader)
    code={};listings={}
    for name,(start,end) in (WINDOWS|STATIC_WINDOWS).items():
        listing=subprocess.check_output([str(reader.resolve()),str((ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME).resolve()),
             hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        checked_listing(listing,image,start,end)
        native=parse_listing(listing,image,BASE)
        if any(code[a]!=native[a] for a in code.keys()&native.keys()):
            raise ValueError('conflicting instruction boundaries')
        if name in WINDOWS:code.update(native)
        listings[name]=listing
    if out:
        for name,listing in listings.items():
            (out/(name+'.tsv')).write_text(listing,encoding='utf8')
    return code


def probe(image,code,package,mode=0,backend_result=0,holes=(),capture=False):
    if mode not in (0,1,2) or not package:
        raise ValueError('undeclared updater mode or empty fixture')
    models={
        0x60401fcc:Boundary('diagnostic',[(0x30,28)]),
        0x6040227a:Boundary('diagnostic-number',[(0xa0,40)]),
        0x605c99f4:Boundary('progress-notification',[(0xf0,72)]),
        0x605c9b0f:Boundary('error-notification',[(0xf0,64)]),
        0x604a0f8b:Boundary('flash-request-trap',[(0xf0,36)],backend_result),
    }
    spans=[];cursor=BASE
    for lo,hi in sorted(holes):
        if not cursor<=lo<hi<=BASE+len(image):
            raise ValueError('invalid isolation hole')
        if lo>cursor:spans.append(Region(cursor,image[cursor-BASE:lo-BASE],False,'main slice'))
        cursor=hi
    spans.append(Region(cursor,image[cursor-BASE:],False,'main slice'))
    memory=Memory([*spans,
        Region(BUFFER,bytearray(package),True,'synthetic package'),
        Region(STACK,bytearray(0x10000),True,'synthetic stack'),
        Region(RESULT,bytearray(16),True,'synthetic caller result')])
    executable={a:v for a,v in code.items() if not any(lo<=a<hi for lo,hi in holes)}
    m=CallMachine(executable,memory,{'sp':SP,'d0':len(package),'d1':mode,'a0':BUFFER,'a1':RESULT},models=models)
    m.package=package
    m.enter(0x6100440a,RETURN,0xf0,16)
    stop=m.run(0x6100440a,stops={RETURN},limit=300000)
    if stop.get('pc')!=RETURN or m.r['sp']!=SP:
        raise Fault(f'updater did not return: {stop}, registers={m.r}')
    after=bytes(memory.read(BUFFER+i,1) for i in range(len(package)))
    row=dict(mode=mode,return_value=m.r['d0'],instructions=len(m.trace),
        input_sha256=sha(package),input_bytes=len(package),
        backend_requests=[e for e in m.events if e.get('model')=='flash-request-trap'],
        events=m.events,output_package_sha256=sha(after),
        physical_writes=False,physical_recovery_proven=False)
    return (row,after) if capture else row


def run_cases(image,code):
    rows=[]
    def add(name,package,mode=0,expected=0,writes=0,**kwargs):
        r=probe(image,code,package,mode,**kwargs)
        assert r['return_value']==expected,(name,r)
        assert len(r['backend_requests'])==writes,(name,r)
        rows.append(dict(name=name,**r))
        return r
    main=fixture()
    resource=fixture(kind=0x101,address=0x421e0000,build=0x100)
    add('same-main-build-SD',main,writes=1)
    add('same-resource-build-SD',resource,writes=1)
    add('two-components-SD',main+resource,writes=2)
    add('USB-check-only',main,mode=2)
    checked,plain=probe(image,code,main,mode=2,capture=True)
    assert plain[:32]==main[:32] and plain[-32:]==main[-32:]
    assert plain[32:-32]==decoded_payload(main[32:-32])
    add('USB-commit-after-check',plain,mode=1,writes=1)
    corrupt=bytearray(main);corrupt[40]^=1
    add('bad-first-checksum',bytes(corrupt),expected=0x3211)
    corrupt_resource=bytearray(resource);corrupt_resource[40]^=1
    add('bad-later-checksum',main+bytes(corrupt_resource),expected=0x3211)
    add('wrong-model',fixture(model=0x1220),expected=0x3202)
    # Unlike some auxiliary kinds, duplicate main is accepted here; last wins.
    duplicate=add('duplicate-main-last-selected',main+main,writes=1)
    assert duplicate['backend_requests'][0]['source']==hex(BUFFER+len(main))
    add('backend-reports-failure',main,backend_result=0x3105,expected=0x3105,writes=1)
    add('ART-code-and-table-inaccessible',main,writes=1,
        holes=((0x607519b8,0x60752f56),(0x6079e1f6,0x6079f309),(0x608ee360,0x608eef34)))
    return rows


class LowerFailure(Boundary):
    def apply(self,m):
        value=self.backend_result
        m.r['d0']=value
        return dict(injected_result=value,physical_operation=False)


def backend_cases(image,code,out):
    """Native status propagation only; program/read APIs never touch storage."""
    extra={}
    for name in ('write_selector','access_mode','program_readback_wrapper'):
        extra.update(parse_listing((out/(name+'.tsv')).read_text(),image,BASE))
    result=[]
    for stage,expected in (('program',0x3101),('readback',0x3105)):
        for entry,mask,frame in ((0x6043a0d9,0xf0,28),(0x604a0f8b,0xf0,36)):
            package=fixture();plain=package[:32]+decoded_payload(package[32:-32])+package[-32:]
            models={
                0x60439f38:LowerFailure('program-boundary',[(0xf0,24)],0x3101 if stage=='program' else 0),
                0x604014c6:LowerFailure('readback-boundary',[(0xf0,32)],0x3102),
                0x6040227a:Boundary('diagnostic-number',[(0xa0,40)]),
            }
            m=CallMachine(code|extra,Memory([
                Region(BASE,image,False,'exact E-PL9 main'),
                Region(BUFFER,bytearray(plain),True,'RAM-only fixture'),
                Region(STACK,bytearray(0x10000),True,'synthetic stack'),
                Region(0x61f01098,bytearray(2),True,'native access mode'),
            ]),{'sp':SP,'a0':0x806e0000,'a1':BUFFER,'d0':len(plain),'d1':1 if entry==0x604a0f8b else 0},models=models)
            m.enter(entry,RETURN,mask,frame)
            stop=m.run(entry,stops={RETURN})
            assert stop.get('pc')==RETURN and m.r['sp']==SP,stop
            assert m.r['d0']==(0 if entry==0x604a0f8b else expected),(stage,entry,m.r)
            result.append(dict(stage=stage,entry=hex(entry),return_value=hex(m.r['d0']),
                injected_error=hex(0x3101 if stage=='program' else 0x3102),
                events=m.events,physical_writes=False))
    return result


def static_contracts(image,code,out):
    all_code=dict(code)
    for name in STATIC_WINDOWS:
        all_code.update(parse_listing((out/(name+'.tsv')).read_text(),image,BASE))
    anchors={
        0x61003f75:'call\t0x6100440a,[d2,d3,a2,a3],16',
        0x6100449c:'call\t0x610050c3,[d2,d3,a2],44',
        0x61004517:'cmp\t4912,d0',
        0x61004ff6:'call\t0x6100511c,[d2,d3,a2,a3],32',
        0x6100517d:'call\t0x604a0f8b,[d2,d3,a2,a3],36',
        0x604a10c2:'call\t0x6043a0d9,[d2,d3,a2,a3],28',
        0x604a11a1:'clr\td0',
        0x6043a0dd:'call\t0x60439f38,[d2,d3,a2,a3],24',
        0x6043a0f1:'call\t0x604014c6,[d2,d3,a2,a3],32',
        0x604015ac:'mov\t131072,d3',
        0x60401588:'mov\t2048,a0',
        0x61003ac1:'mov\t1630699575,d2',
        0x60f59c94:'movhu\t(0x60421018),d2',
    }
    for a,want in anchors.items():
        _,op,args=all_code[a]
        if op+'\t'+','.join(args)!=want:
            raise ValueError(f'instruction anchor mismatch at {a:#x}')
    records=[]
    for address,want in ((0x60418ebc,(18,0,0,0x61003e85,55,2048,0)),
                         (0x60419680,(89,0,0,0x610039fd,45,2048,0))):
        row=struct.unpack_from('<7I',image,address-BASE)
        if row!=want:raise ValueError('task descriptor mismatch')
        records.append(dict(address=hex(address),words=list(map(hex,row))))
    strings=[]
    for a,want in ((0x61327e54,b'S133????BIN'),(0x61327e60,b'E133????BIN'),
                   (0x61328037,b'DCOLYMP    ')):
        if image[a-BASE:a-BASE+len(want)]!=want:raise ValueError('selection string mismatch')
        strings.append(dict(address=hex(a),text=want.decode()))
    return dict(checked_instructions=len(anchors),task_descriptors=records,selection_strings=strings,
                power_on_selector_traced=False,independent_recovery_loader_proven=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if not __debug__:
        parser.error('assertions required')
    out=local_output(args.out)
    image=verified_input(ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME,26214336,MAIN_SHA)
    stock=verified_input(ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN',104552480,STOCK_SHA)
    reader=default_reader()
    out.mkdir()
    code=load_code(image,out,reader)
    rows=run_cases(image,code)
    components=inspect_package(stock)
    backend=backend_cases(image,code,out)
    static=static_contracts(image,code,out)
    report=dict(model='Olympus E-PL9',displayed_version='1.1 (owner report)',main_build='1101',
        stock_bytes=len(stock),stock_sha256=STOCK_SHA,main_bytes=len(image),main_sha256=MAIN_SHA,
        source_sha256=sha(Path(__file__).read_bytes()),reader_sha256=verify_reader(reader),
        stock_components=components,
        backend_status_cases=backend,static_contracts=static,
        dependencies={name:sha((ROOT/'scripts'/name).read_bytes()) for name in (
            'mn103_subset.py','mn103_calls.py','epl9_color_audit.py','epl9_video_audit.py')},
        reference_revision='539fcf1fa9eda5fdef8ede4deeab94a4691d94c3',
        camera_accessed=False,firmware_modified=False,installable_package_written=False,cases=rows)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','backend_status_cases','stock_components')},indent=2))
    print(json.dumps([dict(name=r['name'],result=hex(r['return_value']),requests=len(r['backend_requests'])) for r in rows]))


if __name__=='__main__':
    main()
