"""Host-only SD recipe format and immutable slot-selection prototype.

No native loader, firmware patch, camera access or physical SD preparation.
CLI writes only new files under ignored local/. Logical SD indices are not
native ART keys. Binary format v0 is an experiment, not a camera standard.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import zlib

from epl9_workspace_bridge import ROOT, BASE, MAIN, MAIN_SHA
from epl9_tonal_drafts import remap_curve, validate_knots

HEADER = struct.Struct('<4sHHHHIIIII32s')
PAYLOAD = struct.Struct('<36h4h2H256H')
FILE_BYTES = HEADER.size+PAYLOAD.size
CRC_OFFSET = 16
AUTHOR_SCHEMA = 'epl9-sd-recipe-author-v0'
FILE_MAGIC = b'E9R0'
MODEL, BUILD, ABI = 1330, 1101, 1
CARD_DIRECTORY = 'EPL9MOD'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integers(values, bounds):
    return len(values) == len(bounds) and all(type(v) is int and lo <= v <= hi
                                             for v,(lo,hi) in zip(values,bounds))


def validate_controls(recipe_id, name, hsl, contrast, tone, wb_q10):
    require(type(recipe_id) is int and 0 < recipe_id <= 0xffffffff, 'invalid recipe ID')
    require(type(name) is str and 1 <= len(name) <= 31 and
            all(32 <= ord(c) <= 126 and c != '@' for c in name), 'name must be 1..31 plain ASCII bytes')
    require(type(hsl) is tuple and len(hsl) == 12 and
            all(type(row) is tuple and integers(row, ((-1000,1000),(-240,240),(-100,100)))
                for row in hsl), 'unqualified native HSL records')
    require(type(contrast) is int and -2 <= contrast <= 2, 'invalid contrast')
    require(type(tone) is tuple and integers(tone, ((-7,7),)*3), 'invalid tone biases')
    require(type(wb_q10) is tuple and integers(wb_q10, ((512,2048),)*2), 'invalid native-order WB')


@dataclass(frozen=True)
class Recipe:
    recipe_id: int
    name: str
    hsl: tuple
    contrast: int
    tone: tuple  # highlights, midtones, shadows
    wb_q10: tuple  # native order, no physical channel names inferred
    gamma: tuple  # one shared native variant-zero gamma

    def __post_init__(self):
        validate_controls(self.recipe_id, self.name, self.hsl, self.contrast, self.tone, self.wb_q10)
        require(type(self.gamma) is tuple and integers(self.gamma, ((0,4095),)*256) and
                all(a <= b for a,b in zip(self.gamma,self.gamma[1:])), 'invalid shared gamma')


def pack_recipe(recipe):
    require(isinstance(recipe, Recipe), 'Recipe required')
    header = HEADER.pack(FILE_MAGIC, 0, HEADER.size, MODEL, BUILD, FILE_BYTES,
                         0, recipe.recipe_id, ABI, 0, recipe.name.encode().ljust(32,b'\0'))
    payload = PAYLOAD.pack(*(v for row in recipe.hsl for v in row), recipe.contrast,
                           *recipe.tone, *recipe.wb_q10, *recipe.gamma)
    result = bytearray(header+payload)
    struct.pack_into('<I', result, CRC_OFFSET, zlib.crc32(result))
    return bytes(result)


def unpack_recipe(data):
    require(type(data) is bytes and len(data) == FILE_BYTES, 'wrong recipe file length')
    magic,version,size,model,build,total,checksum,ident,abi,flags,name = HEADER.unpack_from(data)
    require((magic,version,size,model,build,total,abi,flags) ==
            (FILE_MAGIC,0,HEADER.size,MODEL,BUILD,FILE_BYTES,ABI,0), 'incompatible recipe header')
    checked = bytearray(data)
    struct.pack_into('<I', checked, CRC_OFFSET, 0)
    require(zlib.crc32(checked) == checksum, 'recipe checksum mismatch')
    label,zero,padding = name.partition(b'\0')
    require(zero and not any(padding), 'invalid name termination/padding')
    try:
        label = label.decode('ascii')
    except UnicodeDecodeError as error:
        raise ValueError('invalid ASCII name') from error
    values = PAYLOAD.unpack_from(data, HEADER.size)
    return Recipe(ident, label, tuple(tuple(values[n:n+3]) for n in range(0,36,3)),
                  values[36], tuple(values[37:40]), tuple(values[40:42]), tuple(values[42:]))


def validate_author(document):
    """Validate editable controls without inventing or compiling a gamma curve."""
    fields = {'schema','recipe_id','name','native_hsl','contrast','tone','wb_q10','gamma_knots'}
    require(type(document) is dict and set(document) == fields and document['schema'] == AUTHOR_SCHEMA,
            'unsupported author schema/fields')
    tone = document['tone']
    require(type(tone) is dict and set(tone) == {'highlights','midtones','shadows'}, 'explicit H/M/S required')
    require(type(document['native_hsl']) is list and all(type(r) is list for r in document['native_hsl']),
            'HSL must be a list of rows')
    require(type(document['wb_q10']) is list, 'WB must be a list')
    validate_knots(document['gamma_knots'])
    controls = dict(recipe_id=document['recipe_id'], name=document['name'],
        hsl=tuple(tuple(r) for r in document['native_hsl']), contrast=document['contrast'],
        tone=tuple(tone[k] for k in ('highlights','midtones','shadows')),
        wb_q10=tuple(document['wb_q10']))
    validate_controls(**controls)
    return controls


def compile_author(document, image):
    controls = validate_author(document)
    require(len(image) == 26214336 and hashlib.sha256(image).hexdigest() == MAIN_SHA,
            'requires exact E-PL9 build 1101 main for native gamma compilation')
    base = struct.unpack_from('<256H', image, 0x608c37e4-BASE)
    return Recipe(**controls, gamma=tuple(remap_curve(base,document['gamma_knots'])))


def read_json(path, limit=65536):
    """Bound author/manifest reads and reject ambiguous duplicate JSON fields."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON field: '+key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON number: '+value)
    with Path(path).open('rb') as handle:
        raw = handle.read(limit+1)
    require(len(raw) <= limit, 'JSON input exceeds size limit')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique, parse_constant=constant)


def materialize(recipe, color_template):
    """Construct native data only; no pointer installation or execution."""
    require(type(color_template) is bytes and len(color_template) == 3028, 'exact template size required')
    table = bytearray(color_template)
    for n,row in enumerate(recipe.hsl):
        struct.pack_into('<3h',table,n*28+12,*row)
    return bytes(table), struct.pack('<256H',*recipe.gamma)


@dataclass(frozen=True)
class Slot:
    slot_id: str
    fallback: Recipe
    sd_index: int | None = None


@dataclass(frozen=True)
class Selection:
    slot_id: str
    recipe: Recipe
    source: str
    status: str


def load_session(slots, card_root):
    """Read a bounded file per reserved slot, then retain immutable recipes.

    The returned snapshot has no file handles or reload operation. Invalid
    files affect only their destination slot. Filenames provide the binding;
    recipes themselves contain no native ART key or slot number.
    """
    slots = tuple(slots)
    require(all(isinstance(s,Slot) and isinstance(s.fallback,Recipe) for s in slots), 'invalid slot')
    ids = [s.slot_id for s in slots]
    sd = [s.sd_index for s in slots if s.sd_index is not None]
    require(all(type(i) is str and i for i in ids) and len(ids) == len(set(ids)), 'duplicate/invalid slot ID')
    require(all(type(i) is int and 1 <= i <= 99 for i in sd) and len(sd) == len(set(sd)),
            'duplicate/invalid logical SD index')
    selected = []
    for slot in slots:
        recipe,source,status = slot.fallback,'embedded','built-in'
        if slot.sd_index is not None:
            status = 'missing'
            if card_root is not None:
                path = Path(card_root)/CARD_DIRECTORY/f'SLOT{slot.sd_index:02}.RCP'
                try:
                    with path.open('rb') as handle:
                        data = handle.read(FILE_BYTES+1)
                    recipe = unpack_recipe(data)
                    source,status = 'sd','loaded'
                except FileNotFoundError:
                    pass
                except (OSError,ValueError) as error:
                    status = 'rejected: '+str(error)
        selected.append(Selection(slot.slot_id,recipe,source,status))
    return tuple(selected)


def new_local_output(path):
    path = Path(path)
    require(not path.exists() and path.resolve().is_relative_to((ROOT/'local').resolve()),
            'CLI output must be new and under ignored local/; no physical card writes')
    path.parent.mkdir(parents=True,exist_ok=True)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command',required=True)
    export = sub.add_parser('export',help='compile one author JSON to a local experimental recipe file')
    export.add_argument('author',type=Path)
    export.add_argument('--out',type=Path,required=True)
    inspect = sub.add_parser('inspect',help='validate and summarize one experimental recipe file')
    inspect.add_argument('recipe',type=Path)
    author = sub.add_parser('validate-author',help='check editable JSON without compiling a gamma or record')
    author.add_argument('author',type=Path)
    args = ap.parse_args()
    try:
        if args.command == 'validate-author':
            controls = validate_author(read_json(args.author))
            print(json.dumps(dict(recipe_id=controls['recipe_id'],name=controls['name'],
                author_controls_valid=True,gamma_compiled=False,record_exported=False,
                exact_stock_main_required_for_export=True,camera_loader_implemented=False)))
            return
        if args.command == 'export':
            document = read_json(args.author)
            validate_author(document)
            recipe = compile_author(document,MAIN.read_bytes())
            path = new_local_output(args.out)
            with path.open('xb') as handle:
                handle.write(pack_recipe(recipe))
        else:
            with args.recipe.open('rb') as handle:
                recipe = unpack_recipe(handle.read(FILE_BYTES+1))
    except (OSError,ValueError) as error:
        ap.error(str(error))
    print(json.dumps(dict(recipe_id=recipe.recipe_id,name=recipe.name,bytes=FILE_BYTES,
                         schema='experimental host v0',camera_loader_implemented=False)))


if __name__ == '__main__':
    main()
