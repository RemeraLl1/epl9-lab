# E-PL9 v3 integration status — 2026-11-07

**Latest follow-up (November 10):** [bounded component-reader prototype](epl9-bounded-component-read.md).
A separate 877-byte module passes 44 synthetic native controls with bounded
mapping/polls, one page submission and no NAND maintenance. Five host collection
test methods include full candidate/stock main+OSD pairs read twice locally.
Six native capture-ring cases expose the missing destination-capacity check in
that helper. Real ownership/locking, DMA abort, module entry and USB export are
still unqualified; this is not a camera dumper. Both v3 generations stay frozen.

**Previous follow-up:** [diagnostic initialization and read maintenance](epl9-diagnostic-init-read-maintenance.md).
Seventy-five new native controls resolve the mode-zero lens messages, pending
request cleanup and discarded completion errors. Both page and bulk readers
can reach NAND relocation; the direct page reader omits logical remapping and
all three have a tested persistent-error retry path without a bound. Recipes
and both package generations are unchanged. Acquisition remains unqualified.

**Previous follow-up:** [packaged private-COLOR candidate and read service](epl9-v3-private-deployment.md).
The private-COLOR variant now passes load/UI checks and has its own encoded
main+OSD package, native validation and readback references. Recipes v3 and the
stock-return bytes are unchanged. The native read wrapper also masks leaf
errors; diagnostic open reaches TAKE_FUNC/TAKE_FUNC_CP initialization, whose
full effects remain unqualified. No physical installation or return is verified.

**Previous follow-up:** [private COLOR parameters and logical readback](epl9-v3-private-color-readback.md).
An opt-in decoded main removes the film hook's temporary changes from the
shared caller request; 24 nested COLOR checks pass with unchanged v3 tables.
It has a new main hash and a scoped primary-task stack figure of 4816 bytes.
The frozen packages below do not yet contain it. Whole-job exclusivity and a
qualified physical readback/stock-return path remain separate requirements.

**Previous follow-up:** [component verification, synchronization and memory](epl9-v3-readback-sync-memory.md).
The stack prefix is corrected to 480 bytes (2728 including the observed v3 job
peak). Separate-job interleaving passes; same-job overlap remains an exclusion
requirement. The frozen binaries and recipes are unchanged.

**Later November 7:** the owner authorized package construction. The [candidate and stock-restoration pair](epl9-v3-package-validation.md) has now been built and checked, with recipes unchanged. That report supersedes this pass's pending packaging gate and records an additional native multi-component error-masking finding. Physical installation remains unqualified.

## Owner decision and current result

Preserve the pronounced character of Gold 200 v3 and Portra 400 v3, including some extra Gold warmth. Only modest defect correction is requested. Integration of these two slots into the camera is the priority; broad color fitting and the other 29 profiles must not displace it. Freeze v3 for this integration pass. Existing large ART photographs remain stock.

There is now **one consistent offline component candidate** across the native frame, owner/cancellation, load and combined UI checks. It is not yet an encoded, qualified installation package. A complete TruePic pixel cycle cannot be demonstrated by the current software models; real pixels and normal hardware completion are objectives of a later camera test, not an impossible prerequisite imposed on the emulator.

## Pinned identity

Olympus E-PL9, displayed body version **1.1** reported by the owner; downloaded main build **1101**, not a dump of the installed camera.

| Input/component | Bytes | SHA-256 |
| --- | ---: | --- |
| Stock package | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Stock decoded main | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| Stock decoded OSD | 26214336 | `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e` |
| v3 decoded main | 26214336 | `501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686` |
| v3 native module at `604a1300` | 15360; 1646 code bytes | `18f17217c96d0ef7b6cd767f9738825ed9913a0df32435358237304f3f6a73a9` |
| Row-bounded icon OSD | 26214336 | `50141904c211fd16bc4c26b35cd52955f96a9e611ca062d84fe0169eeda21b3b` |

`local/epl9-v3-integration-20261107/manifest.json` pins these components and all evidence reports. Rebuilding for the owner probe reproduces the exact main/module hashes from the frame probe. The load and overlay reports identify that same main. This prevents mixing passing tests from the older diagnostic-color module with the current photographic curves.

The current candidate uses v0 HSL, v2 WB/contrast/H/S/M and the shared v3 gamma remap adapted to the native variant-zero base. Stock matrix and six-axis data are retained. Earlier diagnostic matrix/channel markers are not photographic recipes and are not included. See [the active-gamma report](epl9-workspace-active-gamma.md) for measured Workspace output and the separate native base-table mapping.

## Checks completed with this candidate

- Frame probe: 40 configurations, 24 original-key crosschecks, nine cache transitions, 15 passthrough cases, 275 WB boundaries, 120 routes, 1050 flag cases and 12 connected jobs. Existing native request fields and mode identities are restored; no pixel completion is fabricated.
- Native producer/owner probe: both Watercolor variants through both stock producers (four cases), plus four pre-cancelled jobs and 24 control cases. Events 2/13/21 execute intact native handlers with the constructor-bound context. Recipe application, owner/ISP matrix correspondence, whole-request restoration and cancellation/destructor cleanup pass. Other resource callbacks retain explicit host adapters. Observed peak stack is 2248 bytes from the probe entry, not a worst-case camera-task bound.
- Load probe: all 657408 declared early-load bytes, including the complete placed module, survive the three native planned read chunks. Destination guards and exact bytes match. Known subsequent startup/section intervals do not overlap the module. Physical reads/cache and all runtime writers are not thereby verified.
- Combined UI: current main plus the corrected icon OSD complete the existing 41-frame E133 route. GUI state/actions and diagnostic history match stock. All frames match the icons-only reference; ten differ from stock only within the accepted icon areas. Six resources are observed, while four remain unobserved on this route. Film-processing hook hit counts remain zero in the UI test; native processing evidence comes from the separate probes above.

The current main has five overlay spans: one module and four hooks. The older diagnostic matrix build had six. The comparator now requires an explicitly selected count (legacy default six); a negative check rejects the wrong generation. This does not relax the frame, diagnostic-history or pixel-area checks. Four overlay boundary tests pass; source syntax and Git whitespace checks pass.

Retained runs:

- `local/epl9-native-film-curves-probe-20261107/validation.json`
- `local/epl9-v3-owner-binding-20261107/binding.json`
- `local/epl9-v3-load-20261107/load-sequence.json`
- `local/epl9-v3-combined-overlay-20261107/manifest.json`
- `local/epl9-v3-combined-ui-20261107/comparison.json`

## Next software gate and later camera checks

The next concrete deliverable is an encoded candidate/stock-restoration pair built from these exact components. Before labeling it a camera-test package, verify re-encoding/decoding, all sizes/destinations/build fields/checksums, complete declared-change coverage, native validator behavior and preservation of updater/startup dependencies. Main `0100` and OSD `0101` are the changed components; restoration must cover both. The example-picture component `0102` stays untouched. No encoded update or restore file was created in this pass.

The [existing installation/recovery assessment](epl9-installation-recovery.md) remains separate evidence; it was read, not reopened as a new risk study. A stock restoration design is conditional on reaching the updater and is not an arbitrary-boot-failure recovery guarantee. No camera write or SD preparation occurred.

The remaining runtime uncertainties include same-job concurrent entry/IRQ behavior, physical code-slot lifetime, untested caller states and actual TruePic processing/completion. These must be explicit in the first test's scope. Hardware image output is to be checked on the camera; this document does not demand that an incomplete ISP emulator manufacture it, and does not describe the present offline components as installation-ready.
