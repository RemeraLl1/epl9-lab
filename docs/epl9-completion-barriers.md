# OpenGate: command acknowledgement is not a complete drain proof

2026-11-13. Continuation of source-return lifecycle research (PR #12). Read-only bounded native execution, not a camera test or firmware patch.

## Result

A zero return from `0x60718e02` is insufficient by itself to establish that completion was acknowledged. With a synthetic null allocation outcome for its 12-byte reply buffer, the native routine returns zero **without receiving from the queue**. This is an exact local control-flow observation, not an observed camera failure. Whether this allocation can fail at that call site, or is guaranteed by its allocator contract, remains unresolved.

The processing cleanup routine `0x6074ea4f` invokes object-dependent cleanup services and returns zero. Those service bodies are unresolved here. They may implement synchronization internally, so this experiment does not establish that a real stop sequence lacks a drain barrier.

## What ran

The probe verifies the exact build-1101 decoded-main SHA and pinned GNU reader, checks instruction bytes against the image and checks instruction anchors. It executes native acknowledgement and queue-wrapper instructions, with **explicitly modeled** allocator, kernel receive, memset, logging and free boundaries. No camera or peripheral is emulated.

| Command acknowledgement control | Native return |
| --- | --- |
| Expected opcode 5, successful reply | 0 |
| Expected opcode 6, successful reply | 0 |
| Different reply opcode | `0xff12` |
| Reply status 17 | `0xff12`; output status 17 |
| Injected kernel result -2 | `0x9d10` |
| Injected kernel result 1 | `0x9d09` |
| Null reply allocation | 0; no receive |

The actual wrapper `0x6071771c` is executed; kernel service `0x604313e9` is modeled. Synthetic messages are not evidence of real completion delivery or order.

Six cleanup controls cover object kind 2 with all/nonexistent optional pointers, kind 3, another kind, and arbitrary `d0=0x1234` returns from modeled services for kinds 2 and 3. The latter are register injections, **not an assertion that these services have an error-return ABI**.

- Kind 2 calls nonzero object offsets **12, 24, 16, 20**, in that order, through `0x6076681c`, `0x60766988`, `0x6076692a`, `0x607668d4`.
- Kind 3 calls offset 20 through `0x607668d4`.
- Other kinds and null optional pointers skip the optional calls.
- All tested paths invoke `0x604023b2`, clear `d0`, and return zero.

The outer processing wrappers are byte-checked inputs, but this experiment does not execute the full stop/restart chain. All 13 controls pass.

## Consequence for OpenGate

PR #12 showed that the bounded source-return path identifies a source by address, not generation. A real drain must therefore prevent old queued returns from arriving after address reuse. The acknowledgement success code and cleanup return code alone do not prove that invariant.

Next steps are to resolve the actual command worker/dispatch for operations 5 and 6, establish the allocator guarantee and trace the underlying cleanup services, then join producer admission, outstanding ownership, queue completion and restart in one native ordering experiment. Do not substitute assumed successful services for this missing proof.

This research neither enables nor validates 1920×1440 at 60 fps, sensor readout, ISP/encoder capacity or recovery on physical hardware. The frozen ART candidate and OEM images remain unchanged.

## Reproduce

```sh
python scripts/epl9_completion_barrier_probe.py \
  --main /private/build-1101-main.bin \
  --out /tmp/completion-barriers.json
```

Requires the existing virtual-updater native reader/subset and video-audit dependencies. Use a fresh output path. OEM firmware is intentionally not included. Scalar traces and declared model events: `docs/evidence/completion-barriers-20261113.json`.
