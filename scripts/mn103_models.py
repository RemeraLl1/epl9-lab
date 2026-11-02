"""Explicit host software contracts, NOT decoded E-PL9 implementations.

Only the named fill and one bounded pool allocation are modeled. Volatile
register/flag effects are assumptions, not an ABI or hardware validation.
"""
from mn103_subset import Fault


class FillModel:
    name = 'assumed-byte-fill'

    def validate(self, m, mask, frame):
        if (mask, frame) != (0xa0, 8):
            raise Fault('fill model ABI mismatch')
        start, count = m.r['a0'], m.r['d1']
        self.span = None
        if count == 0:
            return
        for region in m.memory.regions:
            if (region.writable and region.address <= start
                    and start+count <= region.address+len(region.data)):
                # A fill must not corrupt the pending call's frame or return.
                if start < m.r['sp']+4 and start+count > m.r['sp']-frame:
                    raise Fault('fill overlaps call frame')
                self.span = region, start-region.address
                return
        raise Fault('fill range is not wholly inside one writable region')

    def apply(self, m):
        start, count, value = m.r['a0'], m.r['d1'], m.r['d0'] & 255
        if self.span is not None:
            region, offset = self.span
            region.data[offset:offset+count] = bytes([value])*count
        # Explicit assumptions: byte loop exhausts d1 and advances a0;
        # d0/a1/flags stay unchanged. No caller is claimed natively verified.
        m.r['a0'], m.r['d1'] = (start+count) & 0xffffffff, 0
        return dict(start=hex(start), count=count, byte=value)


class OneBlockPool:
    name = 'synthetic-one-block-pool'

    def __init__(self, address, fail=False):
        self.address, self.fail, self.used = address, fail, False

    def validate(self, m, mask, frame):
        if (mask, frame, m.r['d0']) != (0xe0, 16, 0x10004):
            raise Fault('pool model ABI or pool ID mismatch')
        if self.used:
            raise Fault('one-block pool exhausted; no implicit second allocation')
        if not any(r.address == self.address and len(r.data) == 16384 and r.writable
                   for r in m.memory.regions):
            raise Fault('pool requires an explicit writable 16 KiB block')

    def apply(self, m):
        self.used = True
        m.r['a0'] = 0 if self.fail else self.address
        return dict(pool='0x10004', capacity=16384, returned=hex(m.r['a0']))
