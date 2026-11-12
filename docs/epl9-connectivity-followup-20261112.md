# E-PL9 connectivity and effects: next usable experiment

Date: 2026-11-12. No camera or phone was contacted, and no firmware changed.

## New deliverable: offline geotag record auditor

`scripts/epl9_geotag_audit.py` turns explicitly recorded experiment metadata into a report. It is **not** an Android collector, BLE protocol implementation, or proof that the E-PL9 emits a shutter notification. It does not request location, connect to devices, or write EXIF. Only synthetic records have been tested.

Run with Python 3.10+ (standard library only):

```sh
python scripts/epl9_geotag_audit.py private-run.json
python -m unittest discover -s scripts -p test_epl9_geotag_audit.py -v
```

Minimal schema (all identifiers and values below are synthetic):

```json
{
  "schema": 1,
  "units": "elapsed_realtime_ms",
  "ground_truth_shots": ["s1", "s2"],
  "events": [{"boot": "b1", "event_id": "e1", "received_ms": 1000, "shot_id": "s1"}],
  "requests": [{"boot": "b1", "event_id": "e1", "request_id": "r1", "start_ms": 1010,
                "end_ms": 1500, "status": "fix", "fix_boot": "b1", "fix_ms": 1400,
                "accuracy_m": 10}]
}
```

- Use Android elapsed-real-time timestamps converted to milliseconds, not wall-clock time. `boot` is a test-local identifier for one phone boot, not a device serial. A process restart does not restart the device clock; a device reboot does. Keep the same boot identity across process restarts and a new one after reboot.
- `event_id` represents one explicitly deduplicated received event. Notification retransmissions must be resolved by the collector; this tool rejects duplicated identities rather than guessing.
- `request_id` is globally unique within the input. Multiple attempts may refer to one event; they count as requests, while event coverage is deduplicated.
- `status` is one of `fix`, `null`, `timeout`, `error`, `cancelled`, `interrupted`. Every issued request needs a terminal record, including interruption before callback. On non-fix outcomes omit fix fields. A log that omitted failed requests biases its denominator; the auditor cannot recover missing log rows.
- `fix_ms` is the location's own elapsed timestamp, not callback time. `fix_boot` must match the receiving boot. Future location timestamps, invalid numbers, bad ordering and unknown events fail closed.
- `ground_truth_shots` is optional, but must be an independent list of actual shots before calculating coverage. The collector/reviewer must establish each `shot_id` association. Neither EXIF seconds nor nearest timestamp is an automatic identity join. Without ground truth all shot-loss fields are null, **not zero**. A list containing only received events is not independent ground truth.
- No coordinates, MAC address, image filename or image bytes are necessary. Keep raw logs private; review before publication.

The default experiment thresholds are callback fix age <= 2000 ms and accuracy <= 25 m; they are configurable and **not a guarantee of position at shutter time**. The auditor reports fix time minus BLE receipt time separately. A location acquired after the event may be recent at callback but describe where the person moved afterwards. BLE receipt is also later than the shutter by an unknown amount. Eligibility by these thresholds is not photographic geotag correctness.

Outputs distinguish null fraction per request, independent terminal failure categories, callback latency, stale/inaccurate fixes, received events without requests, and independently associated shots without usable fixes. Empty logs and unknown ground truth do not produce fabricated zero-loss claims. Battery savings are not estimated.

### What a future hardware run must establish first

1. Identify a real E-PL9 BLE characteristic/event correlated with independently counted shutter releases, not Wi-Fi wake, generic state change or a phone command echo.
2. Establish notification identity, shot mapping and subscription state. Reconnect must re-establish readiness; pairing alone is not a live subscription.
3. Collect a small foreground baseline, then separately test screen-off, process death and reconnect. Force stop is not equivalent to ordinary process death.
4. Compare GPS-on-demand and ordinary tracking in separate matched runs. Continuous tracking changes the location cache, so running it concurrently contaminates the on-demand experiment. Measure battery and missing-shot rates independently.

Sources checked for this pass: [Android BLE background guidance](https://developer.android.com/develop/connectivity/bluetooth/ble/background), [CurrentLocationRequest](https://developers.google.com/android/reference/com/google/android/gms/location/CurrentLocationRequest). Android background constraints and cached/null location results remain relevant. They do not identify E-PL9 protocol UUIDs or prove a shutter event exists.

## Wi-Fi / Luma / Log: preserve the evidence boundary

The repository's [stock measurements](https://github.com/RemeraLl1/epl9-lab/blob/feat/native-source-v1-package/docs/epl9-wifi-live-20261102.md) measured approximately 1.9 MB/s, including 16 KiB boundary pauses. Parallel downloads and larger client read buffers did not show a substantial general improvement. Do not advertise a new throughput gain without another actual transfer measurement.

The [offline prototype](https://github.com/RemeraLl1/epl9-lab/blob/feat/native-source-v1-package/docs/epl9-wifi-offline-prototype.md) has two unresolved native contracts worth studying next:

- `rd` direct-sector read assumes a successful one-sector completion really returned that sector. A zero-sector successful fixture can propagate stale scratch bytes; this is a model counterexample, not observed camera corruption. Trace the lower storage completion before making it an optimization patch.
- Persistent ISC queue reuse cannot distinguish successive identical requests from a delayed duplicate raw reply by its host-only ticket. Establish exactly-once/drain/cancellation semantics before translating it to firmware.

These are better next targets than changing a 16 KiB constant. No speed patch was created in this pass. Previously reported Luma source improvements and Log LUT/cache experiments are not new APK/device/recorded-video results here. Their separate-source artifacts were not rebuilt by this pass.

## Grain / effects

[Caduceus v0.31c](https://github.com/cakelesscoder/caduceus-ep7/releases/tag/v0.31c) disables Grain, Glow/Clarity, Art and Halo in Movie/AP. Treat its still-photo implementation as a reference, not a video-ready effect engine or E-PL9 port. E-PL9 Grainy Film ART and PEN-F/E-P7 MONO grain are distinct paths.

Before integrating effects on our camera, identify the actual frame layout/stride, completion ownership and cache lifetime, then test bounded processing time in a separate candidate. A CPU image loop that preserves chroma in a desktop fixture does not establish a camera-safe pixel hook. No new grain address, pixel output or hardware runtime is claimed here. Frozen Gold/Portra remains unchanged.

## Validation

Twelve offline unit tests cover valid records, unknown ground truth, empty logs, missing requests, cached stale fixes, inaccurate fixes, request retries, null denominator, duplicate identities, cross-boot clocks, future/NaN timestamps and terminal failure separation. All passed in this environment. There is no physical BLE/GPS, camera, battery, Android lifecycle or recorded-image validation.
