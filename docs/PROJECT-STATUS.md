# Project status and development map

Snapshot checked on **12 November 2026**. This page separates published code, software experiments and physical-camera evidence. Historical reports retain their original claims and dates; they are not current release instructions.

## First milestone: frozen ART candidate

The first candidate changes the two Watercolor ART slots toward Gold 200 and Portra 400-inspired looks, plus their badges. It does not include the later SD/Delete/31-recipe work, OpenGate or gyro logging. It is deliberately frozen until hardware evaluation provides evidence for the next decision.

- Source base: [`feat/native-source-v1-package`](https://github.com/RemeraLl1/epl9-lab/tree/feat/native-source-v1-package), `b0f9ebb`.
- [Candidate report](https://github.com/RemeraLl1/epl9-lab/blob/feat/native-source-v1-package/docs/epl9-native-source-v1-package.md).
- Candidate SHA-256: `10ac83e9beb9dd1bfd12aa6a021135706875d6ea245e58e20ec07fb917229421`.
- Stock main/OSD return SHA-256: `10a7b949d1509ce627cb3c098c0a01a8ae5758fb2ce84b6c887e34b46e349387`.
- Each output is 52,428,800 bytes. This is not a full camera dump or a backup of settings/calibration.
- Original input, not included: E-PL9 build 1101, 104,552,480 bytes; see [Start here](START-HERE.md).

Real-camera installation, photographic output, video support and independent early-boot recovery remain unverified. The menu text still says Watercolor I/II. A UI badge or accepted checksum does not establish a working recipe.

## Published workstreams

All PRs below were **open drafts, not merged**, at this snapshot. Follow the PR for later updates. `main` is the public navigation/historical research branch; do not assume it contains every branch's runtime.

| PR / branch | Purpose and evidence | Next step / boundary |
| --- | --- | --- |
| [#8](https://github.com/RemeraLl1/epl9-lab/pull/8) · `develop/volunteer-builder-20261112` · `51f6dd0` | Clean public source + exact stock reproduce both frozen files; 12 focused tests including full-size reproduction | Windows run and lawful stock-acquisition UX need work; no flashing qualification |
| [#5](https://github.com/RemeraLl1/epl9-lab/pull/5) · `research/virtual-updater-ui-20261112` · `00fb66c` | Native instruction subsets, persistent logical flash and readback; 13 modeled scenarios; separate UI launch from reread components, 164 frames; all 41 restored UI frames match stock | Not NAND hardware, reset-to-boot, sensor/ISP or physical recovery |
| [#4](https://github.com/RemeraLl1/epl9-lab/pull/4) · `develop/recipe-banks-20261112` · `60ba16e` | Host-side bank up to 31 recipes and built-in ↔ SD Delete switch contract; 13 tests | Native loader, complete recipe parameters and mapping to ART slots still required |
| [#6](https://github.com/RemeraLl1/epl9-lab/pull/6) · `e1e1774` | Caduceus atlas comparison and E-PL9 research plan | A documentary map, not newly proven cross-model addresses |
| [#7](https://github.com/RemeraLl1/epl9-lab/pull/7) · `research/opengate-parameter-model-20261112` · `ac5ddb9` | 30 parameter cases using selected native fragments; geometry, rate, budget, buffer and MOV-parameter checks | No sensor, codec, recorded frames or demonstrated OpenGate camera mode |

PRs #4, #5, #6 and #8 target `feat/native-source-v1-package`; #7 is stacked on #5's branch. Review dependencies before rebasing. These are not five independent ready-to-merge releases.

### Validation details

- Builder #8: Linux/Python 3.12.14 clean rebuild matched exact frozen hashes; 12 focused tests passed. Legacy discovery counted 391 tests, two missing-prerequisite errors and 16 skips. Not a complete suite pass.
- Emulator publication #5: 79 scoped tests passed. Aggregate discovery counted 473 tests, two missing-prerequisite errors and 15 skips. No GitHub CI status/check runs were present for the audited commits.
- UI and updater validation are two connected but distinct models. Persisted main/OSD are loaded through the UI harness; a real hardware reset sequence is not emulated. Native instruction tests use specified synthetic state and modeled device operations.
- Fault tests exposed cases where the native updater's final return code can indicate success despite a modeled write/readback error. Independent verification checks actual stored bytes instead of trusting that return code.

## Other ongoing research

### ART recipes in video

Stock E-PL9 supports ART effects in movies, with mode/frame-rate restrictions. This does not establish that our changed WB, colour and tone hooks execute in the saved movie path. Conditional native replay found request types rejected by the recipe gates, but ordinary recording has not been connected conclusively to those states. The next task is to trace recording start through processing to the encoder and then compare saved video. Do not advertise Gold/Portra video support yet.

### Recipe library, SD and Delete

The creative V6 catalogue has 31 named entries, including later Neon City/Astra work. It is not 31 camera-ready native recipes. Some renderer/recipe inputs remain outside the public tree; request provenance before recreating or substituting them. The host model defines safe set switching, not a working physical SD loader or button patch. Playback Delete must keep its normal meaning. Future branches must not silently alter the frozen two-look candidate.

### OpenGate and gyro

OpenGate parameter fragments accept 1920×1440 and the supplied rate, but the 60 fps calculation exceeds the examined internal budgets. Six modeled enlarged buffers can be allocated; that alone says nothing about actual throughput, full field of view or encoder operation. This is a feasibility experiment, not a hard hardware limit or a working recording mode.

Gyro research has identified channel reads in the stabilizer controller, not a calibrated, timestamped synchronous XYZ log. Timer, axis scale, sample timing, exposure association and IBIS motion remain open. A debug CSV is not yet a usable Gyroflow logger.

Wi-Fi transfer, remote-view/control, log curves, sensor capabilities and limited menu improvements remain research topics. Do not inherit advertised E-P7/OM-3 features as E-PL9 features.

## Integration order

1. Keep this documentation index current and link to the exact active branches.
2. Review the frozen ART source base before considering runtime integration into `main`.
3. Review the reproducible builder independently; it must continue producing the frozen hashes.
4. Integrate emulator source and then its dependent OpenGate experiment only after dependency checks.
5. Keep SD/Delete/new recipes in separate feature work until their native paths and ownership/lifetime behaviour are understood.
6. Treat physical installation/recovery qualification as a distinct hardware milestone. Do not infer it from a software merge or build success.

This documentation update does not merge those runtime branches or change the firmware. Contributors can use each branch now; [Contributing](../CONTRIBUTING.md) explains how to avoid repeating work or overstating a result.
