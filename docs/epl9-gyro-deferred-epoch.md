# E-PL9 gyro: deferred timer epoch experiment

Date: 2026-11-12. Read-only source research on the exact build-1101 stabilizer component. This is not a gyro logger, camera emulator, firmware patch or installation qualification.

## New result

The existing timer-0 callback can be followed into an RTOS deferred tick accumulator. There is a potentially useful long counter, but it is **not updated at the instant of the hardware timer event**. Joining its value naively to the hardware phase can produce a backwards timestamp when a tick is pending.

Exact input: 219104-byte stabilizer component, SHA-256 `1c942d2fb6b8830f0195a0be7464880838ddf08c5f038bad626aed8e72789678`. Component mapping base: `0x40002800`. OEM input and disassembly are not distributed here.

### Bounded native path

| Stage | Address | Observed operation |
| --- | --- | --- |
| Timer setup | `0x4001753b` | Configures comparator 50000 and callback `0x40017578` |
| Callback | `0x4001757b` | Calls `0x4001cf1f`, whose call at `0x4001cf26` enters `0x4001cef8` |
| Admission | `0x4001cef8` | Rejects when byte `0x6209` is nonzero or byte `0x6208` is zero |
| Deferred increment | `0x4001cf0f`–`0x4001cf13` | Increments byte `0x61f5` inside critical-section boundaries |
| Deferred drain | `0x4001d385`–`0x4001d38f` | Decrements pending count, then calls tick processing `0x4001e466` |
| Long counter | `0x4001e472`–`0x4001e481` | Increments low 32 bits at `0x620c`, carries into 16 bits at `0x6210` |
| Reset | `0x4001d53a`, `0x4001d5b6` | Clears the long counter and pending byte respectively |

The surrounding drain is reached from an interrupt-nesting exit. This does not prove which interrupt is the first sample event, nor provide a safe acquisition hook. The long counter is 48 bits by observed storage arithmetic, not a certified clock-frequency measurement.

## Reproducible experiment

`scripts/epl9_gyro_epoch_probe.py` verifies the exact private input hash, the pinned MN103 reader and 13 instruction anchors across seven bounded windows. It executes original decoded instructions in the existing subset interpreter using synthetic RAM. Fragments are explicitly entered independently; calls to critical-section helpers are boundaries, not silently simulated successes.

18 native cases passed:

- Four long-counter cases, including low-word carry and full 48-bit wrap.
- Four admission flag combinations; only `(0x6209=0, 0x6208=1)` admits the increment.
- Four pending-byte increments, including synthetic `255 → 0`.
- Three drain prefixes, distinguishing zero pending from a tick-processing call.
- Three existing phase-difference controls, including single comparator wrap.

The byte overflow case proves arithmetic under that synthetic state. It does **not** establish that the camera ever loses pending ticks in operation.

Three separately labelled host-algebra examples show the timing hazard: epoch 10/phase 49999, then epoch 10/pending 1/phase 0, then drained epoch 11/phase 0. `epoch × 50000 + phase` goes backwards at the middle observation. These are not native timing measurements, and 50000's inclusive endpoint remains unqualified.

Run from the repository root with the dependency scripts from the virtual-updater branch:

```sh
python scripts/epl9_gyro_epoch_probe.py --aux /private/exact-stabilizer-component.bin --out /tmp/gyro-epoch-report.json
```

A scalar-only run record is in `docs/evidence/gyro-deferred-epoch-20261112.json`. It includes instruction-address traces, not OEM binary data.

## What this changes for gyro logging

The counter is a lead for preserving time across phase wraps. It is not enough to write `(epoch, phase)` beside yaw/pitch/roll and call that synchronized gyro data. Pending tick service, snapshot atomicity, timer resets and sample acquisition must be accounted for.

Next bounded experiments, in order:

1. Trace the exact timer interrupt acknowledgement/reload path and its relation to pending enqueue. Qualify whether comparator phase includes the endpoint and when it resets.
2. Trace all writers and readers of the long counter and pending byte, including initialization and mode transitions. The current bounded probe is not a whole-program access census.
3. Identify an acquisition-side snapshot point and a consistent read protocol across phase/pending/epoch. Test injected event ordering at every read boundary in a clearly labelled host model, then connect those cases to real interrupt masking semantics. Do not deploy a guessed atomic-read scheme.
4. Tie sample events to that domain separately: existing yaw/pitch rolling sums and roll callback do not yet establish coherent three-axis samples.
5. Resolve timer parent/divider and absolute units; only then compare a paired main-domain event with the stabilizer domain. The main exposure clock and frame timing remain separate until a real join is found.

## OpenGate boundary

This finding does not improve OpenGate video validation. Previous geometry experiments accept requested 1920×1440/60 descriptors but do not prove sensor readout, ISP execution, encoder throughput or buffer ownership safety. An emulator with synthetic RAM cannot establish those physical results.

The next OpenGate experiment must connect the real allocation, frame-generation, outstanding-reference and release paths. It should test a late callback after stop/restart against reused addresses, not merely increase buffer sizes or observe a zero stop-state flag. Existing source-return and release-sweep probes are starting points; their fragments must not be described as an integrated lifecycle until that connection is established.

No frozen ART candidate, camera, device setting or firmware bytes were changed by this work.
