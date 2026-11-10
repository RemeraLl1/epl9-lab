"""Separate synthetic-address T1/T2 processing consumer. Never packages v3."""
import struct
from string import Template
from epl9_workspace_bridge import ROOT, BASE
from epl9_sd_loader import assemble
from epl9_sd_state import overlay as state_overlay
from epl9_sd_recipes import unpack_recipe, materialize
from mn103_emit import encode

BASE_ADDRESS=0x6a000000
TEST_KEYS=(0x01030078,0x01040078)  # Offline aliases, no native menu assignment.
MAGIC=0x31504344
HSL=64
RECORD=3104
GAMMA=RECORD+148
STRIDE=4096
TEMPLATE=ROOT/'firmware_src/epl9_sd_processing.s.in'


def pointer(dest,source,offset):
    lines=[f' mov {source},{dest}']
    while offset:
        n=max(-128,min(127,offset));lines.append(f' add {n},{dest}');offset-=n
    return '\n'.join(lines)


def descriptor(image,raw,at,slot,source):
    recipe=unpack_recipe(raw)
    table,_=materialize(recipe,image[0x608ee360-BASE:0x608ee360-BASE+3028])
    data=bytearray(STRIDE)
    struct.pack_into('<7I',data,0,MAGIC,1,slot,source,at+HSL,at+RECORD,at+GAMMA)
    data[HSL:HSL+3028]=table;data[RECORD:RECORD+660]=raw
    return bytes(data)


def build(image,state):
    values=dict(KEY1=TEST_KEYS[0],KEY2=TEST_KEYS[1],MAGIC=MAGIC,
        GET=state['symbols']['sd_slot_get'],REGISTRY=state['symbols']['sd_registry'],
        EVENT=state['symbols']['sd_state_event'],DEFAULT1=BASE_ADDRESS+0x2000,
        DEFAULT2=BASE_ADDRESS+0x3000,CONTROL_PTR=pointer('a1','sp',2024),
        DEFAULT_GAMMA1=BASE_ADDRESS+0x2000+GAMMA,DEFAULT_GAMMA2=BASE_ADDRESS+0x3000+GAMMA,
        HEADER1=0x00780301,HEADER2=0x00780401,
        SECOND_PTR=pointer('a0','a3',4096),RECORD_PTR=pointer('a1','a3',RECORD),
        SECOND_ARENA=pointer('a0','a2',4096))
    # Dynamic loads; neither tone nor WB values are emitted as recipe constants.
    tone=[]
    for i,off in enumerate((138,140,142)):
        tone += [f' movhu ({4+i*2},a1),d0',' exth d0',f' movhu ({off},a0),d1',' exth d1',
                 ' add d1,d0',f' cmp 7,d0',f' ble tone_hi_{i}',' mov 7,d0',f'tone_hi_{i}:',
                 ' cmp -7,d0',f' bge tone_lo_{i}',' mov -7,d0',f'tone_lo_{i}:',f' movhu d0,({4+i*2},a1)']
    values['TONE']='\n'.join(tone)
    wb=[]
    for i in range(2):
        wb += [f' movhu ({1568+i*2},a2),d0',f' movhu ({144+i*2},a3),d1',
               ' mov 0,d2',' mov 12,d3',f'wb_mul_{i}:',' mov d1,a1',
               ' and 1,d1',' cmp 0,d1',f' beq wb_bit_{i}',' add d0,d2',f'wb_bit_{i}:',
               ' mov a1,d1',' lsr 1,d1',' add d0,d0',' add -1,d3',' cmp 0,d3',f' bne wb_mul_{i}',
               ' add 127,d2',' add 127,d2',' add 127,d2',' add 127,d2',' add 4,d2',' lsr 10,d2',
               ' cmp 65535,d2',f' ble wb_cap_{i}',' mov 65535,d2',f'wb_cap_{i}:',f' movhu d2,({1568+i*2},a2)']
    values['WB']='\n'.join(wb)
    source=Template(TEMPLATE.read_text()).substitute({k:str(v) for k,v in values.items()})
    code,symbols,rows=assemble(source,BASE_ADDRESS)
    if len(code)>0x2000:raise ValueError('consumer code overlaps embedded descriptors')
    data=bytearray(0x4000);data[:len(code)]=code
    for i in range(2):
        at=0x2000+i*STRIDE
        data[at:at+STRIDE]=descriptor(image,state['defaults'][i],BASE_ADDRESS+at,i+1,
                                    state['constants'][f'FALLBACK{i}'])
    return dict(data=bytes(data),base=BASE_ADDRESS,source=source,symbols=symbols,rows=rows,
                code_bytes=len(code),defaults=state['defaults'])


def overlay(image,state,module):
    patched,patches=state_overlay(image,state);patched=bytearray(patched)
    for pc,expected,label in ((0x60ae1c6e,'cd05042008','sd_pipeline_event'),
        (0x6079fb88,'f1d3f1ef53','sd_pipeline_color'),(0x6074f352,'0008257e0e','sd_pipeline_wb_hook'),
        (0x60752202,'881cf9140c','sd_pipeline_route')):
        raw=bytes.fromhex(expected)
        if image[pc-BASE:pc-BASE+len(raw)]!=raw:raise ValueError('processing hook source differs')
        after=encode('jmp',[label],pc,module['symbols'])
        if len(after)!=len(raw):raise ValueError('hook size differs')
        patched[pc-BASE:pc-BASE+len(raw)]=after
        patches=[p for p in patches if p['address']!=pc]+[dict(address=pc,before=expected,after=after.hex())]
    return bytes(patched),patches
