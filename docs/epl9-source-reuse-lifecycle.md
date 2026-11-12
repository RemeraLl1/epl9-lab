# OpenGate: source-return identity after buffer reuse

2026-11-13. Read-only bounded experiment. No firmware patch or camera test.

## New finding

The source-return fragment beginning at `0x607116c6` matches a callback's input address against **record +4** in the nine-entry source table at `0xa2af3ac8`. After a match it changes the current reference byte and record state. No generation comparison occurs in this bounded fragment.

Consequently a hypothetical old return delivered after the same address has been reused is locally indistinguishable from a current return. This does **not** prove that stock firmware delivers such a callback: upstream queue admission, drain and synchronization may prevent it. It identifies the external invariant an OpenGate pool change must preserve.

## Native experiments and explicit host bridge

`scripts/epl9_source_reuse_probe.py` checks the exact build-1101 decoded-main SHA, pinned reader, byte-checked windows and five instruction anchors. It executes:

1. The existing native generic-pool allocation/release/recycle experiment with six host-configured slots and 4147200-byte stride. Six allocations succeed, seventh is denied, release restores capacity, next allocation recycles handle `0x2f01`.
2. **Host bridge:** the first allocation's pixel address is installed into a synthetic source record. This is not execution of the real firmware producer connecting allocator to the source table. Nor does the experiment run actual stop/restart.
3. The complete bounded source-address search and reference update, ending before the service call at `0x60711724`.

Seven return controls pass:

| Injected state | Native result |
| --- | --- |
| Current callback, one reference, another selected slot | Reference 1→0; state 2→1, sweep eligible |
| Hypothetical previous-generation callback, identical address | Identical native trace and mutation |
| Global condition nonzero | No source-reference mutation |
| Address absent from table | No source-reference mutation |
| Two references | Reference 2→1; state stays 2 |
| Matched slot is retained/selected | Reference 1→0; state stays 2 |
| Duplicate address in two synthetic records | First matching record changed, second untouched |

Duplicate records and late callbacks are injected counterexamples, not observed production states. Native sweep eligibility is not a completed release, DMA quiescence or proof of safely displaying a frame.

### The global condition is not a proven stop guard

The fragment first reads `0xa2af3c80`; nonzero skips the search. A direct absolute-address scan led to initialization at `0x60710c74`: input `d1` is narrowed to 16 bits and stored at `0x60710c8e`. Three native controls (0, 1, 65537) confirm stored values 0, 1, 1. Other readers choose different resource behavior according to this field.

Therefore call this a **mode/control condition**, not an established generation or stop/restart interlock. The raw-address scan is not a complete writer census: computed/aliased accesses are not excluded.

## Required lifecycle contract

Before changing raster, slot count, pool ownership or reusing addresses:

- Prevent new producer submissions through the actual native submission gate.
- Drain processing/DMA/codec ownership and queued completion messages, not just the pixel allocator.
- Account separately for retained source references.
- Confirm actual release success, then rebuild/reconfigure records.
- Reopen delivery only once no old address-only return can be mistaken for a new frame.

A generation token is one possible new design, **not a found firmware feature or an implemented patch**. A verified drain barrier could also satisfy the requirement without changing callback format. Do not add a token until every producer/consumer and message format is mapped.

## Next reverse-engineering targets

1. Enumerate callers and message wrappers of `0x607116c6`: recover callback payload lifetime and queue ownership.
2. Trace final-cleanup preconditions `0x6071131d` → queued operations 5/6 → `0x60718e02`, and processing completion `0x60707429` → `0x6071c52f`. Prove what their success/error return paths actually wait for.
3. Connect source record population to allocator outputs and stop/restart transitions. The current host bridge explicitly leaves this open.
4. Exercise native event ordering once those paths are available: callback before drain, during drain, after reset and after reuse. Tests must stop on unresolved services rather than invent their success.

Previous native geometry acceptance remains only descriptor arithmetic. Neither this work nor the six-slot controls establishes 1920×1440/60 sensor/ISP/encoder operation, bandwidth or sufficient in-flight capacity.

## Reproduction

Use a private exact build-1101 decoded main image; OEM input is not published.

```sh
python scripts/epl9_source_reuse_probe.py --main /private/main.bin --out /tmp/source-reuse-report.json
```

Requires the existing virtual-updater branch's native reader/subset and video-audit scripts. Scalar evidence: `docs/evidence/source-reuse-20261113.json`. The frozen ART candidate is unchanged.
