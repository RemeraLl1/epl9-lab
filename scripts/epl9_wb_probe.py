"""Native early-gain hook boundaries and observed connected consumers."""
import struct
from epl9_integrated_probe import native
from epl9_offline_prototype import REQUEST, SP, header
from mn103_subset import Region
from epl9_wb_extension import adjusted
from epl9_film_module import require
from epl9_placement import module_regions


def boundaries(image,code,module):
    if module.get('wb_controls') is None: return []
    cases=[]
    for key in (0x01010078,0x01020078,1,11,0x01030078):
        for kind in (0x200,0x100,0x40,0x1000,0x107):
            values=[(v,v,v,v) for v in (0,1,2,1023,1024,32767,65534,65535)]
            values += [(2048,1536,0,1024),(2048,1536,1024,0),(2048,1536,1024,1056)]
            for record in values:
                request=bytearray([0xa5])*1876
                request[8:12]=header(key)
                struct.pack_into('<H',request,14,kind)
                struct.pack_into('<4H',request,1568,*record)
                before=bytes(request)
                regs=dict(a2=REQUEST,a0=REQUEST+1568,a3=0x11223344,d3=0x55667788,
                          mdr=0x12345678,mdrq=0x76543210)
                m=native(image,code,[Region(REQUEST,request,True),*module_regions(image,module)],regs)
                result=m.run(0x6074f352,[0x6074f357])
                require(result['pc']==0x6074f357 and m.r['sp']==SP,'early gain hook did not return')
                for name,value in regs.items(): require(m.r[name]==value,'early hook clobbered '+name)
                require(m.r['d0']==m.r['d2']==0 and m.r['a1']==3710,'displaced instructions not replayed')
                expected=bytearray(before)
                gains=module['wb_controls'].get(f'0x{key:08x}')
                if gains and kind in (0x200,0x100,0x40,0x1000):
                    struct.pack_into('<4H',expected,1568,*adjusted(record,gains))
                require(request==expected,'early hook differs from scalar oracle or changed unrelated bytes')
                cases.append(dict(key=hex(key),kind=hex(kind),input=record,
                                  output=struct.unpack_from('<4H',request,1568)))
    return cases


class CoefficientReads:
    def __init__(self,module):
        self.code_start=module['base']
    def __call__(self,m):
        from epl9_job_probe import JOB
        self.reads=[]
        read=m.read
        def observed(operand,size=4):
            value=read(operand,size)
            address=m.address(operand) if operand.startswith('(') else -1
            if (JOB+10440+1568<=address<JOB+10440+1576 and m.trace and
                    not self.code_start<=m.trace[-1]<self.code_start+0x1000):
                self.reads.append(dict(pc=hex(m.trace[-1]),index=(address-(JOB+10440+1568))//2,value=value))
            return value
        m.read=observed
