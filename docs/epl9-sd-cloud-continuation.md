# SD recipe cloud continuation, 2026-11-10

The published checkpoint `cloud-sync/2026-11-10` at
`3c42b01444bf933056917768de32a2bbf9e892f0` contains the two-slot SD loader,
manager-tail state, processing consumer and in-image placement study. This
cloud continuation also uses the existing Linux portability follow-up
`02174ffadb5dc0dfd4b492d00328256f7ddead70`. It does not replace or recreate
the later Windows session-shutdown work.

T1/T2 and processing keys `01030078/01040078` are offline aliases. They have
no confirmed native camera menu entries. Configuration comparisons are not
image output; the documented connected jobs stop at unmapped TruePic
`9880014c`. Physical SD, camera execution and installation remain unverified.

## Available and missing material

The cloud source tree includes:

- [SD processing](epl9-sd-processing-prototype.md),
  [placed modules and lifetime](epl9-sd-placement-lifetime.md), and
  [bounded component reader](epl9-bounded-component-read.md).
- `scripts/epl9_sd_{recipes,loader,state,processing,placement}.py` and their
  native sources and tests. The checkpoint's **44 SD test methods passed**
  on Linux without stock firmware or camera fixtures.
- The independent [Linux MN103 tooling](cloud-portability-20261110.md),
  built here from all six checksum-verified upstream inputs at GNU commit
  `2bc7af1ff7732451b6a7b09462a815c3284f9613`. The build passed **1294 opcode
  vectors and five negative controls**. It has a distinct Linux binary
  identity; the historical Windows binary hash is not reused.

The parent handoff reports a later session-shutdown protocol with 53 local
test methods. **None of its following five source files was present in the
cloud checkout or elsewhere in the attached workspace at the initial check:**

| Expected path | Initial cloud status |
| --- | --- |
| `docs/epl9-sd-session-shutdown.md` | Missing |
| `scripts/epl9_sd_session.py` | Missing |
| `firmware_src/epl9_sd_session.s.in` | Missing |
| `scripts/epl9_sd_session_probe.py` | Missing |
| `scripts/test_epl9_sd_session.py` | Missing |

Its contents, exact revision, evidence identities and claimed 53-test result
have not been independently reviewed or reproduced here. File presence alone
will not establish that its protocol is integrated or qualified. Do not
implement a second protocol under those names to fill this transfer gap.

The attached workspace also lacks the ignored exact-stock main, frozen v3
recipe exports, previous native listings, candidate/restoration packages and
retained full processing/placement reports. They are separate private inputs,
not recoverable from the public Git source alone. The source-only work below
does not synthesize replacements for them. Follow the existing
[private migration contract](cloud-migration-20261110.md) for their authorized
transfer and exact identity checks.

## Independent work that can run now

[The new differential probe](../scripts/epl9_sd_validator_probe.py) compares
the host record codec with the standalone native validator and the validator
relocated into the placed state module at `604a5000`. Both native validators
are independently GNU-decoded, including boundaries, mnemonics, scalar/memory
operands, branch targets and save masks, before execution. The runner uses
synthetic fallback recipes and never reads stock firmware.

The deterministic corpus contains **1158 records**: 109 valid and 1049 invalid.
It includes every one of the 660 single-byte CRC corruptions, all 36 HSL
fields at both legal and illegal bounds, contrast/H/M/S and WB limits, header
and name checks, every gamma index outside its 12-bit range, decreasing curves,
full-width recipe IDs and 16 seeded varied recipes. CRC-resealed malformed
records check semantic validation separately from checksum failure.

Each native execution requires an exact 660-byte read-only input, an explicit
instruction limit, balanced return/stack, preserved callee-saved registers,
unchanged record/guards and no external calls. The runner retains per-record
hashes/results/instruction counts, exact module and source hashes, the actual
qualified decoder provenance, and a fresh inventory of the five transfer
files. Generated binaries, listings and reports stay ignored under `local/`.

The retained cloud run is
`local/epl9-sd-cloud-validator-20261110/validation.json`, SHA-256
`f129d16f4e9a4db7fc5f8fec835adc918e98c5955d0ecd1c9cbafb5dfcce069b`.
All **2316 native executions** agreed with the host and the authored expected
result. Both validators reached at most 64457 instructions per record, below
the explicit 200000 limit. This is an interpreter instruction count, not a
hardware latency measurement. The corpus SHA-256 is
`8d99e6cbc3ce43ed3ae223d0fa13bd6459106bfff6276cf0348985eef4471c08`.
GNU decoded all 327 standalone instructions and all 465 placed-state
instructions. The unchanged standalone module retains SHA-256
`ed4d4e9055d00393ad1eea267bd265abf4261c3a12fd1980cac7ad216f15d357`.
The state module contains synthetic defaults, so its hash is not a claim to
reproduce the earlier firmware-derived placement artifact.

The four added unit methods validate corpus completeness/determinism, the
fixed-size native entry and the relocated validator/fallbacks. Thus this
branch has **48 passing SD unit methods** before the missing shutdown work
is transferred. These are not the handoff's 53 tests.

```sh
python3 -m unittest discover -s scripts -p 'test_epl9_sd_*.py'
python3 scripts/mn103_reader/build_reader.py
python3 scripts/epl9_sd_validator_probe.py \
  --out local/new-sd-validator
```

The reader build requires the six exact upstream files recorded in
`scripts/mn103_reader/upstream.json` under ignored
`references/binutils-2.45-mn103/`, plus an installed C compiler. It does not
download them. The cloud run used the GNU upstream mirror
`https://github.com/RTEMS/sourceware-mirror-binutils-gdb` at the recorded commit;
every file matched its existing size and SHA-256 before build. No upstream
source is added to this repository.

## Route after the missing transfer

1. Transfer the five actual shutdown source files with a source commit or
   checksum manifest, together with the original report and its exact input
   identities. Preserve the original Windows work and retained evidence.
   Review its changes against the checkpoint and Linux portability commit.
2. Restore the authorized minimal private inputs into ignored paths and verify
   stock/candidate/restoration identities. Exact decoded stock main remains
   26214336 bytes, SHA-256
   `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
   Its source package remains 104552480 bytes, SHA-256
   `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
3. Run test discovery and the actual shutdown probe after reviewing its CLI
   and dependencies. Record the observed total; neither 48 nor the historical
   53 should be hard-coded after independent tests have been combined.
4. Rerun the full processing and placement probes with new output paths and
   fresh Linux evidence identities. Review teardown against the existing
   stale-root and destructor-prefix controls. Historical Windows receipts
   remain historical; do not silently reseal changed producer sources.
5. Resolve native menu/label/settings bindings and all lifecycle/SD/cache/DMA
   qualifications separately. No additional stock ART slots are assigned by
   this continuation. The frozen Watercolor v3 candidates, accepted looks and
   recovery investigation remain separate.

The new checks concern the record acceptance boundary. They do not execute
stock file-service tasks, verify the reported shutdown protocol, establish
controller cancellation or qualify hardware timing. No camera command, flash
write, physical card preparation or original firmware publication occurs.
`install_ready`, `physical_sd_tested` and
`full_session_shutdown_qualified` remain false.
