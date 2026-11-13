"""Native setters plus late gamma/HSL copies; no camera or release-hook claim."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
from epl9_workspace_bridge import BASE, MAIN_SHA
from epl9_sd_processing import descriptor, HSL, GAMMA
from epl9_sd_loader_probe import sample_recipe
from epl9_sd_recipes import pack_recipe
from mn103_subset import Region, Memory, Machine, parse_listing
from mn103_calls import CallMachine
from mn103_tooling import verify_reader

ARENA,CONFIG,STACK,OWNER,DEST=0x18000000,0x20000000,0x20002000,0x20003000,0x20004000
START,STOP=0x6074151f,0x6074178d
POINTERS=(2596,2600,2604,3124,3128,3132,3136,3140,3144,3148,3152,3156,3160)
WINDOWS=((0x6079e50e,0x6079e6a0),(0x6079d7a0,0x6079d7da),(START,STOP),
         (0x607405f3,0x60740634))

class ObservedMemory(Memory):
    def __init__(self,regions):
        super().__init__(regions); self.reads=[]
    def read(self,address,size):
        if ARENA<=address<ARENA+4096:self.reads.append((address,size))
        return super().read(address,size)


def experiment(image,code,*,overwrite=False):
    raw=pack_recipe(sample_recipe())
    desc=bytearray(descriptor(image,raw,ARENA,1,0x19000000))
    config,stack,owner,dest=bytearray(5200),bytearray(4096),bytearray(256),bytearray(12000)
    mem=ObservedMemory([Region(BASE,image),Region(ARENA,desc,True),Region(CONFIG,config,True),
                       Region(STACK,stack,True),Region(OWNER,owner,True),Region(DEST,dest,True)])
    m=CallMachine(code,mem,dict(sp=STACK+2048,a0=ARENA+HSL,a1=CONFIG,
                              d0=struct.unpack_from('<H',desc,HSL+3024)[0]))
    r=m.run(m.enter(0x6079e50e,0xdeadbeef,0xf0,80),[0xdeadbeef]);assert r['status']=='stop',r
    m.r.update(a0=CONFIG,a1=ARENA+GAMMA,d0=ARENA+GAMMA,d1=ARENA+GAMMA)
    r=m.run(m.enter(0x6079d7a0,0xdeadbeef,0xa0,8),[0xdeadbeef]);assert r['status']=='stop',r
    pointers={str(i):struct.unpack_from('<I',config,i)[0] for i in POINTERS}
    assert all(ARENA<=p<ARENA+4096 for p in pointers.values())
    # Native optional table3164 is null in this fixture. Skip its independent
    # branch with caller-owned flag; this is NOT evidence about that branch.
    assert struct.unpack_from('<I',config,3164)[0]==0
    for off,val in [(8,DEST),(16,OWNER),(20,OWNER+128)]:struct.pack_into('<I',stack,off,val)
    stack[24]=1;struct.pack_into('<I',owner,12,CONFIG);struct.pack_into('<I',owner,128,1)
    if overwrite:
        # Deliberate premature-reuse control after pointers were configured.
        # No cache production API permits this while leased.
        for i in range(HSL,HSL+3028):desc[i]^=0xff
    mem.reads.clear()
    m=Machine(code,mem,dict(sp=STACK));r=m.run(START,[STOP],limit=30000)
    assert r['status']=='stop',r
    reads=tuple(mem.reads)
    # Independently reconstruct the actual branch's copies from the resident
    # descriptor bytes. Gamma: 256 u16->u32; HSL: four 512-byte blocks and six
    # blocks of 128 u16->u32, as read by this native branch.
    expected=bytearray(12000)
    for n in range(256):struct.pack_into('<I',expected,n*4,struct.unpack_from('<H',desc,GAMMA+n*2)[0])
    for off,out in [(3124,5120),(3128,5632),(3132,6144),(3140,7168)]:
        src=pointers[str(off)]-ARENA;expected[out:out+512]=desc[src:src+512]
    for off,out in [(3136,6656),(3144,7680),(3148,8192),(3152,8704),(3156,9216),(3160,9728)]:
        src=pointers[str(off)]-ARENA
        for n in range(128):struct.pack_into('<I',expected,out+n*4,struct.unpack_from('<H',desc,src+n*2)[0])
    assert dest==expected,'native-copy/oracle mismatch'
    return {'instructions':r['instructions'],'source_reads':len(reads),
        'source_min':hex(min(a for a,s in reads)),
        'source_end':hex(max(a+s for a,s in reads)),
        'last_source_read':{'address':hex(reads[-1][0]),'size':reads[-1][1]},
        'pointers':{k:hex(v) for k,v in pointers.items()},'native_copy_matches_oracle':True,
        'output_sha256':sha256(dest).hexdigest(),'hsl_output_sha256':sha256(dest[5120:10240]).hexdigest()}


def run(image,code):
    # Assert actual decoded native call operands and destination immediates.
    sites=[]
    for load,call,destination in [(0x60740606,0x6074060d,0x9f00a400),(0x60740628,0x6074062f,0x9f00d000)]:
        _,op,args=code[load];assert op=='mov' and args[1]=='a0' and int(args[0],0)&0xffffffff==destination
        _,op,args=code[call];assert op=='call' and int(args[0],0)==0x607414a9
        sites.append({'call':hex(call),'destination':hex(destination)})
    good=experiment(image,code);bad=experiment(image,code,overwrite=True)
    assert good['output_sha256']!=bad['output_sha256']
    assert good['hsl_output_sha256']!=bad['hsl_output_sha256']
    return {'main_sha256':sha256(image).hexdigest(),'baseline':good,'premature_hsl_overwrite':bad,
            'static_call_sites':sites,'scope':'Native setters and bounded copy fragment with synthetic stack, owner and output. Optional config3164 skipped. No task completion, ISP, physical allocation, SD/Delete or safe release-hook proof.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--main',type=Path,required=True);p.add_argument('--reader',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    image=a.main.read_bytes();assert sha256(image).hexdigest()==MAIN_SHA
    verify_reader(a.reader);code={}
    for start,end in WINDOWS:
        listing=subprocess.check_output([str(a.reader.resolve()),str(a.main.resolve()),hex(BASE),hex(start-BASE),hex(end-BASE)],text=True)
        code.update(parse_listing(listing,image,BASE))
    result=run(image,code);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
