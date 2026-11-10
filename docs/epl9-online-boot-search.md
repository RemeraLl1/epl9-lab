# E-PL9 / 1330: online BOOT search and hardware evidence

Follow-up: [E-PL9 board images and readout without programming](epl9-board-readout.md)
adds a repair-video layout reference and a native read-to-maintenance write caveat.

## Result — 2026-11-04

**No attributable E-PL9 BOOT image, complete physical flash dump, or downloadable
factory 1.0 package was obtained in this search.** Two real E-PL9 archives were
downloaded and checked. Both contain ordinary model-1330 update containers with
main build **1101**, not a full device backup. Neither has a native BOOT-tagged
component or a checksum-valid nested BOOT envelope of the form searched by our
[source inspector](../scripts/epl9_boot_source_audit.py).

This is a bounded public-source search, not proof that no service image exists.
Public archive contents, firsthand forum reports, our byte measurements, and
proposed hardware qualification are distinguished below. No camera connection,
camera command, SD preparation, body opening, reset or firmware write occurred.

## Identified files and provenance

Target: Olympus PEN **E-PL9**, firmware model **1330**. The official
[instruction manual](https://download.omsystem.com/pages/inst/epl9/manual_epl9_ENU.pdf)
also identifies the regulatory product model as **IM008**. The owner's displayed
body version **1.1** remains owner-reported; none of these downloads is a dump of
that body. Displayed package versions below come from release/forum records.

| Input | Package version / main build | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| xdel `OLY_E_133_1101_0000_0000.BIN.lzma` | 1.1 / 1101, compressed update | 26355496 | `a2ea4f0be65fb4dab434ddcfd4a3f2369da29ae69c7ed9a630e925d957f52b18` |
| Its decompressed `OLY_E_133_1101_0000_0000.BIN` | 1.1 / 1101, model 1330 | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| xdel `pen-e-pl9_v11.rar` | Forum-labeled E-PL9 1.1 modification | 29792358 | `4bd2701ffc6603911e40f0259b52b18af328c252ebb33cfb2f8d7d4b17033b1d` |
| Its sole member `e1339999.bin` | 1.1 / 1101, model 1330 | 104552480 | `131960883affe65e3200489359486ce643fc19cd0272e1dbccd69ff4f9c25f27` |

### Stock: strong identity link to the official update

A fresh request to the official
[OM firmware catalog](https://fw01.om-digitalsolutions.net/ww_inform/fcache.do)
with **placeholder identifiers**, model 1330 and reported installed build
`00001000` offered `OLY_E_133_1101_0000_0000.BIN`, size 104552480, dated
2018/4/26. The official
[E-PL9 changelog](https://dl01.om-digitalsolutions.net/ww/ud2/ENU/0001/1330/index01a.html)
lists 1.1 on that date. Temporary signed download query strings are retained
only in ignored local evidence.

The live
[xdel E-PL9 original directory](http://xdel.ru/downloads/olympus-firmware/original/penepl9/)
lists one file: the LZMA archive above. It was completely downloaded; bounded
decompression reaches EOF without trailing bytes. The resulting **entire file
is byte-for-byte equal** to the previously acquired official stock input, not
merely a matching filename or main segment. This establishes the identity of
this mirror copy. The archive's listed 2022 modification time is not its
firmware release date or proof of when the mirror acquired it.

The current catalog was queried, not asked to install anything. Its installed
version field does not request a historical download. No hypothetical `1000`
or `1001` filename was treated as an obtained factory image.

### Historical modification: traceable publication, incomplete original chain

The live
[xdel patched directory](http://xdel.ru/downloads/olympus-firmware/patched/)
contains `pen-e-pl9_v11.rar`. Its
[credits](http://xdel.ru/downloads/olympus-firmware/credits.txt) attribute the
collection to Olympus and contributors at Mu-43 and Personal-View. Credits are
an attribution claim, not a signed chain of custody for each file.

A directly retrieved primary forum page supplies a more specific link:
[Micro43Club, page 9](https://www.micro43club.pro/forum/threads/modifikacija-proshivki-kamer-olympus.22086/page-9).
ABel's post **#170, 2019-03-23**, publishes an E-PL9 1.1 archive with the same
name, linked to `https://yadi.sk/d/jPmjdIIHHX_K-w`. User edge's post
**#174, 2019-04-01**, reports successful use on E-PL9 and E-M10 III and longer
4K recording. Post #177 is the author's follow-up. These are firsthand claims
about a modification on other bodies, not a recovery test or our measurement.

The original Yandex link now returned HTTP 404. Consequently, **the current
mirror cannot be independently compared to the original 2019 upload**. Its
member hash does match the E-PL9 record in the previously pinned
[inventory at commit 539fcf1fa9eda5fdef8ede4deeab94a4691d94c3](https://github.com/fishcu/oly_fw_analysis/blob/539fcf1fa9eda5fdef8ede4deeab94a4691d94c3/provenance/firmware-inventory.json).
That match is additional identity evidence, not cryptographic author
authentication or a reason to install this modification.

## What the downloaded bytes establish

The existing inspector accepted all five components of both files: model 1330,
bounded lengths, no duplicate kinds, header/trailer agreement and decoded
additive checksums. These checks identify structure and accidental corruption;
they do not authenticate the publisher or qualify physical installation.

| Kind | Header build | Destination | Decoded payload bytes |
| --- | --- | --- | ---: |
| `0100` | `1101` | `406e0000` | 26214336 |
| `0101` | `0100` | `421e0000` | 26214336 |
| `0106` | `0100` | `43ae0000` | 38797248 |
| `010e` | `0001` | `40002800` | 219104 |
| `0102` | `0100` | `468e0000` | 13107136 |

Native BOOT selection tests a kind's **low byte `10`**. None of these kinds
matches; `010e` is not BOOT. Searching all five decoded payloads in each file
found **zero** complete checksum-valid nested `OE` / model-1330 / BOOT envelopes.
This does not exclude bare, compressed or differently wrapped loader code.

Direct stock/mod comparison finds **14 changed decoded main bytes**, in two
spans at analysis addresses `60712c29` (12 bytes) and `609f79cb` (2 bytes), plus
the container checksum change. All bytes after the first complete main
component are equal. Main's full identity is:

- Stock decoded main, 26214336 bytes:
  `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
- Modified decoded main, 26214336 bytes:
  `be527b16e4811e271f88cadae17be6aec25f8dc8a66abf5162ed59b0946385b7`.

The 512 bytes checked at SD-client entry `610039fd` are equal as well; this is
a local byte comparison, not proof of an independent early boot path. Analysis
addresses use main base `60400020`; container destinations use a different
address domain. These update files do not supply the missing pre-main region,
device calibration backup, physical flash geometry or reset ROM.

## Search coverage and actual limits

| Source / route | Observed result | Limit |
| --- | --- | --- |
| Official OM catalog and E-PL9 release history | Current model-1330 offer is 1101; release history identifies the transition 1.0 to 1.1 | A public update listing does not disclose all factory/service assets |
| Live xdel original and patched indexes | One E-PL9 stock 1.1 LZMA and one E-PL9 1.1 RAR modification; both read and identified above | No BOOT/full dump/1.0 is listed in these inspected directories |
| [OFU archive](https://ofu.infinityfreeapp.com/) | Browser selection **PEN → E-PL9** exposes only **1.1 (latest)**, release 2018-04-26 | No earlier E-PL9 option; author says older releases are local copies and latest downloads come from OM. Its general bricked-camera claim is not E-PL9 recovery evidence |
| Micro43Club original modification topic, pages 8 and 9 | Author's archive link and firsthand success report identified | Successful modified main on a working camera does not test damaged-main recovery |
| [Mu-43 modification topic](https://www.mu-43.com/threads/modified-firmware-looking-for-users.99804/) and newer firmware-download topic | Web fetch unavailable; direct request to the modification topic returned HTTP 202 / challenge-sized page | Content behind that response was not inspected or treated as absent |
| [VLab Olympus section](https://vlab.su/viewforum.php?f=168) | Public topic listing read; no E-PL9 BOOT/dump topic identified | No account-only attachments or private archive searched |
| [eServiceInfo Olympus search](https://www.eserviceinfo.com/fulltext.php?search_ft=OLYMPUS) | Public listing retrieved; no matching E-PL9 service/dump item identified | Not a search of every unindexed attachment |
| [Service Manuals Pro Olympus catalog](https://www.service-manuals-pro.com/categories/photography/olympus) | Its displayed catalog does not list E-PL9 | Generic factory/manual marketing is not a file for this model |
| [ServiceManuals.net Olympus catalog](https://www.servicemanuals.net/en/olympus-service-manuals) | Web-visible list of 18 products has no E-PL9; direct fetch was 403 | No paid manual bought; no unlisted inventory assumed |
| Targeted searches for Remont-aud, Monitor.net.ru, Elektrotanya and E-PL9 / EPL9 / 1330 / IM008, BOOT, dump, factory, service, NAND, EEPROM, Russian/English/Japanese/Chinese terms | No retrievable attributable E-PL9 BOOT/full-dump candidate identified | Search results are incomplete; unrelated PL9 components, photo metadata and raw sensor dumps excluded |
| Historical LightSnowDev / Wayback | Live site/archived page could not be fetched by web tool; CDX requests timed out | Historical availability remains open, not a negative archive finding |

The OFU discovery came through the maintainer's
[May 2026 article](https://marcrphoto.wordpress.com/2026/05/11/olympus-om-system-firmware-updates-the-situation-changed-again-may-2026/).
Neither its downloader nor a script's ability to obtain public updates supplies
an E-PL9 BOOT image.

One
[repair-service article](https://rbt33.su/blog/fotoapparatov/remont-olympus/)
mentions E-PL9 in generic firmware-failure text and advertises JTAG/SPI/NAND
repair. It provides no E-PL9 chip marking, pinout, dump hash or documented
damaged-main recovery. Its specific E-PL9 example concerns battery contacts and
a display cable; the programmer-recovery example concerns E-M10. **Do not turn
that page into evidence that this E-PL9 has a particular flash type or recovery
connector.** No E-PL9-specific board/chip evidence sufficient to select a
programmer was established in this search.

## What hardware evidence would answer the recovery question

**Engineering conclusion:** practical recovery confidence needs evidence from
the exact hardware as well as code. A real BOOT/dump could close much of the
static path; an observed independent recovery path would still require hardware
qualification. The three different questions must remain separate:

| Question | Useful evidence | What it still cannot prove |
| --- | --- | --- |
| Where does reset/OK select recovery? | Attributable E-PL9 boot-region bytes and address map; board revision/chip identification; where feasible a read-only reset/storage trace and identified diagnostic output | A passive bus trace alone may show reads, not all executed instructions or internal-ROM behavior |
| Can the owner's exact contents be backed up? | Repeat independent reads with matching hashes; documented chip capacity, region boundaries and logical/physical format; service/calibration regions retained privately | A matching backup does not demonstrate that it can be restored to the device |
| Does recovery work without usable main? | A controlled test on a **separate donor**, with a previously demonstrated independent restore route and precisely defined main fault, followed by verified stock restoration | A hang after ART startup, a black screen, an LED indication or an updater run on healthy main does not cover arbitrary main damage |

Acquisition requirements for a later hardware investigation:

1. Identify an actual **E-PL9 / IM008 / 1330** board revision and its storage
   chips from attributable photographs or service documentation. Confirm
   interface, voltage, capacity and access method before selecting equipment.
   A suggested CH341A, JTAG adapter, UART pad or another model's pinout is not
   an established solution for this board.
2. Obtain the regions missing from the public update, including the relevant
   loader/boot partition, with provenance: source body/board, read method,
   offsets, byte counts, repeated-read agreement and SHA-256. If raw NAND is
   actually identified, document page/spare/ECC/bad-block handling; do not
   assume NAND or SPI from marketing text. An external-flash dump need not
   contain the SoC's internal reset ROM.
3. Map reset, the physical OK input, main loading/checking, recovery selection,
   SD access and the updater's dependencies against those bytes. Resolve
   whether recovery runs before main or loads/executes part of main first.
4. Treat a physical destructive-fault recovery demonstration as separate
   donor-only work in a later explicitly authorized phase. It is **not** a
   prerequisite to collecting public material now and is not authorized here.

The next useful acquisition is therefore an attributable E-PL9 service loader
or a documented donor boot/full dump with board/chip identity. More copies of
the same 1101 update do not answer the missing dependency. **Recovery after
arbitrary damaged main, and readiness for a first installation, remain
unverified.** No probability of safe recovery can be inferred from the number
of successful forum installations.

## Retained evidence and verification

Ignored root: `local/epl9-online-boot-search-20261104/`.

- `artifact-manifest.json`: complete archive/member sizes and hashes, inspector
  identity, retained partial-download exclusion and report paths.
- `vendor-catalog/`: fresh placeholder request, response and sanitized summary.
- `xdel-stock-inspection.json`, `xdel-mod-inspection.json`: full component
  identities, checksum/envelope checks and bounded nested scans.
- `stock-mod-comparison.json`: exact changed spans and component comparisons.
- Saved index/forum/service HTML and probe manifests record successful reads
  and access errors. Browser OFU findings are recorded in the coverage table;
  an HTTP-200 JavaScript challenge is not mistaken for the real catalog.

The interrupted first LZMA request left a 14680064-byte partial file. It is
retained, explicitly excluded from inspection and distinct from the complete
26355496-byte curl download. No incomplete file was renamed as valid firmware.
The LZMA was decoded in memory; the RAR's sole named member was read using the
already installed UnRAR. No downloaded executable or firmware code was run.

All measurements use the existing local-only inspector. No production scripts
were changed by this online search; its eight synthetic guard tests were rerun.
The earlier
[indirect-start and BOOT-source audit](epl9-indirect-start-boot-sources.md)
remains the reference for the missing main-to-physical-OK join.
