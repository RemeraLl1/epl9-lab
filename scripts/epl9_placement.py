"""One offline early-load placement candidate; no install qualification."""
from epl9_workspace_bridge import BASE
from mn103_subset import Region

CANDIDATE=0x604a1300
MODULE_SIZE=0x3c00
EARLY_START,EARLY_END=0x60410000,0x604b0800


def check_slot(image,base,size):
    if base+size<=BASE or base>=BASE+len(image):return 'synthetic; camera placement unqualified'
    if base!=CANDIDATE or size!=MODULE_SIZE:
        raise ValueError('only the reviewed early-load candidate may overlap main')
    if not EARLY_START<=base<base+size<=EARLY_END:
        raise ValueError('candidate escapes early loader request')
    if image[base-BASE:base-BASE+size]!=b'\xff'*size:
        raise ValueError('early-load candidate is not exact stock FF padding')
    return 'offline early-load candidate; runtime ownership and installation unqualified'


def module_regions(image,module):
    at,size=module['base'],len(module['data'])
    if BASE<=at and at+size<=BASE+len(image):
        if image[at-BASE:at-BASE+size]!=module['data']:
            raise ValueError('in-main module bytes missing or changed')
        return []
    if not (at+size<=BASE or at>=BASE+len(image)):
        raise ValueError('partially overlapping module')
    return [Region(at,module['data'],False,'native film module')]


def with_module_data(image,module):
    """Give the independent unhooked oracle the same readonly table bytes."""
    at,size=module['base'],len(module['data'])
    if not BASE<=at<BASE+len(image):return image
    existing=image[at-BASE:at-BASE+size]
    if existing==module['data']:return image
    check_slot(image,at,size)
    result=bytearray(image)
    result[at-BASE:at-BASE+size]=module['data']
    return bytes(result)
