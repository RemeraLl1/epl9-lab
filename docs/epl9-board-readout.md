# E-PL9 / IM008: board evidence and reading without programming flash

## Result — 2026-11-04

**Actual open-body/main-board images were found in an E-PL9 repair video series.**
The inspected frames do not resolve the memory markings or board revision.
No attributable E-PL9 service schematic, boardview or readable two-sided main
PCB photograph was obtained. Consequently there is still no identified memory
part, verified pad map, voltage or programmer configuration for this body.

There is an additional concrete software result: **one native flash-read path
can enter block relocation that calls erase/program functions.** Calling it a
read does not qualify it for a zero-program/erase acquisition. This finding is
from the exact downloaded E-PL9 1101 main, with bounded native fixtures, not
from another model or an observed defect in the owner's camera.

No camera was connected, opened, powered for diagnostics, reset or flashed.
No programmer, UART, JTAG, USB vendor operation or SD update file was used.

## 1. Primary visual source: an E-PL9 repair series

The uploader **techxian** publishes these parts:

| Part | Source | Inspection in this pass |
| --- | --- | --- |
| 1 | [E-PL9 disassemble and assembly](https://www.youtube.com/watch?v=Rdj9ffx8Afs) | Frames at 8:46 and 9:51 show an opened body and work around the PCB/top assembly |
| 2 | [E-PL9 disassemble and assembly](https://www.youtube.com/watch?v=F-Jc3cdIbi0) | **0:00** provides the clearest reviewed overview: PCB at the right of the sensor opening; central square package under a light thermal pad, two dark rectangular packages below. At 2:13 the sensor/front assembly is being handled |
| 3 | [E-PL9 disassemble and assemble](https://www.youtube.com/watch?v=4Arr6x8ek3c) | Frames at 0:04 and 6:17 show the sensor and later assembly around the same PCB |
| 4 | [E-PL9 disassemble and assemble](https://www.youtube.com/watch?v=m5qpQhtaqm0) | Link/title and thumbnail identified; this part was not reviewed |

The part-2 quality menu offers **480p maximum**. Chip markings in the reviewed
frames are not reliably legible; package shape alone cannot distinguish RAM,
NAND or another component. No OCR-derived part number is accepted. The model
attribution is the uploader's E-PL9 labeling and the visible repair context;
**IM008 on the base label and the PCB revision were not independently read**.
The series therefore supplies a useful layout reference, not an authenticated
parts list. No complete video was downloaded or republished.

The official [E-PL9 manual](https://download.omsystem.com/pages/inst/epl9/manual_epl9_ENU.pdf)
identifies the regulatory model **IM008**; our firmware identity is **1330**.
The owner's particular board revision remains unknown. Similar E-PL7/E-PL8
teardowns and E-PL10/IM008Z references were not substituted for E-PL9 evidence.

## 2. Service-document and photo search limits

This extends the [previous online search](epl9-online-boot-search.md), rather
than reclassifying its archive findings as new BOOT material.

- Exact E-PL9/EPL9 and Olympus IM008 queries covered mainboard, PCB, internal
  photos, service manual, schematic, boardview, memory, repair/disassembly and
  Japanese/Chinese equivalents. Search hits frequently concerned another PEN,
  a display flex cable, accessory-system diagrams or unrelated PL9 labels.
- The [TronicsCenter E-PL9 category](https://tronicscenter.com/product-category/olympus/olympus-pen-e-pl9-2018/)
  is real, but its visible single result is an antistatic-brush set, not an
  E-PL9 mainboard or service document. Merely listing the model in a store's
  menu does not identify an available schematic.
- A [firsthand Japanese owner's account](https://rinos.hateblo.jp/entry/2025/09/19/204634)
  documents a damaged E-PL9 LCD connection. It does not establish memory-chip
  identity or a firmware readout connection.
- The indexed certification trail identifies **CCAK17LP1850T6 / IM008**.
  A direct request to its NCC mirror returned 403; no internal-board exhibit
  was obtained. A certification identifier alone is not a board photograph.
- Earlier public service catalogs and repair forums remain recorded in the
  previous search. No new E-PL9 electrical schematic or pinout emerged here.
  Generic repair marketing and user manuals are not service schematics.

This is not a claim that private service documents or higher-resolution donor
photos do not exist. No account-only material was accessed, no document was
bought, and no message or photograph request was sent to another person.

## 3. Firmware memory names are candidates, not chip markings

Exact input identities:

| Input | Model / version / build | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | E-PL9 / 1330 / displayed package 1.1 / main 1101 | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main `00_0100_406e0020.decoded.bin` | Same update; not an installed-device dump | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

Analysis base is `60400020`; addresses below are hexadecimal and must not be
used as physical chip offsets without resolving the address translation.

The image includes a group of `FlashROM Device:` strings:

| String address | Name in software |
| --- | --- |
| `60458231` | `S29PL064J` |
| `6045824d` | `SST39VF6402` |
| `6045826b` | `LH28F640BFG` |
| `60458289` | `TE28F640J3D` |
| `604582a7` | `S29GL064A(MirrorBit)` |
| `604582ce` | `K8P2815UQB(MirrorBit)` |
| `604582f6` | `MX29GL320ET` |

Several mutually different parts are present. No runtime choice or chip ID has
been read. **S29GL064A is not an identified E-PL9 part.** Its manufacturer's
[S29GL-A datasheet](https://www.farnell.com/datasheets/1500802.pdf) describes
64-Mbit parallel flash; it is not an SPI-memory identification. A separate
small loader/configuration chip remains possible, but is not established by
this string group or the public update's much larger size.

The main also contains `[PURNAND]` help, `p read`, `p dump`, `p write`,
`p erase`, `makebbm` and `showbbm`, and legacy `ONENAND_STLREAD` / write / format
names. These are software features/string evidence, not a measured BOM.
In particular, neither the ONENAND name nor the BGA-looking packages in the
video identify eMMC or a specific NAND manufacturer.

## 4. Native read path has a maintenance write route

The ordinary page-read routine `604009bf` is used by the read wrapper
`604014c6`, which the earlier startup audit already follows. A byte-checked
listing shows the routine sampling `98d01194 & 0xf`, storing it at stack+16,
and later testing that value:

```text
60400a4a..53  sample controller field, mask to low four bits, save at SP+16
60400abd     reload sample
60400abf     compare with 13
60400ac1     skip maintenance when sample <=13
60400ac3..c8 otherwise pass physical-page value >>6 to 604007b0
```

**Sixteen isolated native cases** exercise sample values 0 through 15 with
explicit RAM fixtures. Values 0–13 reach `60400acd`; 14 and 15 stop at the
external-call boundary to `604007b0` with the expected block argument. No MMIO
or physical flash is accessed in these tests. The precise physical meaning of
the sampled nibble is not established; do not relabel it as a measured ECC
count or an error present on this camera.

Helper `604007b0` changes a block mapping, chooses a reserved block and reaches:

```text
60400813 -> 60400c60  read old block into temporary RAM
60400826 -> 60401066  erase replacement block
60400838 -> 60400e55  program replacement block
... additional table persistence / erase / program calls follow
```

The erase identity is corroborated by the native diagnostic `erase` branch
calling `60401066` at `6043bd0b`. Routine `60400e55` is used by the diagnostic
write branch and references `[FLASH]write error` and `Bad Block ... WRITE`
diagnostics. The image separately contains `Read Disturb` and BBM diagnostics.

One native helper fixture supplies **synthetic** block 3, an identity mapping,
and reserved slot 992 explicitly marked free. It models the first old-block
read as a boundary without inventing its contents, changes the RAM mapping,
then **stops before** the call to `60401066`. At that boundary the target is
`47c00000`, length **131072**. No erase or program is modeled or executed.
The fixture is not a dump of the owner's bad-block table or proof that this
state occurs on that body.

**Consequence:** this particular ordinary read route cannot be certified as
zero-program/erase for every controller result. A normal read on a good fixture
does not establish that guarantee. This is a software-path finding, not a claim
that reading every NAND device necessarily writes it.

### A separate diagnostic direct-read route remains unqualified

The `p read` parser at `6043b65b..8a` enters `6043b68f..6043b84f`. That fragment
sets up the controller directly, rather than calling `604009bf`. The reviewed
loops print a **2048-byte data area and 128-byte extra area**. This is a debug
loop extent, **not a verified physical page/spare geometry** or a general
whole-flash export API.

It must not be confused with the ordinary read/maintenance route above. Its
console transport, availability on the retail body, buffer initialization,
controller interpretation and error handling remain unqualified. A help entry
is insufficient to authorize sending the command. No UART pad, USB mapping,
debug login or writable test environment was inferred or tested.

## 5. How a future read without programming could be qualified

Here, “without writing” means **no nonvolatile program/erase, partition,
calibration, protection/fuse or mapping changes**. RAM buffers and volatile bus
command registers may need writes to perform a read. The distinction matters
for command-based NAND access; holding every write-strobe inactive is not a
universal way to read every memory type.

| Acquisition route | What it could obtain | Current E-PL9 status |
| --- | --- | --- |
| Existing vendor/service/console read, with all callees reviewed | Logical flash or selected raw areas while main runs | No qualified externally reachable export; ordinary read maintenance caveat above |
| Passive storage-bus capture during startup | Bytes actually fetched, timing and command evidence | Can help locate reset/OK decisions; not a full dump unless every relevant address is captured; a running camera can independently write |
| Identified debug port / boundary-scan read | Potential mapped memory or device access | Port, pinout, access restrictions and no-program behavior unverified; not assumed JTAG |
| External reader on an identified and isolated memory device | External boot regions and physical flash contents independently of main | Most direct candidate for a controlled full acquisition, but chip, bus, package, voltage, isolation and whole-array protection must first be established |

External reading is a **conditional engineering route**, not an instruction to
open this camera now or a risk-free procedure. A clip on an assembled board may
back-power circuitry or contend with the SoC; a successful adapter connection
does not prove isolation or correct data. Off-board reading would be a separate
invasive operation, outside this task.

The no-program acquisition specification should require:

1. Attributable high-resolution **both-side mainboard photos**, PCB revision,
   all storage package markings and pin-1 orientation; distinguish memory from
   RAM and power devices. Use the **exact** datasheet, not a similar family.
2. Confirmed interface/voltage/pinout and how the processor is prevented from
   driving the bus. Reader support must name the actual part, capacity and
   package; do not assume a CH341A or an eight-pin SPI clip fits it.
3. A reviewed acquisition operation list that excludes program/erase, blank
   check with erase, automatic repair/remap, initialization/formatting and
   nonvolatile protection changes. Check the scope of hardware protection:
   for example, **S29GL-A WP# protects selected sector groups, not the whole
   array**; its datasheet describes separate read/write inhibit conditions.
   This is an example of why a generic WP instruction is inadequate, not a
   connection prescription for E-PL9.
4. Two independent complete reads with byte comparison and SHA-256, a defined
   physical address order and records of unreadable/unstable areas. Matching
   reads alone do not prove the correct chip/region was selected.
5. If **raw NAND** is identified: retain every relevant physical block and
   spare/OOB/bad-block/ECC metadata, plus a separate corrected logical view.
   Do not silently skip bad blocks or discard OOB. The primary
   [mtd-utils nanddump implementation](https://github.com/sigma-star/mtd-utils/blob/master/nand-utils/nanddump.c)
   opens the device read-only but has distinct ECC/OOB/bad-block options;
   output format must be deliberate. This is a general host-side example,
   **not evidence that E-PL9 runs Linux or exposes `/dev/mtd*`**.
6. If a **managed eMMC** device were identified instead: distinguish user area
   from boot0/boot1 and record configuration. The
   [kernel partition documentation](https://docs.kernel.org/driver-api/mmc/mmc-dev-parts.html)
   treats them as separate areas. A user-area-only image is not a full boot
   backup. eMMC remains unconfirmed on E-PL9.

For BOOT, read all identified external boot regions first and then determine
their execution/address map. Do not equate file prefix `S133`, an update kind,
the first arbitrary megabytes or a memory chip's “boot-sector” marketing term
with the required E-PL9 pre-main loader. A full external flash dump also need
not include the processor's internal mask ROM/OTP or separate controller NVM.

## Next evidence needed

The remaining acquisition bottleneck is **a readable macro image/parts record
for the E-PL9 storage and its board revision**. The repair video closes the
absence of any board-layout visual, but not that identification. A donor owner
or service specialist could supply the photos and existing documented dump;
no outreach was performed. A useful service record would state whether their
read-only process can capture boot, physical flash and calibration areas
without calling the camera's remapping/repair code.

No exact no-disassembly software dump method or hardware hookup has been
validated. Recovery after damaged main remains unproven. This pass does not
qualify firmware installation.

## Retained evidence

Ignored directory: `local/epl9-board-readout-search-20261104/`.

- `page-probes.json` and saved public HTML record the newly checked catalog,
  owner account and NCC mirror response. The TronicsCenter capture is explicitly
  bounded to 2000000 bytes, not asserted to be a complete page capture.
- `video-observations.json` records exact reviewed frames, available part-2
  resolution, model-attribution limits and the unreviewed fourth part.
- `flash-string-evidence.json` and `debug-string-bindings.json` record the
  exact main's relevant strings and selected native references.
- `listing-manifest.json` and nine byte-checked listings retain the read,
  maintenance, program and debug fragments. The pinned local reader SHA-256 is
  `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae`.
- `trace_readonly.py` / `native-read-path-results.json` retain **16 branch
  cases and one relocation fixture**, script/helper identities and explicit
  stop-before-erase behavior. No downloaded camera code was run on hardware.

Other chats' firmware engines, ART/video work and camera tools were unchanged.

## Follow-up: memory exporters and a one-camera verification boundary — 2026-11-04

**Two additional exact-image paths were traced: a memory-to-file request and
the native monitor's direct memory display. Neither is a qualified retail
E-PL9 BOOT/full-flash acquisition method.** Further execution of `p read`
exposes an argument/help mismatch and unchecked completion results. No camera
or transport was accessed in this follow-up.

Inputs remain the exact E-PL9 / model 1330 / owner-reported displayed 1.1 /
downloaded main build 1101 identified in section 3. This is not an installed
body dump. Main is 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
The reader has the same pinned hash recorded above. Addresses below are in the
analysis mapping, not chip offsets or instructions for connecting to hardware.

### Memory-to-file is present, but its source and destination need qualification

The string at `60a86c7f` describes `memdump NAME ADR LEN`, with hexadecimal
address and decimal length. It has a real dispatch binding:

```text
609c9864..7a  compare "memdump" and call 609cb044
609cb044     parse filename/address/length and construct a file request
609cb10c     call 609c25e7 with that request
```

Another native wrapper, `60fb7ba1`, constructs five arguments including `file`
and `memdump`, then calls the file dispatcher `609c96db`. This is corroborating
code, not a demonstrated USB, Wi-Fi or SD-script entry point. A memory export
does not itself establish external command availability on the retail camera.

The request constructor takes its selected device from halfword `62396ad4`
and current path from `626905f4`; neither is hard-wired to an identified SD
destination in this trace. At the boundary to `609c25e7`, the request carries:

| Offset | Observed value / role in this fragment |
| --- | --- |
| `+6` | Selected device, halfword |
| `+8` | Field copied from the selected device context's `+28` |
| `+16` | Prepared filename pointer |
| `+20` | Parsed source address |
| `+24` | Rounded-up 512-byte unit count for the tested nonnegative lengths |
| `+28` | Exact requested byte length |

**24 native configuration cases** vary four supplied source addresses,
including an MMIO-looking address, and lengths 0/1/511/512/513/2048. The code
preserves the supplied address and exact length and computes the expected
unit count. The fixture starts after parsing/name conversion, supplies two
128-byte allocations and an explicit synthetic device/path context, and stops
before `609c25e7`. Every source range is deliberately unmapped: no source bytes,
filesystem, card or hardware are read or written by this test.

This establishes request construction, not successful file export or the absence
of writes in its downstream device/filesystem implementation. The constructor
does not qualify an arbitrary supplied address as readable RAM. A direct read
of an MMIO address can have hardware side effects; a file export could also
target the wrong storage context. Therefore the command must not be run by
guessing an address and filename.

A RAM export could be useful if an independently identified boot shadow remains
mapped and readable. That shadow has not been identified. Loaded main bytes
would omit unrepresented boot/service/calibration regions, and neither its
mapping nor this exporter supplies a complete physical image with OOB/BBM data.

### Native monitor display is another memory reader, not a discovered USB dump

`mdump4`, `mdump2` and `mdump` select 4/2/1-byte display paths through
`604361dc`. The native loops perform CPU loads and print their values. The
routine has a specific width restriction for `98000000..9fffffff` (message
`[warning] mbc addr. use mdump4 !`), but that does not make all four-byte reads
of that range safe. Its output transport, retail access and a BOOT-readable
mapping remain unresolved. No console was opened or command sent.

### `p read`: the implemented argument contract differs from the help text

The retained help at `6045818d` advertises three arguments after `p read`:
DRAM address, flash address and size. The reviewed implementation at
`6043b68f..6043b84f` instead:

1. Parses only `argv+12`, the **first** argument after `read`, with `%x`.
2. Masks it with `0fffffff`, shifts by 11 and adds `08000000` for the
   controller address/selector write at `6043b6e8`.
3. Uses fixed buffers: the enclosing parser sets the main-area display pointer
   to `a1000000`; this branch sets the extra-area pointer to `a2000000`.
4. Performs a fixed 128-byte CPU copy from the controller data port and later
   displays fixed 2048/128-byte areas. It does not honor a supplied byte length.

The full data-transfer/controller setup is not qualified by this observation.
In particular, preparing a display pointer does not prove that the corresponding
main-area RAM buffer received fresh data.

**24 native fragment cases** vary four first arguments, two pairs of additional
arguments and three declared completion results (0/1/2). All read only the first
argument slot. Extra arguments leave the reviewed operation unchanged. The
mask aliases `40000000` and `80000000`, and truncates a low-bit misalignment;
these are observations about unchecked normalization, not valid chip addresses.

The fragment calls controller-wait helper `6040113a` and status helper
`604010f2` but does not branch on their return values. The latter's own code
returns 2 on timeout. Supplying result 2 at the explicit helper boundaries
still reaches the first display header in these cases. Result 1 is retained
as an uninterpreted fixture value, not classified as a physical error.

All MMIO reads/writes are synthetic RAM/register fixtures. Completion helpers
and time/hex parsing are explicitly supplied software boundaries; this is not
a NAND-controller emulator. The observed controller words are not relabeled
as validated physical NAND commands without its specification. No erase/program
call is reached inside this isolated fragment, which **does not certify** that
the complete real operation cannot program or disturb nonvolatile storage.

Together with the previously proven maintenance branch in ordinary
`604009bf`, this rules out treating either command name or a successful-looking
printout as a sufficient no-program/erase guarantee.

### Additional public-source checks

The refreshed search covered exact E-PL9/IM008/model-1330 BOOT/dump terms,
service/adjustment software, NAND/EEPROM, Japanese board terms, and the literal
candidate names `S133`, `S1339999`, `E1331000`, `OLY_E_133_1000`. No new
attributable loader/full-dump file was obtained. A GitHub search produced RAW
decoder/changelog and unrelated hits, not an E-PL9 boot acquisition. Search
silence is not proof that private or unindexed service assets do not exist.

The [official Japanese release table](https://support.jp.omsystem.com/en/support/imsg/digicamera/download/software/firm/e1/)
still lists E-PL9 1.1, dated 2018-04-26. The manufacturer's
[Chinese historical catalog](https://om-digitalsolutions.cn/support/verup.php?page=6)
also lists its 1.1 release; neither retrieved page supplies BOOT or a full dump.

The official phrase **backup function** means saving and reloading camera
settings around an update, as explained in the
[Workspace procedure](https://support.jp.omsystem.com/en/support/imsg/digicamera/qa/contents/ow/ow_a1.html).
It is not a flash-image backup or independent rollback. E-PL9 is absent from
that procedure's supported-model list. That terminology therefore supplies no
missing recovery mechanism for this body.

The primary [libgphoto2 PTP header](https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/ptp.h)
was inspected as a public protocol lead. Its named Olympus operation definitions
do not identify an arbitrary flash/BOOT readout. This narrow observation does
not establish the absence of undocumented vendor operations or E-PL9 support
for every listed operation. None was sent to the camera.

### What one healthy, unopened camera can actually establish

Here a qualified acquisition means no program/erase or nonvolatile changes to
the camera's internal firmware, calibration, mappings or protection state.
RAM buffers and volatile command registers are a different category. Ordinary
power-on/connection can execute autonomous camera code, so a USB command named
GET alone cannot prove zero internal NVM activity.

| Check | Useful evidence | Limit |
| --- | --- | --- |
| Read the ordinary firmware-version menu | Installed displayed body/lens versions | No BOOT bytes, board revision or full image |
| Capture ordinary USB enumeration and descriptors | Actual interfaces, endpoints, identities and timing | Enumerating MTP/Storage is not arbitrary memory access or ROM rescue |
| Inspect a capture of standard PTP identification, if already obtained during normal connection | Advertised operations and identifiers; parse it offline before selecting anything further | A vendor operation list does not qualify unknown operations as safe |
| Repeat the already allowlisted Wi-Fi information GETs | Fresh public command/capability descriptions | No established BOOT/flash endpoint; does not qualify new service commands |
| Inspect an existing SD card independently on the PC | File inventory and presence of candidate update names | SD contents are not internal firmware; OS mounting is outside a forensic no-card-write guarantee |
| Observe normal versus OK-held startup, only with no update images present | A possible difference in startup timing/display/USB behavior on healthy main | Cannot demonstrate recovery without main or identify all executed code; not performed here |
| Inspect any future donated/service image offline | Identity, layout, candidate loader, reset/OK logic and dependencies | Does not demonstrate restoration on this physical board |

The optional OK observation must use a card whose file inventory has first been
checked independently, including case-insensitive `DCOLYMP` candidates for both
`E133????BIN` and `S133????BIN`, with their normal dotted forms. Do not place a
valid, corrupt, same-version, renamed or deliberately truncated update on it.
No file-selection observation licenses the update check/commit commands. The
test remains an ordinary healthy-main observation, not a recovery qualification.

With this one body we will not deliberately hang/corrupt main, interrupt an
update, test flash protection or try guessed diagnostic reads. There is still
no qualified no-disassembly software acquisition route. A separate donor or
documented service acquisition remains the practical source of independent
boot bytes until external read reachability and all side effects are resolved.

For an existing service/donor dump, request the exact E-PL9/IM008/1330 board
revision, memory markings, acquisition method, complete area boundaries,
sizes/hashes and repeat-read agreement; preserve device-specific calibration
privately. If raw NAND is involved, request physical blocks plus OOB/BBM/ECC
information and a separately labeled corrected logical view. Ask specifically
whether acquisition uses on-camera relocation/repair routines and whether
their procedure has restored a body with unusable main. A generic promise to
"reflash Olympus" does not answer these questions. No outreach was performed.

### Follow-up evidence and validation

Ignored directory: `local/epl9-recovery-readout-followup-20261104/`.
It contains byte-checked listing windows, `explore.py`,
`native_readout_probe.py`, `native-readout-results.json`, public source results
and a SHA-256 manifest. The native result pins its source and execution helpers.
**24 direct-read plus 24 file-request cases passed.** All stop boundaries and
software fixtures are explicit. No firmware container was created or altered;
no BOOT/dump was obtained; no camera, card, USB/serial/debug port or programmer
was accessed. The result still does not qualify firmware installation.

## Follow-up: conditional USB diagnostic shell and direct memory reads — 2026-11-04

**A conditional software path from the main's USB/PTP vendor-operation layer
to the native shell and `file memdump` is now mapped.** Three native CLI runs
reach the file-request boundary. The physical retail USB session, its setup
effects, actual BOOT mapping and complete no-program/erase acquisition remain
unqualified. No camera commands were sent. No network was accessed in this pass.

This uses the same exact E-PL9 / IM008 / model 1330 update input: owner-reported
displayed 1.1, downloaded main build 1101, 26214336 decoded main bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
The source is still the downloaded update, not the installed body's dump.

### The newly connected conditional route

| Fragment | Exact-image evidence |
| --- | --- |
| PTP operation dispatcher | `60faf521`; vendor-class selection reaches `60faf6eb` and `60fada77` |
| Vendor operation bridge | `60fadd74` builds the 80-byte diagnostic envelope and calls message exchange `60434a21`, queue ID from `60420f68` |
| Diagnostic worker | `60f51590` calls `60f51774`; its main operation hash is `612776d0`, subtracting `1001` from the operation code |
| Session gate | Getter `60ef1fe4` reads RAM halfword `626f3d04`; the main diagnostic dispatch requires value 1. Open/close handlers `60f51962` / `60f519ae` change it and make additional initialization/application requests |
| Model-oriented output | Operation `902b` reaches `60f564b2`; selector 15 is `MDO_USR_DEBUG_SHELL`, target `60f56869` |
| String handling | Copies at most 255 bytes into RAM `626f3dc8`, terminates the string, optionally initializes output capture, then selects a shell engine or queue path |
| Normal shell engine | `6056a9d3` tokenizes through `6056a80a`; ordinary selection uses table dispatcher `6056a97d` |
| File command | Stock table `605c90c8` includes row `605c9160`: `file -> 609c96d6`. The native prologue enters the previously mapped file dispatcher `609c96db` |
| Memory exporter | `609c987a -> 609cb044 -> 609c25e7`, stopping before the final file-service request in our execution |
| Output retrieval | Operation `902a`, selector 47 (`MDI_GET_USR_DEBUG_SHELL`) reaches `60f5503b`, which uses `604d5208` to copy and consume a RAM capture ring |

These are connected static/native fragments with explicit message boundaries,
not an executed USB session. Supported transport modes, session setup,
parameter/data phases, concurrency and the underlying application requests
have not all been qualified. The RAM gate alone is not evidence that opening
the diagnostic session has no nonvolatile side effects.

Three separate command tables contain the same `file` callback: rows
`605c8058`, `605c9160`, `6132e434`. The normal shell dispatcher above actually
selects the middle table. This closes the previous gap between a mere
`memdump` help string and its native CLI invocation.

**Three native CLI runs**, using the original tokenizer, table walk, file
dispatcher, filename conversion and request constructor, reach `609cb10c` for
requested lengths 1/512/513. Source is deliberately unmapped synthetic address
`17000000`. Comparisons, numeric parsing, two allocations and current device/path
are declared software fixtures. No source bytes or filesystem are accessed;
the final request is not executed. These results do not identify device 3 in
the fixture as an actual SD device.

**Eighteen shell-boundary runs** vary flags 0/1/2/3/4/5 and lengths 2/255/256.
They confirm clipping, termination and selection between the normal shell,
the monitor engine `6056a9b8` and queued execution `6041700f`. Capture setup,
printing, queue delivery and engine execution are explicit unexecuted boundaries
in those cases. In particular, capture flags do not constitute a sandbox that
restricts which command the shell can execute.

### Correct operation-name alignment

The operation-name table begins with **code, name pointer** pairs at
`61278d2c`, not pointer/code pairs. The native name consumer `60f59ce5` compares
the first word and returns `entry+4`. Correct associations are:

| Proper pair | Operation | Name |
| --- | --- | --- |
| `61278eec` | `9021` | `READ_DATA` |
| `61278ef4` | `9022` | `WRITE_DATA` |
| `61278f34` | `902a` | `MODEL_ORIENTED_DATA_IN` |
| `61278f3c` | `902b` | `MODEL_ORIENTED_DATA_OUT` |

An earlier gyro report associated `902b` with the IN string by reading a pair
shifted four bytes. The actual gyro request still uses `902b` and selector 10;
this corrects its label, not that numeric route. Do not copy an adjacent
operation's name onto a command: the neighboring `9022` handler copies in the
opposite direction and is a write operation. No operation was sent to hardware.

### A more direct candidate: `READ_DATA` without an SD file

The correctly identified `READ_DATA` operation resolves through hash key
`8020` to `60f518b7 -> 60f532d2`. Its reviewed direct modes are:

- Mode 0 supplies the requested address directly as the source of a CPU copy.
- Mode 1 adds `a0000000` to the supplied offset before the copy.
- Mode 15 sends a separate message/processor request; its target semantics are
  outside this direct-RAM qualification.

The direct branches copy into the request's output buffer and report the byte
count. Requested length is checked against the supplied response capacity;
source address validity and harmless MMIO behavior are not established by that
check. The reviewed direct fragment does not call the ordinary flash reader
`604009bf`, its relocation helper, erase or program functions.

**Ten native cases** cover six successful synthetic RAM copies, three rejected
mode/capacity cases, and one MMIO-looking source stopped before copying. The
last case shows that the fragment forwards such an address without qualifying
it as safe. The actual `memcpy` is a bounded software model over explicit
read-only fixture sources; response transmission is suppressed. No actual
camera address was read. This is stronger evidence for a possible memory-export
mechanism, not a certified whole-session no-write result.

This route could avoid the file export's current-device selection and SD
filesystem writes **if** a valid safe mapping and transport are established.
It still cannot turn an arbitrary unmapped/raw flash device into readable
CPU RAM, recover OOB/BBM/ECC information absent from that mapping, or establish
that pre-main BOOT remains resident. A current main/RAM image alone is not a
complete firmware/calibration backup.

Another tempting name is explicitly narrowed: `MDI_ONENAND_STLREAD` selector
23 resolves in this exact image to generic error branch `60f5564d`, ultimately
status `201d`, rather than a working STL reader. Its counterpart
`MDO_ONENAND_STLWRITE` selector 7 similarly selects the generic error branch
`60f56e2d`. These names do not identify an available flash dumper.

### Wi-Fi result and remaining no-write gates

The previously hash-pinned embedded Wi-Fi API 4.00 command list contains
**37 names**; none exposes `memdump`, `READ_DATA`, a shell or a debug tunnel.
The reviewed HTTP download path is a file path, not a demonstrated arbitrary
memory transport. This is a bounded negative result about the embedded list
and previously mapped paths; unreviewed properties/hidden handlers are not
thereby proved absent. No Wi-Fi request was made.

The concrete remaining gates are now:

1. Qualify the retail USB diagnostic ingress and full initialization/teardown
   path. A RAM session flag and static vendor bridge do not cover application
   callbacks, storage initialization or autonomous nonvolatile writes.
2. Establish actual stable readable address regions and locate pre-main BOOT,
   including whether it is resident at all. Neither `60000000`, `80000000` nor
   a guessed flash offset is authorized by this analysis as a camera read.
3. Qualify response capacities/chunking, error handling, concurrent reuse and
   repeated-read identity without using MMIO ranges as test data.
4. For a full physical backup, identify storage geometry and every required
   area, including device-specific calibration and any spare/mapping data.
   CPU-memory export and physical flash acquisition remain separate products.

The most promising software lead is now the **conditional direct memory read**;
an already documented service/donor boot dump remains the source that does not
require experimenting on the owner's body. None of this proves an independent
recovery entry after unusable main.

### Evidence from this pass

Ignored evidence: `local/epl9-memdump-entry-size-20261104/`. It retains checked
listings, `shell_route_probe.py` (3 + 18 cases), `memory_read_probe.py` (10),
`static-bindings.json`, exact source/helper hashes and a SHA-256 manifest.
The accompanying size/version audit adds 12 + 4 cases, for **47 new native
cases total**; see [installation-size findings](epl9-installation-recovery.md).
Exploratory listing names are not authority for function semantics; in
particular the initial `read_data.lst` window contains the neighboring
WRITE_DATA routine, while `actual_read_data.lst` is the verified READ_DATA.
No firmware container was generated, no camera command was sent and no BOOT
or full dump was acquired. Installation remains outside the qualified phase.

## Follow-up: the hidden MTP operation filter — 2026-11-05

In the exact E-PL9 / IM008 / 1330 stock 1.1 build 1101 main (26214336 bytes,
SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`),
mode 4 registers the same 20 ordinary operations that its `GetDeviceInfo`
serializer advertises. The registration block starts at `60faa337`. An
unregistered `0x9xxx` operation goes through an additional admission check at
`60faf5c4` before it can reach the vendor bridge at `60fada77`.

The mode getter `60faa2c5` reads RAM at `626f5542`. The query at
`60fadcc9` sends message **9** for mode 4 and message **6** for the other
modes that reach the query. Mode 7 bypasses it. The worker at `60f51571`
selects different tables for these messages:

| Query | Table | Relevant results |
| --- | --- | --- |
| 9 (mode 4 MTP) | `612773f6` | `9029`, `902a`, `902b`, `9030`–`9034` are classified. `9021 READ_DATA` and `9022 WRITE_DATA` are absent |
| 6 | `6127739a` | `9021` and `9022` are classified along with `9029`–`902b`. This table does not identify an externally reachable retail mode |

Passing this classifier supplies a data phase and allows a request to proceed
to the next dispatcher. `902a` and `902b` still require the diagnostic RAM
session state at `626f3d04` to equal 1. The dispatcher also accepts `9034`
with the gate closed and selects the diagnostic session open or close handler
at `60f535b4`. The open handler updates RAM and sends an application request
via `60f5717a`. The effects of the receiving task remain unqualified.

There is a second session path. After the ordinary handler runs, the main PTP
dispatcher calls `60fadbf4` if the transport marker `626f5bca` equals 2.
The observer's table at `613116fe` forwards `1002 OpenSession` and
`1003 CloseSession` to the diagnostic worker using message 0. Which physical
retail connections set that transport marker was not established. The
observer is separate from the mode 4 vendor classification and cannot make
`9021` pass it.

The bounded stock-instruction runner passed 27 cases covering classification,
message selection, session observation and the diagnostic session gate.
Inputs are synthetic. Runs stop before actual queue exchange or service
handler execution. The runner, checked listings and `usb-offline-results.json`
are in ignored `local/epl9-memdump-entry-size-20261104/`.

The official manual covers Storage, MTP and printing. The model support page
provides links for updates and service. The renewed public search did not yield
an E-PL9 service schematic, documented diagnostic session or attributable BOOT
image. [E-PL9 manual, pp. 140–142](https://download.omsystem.com/pages/inst/epl9/manual_epl9_ENU.pdf#page=140)
[E-PL9 support page](https://learnandsupport.getolympus.com/support/e-pl9)

Microsoft documents host-side access checks in WPD. The earlier WPD
`0x80070005` result produced no live PTP response. Microsoft also documents
`GetDeviceInfo` through a WIA PTP driver. Access to this camera through WIA
is unverified.
[Microsoft WPD access control](https://learn.microsoft.com/en-us/windows-hardware/drivers/portable/handling-access-control)
[Microsoft WIA example](https://learn.microsoft.com/en-us/windows-hardware/drivers/image/vendor-extended-commands)

This pass used the downloaded image and public documentation. The service
routes were not tried on a camera. No BOOT or full backup was obtained.
