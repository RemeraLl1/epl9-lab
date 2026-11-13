# Movie release admission follow-up (2026-11-13)

This extends PR19's movie command20 -> `606fbf10` -> `6071949e` binding. **Not a camera safety qualification or a completed OpenGate mode.** Frozen firmware is unchanged.

## What the next layer actually does

Static stock-code trace, pinned to decoded-main SHA256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`:

* `607c601c` invokes `607c62b1` with flags zero. `607c62b1` selects one of two pools from current mode and calls `607c3f5b` (or `607c3fcb` for flag16). The flag16 path first resolves an index, then reaches the same address-based routine.
* `607c67d6` selects a class from the 8-byte ROM rows at `60908ce4` and calls `607c69ed`. Ordinary classes also reach `607c3f5b`; classes23/24 are special redirects. This is allocator bookkeeping, not in itself an encoder-drain acknowledgement.
* `607c3f5b` acquires the pool lock, then calls `607c4504`. The lookup walks the linked records and compares **record+24** with the supplied address. It does not compare record+28 in this bounded path. Its helper `607c461c` is a constant-zero validation stub.
* A sentinel or inactive record gives local status3. A matching active record invokes `607c441a`, which clears **record+32 before entering** `607c4620` and its external call at `4700111e`. No completion was fabricated for that call. Subsequent coalescing, free-count accounting, allocator calls, unlock and upstream quiescence remain unexecuted in this probe.

## Native checks

Six focused controls passed: active match, same match with a changed unrelated record field, inactive match, missing address, empty list, and nonzero status2. Native lookup and release admission executed without substituted function calls. Three admitted cases stopped at the real external-call boundary; the other cases stopped before unlock. Entry is deliberately **after** lock acquisition, with a synthetic linked pool. This does not model real locks, DMA, IRQ scheduling or physical lifecycle.

The changed-field control demonstrates only what this lookup reads, not a camera stale-callback bug or a proven generation-token format. Upstream barriers could still prevent reuse. Conversely, PR19's command20 completion must not be presented as proof that encoder callbacks have drained.

## Reproduce

Use `scripts/mn103_subset.py` and `scripts/mn103_calls.py` from PR16 (or its descendants), the qualified GNU reader, and your private exact decoded stock main:

```sh
PYTHONPATH=scripts python scripts/epl9_movie_release_admission_probe.py \
  --main /private/main.bin --reader /path/to/mn103-reader --out result.json
```

No OEM input, disassembly, firmware bytes or personal media are distributed. The public result contains addresses/scalars only.

## Next blocker

Identify/execute the `4700111e` software service and subsequent coalescing under a justified allocator/lock contract, then join the release route to encoder stop/queue quiescence. Until that join is established, no full drain, safe reuse, working 1920x1440/60 video, or install readiness is claimed.
