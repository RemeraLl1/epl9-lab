# E-PL9: native completion contracts and input-family identification

## Result, 2026-11-04

The short Bayer input now passes its previously unmodeled software arithmetic/configuration and reaches the same first peripheral boundary as the existing cases. The native owner callback and notification-to-cleanup chain are executable as separate component checks. No full pixel cycle or camera operation is claimed.

The exact firmware's diagnostic classifier identifies `0x0200` as **4AspectsData**. The previous stride measurement remains valid, but a two-byte stride must not be promoted into a conventional pixel-format interpretation. The measured native source configuration does not establish that a camera-produced 4AspectsData buffer has the synthetic fixture's layout.

## Exact input and scope

- Olympus E-PL9; displayed body version **1.1** from the owner; downloaded main build **1101**, not an installed-body dump.
- Stock `OLY_E_133_1101_0000_0000.BIN`: **104552480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- Decoded main: **26214336 bytes**, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, analysis base `0x60400020`.
- GNU reader SHA-256 `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`; fresh listings are byte-checked and overlap-checked by the probes.
- Instruction semantics follow the previously pinned GNU `mn10300.igen` revision `87ffb882e0f4d73401a0746177ffabb8e8bbe4ac` in the ignored reference checkout.

No camera access, firmware writes, peripheral-memory model, DMA/ISP execution or recipe calibration was added. All owner/job records are explicitly synthetic. The native callbacks below are two firmware owner implementations, not a proven binding to every preview/capture context on the owner's body.

## Format identification executed from native code

`0x61767948` masks the descriptor format's high byte and selects its family label. `0x6176799f` separately looks up subtype labels through the exact table at `0x6179ef24`, using `format-255` as its key. The new audit executes both functions through their returns and captures ROM strings at a declared host logging sink.

| Input code | Native family label | Native subtype label |
| --- | --- | --- |
| `0x0100` | Bayer | BayerBit: 8 |
| `0x0200` | 4AspectsData | No subtype output from this printer |
| `0x0302` | YCC | YCC422 |
| `0x0305` | YCC | YCC444 |
| `0x0307` | YC420 | YYCC |

The family-2 branch at `0x6176795c…0x61767974` chooses the string at `0x6179e778`. The YCC422 row's key is `0x203`, corresponding to descriptor format `0x302`; the lookup offset must be accounted for. These labels identify firmware terminology, not byte order, color range, sample placement, CFA pattern, endian order of sensor samples, or a RAW/JPEG file codec. `0x100` is the native diagnostic's 8-bit Bayer variant; the existing two-byte source allocation is deliberately oversized synthetic backing, not a measured Bayer byte depth.

## Events 23/24 depend on the owner

The callback `0x607cfe8d` logs, then dispatches events 2…34 using `0x6090b550 + 4*(event-2)`. Both event **23** and **24** select `0x607cffc0`, returning the byte at owner+195. Neither branch calls a slot allocator/free routine. The wrapper `0x607d16c7` logs and delegates to the same native body; it adds special behavior for event 16 only.

Eight full callback runs cover both entry points, events 23/24 and owner status 0/1. All return the exact owner status, preserve all 512 owner bytes and balance the native stack. Only the two identified logging fronts are modeled. This narrows the previous hypothesis: **event 24 is a lifecycle notification whose effect depends on the owner, not a universal physical-buffer-free operation**. The host fixture's activation set does not prove a leak in a real owner which accepts both notifications without tracking that set.

The request callback `0x607504f6` handles event 10 by storing the supplied status at pending+32. When job+10396 is set and pending+36/+38 contain `0xff07`/`0xff0b`, calls at `0x607505a9`/`0x607505c9` deliver event 24 before the later event signal. The callback then forwards event 10 to the owner and invokes the native signal wrapper.

Four component cases cover notification enabled/disabled and supplied status 0/`0x9e40`. After that notification, native `0x6074edd9` waits, clears the event, releases its host token, delivers owner event 22 and clears all 56 pending bytes. Each case returns its supplied status. There is deliberately no consumer ID in this isolated record; consumer-ID teardown remains covered by the separate failed-job tests. These cases **inject the notification directly** and do not assert hardware completion, successful pixels, output handoff or an end-to-end successful job.

## Short Bayer path and native wide arithmetic

The previous stop `0x6073920e → 0x604bbfac` is a 64-bit left-shift helper, followed by native unsigned 64-bit division at `0x604bbecc`. The interpreter now supports the necessary GNU `lra`, `addc`, `subc` and rotate-through-carry `ror`. The carry/zero/overflow behavior follows the pinned GNU formulas, including its chained Z and carry rules; this is not validation of every hardware CPU corner case.

The native helper tests compare 210 left shifts and 120 divisions with Python integer results, including zero numerators, 32-bit boundaries, full-width values and deterministic random values. Divide-by-zero behavior is not used as an image-processing success case. The short path also executes the native prefix at `0x6078e82d` and full configuration `0x6078e890…0x6078ef25`; the new paths are neither stubbed nor bypassed.

All four short Bayer cases (two identities × selectors 0/2) now stop at **`0x6073eafa` writing `0x800` to unmapped `0x9880014c`**, matching the existing hardware boundary. Their source/output backing remains synthetic and unchanged. The eight connected COLOR table comparisons and all old job negative controls remain intact.

Inspection of the processor after that boundary shows further required work: start at `0x6073f74f`, owner callbacks 5/6, native `0x6073f845`, and workspace/cache cleanup at `0x6073f566`. The selected `0x6073f845` branches reach `0x60740255`/`0x6074044f`, which program additional `0x9f…` peripheral registers and call `0x607a478d`. Exact peripheral-ready/status/interrupt and buffer-coherence semantics remain open. Mapping zero-filled peripheral pages or injecting event 10 would not establish a working image pipeline.

## Reproduction and retained evidence

```powershell
.\.venv\Scripts\python.exe scripts/epl9_completion_audit.py --out local/new-completion-audit
.\.venv\Scripts\python.exe scripts/epl9_job_probe.py --out local/new-job-probe
```

The output directory must be new and ignored under `local/`; Python assertions must remain enabled. Reports retain source hashes and modeled/native call traces.

- New completion audit: eight owner cases, four notification/cleanup cases, five format-label cases and **330 native arithmetic cases**.
- Full job probe: previous baseline, attached COLOR, cancellation/input controls, destructor, buffer sweep and stride checks pass; short Bayer cases now reach the hardware boundary.
- Historical offline regressions: **30 route pairs, 180 saturation cases, two full tables, 1050 flag cases**, zero new ordinary-schedule changes.
- Integrated regressions: **120 full-builder pairs, both COLOR call chains**, existing cancellation/service checks.
- Workspace unit tests: **121 passed**, including added carry/rotate/loop and diagnostic-boundary rejection tests. Independent Wi-Fi/video tests contribute to the workspace count and are not new ART pixel validation.

Retained local outputs: `local/completion-audit-20261104-final/results.json`, `local/job-probe-native-bayer-20261104-final/results.json`, `local/offline-regression-20261104/results.json` and `local/integrated-regression-20261104/results.json`. The completion/job outputs were rerun for the final source state. An initial format assertion needed to strip the diagnostic strings' trailing newlines; it was corrected before the passing runs.

Next qualification is the actual camera caller's input producer and hardware completion/data-flow contract. Film-look rendering, real sample/color verification, complete owner-buffer reuse and a deployable patch remain open. `full_pixel_cycle_passed` stays **false**.
