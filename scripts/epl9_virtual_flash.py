"""Private, logical flash model; no device or camera APIs.

Geometry is an explicit emulation assumption, not measured chip geometry. Files
contain decoded envelopes (32-byte header + payload + 32-byte trailer). A single
writer must own the store. Component/fault/close checkpoints flush and fsync data
then atomically replace the manifest; no per-page fsync. Simulated power loss is
checkpointed deterministically, not a model of host crash atomicity. An actual
host crash between data and manifest writes is detected on open, not recovered.
Hashes detect inconsistency, not malicious coordinated rewriting/authenticity.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LAYOUT = {
    "main": {"base": 0x406E0000, "aliases": [0x806E0000], "size": 26214400},
    "osd": {"base": 0x421E0000, "aliases": [], "size": 26214400},
}
SCHEMA = "epl9-logical-flash-v1"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class FlashError(ValueError):
    """Invalid operation, bounds, geometry or attempted 0-to-1 transition."""


class IntegrityError(FlashError):
    """Stored files and manifest are inconsistent."""


@dataclass(frozen=True)
class FaultPlan:
    kind: str
    block_index: int = 0
    page_index: int = 0
    partial_bytes: int = 0
    stage: str = "program"


class VirtualFlashStore:
    @classmethod
    def create(cls, path, envelopes, *, layout=None, page_size=2048,
               erase_block_size=131072):
        layout = copy.deepcopy(DEFAULT_LAYOUT if layout is None else layout)
        cls._validate_layout(layout, page_size, erase_block_size)
        if set(envelopes) != set(layout):
            raise FlashError("envelopes must exactly match layout")
        for name, spec in layout.items():
            if len(envelopes[name]) != spec["size"]:
                raise FlashError(f"{name}: wrong envelope size")
        path = Path(path)
        path.mkdir(mode=0o700, parents=True, exist_ok=False)
        obj = cls()
        obj.path, obj.closed = path, False
        obj.page_size, obj.erase_block_size = page_size, erase_block_size
        obj.layout = layout
        obj._data = {name: bytearray(data) for name, data in envelopes.items()}
        obj._original = {name: _sha(data) for name, data in envelopes.items()}
        obj.last_result = None
        obj._checkpoint()
        return obj

    @staticmethod
    def _validate_layout(layout, page_size, block_size):
        if type(page_size) is not int or type(block_size) is not int or page_size <= 0 or block_size % page_size or block_size <= 0:
            raise FlashError("invalid logical geometry")
        if not isinstance(layout, dict) or not layout:
            raise FlashError("empty layout")
        spans = []
        for name, spec in layout.items():
            if not isinstance(name, str) or not name.isidentifier():
                raise FlashError("unsafe component name")
            if set(spec) != {"base", "aliases", "size"}:
                raise FlashError("layout fields must be base, aliases, size")
            size = spec["size"]
            if type(size) is not int or size < 64 or size % block_size:
                raise FlashError("component must contain envelope and aligned erase blocks")
            if not isinstance(spec["aliases"], list):
                raise FlashError("aliases must be a list")
            for base in [spec["base"], *spec["aliases"]]:
                if type(base) is not int or base < 0 or base + size > 2**32:
                    raise FlashError("invalid logical address")
                if any(base < end and base + size > start for start, end in spans):
                    raise FlashError("overlapping logical ranges")
                spans.append((base, base + size))

    @classmethod
    def open(cls, path):
        path = Path(path)
        try:
            if (path / "manifest.json").is_symlink():
                raise IntegrityError("manifest symlink is not allowed")
            manifest = json.loads((path / "manifest.json").read_text())
            digest = manifest.pop("manifest_sha256")
            if _sha(_canonical(manifest)) != digest or manifest["schema"] != SCHEMA:
                raise IntegrityError("manifest checksum/schema mismatch")
            obj = cls()
            obj.path, obj.closed = path, False
            obj.layout = manifest["layout"]
            obj.page_size = manifest["geometry"]["page_size"]
            obj.erase_block_size = manifest["geometry"]["erase_block_size"]
            obj._validate_layout(obj.layout, obj.page_size, obj.erase_block_size)
            if set(manifest["components"]) != set(obj.layout):
                raise IntegrityError("component inventory mismatch")
            obj._data, obj._original = {}, {}
            for name, spec in obj.layout.items():
                file = path / f"{name}.flash.bin"
                if file.is_symlink():
                    raise IntegrityError("component symlink is not allowed")
                data = file.read_bytes()
                entry = manifest["components"][name]
                if len(data) != spec["size"] or _sha(data) != entry["sha256"]:
                    raise IntegrityError(f"{name}: size/hash mismatch")
                if entry["size"] != spec["size"]:
                    raise IntegrityError(f"{name}: manifest size mismatch")
                obj._data[name] = bytearray(data)
                obj._original[name] = entry["original_sha256"]
            obj.last_result = manifest["last_result"]
            return obj
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise IntegrityError(f"cannot open consistent virtual flash: {exc}") from exc

    def _check(self, name, offset=0, length=0):
        if self.closed:
            raise FlashError("store is closed")
        if name not in self.layout:
            raise FlashError("unknown component")
        if type(offset) is not int or type(length) is not int or offset < 0 or length < 0 or offset + length > self.layout[name]["size"]:
            raise FlashError("operation outside component")

    def read(self, name, offset, length):
        self._check(name, offset, length)
        return bytes(self._data[name][offset:offset + length])

    def read_component(self, name):
        self._check(name)
        return bytes(self._data[name])

    def erase(self, name, offset, length):
        self._check(name, offset, length)
        if not length or offset % self.erase_block_size or length % self.erase_block_size:
            raise FlashError("erase must cover aligned complete blocks")
        self._data[name][offset:offset + length] = b"\xff" * length

    def program(self, name, offset, data):
        data = bytes(data)
        self._check(name, offset, len(data))
        if not data or len(data) > self.page_size or offset // self.page_size != (offset + len(data) - 1) // self.page_size:
            raise FlashError("program must fit one page")
        old = self._data[name][offset:offset + len(data)]
        if any((a & b) != b for a, b in zip(old, data)):
            raise FlashError("program attempted 0-to-1 transition without erase")
        self._data[name][offset:offset + len(data)] = data

    def _validate_fault(self, fault, size):
        if fault is None:
            return
        if not isinstance(fault, FaultPlan) or fault.kind not in {"erase_error", "program_error", "power_loss", "readback_mismatch"}:
            raise FlashError("unknown fault plan")
        for index, maximum in [(fault.block_index, size // self.erase_block_size), (fault.page_index, size // self.page_size)]:
            if type(index) is not int or not 0 <= index < maximum:
                raise FlashError("fault index out of range")
        if fault.stage not in {"erase", "program"} or type(fault.partial_bytes) is not int or not 0 <= fault.partial_bytes <= self.page_size:
            raise FlashError("invalid fault stage/partial length")
        if fault.partial_bytes and not (fault.kind == "power_loss" and fault.stage == "program"):
            raise FlashError("partial bytes only apply to power loss during program")

    def program_component(self, name, data, fault_plan=None):
        data = bytes(data)
        self._check(name, 0, len(data))
        if len(data) != self.layout[name]["size"]:
            raise FlashError("whole-component write requires exact envelope size")
        self._validate_fault(fault_plan, len(data))
        f = fault_plan
        result = {"component": name, "status": "success", "returned": True,
                  "return_code": 0, "stage": "complete", "offset": len(data),
                  "before_sha256": _sha(self._data[name]), "expected_sha256": _sha(data),
                  "erased_blocks": 0, "programmed_pages": 0, "programmed_bytes": 0,
                  "events": [], "fault": None if f is None else vars(f).copy()}

        def event(stage, offset, **fields):
            result["events"].append(dict(component=name, stage=stage, offset=offset, **fields))

        def finish(status="success", stage="complete", offset=None):
            result.update(status=status, stage=stage, offset=len(data) if offset is None else offset,
                          returned=status != "interrupted",
                          return_code=None if status == "interrupted" else (0 if status == "success" else 0x3101),
                          actual_sha256=_sha(self._data[name]))
            event(stage, result["offset"], status=status)
            self.last_result = copy.deepcopy(result)
            self._checkpoint()
            return copy.deepcopy(result)

        for block in range(0, len(data), self.erase_block_size):
            bi = block // self.erase_block_size
            if f and f.kind == "erase_error" and bi == f.block_index:
                return finish("error", "erase", block)
            if f and f.kind == "power_loss" and f.stage == "erase" and bi == f.block_index:
                return finish("interrupted", "erase", block)
            self.erase(name, block, self.erase_block_size)
            result["erased_blocks"] += 1
            event("erase", block, length=self.erase_block_size)
            for offset in range(block, block + self.erase_block_size, self.page_size):
                pi = offset // self.page_size
                if f and f.kind == "program_error" and pi == f.page_index:
                    return finish("error", "program", offset)
                if f and f.kind == "power_loss" and f.stage == "program" and pi == f.page_index:
                    if f.partial_bytes:
                        self.program(name, offset, data[offset:offset + f.partial_bytes])
                        result["programmed_bytes"] += f.partial_bytes
                        event("partial_program", offset, length=f.partial_bytes)
                    return finish("interrupted", "program", offset)
                self.program(name, offset, data[offset:offset + self.page_size])
                result["programmed_pages"] += 1
                result["programmed_bytes"] += self.page_size
            event("program_block", block, length=self.erase_block_size)
        # Native caller owns readback and checksum comparison. Inject an actual
        # persistent media mismatch while reporting a successful program leaf.
        if f and f.kind == "readback_mismatch":
            offset = f.page_index * self.page_size
            self._data[name][offset] ^= 1
            result["corruption_injected"] = True
            event("corruption_injected", offset, xor_mask=1)
        return finish()

    def identity_report(self):
        if self.closed:
            raise FlashError("store is closed")
        return {"schema": SCHEMA, "layout": copy.deepcopy(self.layout),
                "geometry": {"page_size": self.page_size, "erase_block_size": self.erase_block_size,
                             "basis": "logical assumptions; not proven chip geometry"},
                "envelope": {"header_bytes": 32, "trailer_bytes": 32},
                "persistence": "single writer; fsync at component/fault/close checkpoints, not pages; actual host crash may invalidate store",
                "hardware_qualified": False,
                "components": {name: {"size": len(data), "sha256": _sha(data), "original_sha256": self._original[name]} for name, data in self._data.items()},
                "last_result": copy.deepcopy(self.last_result)}

    def _checkpoint(self):
        for name, data in self._data.items():
            path = self.path / f"{name}.flash.bin"
            if path.is_symlink():
                raise IntegrityError("component symlink is not allowed")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
        manifest = self.identity_report()
        manifest["manifest_sha256"] = _sha(_canonical(manifest))
        temporary = self.path / "manifest.tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as out:
            json.dump(manifest, out, sort_keys=True, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, self.path / "manifest.json")
        fd = os.open(self.path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def close(self, *, checkpoint=True):
        """Close the handle, optionally discarding uncheckpointed RAM changes.

        Use checkpoint=False after create/program_component when reopening to
        verify disk state: closing must not repair or overwrite external changes.
        """
        if not self.closed:
            if checkpoint:
                self._checkpoint()
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
