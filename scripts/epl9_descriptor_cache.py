"""Bounded single-owner lifetime specification, not a native camera allocator.

Every resident owns both raw bytes and its address-bound descriptor. No capture
may outlive its lease. Native consumer completion has NOT been identified.
"""
from dataclasses import dataclass
from hashlib import sha256
from epl9_recipe_banks import pack_bank, unpack_bank
from epl9_sd_recipes import pack_recipe, require
from epl9_sd_processing import descriptor, STRIDE


class CacheBusy(RuntimeError):
    pass


@dataclass(frozen=True)
class Handle:
    token: int
    slot: int
    generation: int
    descriptor_address: int
    raw_address: int


@dataclass(frozen=True)
class Resident:
    key: tuple
    generation: int
    raw: bytes
    data: bytes


class DescriptorCache:
    """Synthetic fixed arenas; call only in one owner task.

    `acquire` precedes exposing pointers to *any* consumer. `release` must mean
    all asynchronous readers are done, not merely shutter-up/config return.
    Full pinned cache raises CacheBusy: caller must defer, never reuse a slot.
    """
    def __init__(self, image, capacity=2):
        require(type(capacity) is int and 1 <= capacity <= 31, 'capacity 1..31')
        self.image = image
        self.capacity = capacity
        self.slots = [None]*capacity
        self.leases = {}
        self.sequence = 0
        self.generations = [0]*capacity
        self.clock = 0
        self.used = [0]*capacity
        self.arena = 0x18000000
        self.raw_arena = 0x19000000

    def acquire(self, bank, ordinal):
        raw_bank = pack_bank(bank)
        bank = unpack_bank(raw_bank)
        require(type(ordinal) is int and 1 <= ordinal <= len(bank.recipes), 'invalid ordinal')
        key = (sha256(raw_bank).digest(), ordinal)
        slot = next((i for i,r in enumerate(self.slots) if r and r.key == key), None)
        if slot is None:
            pinned = {h.slot for h in self.leases.values()}
            free = [i for i in range(self.capacity) if i not in pinned]
            if not free:
                raise CacheBusy('all descriptors retained by consumers; defer request')
            slot = min(free, key=lambda i: (self.slots[i] is not None, self.used[i]))
            raw = pack_recipe(bank.recipes[ordinal-1])
            # Build privately before mutating slot; exceptions keep old resident.
            data = descriptor(self.image, raw, self.arena+slot*STRIDE,
                              ordinal, self.raw_arena+slot*660)
            generation = self.generations[slot]+1
            resident = Resident(key,generation,raw,data)
            self.slots[slot] = resident
            self.generations[slot] = generation
        self.clock += 1
        self.used[slot] = self.clock
        self.sequence += 1
        handle = Handle(self.sequence,slot,self.generations[slot],
                        self.arena+slot*STRIDE,self.raw_arena+slot*660)
        self.leases[handle.token] = handle
        return handle

    def read(self, handle):
        require(isinstance(handle,Handle) and self.leases.get(handle.token) is handle,
                'stale or foreign lease')
        resident = self.slots[handle.slot]
        require(resident.generation == handle.generation, 'resident replaced while leased')
        return resident

    def release(self, handle):
        self.read(handle)
        del self.leases[handle.token]

    def footprint(self):
        return dict(descriptor_bytes=self.capacity*4096, raw_backing_bytes=self.capacity*660,
                    total_resident_payload_bytes=self.capacity*4756,
                    excludes='serialized banks, allocator, leases, code, stack and image template',
                    camera_allocator_proven=False)
