# E-PL9 Watercolor worklist and native color routing

Historical static-routing report. Read [current status](project-status.md), [integration follow-ups](epl9-integrated-prototype.md) and [the real-RAW boundary](epl9-real-raw-boundary.md) before implementing its proposed prototype. Later scheduling experiments preserve the original mode through routing and distinguish separate desktop renders from native camera processing; the proposal below is not the latest executable hook or an approved patch.

## Outcome and scope

The exact E-PL9 main contains a shared worklist branch for the two candidate Watercolor keys. The branch can schedule three processing stages, `0x0600`, `0x0601`, `0x0602`, with intermediate buffers. Separately, an ordinary development request reaches the native COLOR selector. A late request uses a different selector which does not recognize COLOR key `11`.

This locates a plausible replacement boundary **before the Watercolor worklist is built**, followed by ordinary development with recipe-specific parameters. It does not establish a working patch. All observations here are static decoding/table inspection, not execution on the camera or pixel-accurate emulation.

The owner now accepts replacing both Watercolor variants: I with a Gold 200-inspired look, II with a Portra 400-inspired look. Other modes must be preserved. The common routing can be investigated once; recipe identity must remain separate.

## Input identity

- Model: Olympus E-PL9, owner-reported body version `1.1`; downloaded main build `1101`.
- Stock container: `OLY_E_133_1101_0000_0000.BIN`, `104552480` bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.
- Decoded main: `26214336` bytes, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
- Candidate runtime base `0x60400020`; file offset = address minus this base. All code addresses below use this mapping, not a camera memory measurement.
- Watercolor key names remain inferred from the pinned E-P7 reference in [the target document](watercolor-gold200.md). The E-PL9 keys and code paths are locally verified; menu selection → key has not been measured on this body.

The owner's installed firmware has not been dumped or proven byte-identical to this input. Raw firmware, listings and audit reports remain ignored under `local/` or `firmware/`.

## Mode identity has more than one representation

Constructor `0x6074df04` requests a `14552`-byte job allocation. It copies eight words of input parameters into `job+4`. At `0x6074e040..0x6074e05a`, it assembles a composite key from `job+12` and stores it at `job+10384`.

| Field | E-PL9 observation |
| --- | --- |
| `job+12..15` | Four mode bytes: group, variant, little-endian 16-bit ID |
| I candidate bytes | `01 01 78 00` → `0x01010078` |
| II candidate bytes | `01 02 78 00` → `0x01020078` |
| COLOR bytes | `00 00 0b 00` → `11` |
| `job+16` | Flags subsequently consulted by worklist construction |
| `job+20` | Type/format word consulted by Watercolor branch |
| `job+25` | Additional branch selector; value `2` chooses a different worklist arrangement |
| `job+10060` | Worklist start; entries advance by 12 bytes in the decoded code |
| `job+10384` | Cached composite mode key |
| `job+10440` | Request workspace used by the examined constructors |

Helper `0x6074f225` copies the mode bytes from `job+12` to `request+8`, sets the stage at `request+12` to zero, and copies `job+20` to `request+14`. The native COLOR selector later reconstructs the key from `request+8`; it does not read the cached job key.

Consequently, rewriting only `job+10384` would leave downstream selectors with the original ART identity. Rewriting the mode header after the cache was computed has the opposite inconsistency. A future hook needs a consistent **effective processing mode**, while retaining the original I/II choice for the recipe and user-facing state.

These E-PL9 offsets are not the E-P7 job offsets reported by external projects.

## The common Watercolor branch

Worklist builder `0x607519b8` has early conditions, a 16-entry special-path table and a 32-entry ART table. The two tables subtract `0x01010067` from the key, mask the result with `15` or `31`, then linearly probe 8-byte key/target entries with wraparound. Zero is an absent-key sentinel. The guarded range is `0x01010068..0x0102007b`.

Neither Watercolor key is present in the special-path table at `0x608f23c0`. In the ART table at `0x608f22c0`:

| Candidate mode | Stored normalized key | Row address / file offset | Target |
| --- | --- | --- | --- |
| Watercolor I | `0x11` | `0x608f2350` / `0x4f2330` | `0x607521db` |
| Watercolor II | `0x10011` | `0x608f2358` / `0x4f2338` | `0x607521db` |

Both lookups initially hash to slot 17; I is in slot 18 and II in slot 19. Only these two entries in this table target `0x607521db`; this is not a whole-program exclusivity claim. Looking only for literal full keys misses these normalized entries. Key `11` is outside this dispatch range and takes its default branch **when this lookup is reached**. Earlier optimized paths and later effect flags are still relevant.

At the common Watercolor branch:

- If `(job_type & 0x0f00) == 0x0100` or `(job_type & 0x00f0) == 0x0040`, append ordinary development entry `0x60751319`.
- Otherwise append `0x60754834`, then `0x60754944`.
- With `job+25 == 2`, append `0x60754a4b`, followed through the common continuation by `0x607511db` and `0x607518d3`.
- Otherwise append `0x60754ba6` and retain `0x60754a4b` as a pending function for later worklist logic.

The default branch at `0x607523a5` uses `0x60751319` when `job+25 != 2`, or the `0x607518c5`, `0x607511db`, `0x607518d3` sequence otherwise. Subsequent flags can append or change processing entries. These branches have **not** been labeled “live view” and “JPEG capture”: caller/context evidence is still needed for that mapping.

## Distinguishing the Watercolor passes

| Entry / callback | Observed construction |
| --- | --- |
| `0x60754834` / `0x60754c17` | Intermediate buffer ID `0x1040`, format `0x0304`; callback writes stage `0x0600` |
| `0x60754944` / `0x60754c24` | Intermediate buffer ID `0x1041`, format `0x0302`; callback writes stage `0x0601` |
| `0x60754a4b` | Looks up both intermediate buffers; writes stage `0x0602` |
| `0x60754ba6` / `0x60754c31` | Alternate submission; callback sets stage `0x0602` and attaches a buffer when request kind is `3` |

The first two entries call `0x60761b6a`. It constructs a request through `0x6074f931 → 0x6074f250` and then invokes the callback. This constructor clears `1876` bytes and writes request kind `0` at `request+16`.

The third entry uses `0x6074f961 → 0x6074f873`, which clears `708` bytes and writes request kind `3`. This is a different request layout. It is unsafe to treat a late kind-3 request as if it contained kind-0 COLOR fields at offsets above 1800. The intermediate formats' exact pixel semantics and buffer cleanup have not been established.

## Where the color recipe could enter

Dispatcher `0x60799eb6` selects by request kind and input-format family:

- Kinds `0` and `16`, input-format high byte `1` or `2`, reach wrappers `0x6079fef0` / `0x6079ff23`, then common pipeline `0x6079fb88`. Its ordinary path calls COLOR selector `0x6079ebcc`.
- Kind `3`, input family `3` (except `0x0304`) or `4`, reaches `0x6079fc39` through `0x6079ff4d` / `0x6079ffbf`. This path calls the late selector `0x6079ecbf`.
- Kind `3` with format `0x0304` follows another wrapper which calls the color-disable helper `0x6079ebc1`.

The late selector recognizes only keys `0x0101006c` with stage `0x0201` and `0x0101007c` with stage `0x0b02`; otherwise it disables this color block. Therefore changing the final Watercolor pass's mode key to `11` alone does **not** enable the native COLOR consumer.

The ordinary selector provides two candidate mechanisms:

| Mechanism | Exact code observations | Remaining issue |
| --- | --- | --- |
| Key `11`, stock table + twelve per-request values | At `0x6079ec3b`, key `11` selects stock table `0x608ee360`, values at `request+1813`, builder `0x6079e9e2` | Numerical interpretation/ranges and complete recipe controls need execution validation; changing to key `11` must be consistent across the job and request |
| Per-request full table | `job+12320` is copied to `request+1524`; when nonzero and `context+60` contains bit `0x10000000`, selector loads table pointer from that object's `+16`, reads table trailer `+3024`, and calls `0x6079e50e` | The object contract, flag setup and lifetime are not yet traced; a nonzero pointer alone is insufficient |

The request constructor copies 12 bytes from `job+36+4764` (`job+4800`) into `request+1813..1824`. This locates the parameter transfer; the values currently present when Watercolor is selected have not been captured.

The full-table builder iterates two groups of six 28-byte source records, packs them into configuration records beginning at `config+688` with 24-byte stride, writes the trailer-derived control at `config+976`, and installs LUT pointers at offsets in `config+3124..3160`. The table buffer must outlive consumption of those pointers. This is a stronger candidate for separate Gold/Portra tables than globally overwriting the shared stock table, but not a validated attachment method.

Other processing stages (tone, matrix, detail and flags) also depend on the effective mode. Removing the three Watercolor stages alone is not proof that every Watercolor-specific color/detail choice has been removed.

## Proposed offline prototype boundary

1. Capture the original I/II key before any effective-mode change and map it to a separate recipe ID. Match the complete key, not only low ID `0x78`.
2. Before worklist formation, make the effective mode header and cached key agree with a validated ordinary development route. Verify early paths and inherited flags; do not just delete intermediate-buffer callbacks.
3. At ordinary request construction, attach a neutral test recipe through a fully specified native color mechanism. Establish the twelve-value encoding or the full-table object/flag/lifetime contract before injecting parameters.
4. Execute the isolated constructors/selectors in an offline harness, comparing complete worklists and output configuration for both targets and unaffected control modes. Preserve request sizes, completion and buffer ownership.
5. Only after a neutral route preserves detail, tune independent Gold 200 and Portra 400 recipes against original RAW/JPEG and reference renderings. Independently establish preview and capture callers.

This is the next implementation experiment, not a set of approved binary patch offsets. No stub, modified firmware, on-camera command or installation procedure was produced in this investigation.

Follow-up: the [first bounded offline prototype](epl9-offline-prototype.md) now executes selected decoded sections with synthetic state. It passes component checks but exposes four already-ordinary cases whose worklist changes under key substitution. This supersedes the no-execution status only for the explicitly tested sections; a native hook and integrated processing remain unvalidated.

The subsequent [service-dependency audit](epl9-service-dependencies.md) identifies pending-request completion, owner notification 31 and balanced parameter-object references. It calls for retaining the compatible short schedules rather than applying key-11 substitution indiscriminately. [Icon extraction](epl9-watercolor-icons.md) separately identifies existing I/II artwork and UI values; the conversion between UI values and processing keys remains untraced.

The [revised prototype](epl9-integrated-prototype.md) now intervenes only at the actual Watercolor-pass branch, retains the earlier optimized paths, and hands off a consistent header/cache afterward. This supersedes the blanket pre-worklist rewrite as an experiment design. Full worklist execution passes for the documented synthetic states, but full job construction/execution and actual image output remain incomplete.

## Reproduction and validation

Build the [GNU-based reader](mn103-tooling.md), then:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_art_routing_probe.py -v
.\.venv\Scripts\python.exe scripts/epl9_art_routing_probe.py --out local/new-art-routing-audit
```

The new probe verifies exact input size/hash, decodes 11 windows, checks 43 instruction anchors, reproduces both normalized table lookups, and checks which keys in the ART table share the Watercolor branch. Output must be a new ignored `local/` directory. Five synthetic tests exercise header byte order, type-I/type-II hash collisions, wraparound, absent keys, invalid/full tables and wrong-image rejection before output or reader invocation.

The 2026-11-02 run passed all five tests and all 43 instruction anchors; both Watercolor lookups resolved to `0x607521db`. Reports/listings are locally stored under `local/art-routing-audit-20261102-v2/`. The original container and decoded-main SHA-256 values remained unchanged after analysis. These checks validate the inspection tooling and selected static observations, not firmware execution, color fidelity or hardware reachability. GNU custom-op names such as `udf00`/`udfu01` are not emulated by this probe.
