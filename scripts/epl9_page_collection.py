"""Strict host collection contract for a FUTURE qualified page transport.

There is no USB backend or camera packet format here. Inputs must come from a
separately qualified adapter. Passing these checks never certifies provenance.
"""
from dataclasses import dataclass
from epl9_component_readback import ADDRESSES, SIZE, compare

PAGE = 2048
COUNT = SIZE//PAGE


def mapped_pages(table, kind):
    if kind not in ADDRESSES or len(table) != 1024:
        raise ValueError('component or mapping size')
    base = (ADDRESSES[kind]-0x40000000)//PAGE
    pages = []
    for logical in range(base, base+COUNT):
        block = logical//64
        seen = set()
        while True:
            if block in seen or not 0 <= block < 1024:
                raise ValueError('invalid/cyclic mapping')
            seen.add(block)
            nxt = table[block]
            if not isinstance(nxt, int) or not 0 <= nxt < 1024:
                raise ValueError('mapping target outside table')
            if nxt == block:
                break
            block = nxt
        pages.append(block*64+logical % 64)
    return tuple(pages)


@dataclass(frozen=True)
class PageResult:
    session: int
    component: str
    pass_index: int
    ordinal: int
    physical_page: int
    result: int
    reader_state: int
    data: bytes


class Collection:
    def __init__(self, session, table):
        if not isinstance(session, int) or not 0 < session < 2**32:
            raise ValueError('nonzero session identity required')
        self.session = session
        self.maps = {kind: mapped_pages(tuple(table), kind) for kind in ADDRESSES}
        self.buffers = {(kind, run): bytearray() for kind in ADDRESSES for run in (0, 1)}
        self.failed = False

    def accept(self, page):
        if self.failed:
            raise ValueError('collection already failed')
        try:
            key = (page.component, page.pass_index)
            if page.session != self.session or key not in self.buffers:
                raise ValueError('wrong session or stream')
            dest = self.buffers[key]
            if page.ordinal != len(dest)//PAGE or not 0 <= page.ordinal < COUNT:
                raise ValueError('missing, reordered, duplicate or excess page')
            if (page.result != 0 or page.reader_state != 2 or not isinstance(page.data, bytes)
                    or len(page.data) != PAGE):
                raise ValueError('incomplete or failed reader result')
            if page.physical_page != self.maps[page.component][page.ordinal]:
                raise ValueError('mapping changed or wrong physical page')
            dest.extend(page.data)
        except (ValueError, AttributeError):
            self.failed = True
            raise

    def finish(self, refs, expected):
        if self.failed or any(len(b) != SIZE for b in self.buffers.values()):
            raise ValueError('four complete successful streams required')
        samples = {kind: tuple(bytes(self.buffers[(kind, run)]) for run in (0, 1))
                   for kind in ADDRESSES}
        result = compare(samples, refs, expected)
        result['collector_session'] = self.session
        result['input_transport_qualified'] = False
        return result
