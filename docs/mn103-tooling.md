# Local MN103 disassembly on Windows and Linux

The project uses unmodified GNU binutils MN103 opcode/disassembler sources with a small local file-reading adapter. It is a window disassembler, not a full binutils installation, assembler, emulator, decompiler or control-flow analyzer. It cannot establish code reachability or firmware bootability.

## Provenance

- GNU binutils tag `binutils-2_45`, commit `2bc7af1ff7732451b6a7b09462a815c3284f9613`, upstream `https://sourceware.org/git/binutils-gdb.git`.
- A pinned source subset lives in ignored `references/binutils-2.45-mn103/`, retaining original notices and `COPYING3`. The primary GNU mirror provides each file at `https://gnu.googlesource.com/binutils-gdb/+/2bc7af1ff7732451b6a7b09462a815c3284f9613/<path>?format=TEXT` (base64-encoded content).
- TinyCC 0.9.27 Windows x64 archive: [official release location](https://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip), `489586` bytes, SHA-256 `34a721949a2583fdff725312da092fa0f5f1f284b702e6f811c6954714faabb2`. Installed only under ignored `tools/tinycc/`.
- Exact source and compiler hashes are recorded in `scripts/mn103_reader/upstream.json`. These hashes pin the inspected input; they are not a publisher-signature verification claim.

The public project contains its own adapter and validation scripts, not copied GNU disassembler code. The adapter's C/header files are GPL-3.0-or-later. The locally linked program incorporates GNU code under GPL-3.0-or-later; preserve the corresponding upstream source, notices and license if redistributing it.

## Build and validate

Place the exact source files listed in `upstream.json` below `references/binutils-2.45-mn103/`. The builder performs no downloads and verifies every file's raw byte length and SHA-256, including the upstream test vectors and licence.

On Windows, extract the pinned compiler archive below `tools/tinycc/` so the compiler is `tools/tinycc/tcc/tcc.exe`.

```powershell
.\.venv\Scripts\python.exe .\scripts\mn103_reader\build_reader.py
```

On Linux, use an installed C compiler (`cc` by default, or an explicit local `--compiler` path):

```sh
python scripts/mn103_reader/build_reader.py
python scripts/mn103_reader/smoke_reader.py --out local/mn103-linux-smoke
```

Python 3.12 or newer is required. Linux uses `-std=c99 -O2`; Windows retains the pinned TinyCC recipe. The adapter and GNU source files are unchanged. Output is restricted to ignored `local/`. The Linux build writes `local/mn103-tooling/mn103-reader`, while Windows writes `mn103-reader.exe`. Nothing is added to `PATH` or downloaded by these commands.

Each successful build writes `build.json` with the actual executable digest, compiler executable digest/version, host platform/architecture, exact command, pinned upstream identities, adapter-source identities and validation report. The Linux compiler is recorded, not misrepresented as the historical Windows compiler. A failed rebuild removes the successful receipt before compilation. The linked executable is not published by the build.

`scripts/mn103_tooling.py` selects the platform-specific local path. It preserves acceptance of the exact historical Windows reader SHA `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`. Other binaries require a matching current build receipt, unchanged upstream/adapter files, exact validation inventory and a fresh independent vector/rejection check once per process. Altered binaries, stale sources, changed receipts and foreign-host receipts fail closed. A receipt alone does not replace executing the validation. Rebuild after changing the reader's build/validation sources. These are local provenance checks, not a publisher signature or a sandbox against malicious local compilers.

Research consumers retain explicit `--reader` overrides where previously available and report the actual selected binary SHA. Parsing CLI options or using a saved-listing-only workflow does not require an installed reader. Input-model/hash gates still precede decoding.

Initial validation passed **1294 upstream AM33-2 instruction vectors** (addresses, bytes, lengths and instruction text) and five rejection cases: truncated instruction, out-of-image range, address overflow, negative offset and unsupported machine. The fixture comparison removes only objdump symbol decorations while retaining numeric target checks. This validates the adapter/decoder for those vectors, not all camera instructions or runtime behavior.

The validator now requires the exact pinned vector file, exactly 1294 instructions and 5694 fixture bytes, rather than accepting an arbitrary file containing at least 1000 parsed vectors. The firmware-free smoke check independently decodes the separate 877-byte bounded-reader module (197 instructions) and executes three modeled-MMIO controls: completion, absent exclusivity and DMA timeout. It does not reproduce the archived exact-stock 44-case probe and does not execute physical DMA.

The historical Windows workstation sandbox blocked TinyCC and its output executables with a Windows DLL relocation error. Those recorded commands required the approved execution path outside that isolation; neither a Windows reboot nor camera access was involved. The new Linux path was tested with GCC 14.2.0 on x86-64. A new Windows build has not been rerun in the cloud.

## Use

```powershell
.\local\mn103-tooling\mn103-reader.exe <decoded-image> <candidate-base> <start-file-offset> <stop-file-offset> [machine]
```

On Linux the equivalent executable is `./local/mn103-tooling/mn103-reader`.

Numbers accept `0x` notation. Machine `332` (AM33-2) is the default. A listing line contains address, instruction bytes and GNU mnemonic/operands, separated by tabs. The reader opens the input in binary read-only mode and has no camera or firmware-writing interface.

The caller must identify instruction boundaries. Decoding arbitrary data or starting inside an instruction can produce plausible nonsense. A stop offset limits instruction start addresses; the last complete instruction may end beyond it. Unknown/custom opcodes such as `udf00` are not assigned execution semantics by this adapter.

Use the exact-input-gated `scripts/epl9_art_probe.py` for the recorded E-PL9 research windows. The reader alone accepts arbitrary local binaries for synthetic validation and is not a model compatibility check.
