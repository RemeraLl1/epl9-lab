# E-PL9 native SD loader prototype

The subsequent [owned-state/two-slot prototype](epl9-sd-state-slots.md) binds
session state to an explicitly enlarged HLS singleton and adds logical T1/T2
selectors. This report preserves the earlier standalone generation; its
synthetic context root is not the newer allocation design.

## Result on November 7 2026

A separate original **1322-byte MN103 loader** now executes with the exact stock E-PL9 file wrappers and a native CRC/range validator. A candidate call point is identified in the HLS_EVENT loop after its event-get operation and before dispatch. The loader waits for SD readiness, leaves the embedded recipe selected when the file is absent or rejected, and publishes a retained record only after reading, closing and validating it.

The [source](../firmware_src/epl9_sd_loader.s.in), [emitter](../scripts/epl9_sd_loader.py), [trigger audit](../scripts/epl9_sd_load_trigger_audit.py), [native probe](../scripts/epl9_sd_loader_probe.py) and [synthetic tests](../scripts/test_epl9_sd_loader.py) are separate from the Watercolor module. No hook has been installed or patched into a main image. The loader's `0x69000000` code base and external context root are synthetic probe addresses. This is an executable offline prototype, not a camera-qualified loader or update package.

The owner explicitly accepted embedded fallback when no file exists. The same fallback is retained on invalid data and ordinary completed failures. Exact fallback recipe selection for the eventual custom slots remains open.

## Candidate call point

These findings come from the exact E-PL9 1.1/build 1101 main, independently decoded into nine retained windows. They are E-PL9 addresses, rather than offsets copied from the E-P7 reference.

| Native location | Observed role |
| --- | --- |
| `0x60ae1bb2` | Event-manager task creation; manager +172 holds the returned task ID. |
| `0x60ae1bdc` / `0x60ae1be4` | Supplies the `HLS_EVENT` name and entry `0x60ae1c12` to task creation. The task's ID is the runtime return value, distinct from the constant creation argument 54. |
| `0x60ae1a4d` | Manager getter uses root `0x6239790c`; it can allocate on the null path. The candidate loop already holds its manager in A3. |
| `0x60ae1c6e` | Five-byte `call 0x60ae2073,[a2],8`, bytes `cd05042008`. A1 and D3 identify the event word at caller SP+4. |
| `0x60ae2073` | Event-get adapter calls `0x606b686a`, writes the returned event to its supplied output pointer and returns status zero. Null output returns an error. |
| `0x60ae1c73` | Original continuation checks the returned status. Subsequent dispatch acquires its observed lock at `0x60ae1ccc/1cd1`, after this candidate call point. |

The test-only `sd_event_adapter` replays the original event-get adapter, saves its volatile outputs, invokes the loader when appropriate, restores those outputs and returns to `0x60ae1c73` using the same `[a2],8` convention. It receives the manager and event pointer from the traced caller registers. The context root at synthetic `0x18004000` is explicitly supplied by the harness; it is not a discovered camera state slot. A zero root bypasses loading.

This location avoids adding file I/O to frame configuration or to an IRQ handler. The extra work is deferred until a qualifying user event after readiness. The exact event `0x02000100` is the prototype's reference-consistent half-press gate; source variants such as `0x02040100` are deliberately not normalized by the new loader. Actual E-PL9 event-source normalization, first-half-press delivery and latency still need a runtime check. The native event-get wrapper executes in the probe, while its blocking receive/filter service supplies a declared event through a host model.

## SD readiness and task gates

The native media-status setter at `0x60aef921` distinguishes selectors **4=SD, 1=internal, 32=Cube** through its respective diagnostic strings. For SD, `0x60aef936` writes the incoming status word to **`0x6239914c`**. The native cached-status getter at `0x60aef826` reads this same field; status `0xf000` selects its OK formatting branch. The prototype requires exactly this SD status. An internal-medium OK value does not qualify the SD slot.

Before allocating or opening a file, `sd_try` requires:

1. Event `0x02000100` and this slot's state still zero.
2. CPU identity zero and all nine section-loaded bits at `0xa2aeaa3c` set, using mask `0x1ff`. The existing native loader writes these flags at `0x60422ab8`.
3. Native `get_tid` at `0x604117be` succeeds, and its task ID equals the supplied manager's +172 halfword in range 1..32767.
4. The SD-specific cached mount status equals `0xf000`.

The final probe executes the real task-ID routine as well as the real file context classifier. The per-CPU kernel roots, IRQ-state bytes and current-task/TCB records are explicit read-only fixtures, so this does not emulate an RTOS. The native routine returns -25 for the supplied non-task/interrupt-state control. Runtime file task/service IDs, section flags and mount status are also declared fixtures.

Failing a readiness gate leaves state zero and makes no allocator/file call. Therefore an early half-press does not consume the session's load attempt. A later supplied SD-OK transition and another qualifying event successfully load the record in the probe. This is a controlled input transition, not a measurement of physical mount timing or removal races.

## Loader lifecycle and fallback

Each slot has a caller-owned 32-byte context. Its embedded record pointer and selected record pointer initially agree. The remaining fields hold state, owned block, fixed path/mode pointers and a diagnostic result. All mutable loader state is outside the code image; no stores into a loaded firmware component are introduced.

| State | Meaning | Selected recipe |
| --- | --- | --- |
| 0 | Waiting for an eligible event, task and SD-ready status | Embedded |
| 1 | Load in progress | Embedded |
| 2 | Completed fallback for this session | Embedded |
| 3 | Valid record retained and published | SD record |
| 4 | Close outcome uncertain; resources retained | Embedded |

After the gates, native code sets state 1 and requests one ordinary 2048-byte block. It opens the context's fixed `C:\EPL9MOD\SLOTnn.RCP` path in `r`, reads at most **661 bytes with item size 1**, closes the file and requires exactly 660 returned bytes. It then validates the complete record in native code. Only a valid record becomes the selected pointer, followed by state 3. The retained packed record is the loader's output; expanding it and supplying a generalized film descriptor remain separate consumer work.

A missing file returns a null handle: the block is freed, the embedded pointer stays selected, and state becomes 2. Short, oversized, incompatible and corrupt files are closed and rejected with the same fallback. An ordinary allocation failure also completes fallback. States 2 and 3 suppress subsequent attempts until a new initialized session. File writes and live reload are absent from this prototype.

If close returns an uncertain result, the block is not published or freed; state 4 prevents repeated attempts. A deliberately pending read receives no fabricated RPC completion: execution stops with state 1, the embedded recipe still selected, and the file/request/buffer retained. These incomplete/uncertain paths are not reported as successful cleanup. A real resolution or teardown policy would require the service's completion contract.

The busy state rejects the tested recursive entry from inside the modeled file RPC. This is a scoped reentry check after the busy mark, not an atomic lock or proof against every IRQ/concurrent caller.

## Native validation and file services

The loader checks the [experimental 660-byte format](epl9-sd-slot-study.md#experimental-file-format) independently of the Python decoder. Its native code checks the exact header/model/build/ABI, a nonzero recipe ID, CRC-32 over the whole file with the CRC field treated as zero, ASCII name termination/padding, twelve signed HSL triplets, contrast/H/M/S, two WB gains, and all 256 monotone 12-bit gamma entries. CRC and range validation are original MN103 instructions, with no host validation callback replacing them.

The probe executes stock public open/read/close wrappers, their native context classification and the native registered-file-task lookup. Their synchronous RPC at `0x60434a21` is an explicit finite host service. Open results, file handles and request replies come from that service; no full FAT open/mount or FILECLBK task is simulated. Read requests additionally pass through the existing native buffered read backend with its named local-sector models. Kernel queues, physical card reads/cache/DMA and actual scheduling remain outside these tests. The public read/close wrappers' 128-byte request allocations are supplied successful finite blocks; their exhaustion behavior is not qualified here.

The experiment extends opcode emission locally for register comparisons, SP halfword loads, bitwise operations and conditional branches. It does not edit the shared emitter/interpreter. GNU decoding independently verifies all **327** emitted instruction boundaries, mnemonics, operands, immediates and labels. Encoding reference: GNU binutils tag `binutils-2_45`, commit `2bc7af1ff7732451b6a7b09462a815c3284f9613`, [opcode table](https://gnu.googlesource.com/binutils-gdb/+/2bc7af1ff7732451b6a7b09462a815c3284f9613/opcodes/m10300-opc.c), SHA-256 `1e1150db856998de8366870394297e37d51db464164190e6ed0f988b44910796`. External source remains under ignored `references/`.

## Validation results

- **28 synthetic tests pass:** fourteen existing codec/resolver tests and fourteen new native-loader tests. Native checker cases include valid distinct records, limits, resealed invalid fields, descending/oversized gamma values and CRC corruption. Unit tests use authored instructions with named public-service fixtures; independent GNU and stock-wrapper checks are in the retained probe.
- **19 native probe cases pass their expected outcomes:** valid/missing/short/oversized/corrupt files, ordinary allocation failure, SD-not-ready/in-progress, incomplete sections, wrong CPU/task or unbound manager, close uncertainty, a pending read and four nonmatching events. Native task-ID and file wrappers execute on the declared state.
- **Five event-adapter comparisons pass:** load, release event, early SD state, null event output and an unbound context root. Nine general/SP registers, the returned event word and 32 bytes of the caller's live frame match the original event-get call. PSW flags and MDR are not compared: the traced continuation immediately performs its own compare and calls before using them.
- The not-ready → ready retry and post-busy recursive-entry controls pass separately. A completed valid/missing attempt performs no repeated file operation on the next call.
- Nine protected inputs, including the frozen main/OSD, both encoded candidate/restore packages and the original recipe/module sources, have identical hashes before and after the probe.

Current retained result: `local/epl9-sd-loader-probe-20261107-native-task/validation.json`. Trigger discovery and before-hashes: `local/epl9-sd-loader-trigger-20261107/discovery.json` and `protected-before.json`. Earlier runs are preliminary and remain distinct; the original 1240-byte run did not yet include the event adapter, and earlier 1322-byte runs modeled the task-ID call.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_sd_*.py -v
.\.venv\Scripts\python.exe scripts/epl9_sd_load_trigger_audit.py --out local/new-sd-trigger
.\.venv\Scripts\python.exe scripts/epl9_sd_loader_probe.py --discovery local/new-sd-trigger --file-listings local/epl9-sd-slot-audit-20261107-final --read-listings local/wifi-limits-20261102-v6 --out local/new-sd-loader-probe
```

All output paths must be new and inside ignored `local/`. The source audit and probe use the pinned existing GNU reader; the probe emits only a standalone synthetic-address module and evidence, not an overlay or firmware container.

## Input identity and remaining integration

Olympus E-PL9, displayed body **1.1** reported by the owner, downloaded main build **1101**. Installed camera bytes remain unidentified. Stock package: **104552480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`; stock main: **26214336 bytes**, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`. GNU reader SHA-256: `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.

| Protected or generated component | Bytes | SHA-256 |
| --- | ---: | --- |
| Frozen v3 main | 26214336 | `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686` |
| Frozen icon OSD | 26214336 | `50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b` |
| Encoded v3 candidate | 52428800 | `8d606a028f4b533db6431f1a0271a92d8f3f1c71e08833b481dcb2310d79ef8f` |
| Encoded stock main/OSD restoration | 52428800 | `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387` |
| Standalone loader including event adapter | 1322 | `ed4d4e9055d00393ad1eea267bd265abf4261c3a12fd1980cac7ad216f15d357` |

The next integration work is to qualify real allocation and a durable context root, materialize a common recipe descriptor, and bind that descriptor to future reserved slots without altering the frozen Watercolor candidate. Native task scheduling, event delivery, mount/removal timing, full file service behavior, every allocator failure, display labels and actual image output still need qualification. No camera, SD card or firmware write was used, and the selected call point has not been exercised on hardware.
