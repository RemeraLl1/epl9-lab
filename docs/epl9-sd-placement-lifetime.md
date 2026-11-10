# E-PL9 T1/T2: in-image placement, loading and session memory

2026-11-10. The separate [SD processing prototype](epl9-sd-processing-prototype.md)
now has a rebuilt offline main with both modules at actual addresses inside
the downloaded E-PL9 1101 image. Native early-load planning brings in both
blocks; the placed code then constructs HLS state, loads/selects recipes and
configures connected processing requests without synthetic module regions.
Missing files retain the embedded recipes.

Normal session retention passes the checks below. **Complete teardown remains
unqualified:** an intentional free/getter control demonstrates that the native
singleton root alone does not prove object ownership. Physical instruction
cache, SD, DMA and camera execution also remain unverified. No installation
package, card preparation or camera operation was performed.

## Chosen addresses and exact identity

| Block | Start | End, exclusive | Bytes / code bytes |
| --- | --- | --- | ---: |
| Loader and manager-tail state | `0x604a5000` | `0x604a6800` | 6144 / 1877 |
| Processing and embedded fallback descriptors | `0x604a8100` | `0x604ac100` | 16384 / 2253 |

Both spans are exact stock `FF` padding, aligned to 256 bytes, inside the
early loaded range `60410000..604b0800`. They are disjoint from each other
and from the frozen v3 module slot `604a1300..604a4f00`. The existing
16-byte zero record at `604a8000..604a8010` is preserved. Placement uses two
padding runs, not a contiguous overwrite across that record.

The new builder reassembles every instruction at its placed address and
rebuilds paths, fallback and descriptor pointers. It checks GNU-decoded
instruction boundaries, targets, masks and operands. Original synthetic
builders, native templates and both preceding module generations remain
unchanged. Their addresses are not supplied as extra regions to the placed
execution fixture.

This main is built from exact stock 1101 with the SD prototype's six hooks.
The fixed Gold/Portra Watercolor v3 candidates remain separate. The new
offline main contains only two declared module spans and those six hook
spans; its length and all other bytes match stock, including the unused
stock bytes in the frozen v3 placement slot.

| Retained output | SHA-256 |
| --- | --- |
| Loader/state module | `58604d799da9c825dcd2fc5ed1caae0b0474c1f190db76dd700449d4934e9944` |
| Processing module | `2507b5aeb42b5df32330cc74173b73cbe18eb0fb3bbd35e0e0ab17cb4312487b` |
| 26214336-byte placed offline main | `b739650eb2d2e0fe1d4dee2699cf684efc03de7b79850edec2daf99ffbbe8b16` |

The main is
`local/epl9-sd-placement-20261110-final/main-SD-PLACED-OFFLINE-ONLY.decoded.bin`.
It is a decoded research artifact, not an installation container or SD update
file. Standalone module binaries, source and GNU listings are in the same
ignored output directory.

## Native loading and preservation scope

Native startup arguments at `60400174..604001cb` request 657408 bytes into
`0xa0410000`, whose cached view is `0x60410000`. Native read planner
`60401561..6040168b` executes the same three chunks as the previous load study:

| Source | Destination | Bytes |
| --- | --- | ---: |
| `0x406f0000` | `0xa0410000` | 65536 |
| `0x40700000` | `0xa0420000` | 524288 |
| `0x40780000` | `0xa04a0000` | 67584 |

The third chunk contains both complete modules. All 657408 bytes match the
candidate; destination guards and both module binaries match exactly. A
negative control deliberately returns success without copying the third
chunk and is rejected. Subsequent execution receives the bytes copied by
these native planned reads, with no separately injected module regions.

Five later startup destinations, two initialization intervals and the nine
known post-entry section intervals do not overlap either module. This is
coverage of the known startup/load paths, not a scan of all possible runtime
stores. HLS_EVENT's native getter/constructor/task adapter are in the later
`60acc800..60efe000` section. The modules belong to the preceding early load;
the tested session executes their initialization only after the early load
has completed. Whole RTOS boot ordering is not executed by this harness.

The seven ROM pool records at `60405f10..60405f80` agree with native
deallocation classifiers. Fourteen positive boundary controls select the
expected IDs. **33792 native word-address checks** reject both modules and
their `a04a...` aliases across all three classifiers. Pool intervals remain
disjoint after address-alias normalization. These checks stop before free,
logging or hardware operations; they do not measure runtime allocator metadata.

There are no raw full-immediate `FC` reference candidates into either stock
padding span or its matching physical alias. The scan compares physical
address bits correctly: a numerical `404a...` value is not treated as the
`a04a...` alias of `604a...`. This limited static scan does not exclude
computed references, other overlays, direct stores or DMA.

## Runtime memory checks

The placed variant keeps the existing design:

- The native HLS singleton requests 288 bytes, initializes the new tail before
  root publication and keeps the original 180-byte object prefix.
- Accepted SD records retain their separate 2048-byte loader blocks.
- HLS prepares two descriptor snapshots using an 8192-byte request from native
  class `10004` (16384-byte pool payload), then publishes manager +212.
- Embedded descriptors remain in the loaded processing module and are usable
  before SD readiness or when no accepted override exists.
- Image hooks read retained data and use private COLOR context/request copies.
  They perform no file I/O or arena allocation during frame configuration.

For both **no files** and **exchanged valid SD files**, the placed modules pass:

- **16 full 5200-byte configuration comparisons**, two slots and four formats,
  against independent parameter arithmetic and unhooked native setters.
- **26 warm-cache/exit/passthrough controls**, including both fixed Watercolor
  keys; **four native WB controls** also exercise the placed entry.
- **12 connected native jobs**, two slots and three kinds in both sessions,
  reaching the same unmapped TruePic register `0x9880014c`. Selected gamma and
  WB reach the request, while job identity is preserved. No pixels or normal
  completion are manufactured.
- **32 temporary allocation/free pairs per session**, alternating 2048- and
  8192-byte requests through the native ordinary size/free classifiers.
  Declared finite backing reuses available blocks while excluding the retained
  manager, file blocks and descriptor arena. Repeated getters/events do not
  reset slot selection or reopen files. Both 4096-byte descriptor snapshots
  remain identical, including all padding, and allocation guards remain intact.

Module and retained pool regions are read-only in the image-configuration and
connected-job tests. Real pool addresses and availability are not measured:
`62267000` (manager) and `61fc0000` (arena) remain finite fixture choices.
The source builds are at real image addresses; these runtime allocations
still require hardware qualification.

## Teardown controls and remaining lifetime gate

The native HLS destructor prefix `60ae1910..60ae1944` executes in a separate
test session. It releases the five original vector buffers, then stops before
calling base cleanup. The new descriptor arena is still allocated at that
boundary. This is deliberately a prefix check, not a completed destructor,
task stop or safe shutdown.

A second negative control deliberately frees the manager through native
ordinary free classification, then calls the native singleton getter. The
getter returns the same pointer from root `6239790c` although the finite pool
now marks that block unowned. No real camera race or normal shutdown is
inferred from this forced misuse. It falsifies the broader claim that a
nonnull singleton pointer is sufficient lifetime protection.

The accepted session checks therefore require keeping the manager, accepted
file blocks and published descriptor arena alive while any consumer can use
them. Safe teardown must establish HLS task quiescence, stop new frame
selection, drain pending processing/file requests and retire retained pointers
before release/reset. That protocol is not implemented or qualified here.
The existing same-job serialization requirement also remains in force.

Physical instruction-cache coherence/executable mapping, all boot/runtime
writers, SD mount/removal timing, power-off/restart behavior and all pool
failure paths remain open. `install_ready` and `full_teardown_qualified` are
false. The known loaded ranges and normal-session checks are useful offline
evidence; they do not establish a hardware-safe installation.

## Inputs, protection and reproduction

Olympus E-PL9 / IM008 / model 1330, displayed body **1.1** reported by the
owner, downloaded main build **1101**. Stock decoded main: **26214336 bytes**,
SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
Source stock package: **104552480 bytes**, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
These are downloaded files, not a dump of the installed camera. GNU reader
SHA-256: `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.

Retained report: `local/epl9-sd-placement-20261110-final/validation.json`.
Twenty protected inputs, including both v3 main/package generations, icon OSD,
stock restoration, recipes and prior SD sources, match their earlier hashes
before and after this run. All **44 SD tests pass**, including four new
synthetic placement controls. Known stock listings are byte-checked again.
Resource, kernel, file-service and finite-float models retain their previous
explicit boundaries; no model shadows native code.

Implementation: [placement builder](../scripts/epl9_sd_placement.py),
[load/lifetime probe](../scripts/epl9_sd_placement_probe.py),
[synthetic tests](../scripts/test_epl9_sd_placement.py).

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_sd_*.py
.\.venv\Scripts\python.exe scripts/epl9_sd_placement_probe.py --out local/new-sd-placement
```

The output must be new and inside ignored `local/`. This probe reuses the
preceding processing run's stock listings and frozen example records, checks
their identities, and freshly decodes the placed modules, hooks, startup/load
and pool windows. No existing candidate, package or recipe is overwritten.
