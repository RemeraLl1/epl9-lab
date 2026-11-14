# E-PL9 read-dispatch return semantics, 2026-11-14

## Outcome

This pass adds focused native controls of the storage mode dispatcher: several modes return zero without reaching a data reader. The maintenance threshold is independently reproduced, not newly discovered. The more extensive prior analysis is in [diagnostic init/read maintenance](epl9-diagnostic-init-read-maintenance.md); the existing bounded-reader prototype is described in [bounded component read](epl9-bounded-component-read.md). Those earlier results remain authoritative and their scripts are unchanged. No camera was accessed.

The original ART candidate and stock-return packages are unchanged. Independent reset-to-recovery is still unproven; `install_ready=false`.

## Exact evidence

Main SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, base `0x60400020`.

1. Previously studied section loading calls `6043ae0d` with operation `0x101`. The `0x100` operation-class branch calls `604a0f03` at `6043aea7`.
2. Mode `0x101` is translated to subtype 1 and `0x103` to subtype 4 by `604a0f03`, both calling `60439e72`, which calls `604014c6`. The latter takes length in d1, source in a0 and destination in a1. These describe the inner ABI, not the reversed a0/a1 convention at the outer wrapper.
3. The lower read worker `604009bf` reads register `98d01194`, retains its low nibble at stack +16, then compares it with 13 at `60400abd`. Values 14 and 15 call `604007b0` with a block-like index shifted right by 6. Values 0 through 13 skip it. We have not established the hardware meaning or frequency of those status values.
4. `604007b0` changes entries in tables at `a03ffe80` and `a03fdf80`; it then calls `60400c60`, `60401066` and `60400e55`, and updates regions addressed as `47ec0000`, `47ee0000`, `47f0000`. These are observed logical arguments, not a verified physical NAND map.
5. `60401066` uses a 128 KiB stride and storage-controller writes; `60400e55` uses a 2 KiB stride with command `0x01402101` versus the read worker's `0x01402001`. Together with the table handling these are consistent with remap/copy/erase/program maintenance. The exact physical operation semantics are not proven in this pass. Calling this whole path harmless/read-only is not justified.

A second trap for a future reader: native modes `0x104`, `0x105`, `0x106` call a diagnostic and return zero without reaching the lower reader. Mode `0x102` with the tested unrecognized a0 returns zero too. Therefore zero return status alone is not evidence that bytes were acquired. Unknown `0x107` returns `0x3109` in the tested dispatcher.

## Verification

`scripts/epl9_read_dispatch_probe.py` executes **7 native dispatch controls** and **16 native maintenance-gate controls** using the existing bounded MN103 engine. All passed. It also checks **13 static call/instruction anchors** against exact-main bytes. The reader binary hash and script hash are recorded in `result.json`.

Only diagnostic calls are explicitly modeled. Real storage and maintenance calls stop at their boundary; no fake storage success or synthetic image bytes are returned. Registers and stack are declared synthetic fixtures. Native snippet reachability does not establish complete scheduler, hardware, reset or physical recovery behavior.

```sh
python scripts/epl9_read_dispatch_probe.py --main PRIVATE_EXACT_MAIN --reader PINNED_MN103_READER \
  --engine-dir PATH_TO_EPL9_LAB_SCRIPTS --out result.json
```

## Next useful step

Continue qualifying a distinct acquisition path below or around the maintenance wrapper, with complete source-address mapping, explicit bounded buffer ownership, cancellation and completion semantics. Do not simply remove this branch on the camera: the underlying condition may be protecting data integrity. First-stage CPU bytes and logical NAND bytes remain different inputs, so even a successful ordinary storage dump would not prove that the external `0x4700` reset code was recovered.

No camera invocation, firmware change, binary publication or installation was performed.
