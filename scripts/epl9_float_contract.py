"""Opt-in inferred scalar-float ABI, NOT a decoded E-PL9 instruction model.

The math callers and IEEE-shaped constants support these contracts. Hardware
opcode semantics, rounding mode, exceptional inputs and flags are unverified.
Only finite normal values/zero and bounded integer conversions are accepted.
Native pow/log/exp bodies are not replaced by a host pow success model.
"""
from fractions import Fraction
from mn103_subset import Fault, signed


def unpack(bits):
    e=(bits>>23)&255;m=bits&0x7fffff
    if e==255 or e==0 and m:raise Fault('float contract excludes exceptional/subnormal input')
    if e==0:return Fraction(0)
    value=Fraction((1<<23)+m)*Fraction(2)**(e-150)
    return -value if bits>>31 else value


def pack(value):
    if not value:return 0
    sign=0x80000000 if value<0 else 0;value=abs(value)
    n,d=value.numerator,value.denominator
    e=n.bit_length()-d.bit_length()
    if value<Fraction(2)**e:e-=1
    if not -126<=e<=127:raise Fault('float contract excludes overflow/underflow')
    scaled=value*Fraction(2)**(23-e)
    q,r=divmod(scaled.numerator,scaled.denominator)
    if 2*r>scaled.denominator or 2*r==scaled.denominator and q&1:q+=1
    if q==(1<<24):q>>=1;e+=1
    if e>127:raise Fault('float contract overflow')
    return sign|((e+127)<<23)|(q-(1<<23))


class FloatContract:
    name='inferred-finite-binary32-contract'
    def __init__(self,operation):self.operation=operation
    def validate(self,m,mask,frame):
        if mask or frame:raise Fault('float contract requires [],0 ABI')
    def apply(self,m):
        op=self.operation;input0,input1=m.r['d0'],m.r['d1']
        if op in ('i32_float','u16_float','u32_float'):
            value=signed(input0) if op=='i32_float' else input0&65535 if op=='u16_float' else input0
            m.r['d0']=pack(Fraction(value))
        elif op in ('i32_trunc','u16_trunc'):
            value=int(unpack(input0))
            if not -0x80000000<=value<=0x7fffffff:raise Fault('integer conversion out of inferred domain')
            m.r['d0']=value&(65535 if op=='u16_trunc' else 0xffffffff)
        elif op in ('cmp','cmpzero'):
            a=unpack(input0);b=unpack(input1) if op=='cmp' else Fraction(0)
            if op=='cmpzero':m.r['d1']=0
            m.z=a==b;m.n=a<b;m.v=False;m.c=a<b
        elif op=='neg':m.r['d0']=input0^0x80000000
        else:
            a,b=unpack(input0),unpack(input1)
            if op=='div' and not b:raise Fault('zero divisor outside inferred domain')
            value={'add':lambda:a+b,'sub':lambda:a-b,'mul':lambda:a*b,'div':lambda:a/b}[op]()
            m.r['d0']=pack(value)
        if op in ('add','sub','mul','div','neg'):
            # Wrappers execute mov D0,D1; add D1,D1 before RETF.
            old=m.r['d0'];m.r['d1']=(old*2)&0xffffffff
            m.nz(m.r['d1']);m.c=old>=0x80000000;m.v=bool((old^m.r['d1'])&0x80000000)
        return dict(operation=op,input=[hex(input0),hex(input1)],output=hex(m.r['d0']),
                    inferred_contract=True,hardware_semantics_verified=False)


def models():
    return {a:FloatContract(op) for a,op in {
        0x604bbbeb:'i32_float',0x604bbbf4:'u16_float',0x604bbc33:'u32_float',0x604bbaba:'i32_trunc',0x604bbac1:'u16_trunc',
        0x604bbb1d:'add',0x604bbb16:'sub',0x604bbb42:'mul',0x604bbb30:'div',
        0x604bbb24:'cmp',0x604bbb29:'cmpzero',0x604bbb37:'neg'}.items()}
