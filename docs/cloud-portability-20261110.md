# Source-only cloud portability follow-up, 2026-11-10

This separate development change starts from checkpoint
`3c42b01444bf933056917768de32a2bbf9e892f0`. It does not modify recipes, firmware,
candidate packages, restoration packages or archived evidence seals. No private
backup, camera media or firmware was needed, copied or published for this work.

## Changes

- Build the same unmodified pinned GNU MN103 source subset and project adapter
  with an installed Linux C compiler. Retain the pinned Windows TinyCC path.
- Select `mn103-reader` on Linux and `mn103-reader.exe` on Windows across all 42
  research consumers. Preserve explicit reader overrides and saved-listing-only
  behavior. Report the actual binary SHA rather than the historical Windows SHA.
- Require exact source/adapter identities, build provenance and independent
  opcode/rejection validation for portable binaries. A new executable is never
  accepted just because it is named `mn103-reader` or because JSON claims success.
- Accept uniform LF or CRLF for the two pinned external Python sources only.
  Record raw and canonical LF digests, preserve the old Windows raw SHA values,
  and reject mixed endings, bare CR and every other byte change. Firmware,
  packages, recipe payloads and binaries remain byte-exact. Execute the verified
  source snapshot, not a cached `.pyc`.

The canonical LF source identities are:

- caduceus `tools/osd_extract.py`, commit
  `7d42c1f258737b7196c6b17cec5d643b5080ece6`:
  `c7fe693c1322553758a7f312c8e31009b9f45016702f83c24eaec6cbd2910396`.
- oly_fw_analysis `tools/oly_container.py`, commit
  `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`:
  `ab842e186049074848a24dda432e8a5b85d52390fd22af9d059bf630def9cb6b`.

## Verification scope

The Linux GCC 14.2.0 x86-64 reader passed all 1294 pinned AM33-2 vectors and five
negative controls. The independent firmware-free smoke check decoded all 197
instructions in the 877-byte synthetic-address bounded-reader module, then
passed completion, missing-exclusivity and timeout controls with modeled MMIO.
This establishes decoder/build portability within these scopes, not native
firmware reachability or physical NAND/DMA behavior.

Twelve new source-only tooling guard tests cover host selection, historical
identity retention, missing/stale/altered receipts, compiler/source identities,
changed executables, mandatory fresh validation and source changes during a
build. Seven new source-identity
tests cover the precise LF/CRLF policy and reject altered source bytes.

The final cloud run used Python 3.12.14 and Pillow 13.0.0. The complete discovery
had 323 tests: 311 passed, one missing-private-package error and 11 native-fixture
skips. An explicitly scoped run omitting exactly those 12 private-fixture cases
passed all 311 available tests, with no skips. That scoped result is not a full
firmware regression. All 150 Python sources parsed successfully. Real negative
controls rejected both a changed ELF and a nondecoder paired with a forged
matching binary digest in its receipt.

## Remaining gates

The full unit suite still needs ignored private package and exact-stock
image/listing fixtures. Missing fixtures remain errors/skips, not a full pass.
Frozen v3 curve data, stock firmware and archived candidate/restore components
cannot be recreated from the public source tree alone. The checkpoint's private
restore contract and exact identities remain unchanged.

Some higher-level probes intentionally check source hashes recorded in prior
private reports/seals. Their producer source now has a distinct portability
revision. Those historical source checks were not removed, normalized or
silently resealed: new runs need fresh, separately identified evidence after
the permitted private inputs are restored. Old evidence must remain historical.

No new Windows execution, OM Workspace run, camera/USB/SD operation, full native
firmware regression, installation or restoration test was performed. Passing
the source-only checks does not make either v3 generation installation-ready.
