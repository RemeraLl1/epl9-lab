"""Bounded execution of GNU-decoded MN103 instruction listings.

This is a research subset, NOT GNU libsim or a complete CPU emulator. Calls
and returns are explicit stop boundaries; no hardware or automatic stubs.
Arithmetic/loop semantics consulted: GNU mn10300.igen at revision
87ffb882e0f4d73401a0746177ffabb8e8bbe4ac. See docs/epl9-offline-prototype.md.
"""
from dataclasses import dataclass

MASK = 0xffffffff


def signed(value, bits=32):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def operands(text):
    parts, start, depth = [], 0, 0
    for i, char in enumerate(text):
        depth += char in '(['
        depth -= char in ')]'
        if char == ',' and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    return parts + [text[start:].strip()] if text else []


class Fault(RuntimeError):
    pass


@dataclass
class Region:
    address: int
    data: bytearray
    writable: bool = False
    name: str = ''


class Memory:
    def __init__(self, regions):
        self.regions = sorted(regions, key=lambda r: r.address)
        end = 0
        for r in self.regions:
            if not r.data or r.address < end or r.address + len(r.data) > 1 << 32:
                raise ValueError('invalid or overlapping memory regions')
            end = r.address + len(r.data)

    def region(self, address, size, write=False):
        if size not in (1, 2, 4) or address % size:
            raise Fault(f'unsupported or unaligned access at {address:#x}, size {size}')
        for r in self.regions:
            if r.address <= address and address + size <= r.address + len(r.data):
                if write and not r.writable:
                    raise Fault(f'write to read-only {r.name} at {address:#x}')
                return r, address - r.address
        raise Fault(f'unmapped access at {address:#x}, size {size}')

    def read(self, address, size):
        r, offset = self.region(address, size)
        return int.from_bytes(r.data[offset:offset+size], 'little')

    def write(self, address, value, size):
        r, offset = self.region(address, size, True)
        r.data[offset:offset+size] = (value & ((1 << (size * 8)) - 1)).to_bytes(size, 'little')


def parse_listing(listing, image, base):
    instructions = {}
    for line in listing.splitlines():
        at, raw, text = line.split('\t', 2)
        at, raw = int(at, 16), bytes.fromhex(raw)
        if at < base or image[at-base:at-base+len(raw)] != raw:
            raise ValueError('listing bytes do not match input image')
        fields = text.rstrip().split('\t', 1)
        instructions[at] = (raw, fields[0], operands(fields[1] if len(fields) > 1 else ''))
    return instructions


class Machine:
    def __init__(self, code, memory, registers=None):
        self.code, self.memory = code, memory
        self.r = {r: 0 for r in ['d0', 'd1', 'd2', 'd3', 'a0', 'a1', 'a2', 'a3', 'sp', 'mdr', 'mdrq']}
        for name, value in (registers or {}).items():
            if name not in self.r:
                raise ValueError(f'unknown register {name}')
            self.r[name] = value & MASK
        self.n = self.z = self.c = self.v = False
        self.loop = None
        self.trace = []

    def atom(self, value):
        return self.r[value] if value in self.r else int(value, 0)

    def address(self, operand):
        return sum(self.atom(x.strip()) for x in operand[1:-1].split(',')) & MASK

    def read(self, operand, size=4):
        return self.memory.read(self.address(operand), size) if operand.startswith('(') else self.atom(operand) & MASK

    def write(self, operand, value, size=4):
        if operand.startswith('('):
            self.memory.write(self.address(operand), value, size)
        elif operand in self.r:
            self.r[operand] = value & MASK
        else:
            raise Fault(f'invalid destination {operand}')

    def nz(self, value):
        self.z, self.n = (value & MASK) == 0, bool(value & 0x80000000)

    def arithmetic(self, left, right, subtract=False):
        value = right - left if subtract else right + left
        self.nz(value)
        self.c = right < left if subtract else value > MASK
        self.v = bool(((right ^ left) if subtract else ~(right ^ left)) & (right ^ value) & 0x80000000)
        return value & MASK

    def condition(self, suffix):
        conditions = {'eq': self.z, 'ne': not self.z, 'cs': self.c, 'cc': not self.c,
                      'lt': self.n != self.v, 'ge': self.n == self.v,
                      'gt': not self.z and self.n == self.v,
                      'le': self.z or self.n != self.v,
                      'hi': not self.c and not self.z, 'ls': self.c or self.z}
        if suffix not in conditions:
            raise Fault(f'unsupported condition {suffix}')
        return conditions[suffix]

    def run(self, start, stops=(), limit=20000, single_step=False):
        pc = start
        for _ in range(limit):
            if pc in stops:
                return {'status': 'stop', 'pc': pc, 'instructions': len(self.trace)}
            if pc not in self.code:
                raise Fault(f'unmapped instruction at {pc:#x}')
            raw, op, args = self.code[pc]
            if op in ('call', 'calls', 'ret', 'retf'):
                return {'status': op + '_boundary', 'pc': pc, 'operands': args,
                        'instructions': len(self.trace)}
            self.trace.append(pc)
            nxt = pc + len(raw)
            try:
                if op in ('mov', 'movbu', 'movhu', 'movb', 'movh'):
                    size = 1 if op in ('movbu', 'movb') else 2 if op in ('movhu', 'movh') else 4
                    value = self.read(args[0], size)
                    if op in ('movb', 'movh') and not args[1].startswith('('):
                        value = signed(value, size * 8)
                    self.write(args[1], value, size)
                elif op == 'clr':
                    self.write(args[0], 0)
                    self.nz(0)
                    self.c = self.v = False
                elif op in ('add', 'sub', 'cmp'):
                    left, right = map(self.read, args)
                    # SP arithmetic has no condition-code effects in this subset.
                    if args[1] == 'sp' and op == 'add':
                        value = right + left
                    else:
                        value = self.arithmetic(left, right, op != 'add')
                    if op != 'cmp':
                        self.write(args[1], value)
                elif op in ('inc', 'inc4'):
                    value = self.read(args[0]) + (4 if op == 'inc4' else 1)
                    if args[0].startswith('d'):
                        value = self.arithmetic(1, self.read(args[0]))
                    self.write(args[0], value)
                elif op in ('extb', 'exth', 'extbu', 'exthu'):
                    bits = 8 if op in ('extb', 'extbu') else 16
                    value = self.read(args[0])
                    self.write(args[0], value & ((1 << bits)-1) if op.endswith('u') else signed(value, bits))
                elif op == 'ext':
                    self.r['mdr'] = MASK if self.read(args[0]) & 0x80000000 else 0
                elif op in ('and', 'or', 'xor', 'btst'):
                    left, right = map(self.read, args)
                    value = left & right if op in ('and', 'btst') else left | right if op == 'or' else left ^ right
                    self.nz(value)
                    self.c = self.v = False
                    if op != 'btst':
                        self.write(args[1], value)
                elif op in ('asl', 'asr', 'lsr', 'asl2'):
                    count, dest = (2, args[0]) if op == 'asl2' else (self.read(args[0]), args[1])
                    if not 0 <= count < 32:
                        raise Fault('shift count outside supported subset')
                    value = self.read(dest)
                    # GNU left shifts preserve C/V; right shifts use original
                    # bit 0 for C (even for a multi-bit shift) and preserve V.
                    if op in ('asr', 'lsr'):
                        self.c = bool(value & 1)
                    value = value << count if op in ('asl', 'asl2') else signed(value) >> count if op == 'asr' else value >> count
                    self.nz(value)
                    self.write(dest, value)
                elif op in ('udf00', 'udfu01'):
                    left, right = map(self.read, args)
                    if op == 'udf00':
                        left, right = signed(left), signed(right)
                    elif args[0] not in self.r and left >= (1 << (8 * (len(raw)-2)-1)):
                        raise Fault('ambiguous GNU unsigned multiply immediate')
                    product = left * right
                    self.write(args[1], product)
                    self.r['mdrq'] = (product >> 32) & MASK
                    self.nz(product)
                    self.c = self.v = False
                elif op == 'div':
                    divisor = signed(self.read(args[0]))
                    dividend = signed((self.r['mdr'] << 32) | self.read(args[1]), 64)
                    if not divisor:
                        raise Fault('division by zero')
                    quotient = abs(dividend) // abs(divisor) * (-1 if (dividend < 0) != (divisor < 0) else 1)
                    if not -(1 << 31) <= quotient < 1 << 31:
                        raise Fault('division overflow outside supported subset')
                    self.r['mdr'] = (dividend - quotient * divisor) & MASK
                    self.write(args[1], quotient)
                    self.nz(quotient)
                    self.c = self.v = False
                elif op == 'setlb':
                    self.loop = nxt  # GNU LAR=PC+5; loop target=LAR-4.
                elif op in ('jmp', 'bra'):
                    nxt = self.address(args[0]) if args[0].startswith('(') else self.read(args[0])
                elif op.startswith('b') and self.condition(op[1:]):
                    nxt = self.read(args[0])
                elif op.startswith('b'):
                    pass
                elif op in ('lne', 'leq', 'llt', 'lge', 'lcs', 'lcc', 'lhi', 'lls', 'lgt', 'lle'):
                    if self.loop is None:
                        raise Fault('loop without setlb')
                    if self.condition(op[1:]):
                        nxt = self.loop
                elif op == 'nop':
                    pass
                else:
                    raise Fault(f'unsupported instruction {op}')
            except (ValueError, KeyError, Fault) as error:
                raise Fault(f'{pc:#x} {op} {args}: {error}') from error
            pc = nxt
            if single_step:
                return {'status': 'step', 'pc': pc, 'instructions': len(self.trace)}
        raise Fault(f'instruction limit {limit} at {pc:#x}')
