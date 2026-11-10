"""Sample Windows instruction pointers in OM Workspace's software RAW workers.

No code injection, memory writes, breakpoints, camera access, or DLL calls.
Each successful thread suspension is paired with ResumeThread in finally.
Addresses identify executing libraries, not a proven pixel algorithm or call chain.
"""
import argparse
import collections
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(r'C:\Program Files (x86)\OMDS\OM Workspace')
NAMES = {'OM Workspace.exe', 'cmdDecode.exe', 'cmdBatch.exe'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seconds', type=int, default=45)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if not 1 <= args.seconds <= 180:
        ap.error('duration must be 1..180 seconds')
    if args.out.exists() or not args.out.resolve().is_relative_to((ROOT / 'local').resolve()):
        ap.error('output must be a new ignored local file')
    if C.sizeof(C.c_void_p) != 8:
        ap.error('requires 64-bit Windows Python')
    k = C.WinDLL('kernel32', use_last_error=True)
    SIZE = C.c_size_t
    class Process(C.Structure):
        _fields_ = [('size', W.DWORD), ('usage', W.DWORD), ('pid', W.DWORD),
                    ('heap', SIZE), ('module', W.DWORD), ('threads', W.DWORD),
                    ('parent', W.DWORD), ('priority', W.LONG), ('flags', W.DWORD),
                    ('exe', W.WCHAR * 260)]
    class Thread(C.Structure):
        _fields_ = [('size', W.DWORD), ('usage', W.DWORD), ('tid', W.DWORD),
                    ('pid', W.DWORD), ('priority', W.LONG), ('delta', W.LONG),
                    ('flags', W.DWORD)]
    class Module(C.Structure):
        _fields_ = [('size', W.DWORD), ('id', W.DWORD), ('pid', W.DWORD),
                    ('global_usage', W.DWORD), ('process_usage', W.DWORD),
                    ('base', C.c_void_p), ('bytes', W.DWORD), ('handle', W.HMODULE),
                    ('name', W.WCHAR * 256), ('path', W.WCHAR * 260)]
    signatures = {
        'CreateToolhelp32Snapshot': ([W.DWORD, W.DWORD], W.HANDLE),
        'CloseHandle': ([W.HANDLE], W.BOOL),
        'OpenProcess': ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
        'QueryFullProcessImageNameW': ([W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)], W.BOOL),
        'OpenThread': ([W.DWORD, W.BOOL, W.DWORD], W.HANDLE),
        'GetProcessIdOfThread': ([W.HANDLE], W.DWORD),
        'SuspendThread': ([W.HANDLE], W.DWORD),
        'ResumeThread': ([W.HANDLE], W.DWORD),
        'GetThreadContext': ([W.HANDLE, C.c_void_p], W.BOOL),
    }
    for typ, cls, suffix in [('Process', Process, 'W'), ('Thread', Thread, ''), ('Module', Module, 'W')]:
        for action in ['First', 'Next']:
            signatures[f'{typ}32{action}{suffix}'] = ([W.HANDLE, C.POINTER(cls)], W.BOOL)
    for name, (parameters, result) in signatures.items():
        f = getattr(k, name)
        f.argtypes, f.restype = parameters, result

    def snapshot(flags, pid, typ, cls, suffix):
        handle = k.CreateToolhelp32Snapshot(flags, pid)
        if handle == C.c_void_p(-1).value:
            return []
        rows = []
        try:
            entry = cls()
            entry.size = C.sizeof(cls)
            ok = getattr(k, f'{typ}32First{suffix}')(handle, C.byref(entry))
            while ok:
                rows.append(cls.from_buffer_copy(entry))
                ok = getattr(k, f'{typ}32Next{suffix}')(handle, C.byref(entry))
        finally:
            k.CloseHandle(handle)
        return rows

    counts = collections.Counter()
    errors = collections.Counter()
    processes, modules = {}, {}
    start = time.monotonic()
    until = start + args.seconds
    next_scan = 0
    targets = {}
    while time.monotonic() < until:
        now = time.monotonic()
        if now >= next_scan:
            targets = {}
            for row in snapshot(2, 0, 'Process', Process, 'W'):
                if row.exe not in NAMES:
                    continue
                handle = k.OpenProcess(0x1000, False, row.pid)
                if not handle:
                    continue
                try:
                    path = C.create_unicode_buffer(32768)
                    length = W.DWORD(len(path))
                    if not k.QueryFullProcessImageNameW(handle, 0, path, C.byref(length)):
                        continue
                    if Path(path.value).parent != INSTALL:
                        continue
                finally:
                    k.CloseHandle(handle)
                targets[row.pid] = row.exe
                processes[row.pid] = row.exe
                modules[row.pid] = snapshot(8 | 16, row.pid, 'Module', Module, 'W')
            next_scan = now + 0.25
        for row in snapshot(4, 0, 'Thread', Thread, ''):
            if row.pid not in targets:
                continue
            handle = k.OpenThread(2 | 8 | 0x40, False, row.tid)
            if not handle:
                errors['open_thread'] += 1
                continue
            try:
                if k.GetProcessIdOfThread(handle) != row.pid:
                    errors['thread_owner_changed'] += 1
                    continue
                buffer = C.create_string_buffer(1232 + 16)
                address = (C.addressof(buffer) + 15) & ~15
                C.c_uint32.from_address(address + 48).value = 0x100001
                previous = k.SuspendThread(handle)
                if previous == 0xffffffff:
                    errors['suspend'] += 1
                    continue
                try:
                    if not k.GetThreadContext(handle, address):
                        errors['context'] += 1
                        continue
                    rip = C.c_uint64.from_address(address + 248).value
                finally:
                    if k.ResumeThread(handle) == 0xffffffff:
                        raise OSError(C.get_last_error(), 'ResumeThread failed')
            finally:
                k.CloseHandle(handle)
            module = next((m for m in modules[row.pid] if m.base <= rip < m.base + m.bytes), None)
            if module:
                counts[(row.pid, row.tid, module.name, rip - module.base)] += 1
            else:
                errors['unmapped_ip'] += 1
        time.sleep(0.01)
    inventory = {}
    for rows in modules.values():
        for m in rows:
            if Path(m.path).parent == INSTALL:
                p = Path(m.path)
                inventory[m.name] = {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    report = {'scope': 'Sampled execution addresses during software Workspace work; not camera TruePic execution',
              'duration_seconds': time.monotonic() - start, 'processes': processes,
              'modules': inventory, 'errors': dict(errors),
              'samples': [{'pid': p, 'tid': t, 'module': m, 'rva': hex(r), 'count': n}
                          for (p, t, m, r), n in counts.most_common()]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    totals = collections.Counter()
    for (_, _, name, _), count in counts.items():
        totals[name] += count
    print(json.dumps({'out': str(args.out), 'errors': dict(errors), 'top_modules': totals.most_common(20)}))


if __name__ == '__main__':
    main()
