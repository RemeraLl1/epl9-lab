# Local MN103 disassembly on Windows

The project uses unmodified GNU binutils MN103 opcode/disassembler sources with a small local file-reading adapter. It is a window disassembler, not a full binutils installation, assembler, emulator, decompiler or control-flow analyzer. It cannot establish code reachability or firmware bootability.

## Provenance

- GNU binutils tag `binutils-2_45`, commit `2bc7af1ff7732451b6a7b09462a815c3284f9613`, upstream `https://sourceware.org/git/binutils-gdb.git`.
- A pinned source subset lives in ignored `references/binutils-2.45-mn103/`, retaining original notices and `COPYING3`. The primary GNU mirror provides each file at `https://gnu.googlesource.com/binutils-gdb/+/2bc7af1ff7732451b6a7b09462a815c3284f9613/<path>?format=TEXT` (base64-encoded content).
- TinyCC 0.9.27 Windows x64 archive: [official release location](https://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip), `489586` bytes, SHA-256 `34a721949a2583fdff725312da092fa0f5f1f284b702e6f811c6954714faabb2`. Installed only under ignored `tools/tinycc/`.
- Exact source and compiler hashes are recorded in `scripts/mn103_reader/upstream.json`. These hashes pin the inspected input; they are not a publisher-signature verification claim.

The public project contains its own adapter and validation scripts, not copied GNU disassembler code. The adapter's C/header files are GPL-3.0-or-later. The locally linked program incorporates GNU code under GPL-3.0-or-later; preserve the corresponding upstream source, notices and license if redistributing it.

## Build and validate

Place the source files listed in `upstream.json` below `references/binutils-2.45-mn103/` and extract the pinned compiler archive below `tools/tinycc/` so the compiler is `tools/tinycc/tcc/tcc.exe`. The dependencies are already present in this workstation.

```powershell
.\.venv\Scripts\python.exe .\scripts\mn103_reader\build_reader.py
```

The build verifies every listed source hash and the compiler executable hash, compiles the adapter, and runs the validation fixture. It performs no downloads. Output is restricted to ignored `local/`.

Initial validation passed **1294 upstream AM33-2 instruction vectors** (addresses, bytes, lengths and instruction text) and five rejection cases: truncated instruction, out-of-image range, address overflow, negative offset and unsupported machine. The fixture comparison removes only objdump symbol decorations while retaining numeric target checks. This validates the adapter/decoder for those vectors, not all camera instructions or runtime behavior.

The sandbox on this workstation blocks TinyCC and its output executables with a Windows DLL relocation error. These commands required the approved execution path outside that isolation; neither a Windows reboot nor camera access was involved.

## Use

```powershell
.\local\mn103-tooling\mn103-reader.exe <decoded-image> <candidate-base> <start-file-offset> <stop-file-offset> [machine]
```

Numbers accept `0x` notation. Machine `332` (AM33-2) is the default. A listing line contains address, instruction bytes and GNU mnemonic/operands, separated by tabs. The reader opens the input in binary read-only mode and has no camera or firmware-writing interface.

The caller must identify instruction boundaries. Decoding arbitrary data or starting inside an instruction can produce plausible nonsense. A stop offset limits instruction start addresses; the last complete instruction may end beyond it. Unknown/custom opcodes such as `udf00` are not assigned execution semantics by this adapter.

Use the exact-input-gated `scripts/epl9_art_probe.py` for the recorded E-PL9 research windows. The reader alone accepts arbitrary local binaries for synthetic validation and is not a model compatibility check.
