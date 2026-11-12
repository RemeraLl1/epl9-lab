"""Future recipe-bank host reference. Not a camera patch or native slot map.

Reuses E9R0 records. Delete requests are serviced outside the key handler;
all records in a bank publish together, and capture leases block replacement.
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import hashlib
import json
import struct
import zlib

from epl9_sd_recipes import Recipe, pack_recipe, unpack_recipe, FILE_BYTES, require, ROOT

MAX_RECIPES = 31
HEADER = struct.Struct('<4sHHIIII')
MAGIC = b'E9B1'
MAX_BANK_BYTES = HEADER.size + MAX_RECIPES * FILE_BYTES
CARD_PATH = Path('EPL9MOD/RECIPES.RBK')


@dataclass(frozen=True)
class Bank:
    bank_id: int
    recipes: tuple

    def __post_init__(self):
        require(type(self.bank_id) is int and 1 <= self.bank_id <= 0xffffffff, 'invalid bank ID')
        require(type(self.recipes) is tuple and 1 <= len(self.recipes) <= MAX_RECIPES,
                'bank requires 1..31 immutable recipe records')
        require(all(isinstance(r, Recipe) for r in self.recipes), 'invalid recipe')
        require(len({r.recipe_id for r in self.recipes}) == len(self.recipes), 'duplicate recipe ID')


def pack_bank(bank):
    require(isinstance(bank, Bank), 'Bank required')
    payload = b''.join(pack_recipe(r) for r in bank.recipes)
    raw = bytearray(HEADER.pack(MAGIC, 1, HEADER.size, bank.bank_id,
                               len(bank.recipes), len(payload), 0) + payload)
    struct.pack_into('<I', raw, 20, zlib.crc32(raw))
    return bytes(raw)


def unpack_bank(raw):
    require(type(raw) is bytes and HEADER.size <= len(raw) <= MAX_BANK_BYTES, 'invalid bank length')
    magic, version, header, ident, count, length, crc = HEADER.unpack_from(raw)
    require((magic, version, header) == (MAGIC, 1, HEADER.size), 'unsupported bank header')
    require(1 <= count <= MAX_RECIPES and length == count * FILE_BYTES and
            len(raw) == header + length, 'bank size/count mismatch')
    checked = bytearray(raw)
    struct.pack_into('<I', checked, 20, 0)
    require(zlib.crc32(checked) == crc, 'bank checksum mismatch')
    return Bank(ident, tuple(unpack_recipe(raw[i:i+FILE_BYTES])
                            for i in range(header, len(raw), FILE_BYTES)))


def read_bank(path):
    with Path(path).open('rb') as stream:
        return unpack_bank(stream.read(MAX_BANK_BYTES + 1))


@dataclass(frozen=True)
class View:
    generation: int
    source: str
    bank: Bank


class BankController:
    """Single-owner event-loop reference; not a thread-safe firmware lock.

    The actual camera adapter must prove contexts, task ownership, and capture
    drain. No camera address, enum, mutex or SD service is inferred here.
    """
    def __init__(self, embedded):
        require(isinstance(embedded, Bank), 'embedded Bank required')
        self.embedded = embedded
        self.view = View(0, 'embedded', embedded)
        self.pressed = False
        self._owned_press = False
        self.pending = False
        self._leases = {}
        self._next_token = 1
        self.last_status = 'embedded'

    def key(self, phase, context):
        require(phase in ('down', 'hold', 'up'), 'unknown key phase')
        require(context in ('idle-still', 'capture', 'playback', 'review', 'menu', 'movie', 'unknown'),
                'unknown context')
        if phase in ('up', 'hold'):
            result = 'handled' if self.pressed and self._owned_press else 'stock'
            if phase == 'up':
                self.pressed = False
                self._owned_press = False
            return result
        if self.pressed:
            return 'handled' if self._owned_press else 'stock'
        self.pressed = True
        self._owned_press = context == 'idle-still'
        if not self._owned_press:
            return 'stock'
        if not self.pending:
            self.pending = True
        return 'handled'

    def acquire(self):
        """Reference capture handoff keeps its immutable bank until release."""
        token = self._next_token
        self._next_token += 1
        self._leases[token] = self.view
        return token, self.view

    def release(self, token):
        require(type(token) is int and token in self._leases, 'unknown capture lease')
        del self._leases[token]

    def service(self, card_root, context):
        """Called in the owner task, never directly in a key/IRQ callback."""
        if not self.pending:
            return self.last_status
        if context != 'idle-still' or self._leases:
            self.last_status = 'waiting-for-idle'
            return self.last_status
        self.pending = False
        if self.view.source == 'sd':
            next_bank, source = self.embedded, 'embedded'
        else:
            try:
                if card_root is None:
                    raise FileNotFoundError('no card')
                next_bank = read_bank(Path(card_root) / CARD_PATH)
            except FileNotFoundError:
                self.last_status = 'sd-missing-kept-embedded'
                return self.last_status
            except (OSError, ValueError):
                self.last_status = 'sd-rejected-kept-embedded'
                return self.last_status
            source = 'sd'
        self.view = View(self.view.generation + 1, source, next_bank)
        self.last_status = source
        return source


def summary(bank):
    raw = pack_bank(bank)
    return dict(schema='epl9-future-recipe-bank-v1', bank_id=bank.bank_id,
                recipe_count=len(bank.recipes), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                recipes=[dict(id=r.recipe_id, name=r.name) for r in bank.recipes],
                native_slots_assigned=False, camera_tested=False, install_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('pack', help='pack existing validated records into a new local bank')
    build.add_argument('--bank-id', type=int, required=True)
    build.add_argument('--out', type=Path, required=True)
    build.add_argument('records', type=Path, nargs='+')
    check = sub.add_parser('inspect')
    check.add_argument('bank', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'pack':
            require(len(args.records) <= MAX_RECIPES, 'at most 31 records')
            records = []
            for path in args.records:
                with path.open('rb') as stream:
                    records.append(unpack_recipe(stream.read(FILE_BYTES+1)))
            bank = Bank(args.bank_id, tuple(records))
            out = args.out
            require(not out.exists() and not out.is_symlink() and
                    out.resolve().is_relative_to((ROOT/'local').resolve()),
                    'write a new file under ignored local/; no physical card writes')
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open('xb') as stream:
                stream.write(pack_bank(bank))
        else:
            bank = read_bank(args.bank)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(summary(bank), indent=2))


if __name__ == '__main__':
    main()
