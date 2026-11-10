# E-PL9: 1920×1440 OpenGate at 60 fps

## Accepted target and current answer

On 2026-11-02 the owner clarified the target to **1920×1440, square pixels,
4:3, 60 frames/s**, retaining the full usable sensor field. This supersedes
1440×1080 as the primary candidate. It does not require storing 16 MP frames:
full-field subsampling/binning followed by scaling could satisfy the goal.
Cropping a 16:9 source, stretching it or changing MOV metadata cannot do so.
The paired requirement is [gyro logging during recording](epl9-gyro-logging.md).

**Feasibility remains unproven.** The exact image contains useful sensor and
encoder code, but no continuous full-field 4:3/60 acquisition path has been
established. There is no installable patch. This investigation is offline;
no camera commands, recording tests or flashing were performed.

The [geometry override probe](#november-4-follow-up-bypassing-the-preset-list-at-the-encoder)
executes verified firmware instructions with host-owned parameter objects.
1920×1440 and rate keys 5994/6000 survive the tested encoder configuration
copy, and the driver-side arithmetic computes 10800 macroblocks per frame.
At the tested 30 Mbit/s argument the target still selects the same native
class and preset pointer as FHD60. This identifies a real geometry input to
investigate without a new menu entry. It does not establish driver acceptance,
buffer capacity, or full-field acquisition at 60 fps.

The [November 7 E-P7 comparison](#november-7-e-p7-xpan-comparison-and-native-aspect-bypasses)
finds corresponding E-PL9 aspect helpers and executes their native call chains.
A host-only change to the aspect table preserves 1440 lines in one crop helper,
but separate context overrides and a hardcoded FHD branch still return 1080.
These are additional geometry consumers to reconcile, with their ordinary
recording-instance binding still open.

The [source configuration and resource follow-up](#november-7-follow-up-source-configuration-and-resource-backed-pixel-buffers)
connects J to the configuration consumed by the conditional raster builder.
It separates the special-preset cyclic pool from resource class `0x2f00`,
whose stock constructor defines nine slots with a 3133440-byte stride.
That stride fits the existing padded FHD420 layout, but not a tightly packed
1920×1440 frame. The exact ordinary FHD60 application-state binding and
full-field/60 sensor input remain unproved.

The [next November 7 pass](#november-7-follow-up-producers-of-the-fixed-dimension-branches)
traces frame-header kind into J+874 and then the processing type, plus a
separate J+902 conversion into parameter +30. It locates the global branch
selector's writers. Native replay distinguishes fixed raster selection from
a separate 16:9 fit path; the normal FHD60 instance is still not identified.

The [eleventh timing pass](epl9-video-timing-sync.md#eleventh-november-4-pass-alternative-source-states-and-the-queued-pts-join)
connects the alternative source through its receive queue to the common PTS
builder and identifies its conditional source states. Its cyclic pixel-slot
key is not a write generation. A capture key reaches an intermediate processing
job, but ordinary-60 state selection and exposure-to-pixels/MOV remain open.
TG `free` delay inputs now connect to upper VD and phase-count fields; the
hardware parent and frequency remain unproved.

The [tenth timing pass](epl9-video-timing-sync.md#tenth-november-4-pass-q-mode-gate-alternative-source-and-tg-free-callbacks)
shows that the known public configuration classifier returns only 0/1,
whereas Q needs metadata mode 2. That path cannot establish Q as ordinary
60 fps recording. A separate source route passes an independently selected
pixel address to the shared video-item builder, but its ordinary-60 state,
exposure identity and MOV picture association remain open. TG `free` comparison
callbacks receive zero in the default IRQ dispatcher, not a sampled counter;
the counter's hardware clock parent is still unknown.

The [ninth timing pass](epl9-video-timing-sync.md#ninth-november-4-pass-q-constructor-and-the-real-request12-writer)
finds Q's separate heap pool, snapshot constructor, pixel-ring address writer
and command-7 request +12 assignment. Q is not constructed by copying the
812-byte E pool. The input branch is selected by metadata mode 2, whose ordinary
60 fps movie association remains unverified. A named TG `free` counter supplies
additional counter/compare evidence, without a verified clock parent or rate.

The [eighth timing pass](epl9-video-timing-sync.md#eighth-november-4-pass-q-completion-message-provenance)
identifies upstream senders of completion descriptor Q: command 36/event 37
conditionally forwards the pointer through command 25/event 9. Its association
with the `E+32` generation and an encoded MOV picture remains open; a retained
buffer path can replace Q's source address. Newly checked TG control writes
do not resolve CLKCAMDS-to-counter wiring or establish full-field 60 fps.

The [next timing/clock pass](epl9-video-timing-sync.md) identifies configured
HD/VD-period fields and distinguishes video PTS generation from hardware time.
Its 2026-11-04 follow-up reaches actual TG period registers and their writer,
but the movie-mode-to-register payload and full-field 4:3/60 schedule remain open.
The second pass identifies the payload producers and native FULL templates;
requesting 60 selects a generic fallback without matching that rate. It does
not establish either full-field 60 operation or a hardware impossibility.
The third pass calculates a nominal 36 MHz `CLK_CAMOUT` programming branch,
but has not joined it to the TG counting domain. It also connects the TG marker
to the logical exposure descriptor; neither result establishes 4:3/60 readout.
The fourth pass identifies a 144-tick time-conversion model: unchanged FULL
HD/VD fields calculate to 43.783 ms per counter cycle. This is not a measured
sensor limit, but it rules out calling that unchanged fallback an established
60 fps schedule. The hardware clock source and full-field readout remain open.
The fifth pass corrects the exposure-center gate: normalized rates <=60 are
accepted, rather than skipped. It resolves a separate calculated 144 MHz
`CLKCAMDS` branch without proving its connection to TG. An already downloaded
original confirms stock 1920×1080 at **60000/1001 fps**, with composition
reordering and a 180000 Hz MOV video timescale. This is evidence for that
recording's timing, not full-field 1920×1440 support. See the
[fifth-pass details](epl9-video-timing-sync.md#fifth-november-4-pass-correcting-the-60-fps-gate-and-checking-an-original-mov).
The sixth pass follows capture identity into the processing ring and identifies
the video source-address field and native MOV timescale/CTTS construction.
CLKCAMDS-to-TG wiring and the exact exposure-to-encoded-sample mapping remain
open; these results do not establish a full-field 4:3/60 sensor schedule.
The [seventh pass](epl9-video-timing-sync.md#seventh-november-4-pass-slot-generations-encoder-metadata-and-mov-sample-boundaries)
identifies a resettable processing-slot build counter and conditional time-tag
copies through encoder metadata to the mux. The actual completed pixel-buffer
generation, connection instances and exposure-to-MOV sample mapping remain
open. Identical upper HD control fields across all 58 templates do not identify
a physical TG divider or clock parent. The accepted 1920×1440/60 target remains
unproven.

The [official manual](https://download.omsystem.com/pages/inst/epl9/manual_epl9_ENU.pdf),
pp. 81–84, documents still-image aspect selection, FHD through 60p, and 4K
through 30p. Those are manufacturer specifications, not measurements of this
body. The historical 1280×960 Wi-Fi preview report does not prove full-field
recording at any frame rate.

## Exact input and reproducible evidence

Repository inspected at branch `main`, initial HEAD
`8bdc281d0caa31130a8a23fae730000f7f48dc6f`. Existing ART/interpreter and Wi-Fi
work belongs to other work and was preserved. Firmware input:

| Item | Identification |
| --- | --- |
| Model / catalog ID | Olympus PEN E-PL9 / `1330` |
| Owner-reported displayed body version | `1.1`; not a dump of installed bytes |
| Stock filename / main build | `OLY_E_133_1101_0000_0000.BIN` / `1101` |
| Stock bytes | `104552480` |
| Stock SHA-256 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main bytes | `26214336` |
| Decoded main SHA-256 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

The [initial audit](epl9-1.1-initial-findings.md) establishes container decoding.
The new `scripts/epl9_video_audit.py` rechecks stock/main identities and checks
**53 instruction anchors in 11 windows**, including gyro investigation. Each
listing is checked against image bytes for continuity and coverage. Addresses
below use the established main analysis base `0x60400020`. They are research
locations, not validated patch sites. Other-model patches were not used.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_epl9_video_audit.py -v
.\.venv\Scripts\python.exe scripts/epl9_video_audit.py --out local/new-video-audit
```

Final session evidence: ignored `local/video-audit-20261102-v2/audit.json` and
eleven TSV listings. Four synthetic safety tests pass. Decoder provenance and
Windows execution restrictions are recorded in [tooling](mn103-tooling.md).
These checks are static analysis, not video pipeline emulation.

## Firmware findings

| Location | Observation | What it does not prove |
| --- | --- | --- |
| File `0x1fddea`, analysis address `0x605fde0a` | Diagnostic text names `CAM_SENSOR_MODE_MOVIE_FULL(--fps)`; other strings name several movie sensor modes. | A working full-field mode, its rate, or model-specific hardware support. The missing rate is explicit. |
| `0x60749150..0x60749186` | Native selector bounds an index below 35 and derives an address from table base `0x608be920`; special cases select other records. | Which record gives the desired field, timing or sampling. Record semantics and sensor programming remain open. |
| `0x607bd6ac..0x607bd73a` | Diagnostic output names `SAvScaEncVideoParam`. Relative to its video subobject, `+16/+20` supply `ulHsize/ulVsize`; `+24/+28` supply maximum dimensions. | Caller provenance, permitted dimensions or encoder acceptance. |
| `0x6169f340..0x6169f481` | Progressive H.264 code branches on dimensions including 2160, 1920 and 1280, and copies two dimensions from object `+16/+20` into another configuration. | That an arbitrary geometry works. Its internal numeric classifications must not be called H.264 levels without further tracing. |
| File `0xaece34` | Data row `(1,1920,1440)` exists in a dimension map. | A hidden movie mode. Nearby literal associations are data; decoding them as instructions produced nonsense and was rejected. |
| `0x6056532d`, `0x60565411` | Native code selects a table at `0x605c5e58`, containing twelve `(1440,1080,720)` triples. Other selected tables have different triples. | Output recording dimensions. This is deliberately retained as an unknown-semantic table, not an OpenGate discovery. |

## Follow-up: native geometry records and mode conversion

Further offline analysis started from repository HEAD
`c69e3e6f8ba01d494617684604ee7c9581cf9d45` on the same dirty `main` checkout;
unrelated ART/Wi-Fi work was preserved. It narrows the search but still does
**not establish full-field 4:3/60 support**.

There are two distinct record selectors. `0x60749150` returns **26-byte**
records from `0x608be920`. `0x607491bf` returns **24-byte** records from
`0x608bece4` (file offset `0x4becc4`), with index below 35 and fallback index 0.
Do not describe the 26-byte records as proven sensor timing schedules:
`0x6074255d` builds a small image-like descriptor from their fields, and other
consumers scale coordinates. They may describe an auxiliary sampling grid;
line time, pixel clock and frame period have not been identified there.

The 24-byte records have a much clearer geometry consumer at `0x60742499`.
It selects a format from byte `+20`, copies widths/heights from `+8/+12/+14`,
and copies record `+16/+18` into output descriptor `+16/+18`. These last two
fields are the active-dimension candidates below. The complete 35 rows are
retained in the ignored audit output.

| Record index | Record address | Candidate active dimensions (`+16/+18`) | Boundary of inference |
| --- | --- | --- | --- |
| 0, 6, 9 | `0x608bece4` + index × 24 | 4608×3456 | Matches a 16 MP 4:3 geometry; no movie cadence is attached. |
| 4, 7, 8, 12, 26 | Same table | 1536×1152 | 4:3, but width is below 1920; sensor coverage remains unverified. |
| 5, 27 | Same table | 1728×1296 | 4:3, but could be a crop; width is below 1920. |
| 14, 15 | Same table | 2304×1296 | 16:9; does not supply the extra vertical field by itself. |
| 21 | Same table | 4080×2295 | 16:9; record presence does not establish a working mode. |
| 11 | Same table | 9216×6912 | Clear reason to distrust blanket model applicability of this shared table. |

No row in this table has the candidate active pair 1920×1440. This is **not**
proof of impossibility: a larger full-field acquisition followed by a scaler
could generate that output. Conversely, upscaling 1536×1152 to 1920×1440
would create the requested file size without 1920-pixel source detail. Coverage,
sampling and effective detail must be evaluated separately.

A second concrete trace now connects internal settings to record indices:

1. `0x607031f0` reads settings word `+4` and converts it to an internal mode.
   For example input values `0/1/2/4/5/6/7` yield `1/3/5/6/4/13/12`;
   input 3 yields 8 or 9 depending on settings `+332`. Other values use an
   error/default branch returning 0. This is a conversion, not a capability list.
2. `0x60701b03` calls that function; `0x60701b18` stores its result into camera
   state byte `+902`. The camera-state record stride is 1020 bytes.
3. `0x60706650` feeds state `+902` through `0x6071d49d` and publishes the result
   as descriptor byte `+25`. Its 18-entry jump table is at `0x608b81ec`.
   Conversion outputs for inputs 0 through 17 are
   `0,1,1,2,17,3,14,16,12,13,20,20,4,21,22,5,18,19`.

Diagnostic setup at `0x605ef8bc` writes 60 into a setting and prints the HSSC
60fps label; another branch names `MOVIE_FULL(--fps)` without setting a known
rate. Those diagnostic enums, the input settings enum, state `+902` and the
35-record index must **not be silently equated**. The entire conversion from a
normal movie preset to sensor register writes and frame timing remains open.
In particular, there is no demonstrated path from the `FULL` label to 60 fps.

The next decisive trace is **normal movie preset → settings conversion →
sensor register schedule and active rectangle → scaler/crop → encoder → MOV**.
We need a register schedule and frame-period calculation for the same 4:3
field as the still-photo baseline. Photo/preview geometry and table names cannot
substitute for that evidence. No exact sensor chip identification or register
datasheet mapping has been established in this follow-up.

### Reproducing the follow-up

`scripts/epl9_video_deep_audit.py` checks the original stock and decoded main
hashes again, plus the separate component used by the gyro investigation. It
extracts the 35 geometry rows and verifies native selectors/consumers, mode
conversion code, gyro dispatches and acquisition code. Final evidence is in
ignored `local/video-deep-audit-20261102-v2/`: **57 instruction anchors, 25
windows, 35 geometry records and 3 gyro selector rows**. These are independent
static checks; a checked instruction is not evidence that its branch executes
in normal recording.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p 'test_epl9_video*_audit.py' -v
.\.venv\Scripts\python.exe scripts/epl9_video_deep_audit.py --out local/new-video-deep-audit
```

Seven synthetic checks passed, including wrong-component-base rejection and
bounded hash-dispatch lookup with collisions. The deep audit passed against the
exact images. The native reader required an approved local process launch under
the Windows sandbox; no elevated camera access was requested or used.

The paired [gyro investigation](epl9-gyro-logging.md#follow-up-producer-and-component-boundary)
now identifies acquisition points, but timestamps and availability during movie
recording remain unverified. Gyro progress does not change the 4:3/60 conclusion.

## 60 fps budget and codec constraint

These are arithmetic comparisons of output geometry, not hardware measurements:

| Geometry / rate | Output MP/s | H.264 16×16 macroblocks/frame | Macroblocks/s |
| --- | ---: | ---: | ---: |
| 1920×1080 / 60 | 124.416 | 8160 | 489600 |
| **1920×1440 / 60** | **165.888** | **10800** | **648000** |
| 3840×2160 / 30 | 248.832 | 32400 | 972000 |

The target has one third more output pixels than FHD60 and two thirds of the
output pixel rate of 4K30. Neither comparison establishes sensor readout speed,
line timing, ISP access, buffer allocation or arbitrary aspect support.

There is a concrete codec issue: 10800 macroblocks/frame exceeds H.264 level
4.2's frame limit, and 648000 macroblocks/s exceeds level 5.0's rate limit.
Ordinary AVC level **5.1** accommodates these two quantities; other constraints
also apply. Thus a stock FHD stream's level/resource setup cannot simply be
assumed suitable. See [ITU-T H.264, Annex A, Table A-1](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-H.264-202408-I%21%21PDF-E&lang=e&type=items).
This is a standards calculation, not an observed E-PL9 SPS or proof that changing
`level_idc` unlocks hardware. Investigate the 4K encoder resource path as a
candidate while separately solving full-field **60 fps** acquisition.

A tightly packed 8-bit YUV420 output frame is 4147200 bytes, or 3.955 MiB.
At 60 fps that is 248.832 MB/s before encoding, excluding padding, reference
frames and intermediate buffers. This is internal traffic, not SD bitrate.
The initial pass had no original MOV. The later timing passes inspect an
existing stock 1080p original; it does not validate SPS/resources or readout
for the proposed 1920×1440 mode.

## Implementation gates

1. Identify a sensor schedule that continuously covers the same usable 4:3
   field as the still-photo baseline at 60 fps. Determine line skipping/binning,
   bit depth, exposure timing and rolling-shutter time. If it cannot do so,
   downstream encoder edits cannot achieve the accepted target. A later 30p
   experiment would be a separate fallback requiring the owner's choice.
2. Trace input/crop/scaler rectangles and stride. Obtain 1920×1440 without
   stretching, pillarboxing or extracting a central crop. Separate electronic
   stabilization crop from the ordinary 16:9 crop.
3. Trace buffer pools, AVC resource selection, SPS dimensions/level, reference
   allocation, rate control and MOV track dimensions. Preserve playback and
   handling of unsupported settings. An enum/label edit alone is insufficient.
4. Design one isolated opt-in mode retaining stock modes and ART work. First
   validate bounded configuration/serialization offline; hardware-dependent
   behavior remains unverified until an authorized later camera phase.
5. In that later phase, verify actual captured field against a fixed 4:3 photo
   reference, true frame cadence versus duplicates, readout time, sustained
   recording, audio sync and thermal behavior. Adding gyro logging is a separate
   validation axis and does not prove OpenGate.

Present blockers: no mapped 4:3/60 sensor schedule, no integrated crop/scaler
trace, no validated encoder configuration, and no established modified-firmware
installation/recovery procedure. Flashing and experimental vendor writes remain
outside the current phase.

## November 4 follow-up: bypassing the preset list at the encoder

The practical question is whether the stock recording session can be reused
while configuring a different raster below the menu. There is now a concrete
**software parameter entry to investigate**. We ran isolated native firmware
instructions with synthetic objects on the workstation. We did not open the
encoder, run its firmware driver, generate pixels, access the camera, or
modify an image. Started from local `main`, HEAD
`cada1a797ad29ae229182b676044d7cf7debb329`.

Exact inputs: E-PL9/model 1330, displayed 1.1, internal build 1101. Stock
`OLY_E_133_1101_0000_0000.BIN`, 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`;
decoded main `00_0100_406e0020.decoded.bin`, 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`,
analysis base `0x60400020`.

### The encoder preparation uses numeric dimensions

In the progressive encoder object's checked branch at **`0x6169f34a`**,
object **+16/+20** supply width/height, +32 supplies the bitrate argument,
and +52 supplies the rate key. The code selects a numeric class at +1008.
The copy at `0x6169f456..0x6169f465` stores dimensions and rate as-is into
the configuration at object +1116, fields +8/+12/+16. The class is copied
to configuration +40. `0x6169f501` is the next call to `0x616a27a3` with
this configuration. The workstation probe stops before that call.

The probe separately executes the driver's local geometry calculation at
**`0x616a2a3e..0x616a2acc`**. It rounds width/height up to multiples of 16,
stores them at driver +3588/+3592, and stores the macroblock count at +3612.
The preset selection at `0x616a2814` is also tested separately, stopping
before it uses the selected tuning block. These are verified instruction
fragments, with no stubs pretending to accept a driver command.

| Synthetic input | Rate key | Bitrate argument | Native class | Padded raster | Blocks/frame | Selected preset pointer |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| 1920×1080 control | 5994 | 30 Mbit/s | 6 | 1920×1088 | 8160 | `0x623bbfd0` |
| **1920×1440 target** | **5994** | **30 Mbit/s** | **6** | **1920×1440** | **10800** | `0x623bbfd0` |
| **1920×1440 target** | **6000** | **30 Mbit/s** | **6** | **1920×1440** | **10800** | `0x623bbfd0` |
| 1920×1440, bitrate control | 5994 | 60 Mbit/s | 7 | 1920×1440 | 10800 | `0x623bbfd0` |
| 3840×2160 comparison | 2997 | 100 Mbit/s | 8 | 3840×2160 | 32400 | `0x623bb6dc` |
| 1536×1152 candidate input geometry | 5994 | 30 Mbit/s | 5 | 1536×1152 | 6912 | `0x623bbfd0` |

Two additional controls exercise a lower rate and non-16-aligned dimensions.
The bitrates are synthetic arguments, not observed recording presets or
recommendations. The 6000 probe preserves the number; it does not measure a
physical 60 fps cadence. A class-7 input reaches a different downstream
tuning branch (`0x616a2fc1`) while selecting the same preset pointer as class 6
in this test. **The numeric class is not established as an AVC level**, and a
preset pointer is not evidence of allocated frame-buffer capacity. Raising the
bitrate merely to obtain a different class is not a validated workaround.

There is no 1080-height equality check along the tested class-6 route.
There may still be checks in later driver configuration, memory allocation,
SPS construction, or other branches. The separate application diagnostic
`SAvScaEncVideoParam` exposes active and maximum width/height fields, but its
producer-to-progressive-object mapping was not closed. Do not apply these
offsets to that application object merely because some offsets coincide.

### Where the extra field could come from

The checked geometry-table rows **14/15** contain the pairs 2352×1330,
2312×1330 in halfwords +8..+14, and 2304×1296 in the candidate active fields
+16/+18. The descriptor consumer `0x60742499` copies selected fields, including
both active dimensions. At this boundary the checked heights do not expose a
hidden **1728-line** rectangle
needed for 4:3 at 2304 pixels wide. This comparison does not bind rows 14/15
to the actual 60p preset or prove that earlier sensor output is cropped.
It does rule out treating these particular descriptor values as evidence of
1728 lines already waiting behind a final 16:9 crop.

Row 4's 1536×1152 is exactly one third of the 4608×3456 active pair in row 0
on both axes. This makes it a useful lead for full-field reduced readout.
The equality does not establish binning, full-field coverage, or 60 fps.
If an existing 60 fps acquisition can supply that entire field, scaling by
5/4 on both axes gives 1920×1440 with the same aspect and field. The resulting
detail would still come from the smaller raster. That is an explicit
upscaling candidate, not evidence for native 1920-pixel sensor detail.

The native FULL/60 lookup still selects the rate-ignoring FULL fallback.
The HSSC 60 template is an independently identified fast timing path, but
there is no proven binding from it to the above 4:3 pixels. No candidate may
claim the required field by repeating slower source frames or editing MOV
dimensions/rate after capture.

### Concrete next offline experiment

Reuse the stock recording controller and feed a **synthetic 1920×1440
source configuration** through the upstream parameter builder, scaler
output and encoder/MOV configuration as a matched set. The bounded probe
already demonstrates the local progressive-configuration copy and alignment.
Next trace and check the active versus maximum allocation dimensions before
driver open, real plane strides and chroma offsets, and the SPS/MOV width and
height producers. Use independent expected byte ranges for each plane; a
1920×1440 8-bit 4:2:0 frame needs **4147200 bytes** before padding, versus
3110400 bytes for 1920×1080. Reference buffers and the actual layout add
constraints. A larger stock encoder resource configuration is worth tracing
separately from the active raster, without pretending that the pixels are 4K.

For actual OpenGate, join that geometry experiment to a verified full-field
60 fps acquisition before choosing a future patch. If the stock sensor
path already crops before the scaler, source window/binning/timing must change;
an encoder-only override can change raster size but cannot recover the lost
field. The gyro identity/clock joins remain the separate work recorded in the
[timing investigation](epl9-video-timing-sync.md).

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --out local/video-geometry-audit-20261104-v2
```

The audit checks exact firmware hashes, **42 instruction anchors in seven
windows**, six descriptor rows, and **eight native fragment probes**. Results
and instruction traces remain under ignored `local/`. No output is a camera
patch or evidence of actual 1920×1440/60 recording.

## November 4 follow-up on the 4K30 resource comparison

At nominal rates, 1920×1440/60 feeds **165.888 Mpixel/s** and **648000
macroblocks/s** to AVC. UHD 3840×2160/30 feeds **248.832 Mpixel/s** and
**972000 macroblocks/s**. The proposed raster uses two thirds of both rates.
Its frame interval is **16.67 ms** versus **33.33 ms** for UHD30. These
calculations concern the encoded raster. Full-field sensor readout and
per-frame scheduling have their own timing requirements.

The existing 8105416-byte original MOV, SHA-256
`2adb950f5ae41bf92fa01f921fb8ca06056ee8094e389e83dc266e3ad4877ad0`, reports
**H.264 High, level 4.2**, 1920×1080 at `60000/1001` in `ffprobe`.
Its video stream averages about 27.29 Mbit/s. This confirms the level in
that stock FHD recording. A corresponding UHD source file was unavailable
in the local sample set.

The rate-control code associated with `CAvpiVenH264RateCtrl.cpp` reads the
configuration class at +40 (`0x616a42b4`) and dispatches through the ROM table
at **`0x617013f0`**. Its class 6, 7 and 8 entries select 522240, 589824 and
983040 respectively. These constants match the AVC macroblock rate limits
for levels 4.2, 5.0 and 5.1. The target's 648000 lies above the first two
and below the third. The executed fragment uses these constants for rate
control. SPS generation, driver admission and clock selection remain separate
questions.

The extended probe writes the class independently into a host-only
configuration and executes the native dispatch. This separates the 4K class
from the progressive object's original class selection and keeps the target
geometry at 1920×1440 throughout the probe.

| Probe | Class at configuration +40 | Table rate | Divisor | Value at `0x616a43b4` in high-class branch |
| --- | ---: | ---: | ---: | ---: |
| 1920×1440/60, native selection | 6 | 522240 | 4 | — |
| 1920×1440/60, host override | 7 | 589824 | 2 | 16588800 |
| 1920×1440/60, host override | 8 | 983040 | 2 | 16588800 |
| 3840×2160, native selection | 8 | 983040 | 4 | 24883200 |

At class 7 and above this branch replaces the intermediate value at
`0x616a43a5..0x616a43b1` with `floor(blocks_per_frame * 384 / divisor) * 8`.
Class 8 selects divisor 2 below padded height 2160 and divisor 4 at or above
that height. Thus the host override reaches the 983040 table entry while
the later frame calculation still uses the actual 10800 blocks in the
target raster. The subsequent picture-dependent adjustments are outside the
probe. The earlier tuning-block selector uses height and rate independently
of this class, so the 4K tuning block and allocation layout still need tracing.

The next firmware boundary is the allocation and SPS setup reached by this
configuration. The proposed experiment keeps the active raster at 1920×1440
and traces whether it can borrow a larger resource budget. Its sensor input
still needs continuous full-field 4:3 acquisition at 60 fps. This pass uses
the same verified E-PL9 1.1 build 1101 inputs listed above.

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --out local/video-geometry-audit-20261104-v3
```

The audit verified 53 instruction anchors in nine windows, eight geometry
probes and five rate-control probes using the firmware's jump-table bytes.

## November 5 follow-up on frame storage and AVC headers

This pass uses the same hash-verified E-PL9 1.1 build 1101 inputs. It separates
three settings that a 1920×1440 recording would need to agree on: active
geometry, pixel storage and the encoder's AVC sequence parameters.

### Frame storage in the conditional Q branch

`0x60729ce8` calls `0x60727cba`. The latter reads `Q+805` and selects a
frame-slot stride of 353280 for value 17, 1382400 for value 16, or **3133440**
otherwise. At `0x60727cdf` it writes the stride to `0x62a25ca4`. At
`0x60727cee..0x60727cf0` it divides 119439360 by the stride and writes the
integer slot count to `0x62a25ca8`. The pixel-address producer at
`0x60727859..0x6072786e` uses the stride and base `0xa45f82c0`.

| Q sizing probe | Slot stride, bytes | Complete slots |
| --- | ---: | ---: |
| Default branch | 3133440 | 38 |
| `Q+805 = 16` | 1382400 | 86 |
| `Q+805 = 17` | 353280 | 338 |
| Host injects a tightly packed 1920×1440 4:2:0 stride | 4147200 | 28 |

The injected stride leaves 3317760 bytes after the 28 complete slots. The
stock default equals 1920×1088 in packed 8-bit 4:2:0. The injection runs the
native stride and count stores against host memory. It does not allocate
camera memory or establish actual plane pitches or padding.

Other stock allocator objects reuse `0xa45f82c0`. Registration calls at
`0x607c4dc4` and `0x607c4e9b` pass different strides, 13271040 and 3133440.
The adjacent registrations at `0x607c4ec2` and `0x607c4ee9` use other bases
and strides of 8294400 and 12441600. Constructor `0x607c6d44` stores the
base and stride at object +8 and +12. These descriptors do not establish
which regions are live together or which can be reassigned in a movie.
The Q route is gated separately, and its use by ordinary 60 fps recording
is still unverified. The alternative source has its own 1382400-byte
initializer. A viable override needs the active recording allocator and
all of its address consumers. [Source-route investigation](epl9-video-timing-sync.md#eleventh-november-4-pass-alternative-source-states-and-the-queued-pts-join)

### MOV track geometry and the input SPS

The constructor at `0x6168c146` writes the MOV visual sample entry's width
from track +96 and height from track +92 (`0x6168c1ff..0x6168c20a`). The
same constructor creates the `avcC` child at track +692. Its payload starts
at +700, with version 1 and zero-initialized profile, compatibility and
level bytes at +701 through +703.

The video track ingress recognizes a type-7 NAL at `0x6168aeeb`, copies the
first SPS into the track's SPS slot at `0x6168af18`, then takes the three
bytes immediately after the NAL header at `0x6168af34..0x6168af50`. They
populate the `avcC` profile, compatibility and level bytes. The later
profile-dependent path can normalize the compatibility byte in both copies
(`0x6168af53..0x6168afac`). The level comes from the incoming SPS on this
path. The native rate-control class is a separate field.

The original FHD MOV has `avcC` payload prefix `01 64 00 2a` and begins its
SPS with `67 64 00 2a`, consistent with High profile and level 4.2. Two
bounded host probes copy independent track dimensions and SPS bytes. The
stock-shaped inputs produce 1920×1080 and `01 64 00 2a`. Injecting
1920×1440 and the synthetic four-byte SPS prefix `67 64 00 33` produces
1920×1440 and `01 64 00 33` (level 5.1). This exercises the copies before
serialization. The short synthetic prefix is not a decodable SPS, and
the probe does not open the encoder or generate a MOV.

The next downstream check is to find the encoder's SPS producer and run
the real geometry through the recording allocator and encoder setup. For
the target, the SPS must describe the actual coded dimensions, cropping
and timing in addition to an appropriate level. The sensor task remains
separate: identify a continuous full-field 4:3 acquisition with a 16.67 ms
frame budget. Neither the buffer arithmetic nor the header copies resolve
the TG clock, physical exposure phase or raw gyro-to-frame join.

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --out local/video-geometry-audit-20261105-v2
```

The audit checked 74 instruction anchors in 13 windows and ran eight geometry,
five rate-control, four Q sizing and two MOV header probes. No camera commands
were sent and no firmware images were modified.

## November 5 follow-up on integrating a recording mode

The application sets active and maximum video dimensions before opening the
AVM engine. This gives a session-specific integration point above the H.264
driver. The evidence below uses the same E-PL9 1.1 build 1101 inputs on local
`main`, HEAD `fe4bf11248ea14f806402a77f8476520ed8a2b1b`.

### Application settings before AVM open

1. At `0x607b9bd8` the recording-open path attaches a per-stream 284-byte
   parameter block to the API record at +16. It calls `0x607bb1c4` at
   `0x607b9be6`. The nested call at `0x607bb29a` passes that block's video
   subobject at +96 to `0x607bb467`.
2. `0x607bb56f..0x607bb624` chooses the active raster at video +16/+20, the
   maximum raster at +24/+28 and a separate limit at +56. The diagnostic
   load at `0x607bd7bd` identifies +56 as `ulMaxCodeSize`. The geometry key
   is local to the builder. It is neither a public menu ID nor a TG mode.
3. The switch at `0x607bb6e8` independently sets output-rate key at +60
   and `ulIvopInterval` at +64. Nominal 60 selects 5994 and 30. Nominal 30
   reaches the default 2997 and 15 in the tested switch. This fragment does
   not establish the upstream acquisition cadence or all rate fields.
4. At `0x607b9c0d` the same API record goes to `0x6164bd35`. For API types
   6/8 this copies all 284 bytes before submitting open command 257. The
   transport forwards the block. The destination mapping to the scaler,
   memory allocator and progressive encoder remains to be verified.

| Geometry key | Active | Maximum | `ulMaxCodeSize` |
| --- | --- | --- | ---: |
| 0 or 1 | 1920×1080 | 1920×1080 | 783360 |
| 2 | 1280×720 | 1920×1080 | 345600 |
| 3 | 640×480 | 1920×1080 | 115200 |
| 4 | 640×360 | 1920×1080 | 88320 |
| 5 | 4096×2160 | 4096×2160 | 3317760 |
| 6 | 3840×2160 | 4096×2160 | 3110400 |

Seven bounded probes run the raster and output-rate switches against host
memory with injected builder keys. Every +56 value equals 96 times the
macroblock count after rounding both dimensions to multiples of 16. The
same arithmetic gives **1036800** for 1920×1440. This is a candidate value
for that limit. It does not measure encoded picture size or pixel storage.
The UHD row demonstrates that maximum dimensions and active dimensions can
differ in the native application contract.

### Candidate mode design

Start with a session-local experimental flag on the normal FHD60 route and
keep the stock 5994 cadence and recording lifecycle. After the builder
finishes, before command 257 snapshots the block, a host-only experiment
would substitute 1920×1440 for both active and maximum dimensions and
1036800 for `ulMaxCodeSize`. Trace those fields through the command receiver
first. The numerical encoder class 8 is a separate candidate override after
that join, with the input geometry and cadence held fixed. Selecting geometry
key 6 would instead replace both dimensions with the stock UHD pair and its
larger maximum envelope. A dedicated menu entry can follow once this route
is shown to work.

The scaler must get a verified full-field 4:3 source at the required cadence
and produce 1920×1440 before handoff. Its selected buffer layout needs matching
plane offsets, pitch and write extent. The encoder must generate a matching
SPS, and the muxer must receive matching track dimensions. Test both the stock
and experimental sessions through stop/restart. A recording check also needs
unique completed source generations through repeat and reorder paths so that
gyro samples can be joined by exposure time, independently of file geometry.

The expanded audit checked 85 anchors in 15 windows and added seven
application probes. This run used saved disassembly for previous windows
and a direct decode of the restricted opcode set in the new raster switch.
The audit checked the listings against the verified binary before execution.
No native reader process ran in this pass. Outputs are in ignored
`local/video-geometry-integration-20261105-v1/`. The normal audit entry point
is `scripts/epl9_video_geometry_audit.py`. No firmware image or camera state
was changed.

## November 5 follow-up on the command 257 receiver and pixel input

This pass uses the same exact E-PL9 1.1 build 1101 input. It closes the
command-to-configuration joins for VideoSource and the video encoder.
It also identifies a recording-side hardware address selection that runs
before command 257, independently of the dimensions in the copied block.

### Command 257 and the two geometry payloads

- The open message uses destination task ID `0x1048` from ROM `0x604211da`.
  The task descriptor at `0x6041cc2c` names the worker `0x6164c388`.
  At `0x6164c3e9` this worker receives the command, then indexes table
  `0x616fac48` by `command - 257`. Entry 0 leads through `0x6164c478` to
  `0x6164c619`. The separate application `REC_INIT` dispatcher calls the
  sender through `0x607bdf49 -> 0x607b9b3f`.
- For API types 6/8 the receiver constructs the recording object at
  `0x6165f8b4`. Its vtable is `0x616fd22c`, open entry `0x61660cd1`.
  The call at `0x61660da5` reaches vtable +196, `0x6165ffa2`. This method
  reads the pointer at API record +16 and passes the original 284-byte copy
  through the new recording instance. The configuration sequence at
  `0x6166001d` branches to the source and encoder builders.

The table uses offsets relative to the video subobject at +96 of the copied
block, then offsets relative to the individual downstream payloads.

| Destination | Dispatch | Video subobject → payload |
| --- | --- | --- |
| VideoSource | `0x61660256`, control `0x01000201`, 56 bytes | Active width/height +16/+20 → +12/+16. Input-rate field +8 → +8. |
| Video encoder | `0x61660342`, control `0x03000101`, 176 bytes | Maximum width/height +24/+28 → +52/+56. `ulMaxCodeSize` +56 → +0. Output-rate key +60 → +32. Input-rate field +8 → +36. |

VideoSource handler `0x616b0164` recognizes `0x01000201`. Its checked path
copies the active dimensions to the configuration it passes to its source
object at `0x616b038c`. Its aspect switch at `0x616b031f` accepts 16:9 when
`16 * height == 9 * width`, 4:3 when `4 * height == 3 * width`, square, and
the special 4096×2160 case. The target takes **4:3 key 1**. The FHD control
takes **16:9 key 2**. This path configures the source contract. It does not
demonstrate sensor cropping, scaling of pixels or frame cadence.

The encoder receives `0x03000101` at `0x616a7e18`, dispatches via ROM table
`0x61701600`, then calls `0x6169d964` at `0x616a7f2d` for the checked
encoder object. That function copies the maximum dimensions to object
+144/+148 (`0x6169da0b..0x6169da12`). They are distinct from the active
dimensions used later by the progressive driver. This pass does not join
the delivered pixel raster to those active encoder fields.

### Hardware address selection precedes the open message

On first stream open, `0x607b9b70..0x607b9b91` selects two addresses using
**recording request byte +2**. Value 6 selects `0xa9facc00` and `0xaf0c5dc0`.
The other branch selects `0xb1e51000` and `0xb937a000`. It passes those
addresses to `0x607bdbde`, which writes MMIO `0x98100c1c` and `0x98100c2c`.
Nearby register-handling code refers to `NACH(3)`. The mapping of these
registers to individual pixel pools is unverified. They cannot be used as
evidence that the recording owns the memory between the two addresses.
The ordering is clear: these writes occur before the application builder at
`0x607b9be6` and before the command sender at `0x607b9c0d`. Changing the
dimensions in the 284-byte block cannot change this earlier selection.

The frame-delivery side uses a separate application callback. The builder
publishes `0x607bce64`, and the supply path at `0x607b9f2f` passes video items
with existing pixel addresses through the registered callback. The conditional
pool resolvers previously traced on the capture side use their own slot keys
and stride storage. The alternative route uses the 1382400-byte stride at
`0xa2af4a00`; the Q route can use 3133440 at `0x62a25ca4`. Neither initializer
has a verified binding to ordinary FHD60 or to the command 257 width/height.
The confirmed VideoSource path has allocations for descriptor lists, which
must be kept separate from the actual pixel-plane allocation.
[Capture-side slot and supply provenance](epl9-video-timing-sync.md#eleventh-november-4-pass-alternative-source-states-and-the-queued-pts-join)

### A separate image-processing request fixes the raster and plane offsets

The conditional branch at `0x6072554f` calls `0x6071184a` before choosing the
raster. Within that helper, a nonzero `0xa2af3c80` takes the cyclic allocator
`0x60719c8a` and address resolver `0x60719ccb` at `0x60711889..0x60711894`.
It publishes the selected key at result +26 and address at +12. The zero
case follows a different allocator. This identifies a pixel-pool producer
inside the processing path, independently of command 257. The mode gates
and the exact pool used in ordinary FHD60 still need a binding.

The raster switch at `0x60725560` uses a separate internal key from the
configuration obtained via `0x60714c3a`. Keys 5/6 choose **1920×1080** and
plane delta **2088960** (`1920 * 1088`), key 8 chooses **3840×2160** and
**8294400**, and key 9 chooses **4096×2160** and **8847360**. The switch
also has a 1280×720 case. These keys are distinct from the request byte
used for MMIO selection and the earlier application geometry key.

At `0x607255eb..0x6072564e` the code builds two base-plus-plane-offset
address pairs, plus full and half raster fields. The address returned by
`0x6071184a` is one of the bases. `0x60725650` submits the descriptor as
operation 7 to `0x60706f1b`. The wrapper marshals the two address pairs and
halfword geometry into separate image descriptors and calls `0x6071c021`,
which reaches the image operation entry at `0x6074c398`. That function has
an equality-dependent fast path and a separate call to `0x6074d735`. The
physical scaler registers and exact input/crop and output-plane roles
remain to be resolved.

The host replay fed keys 5, 6 and 8 into the stock switch. A fourth case
kept width 1920 and substituted 1440 and a packed plane delta of 2764800
before the descriptor builder. Native stores produced 1920×1440, half
raster 960×720 and the same new delta in both address pairs. This marks
another required geometry change if the branch proves active in FHD60.
The replay stops before operation 7 and assigns synthetic base addresses.
It gives no evidence that the selected pool can hold the larger layout.

### What to change in the offline prototype

Set active and maximum geometry at video +16/+20 and +24/+28 before the
284-byte copy and retain the separate output-rate field. Two host probes
checked this boundary at rate key 5994. The synthetic 1920×1440 case kept
its dimensions through both payload builders, selected 4:3 in VideoSource,
and preserved the candidate `ulMaxCodeSize` 1036800. The probes also checked
both recording range branches, stopping before MMIO. They did not invoke
the full receiver, write pixels or open the encoder.

The upstream change still needs a 4:3 acquisition window at 60 fps, the
matching scaler destination and an output pool with verified plane offsets,
pitch and extent. Packed 8-bit 4:2:0 at this size needs at least 4147200 bytes
per frame. The native FULL/60 lookup still selects its generic fallback.
HSSC has an explicit 60 timing entry, but its full usable 4:3 coverage and
its binding to the ordinary recording route remain unverified. The next
trace is the source of the scaler output request and its completed pixel
address upstream of the supply callback.

The audit checked 110 instruction anchors in 22 windows and six ROM routing
words. The added runs cover two receiver payload/ratio cases, two range
selectors and four processing descriptor layouts. This pass reused saved
listings and an offline integer decoder
based on the local GNU opcode tables. The decoder matched 218 cached GNU
transport instructions after normalizing empty operand fields. All audited
listing bytes were checked against the exact firmware. Evidence stays in
ignored `local/video-geometry-avm257-20261105-v2/`. No camera access or
firmware mutation occurred.

## November 5 follow-up on the image job and intermediate storage

The processing branch reached from `0x60725560` has its own source and
destination descriptors, plus an optional intermediate raster. The evidence
uses the same exact E-PL9 1.1 build 1101 inputs as the command 257 pass.

### From the processing request to the worker

- The layout key used by `0x60725560` is byte +1 of the record returned by
  `0x60714c3a`, at `0xa2af3e6a`. The writer `0x60714652` copies that byte
  from initialization data. `0x6072bef7` passes its nested pointer at
  message payload +12 to `0x6071382b`, which calls the writer. The ROM
  state-0/event-0 entry at `0x608b9d24` points to the handler `0x6072beb8`.
  The route to `0x60725560` also checks render record +10 for value 2,
  initialization byte +0 for value 3 and render byte +77 for zero.
  These are concrete mode gates. The producer of the ordinary FHD60
  instance's nested configuration remains unresolved.
- `0x60706f1b -> 0x6071c021` marshals the two plane pairs into image
  descriptors. `0x6074c398` has a specific equal-size fast path. Its other
  branch goes to `0x6074d735`. At `0x6074f0bc`, the latter compacts the
  source descriptor for the job, including the dimension pair +16/+18
  and the two origin fields +20/+22. It preserves the stride-related
  halfword at +10. The destination descriptors have a 56-byte stride.
- `0x6074d735` writes image-job kind 3 at `0x6074d81f`, and submits the
  708-byte request at `0x6074db6e`. The chain goes through `0x6074ef3a`,
  `0x6074fdf6` and `0x6072fb1b`. ROM slot `0x608bae90` maps kind 3 to
  `0x6072fd27`. Its general processing branch calls `0x60734068`, whose
  kind-3 slot at `0x608bb0d8` selects `0x60734479`. That worker has another
  guarded fast branch and a general path via `0x6073416b` to the hardware
  setup code. These dispatches preserve separate dimensions and origin.
  The final crop and scale register fields on the ordinary FHD60 instance
  have not been established.

### Conditional intermediate footprint and its hardware fill

When `0x6074d735` enables the intermediate path, it rounds the intermediate
width to even, rounds the pitch up to a multiple of 32, and sets height
from the selected height. At `0x6074da34..0x6074da3c` it stores
`2 * pitch * height` as the requested byte count. The width and height here
are selected intermediate dimensions. The code can clamp or adjust them
before this arithmetic. Full output dimensions alone do not prove that
the intermediate will use that same size on the camera.

The owner callback is concrete. `0x60706fcc` attaches `0x606fbc6c` and
`0x6074adbe` requests a temporary address using event 19. The ROM entry
at `0x608b4850` goes through `0x606fbcf1` to `0x606fbebb`. The owner
chooses allocator IDs according to mode and descriptor fields. Paths
through `0x606fc0e5` use the calculated size, obtain memory through
`0x607193c9`, then publish the returned pointer at callback argument +64.
The following `0x6074bb0a` submits a kind-15 fill using that address, the
calculated count and pattern `0x80008000`. The fill's downstream handler
reaches `0x6073a393`. With no image-descriptor pointer at job +32, it writes
the fill address to `0x9cb00084`, the byte count to `0x9cb0036c`, and the
pattern to `0x9cb00380`. These registers describe the intermediate fill.
The full scaler programming and completion are separate steps.

| Host replay input for the intermediate | Rounded width | Pitch in samples | Bytes written into the fill count |
| --- | ---: | ---: | ---: |
| 1920×1080 | 1920 | 1920 | 4147200 |
| 1920×1440 | 1920 | 1920 | **5529600** |
| 1921×1440 | 1922 | 1952 | 5621760 |

The replays use synthetic intermediate sizes and a host-owned register
shadow. They stop before any hardware activity. The 5529600-byte temporary
layout is separate from the minimum 4147200-byte packed 8-bit 4:2:0 output
frame. A future test of this branch needs the active output pool and the
conditional temporary allocation to be validated independently, including
which regions are live together. The unchanged timing evidence still does
not establish full-field 4:3 acquisition at 60 fps. The next upstream join
is from the normal movie settings to the nested configuration sent to
`0x6072beb8`, then to the incoming pixel descriptor and sensor window.

The audit replay used saved and locally decoded listings checked against
the exact input, covering 118 anchors in 24 windows, ten ROM entries and
three new intermediate layout/fill cases. The 31 existing video and CPU
subset tests passed. Evidence stays in ignored
`local/video-geometry-scaler-20261105-v1/`. No camera access or firmware
mutation occurred.

## November 7: E-P7 XPan comparison and native aspect bypasses

### What the E-P7 project actually implements

The likely reference in the owner's request is **XPan**, in
[Caduceus for E-P7](https://github.com/cakelesscoder/caduceus-ep7).
Its README describes 65:24 and 21:9 **still-photo crops**, 5184×1920 and
5184×2224, with matching live view and playback. This is a source report
about E-P7, not a measured E-PL9 capability or a full-field movie mode.
The [v0.29 release](https://github.com/cakelesscoder/caduceus-ep7/releases/tag/v0.29),
commit `d5ff5a5830b25c04b94aef0433e5a833b85b48a9`, reports camera-tested AF,
metering, tracking, reboot-persistence and SCP-label fixes on November 7.
The composition grid overlay remains open. The README still contains older
boot-reset wording; the author's [issue #23 reply](https://github.com/cakelesscoder/caduceus-ep7/issues/23)
explicitly says that reset was removed. The README advertises v0.29a;
v0.29 is the specific release inspected for these XPan fixes.

Implementation details were read from the existing ignored checkout
`references/caduceus-ep7`, origin
`https://github.com/cakelesscoder/caduceus-ep7.git`, pinned at
`7d42c1f258737b7196c6b17cec5d643b5080ece6` (not updated in this pass).
Its [ASPECT.md](https://github.com/cakelesscoder/caduceus-ep7/blob/7d42c1f258737b7196c6b17cec5d643b5080ece6/docs/ASPECT.md)
repurposes hidden aspect IDs 6/7 and coordinates dimension tables, crop
consumers, validators, JPEG/ORF framing, live view, playback and UI.
Early table-only versions still produced incorrect framing. This gives a
useful method for locating dependent geometry consumers; it does not supply
a new 4:3/60 sensor schedule. No E-P7 firmware input or patch was applied here.

### Corresponding E-PL9 helpers and exact boundaries

The input remains Olympus E-PL9 model 1330, displayed version 1.1, internal
build 1101: stock container 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`;
decoded main 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`,
analysis base `0x60400020`.

The E-P7 crop helper `0x6035585e` and selector `0x6034ee0b` have corresponding
E-PL9 behavior at **`0x6074fd86`** and **`0x60749187`**. The E-PL9 selector
uses six-byte rows at `0x608bf038 + 6*aspect_id`: width, height, ratio code.
Aspect 1 is 4608×3456; aspect 3 is 4608×2592. The crop helper multiplies
the supplied width and height independently by the selected row divided
by row 1. Four direct call sites are instruction-verified at
`0x60758e52`, `0x60761cba`, `0x60763ba4`, `0x60764155`; each passes width
and height pointers within an image descriptor. This alone does not bind
any of the callers to the ordinary movie instance.

Two separate bypasses matter for a video extension:

- Selector argument `d1=1` returns the fixed row at `0x608bf02c`,
  **1824×1024**. Argument `d1=2` returns `0x608bf032`, **1920×1080**,
  independently of aspect ID. These are distinct from the aspect rows.
- Native dimension wrapper `0x60750ada` supplies record +16 as a type word,
  +18 as aspect ID and +21 as selector context to `0x607509cd`.
  The classifier `0x607a3c9e` and jump table `0x608f2118` can choose
  `0x60750a60`, which writes **1920×1080** directly. That branch never
  calls the aspect selector. Another branch writes 3840×2160.

The crop helper also exits without changing dimensions for request byte
+10417 equal to 4, 5, 6 or 7, among other gates. These numeric fields and
types have not been assigned ordinary recording-mode names in this pass.
Their runtime producer remains necessary evidence.

### Native execution on synthetic requests

The extended geometry audit runs the selector, crop helper and complete
dimension wrapper with the existing opt-in CALL/RET engine. No software
callee models are installed. It checks return, stack and saved registers.
The counterfactual changes only aspect 3's height word from 2592 to 3456
in a host-owned table copy; the ratio code is deliberately left unchanged.
It isolates one dependency and is **not a consistent proposed firmware patch**.

| Native path and synthetic arguments | Stock table | Host height-word change |
| --- | --- | --- |
| Crop helper, 1920×1440 input, aspect 3, gates clear | 1920×1080 | 1920×1440 |
| Dimension wrapper, type 0, context 0, aspect 3 | 4608×2592 | 4608×3456 |
| Dimension wrapper, type 0, context 2, aspect 3 | 1920×1080 | 1920×1080 |
| Dimension wrapper, type 4, context 0, aspect 3 | 1920×1080 | 1920×1080 |

Eighteen audit scenarios retain both stock and changed-table comparisons,
and additionally cover aspect 1, all four numeric bypass modes, context 1
and the type-5 UHD branch.
These results show why a still-aspect-table edit alone cannot cover these
dimension paths. They do not prove that the tested synthetic type/context
is used by normal FHD60 or that any source contains the extra sensor lines.

The next join is the ordinary recording producer of the type/context/aspect
record, especially +16/+18/+21, and its relation to the nested initialization
record supplied to `0x6072beb8`. It must then be reconciled with the earlier
processing raster, output-plane offsets, pool capacity and sensor window.
Full-field 1920×1440/60, TG clock/physical exposure phase and exposure-to-video/
MOV/gyro timestamp association remain unverified.

The audit now verifies **134 anchors in 29 windows and 20 ROM dispatch words**.
All earlier geometry probes and 18 new aspect scenarios passed; 15 existing
video tests and 31 CPU subset/call tests passed. The new `--listing-dir`
option reuses saved listings while still checking exact input bytes and
anchors, and records their hashes without claiming the native reader ran.
Evidence is in ignored `local/video-geometry-aspect-20261107-v2/` and
`local/video-geometry-aspect-listings-20261107-v1/`. No camera access or
firmware mutation occurred.

## November 7 follow-up: producers of the fixed-dimension branches

### Result and scope

The producer is now substantially more specific than a synthetic type 4
fed into the dimension helper. Camera frame-header kind reaches **J+874**;
`0x60708d80` converts it into a processing type and aspect. A separate
operation field reaches **J+902**, then converter `0x6071d49d` produces
**parameter +30**, which participates in dimension classification. The
global selector read at `0x6070899c` chooses between two materially
different type encodings and dimension paths.

**This does not yet establish which path normal FHD60 actually instantiates.**
The checked fragments contain no 5994/6000 cadence test that closes that
association. One selector-enable call belongs to the earlier conditional
Q construction path, which cannot be assumed to be ordinary FHD60. A
complete claim about normal recording still needs its concrete instance
and configuration producer.

This pass stayed on dirty local `main`, HEAD
`1f4dc523fc8db1a61863da66a09413627d5eb8e8`, preserving unrelated work.
Inputs are the same exact E-PL9/model 1330, displayed 1.1, build 1101:
stock container `OLY_E_133_1101_0000_0000.BIN`, 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`;
decoded main 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`,
analysis base `0x60400020`. No camera access or firmware mutation occurred.

### Frame kind and classifier context have different producers

1. `0x6091a11a` calls adapter `0x6091a079` with a subrecord at owner +4.
   The adapter passes its first plane record at subrecord +16 to
   **`0x6091a167`**, destination header +34. That packer copies plane
   byte +3 to output descriptor +30 (`0x6091a1c3..0x6091a1c6`). In this
   caller the source byte therefore aliases original owner **+23**.
   These numeric kinds are not interchangeable with the native TG enum
   in the timing audit.
2. Callers `0x60679fda` and `0x6067a7d5` publish header +34 through
   `0x606f942b -> 0x606fc9ff`. The latter copies **32 bytes** into
   `0xa2aed574`. Other publishers exist too. Receiver `0x606ffdbe`
   calls `0x606fca3f` at `0x606ffe6d`, copying that mailbox into **J+844**.
   Its descriptor byte +30 is consequently **J+874**. This is a settings/
   geometry snapshot path, not a pixel-completion or exposure timestamp.
3. **`0x60708d80`** reads J+874 together with J+808, J+818, J+273 and
   the global at `0x62a24d14`. For the tested global=1, J+818=0 state,
   frame kind 6 gives type **`0x2004`** and aspect **3**; kinds 4/7 give
   **`0x2002`** and aspect **1**; kind 3 gives `0x2003`/3; kinds 8/9 give
   `0x2005` with aspect 3/10. These are actual native outputs on the
   specified synthetic states, not assumed mode labels.
4. Independently, `0x60701b03 -> 0x607031f0` maps input settings +4
   into J+902. For input 4 the result is **6**; for input 6 it is **13**.
   At `0x60706650`, converter **`0x6071d49d`** maps J+902=6/7 to
   **14/16**, and J+902=13 to **21**. `0x60706659` stores this at the
   processing API subrecord K+25.

The constructor adapter's callable entry is **`0x6071b691`**. The nearby
`0x6071b68c` is an alternate prologue, not the target of its four inspected
direct callers. At `0x6071b7ac..0x6071b7e1`, K+16/+18/+21/+25 become
the 32-byte constructor parameters' **+16/+18/+21/+30**. The constructor
`0x6074df04` copies those 32 bytes into job +4 at
`0x6074e02f..0x6074e03b`. Therefore the helper's parameter +16/+18/+21/+30
alias full job **+20/+22/+25/+34**. Do not shift those offsets twice.

The earlier +21-only context description was incomplete. Wrapper
`0x60750ada` passes **+21** as the ratio-selector context, but passes
**+30** to classifier `0x607a3c9e` via `0x607509d4`. In the inspected
`0x60706502` producer, +21 is the boolean **J+902 == 2**, so it can be
0 or 1; the fixed selector-context-2 row from the previous pass is not
produced by this particular assignment.

### Who switches the encoding, and why it matters

Setter **`0x60708993`** writes `0x62a24d14`, and getter `0x6070899c`
reads it. Four direct call sites were found and instruction-checked:

| Site | Written value | Established scope |
| --- | ---: | --- |
| `0x60726f27` | 1 | Conditional setup inside function whose body begins `0x60726d4d`; not bound to FHD60 |
| `0x60727af0` | 1 | Called by `0x60729cd4`, beside the conditional Q/pool setup at `0x60729ce8` |
| `0x60727eb6` | 0 | Cleanup path |
| `0x60728fb5` | 0 | Reset path through `0x60728fae` |

With global=1, kind 6 creates `0x2004`. Dimension class 6 then takes
the **constant 1920×1080** path at `0x60750a60`. With global=0 and J+808=1,
the same kind instead creates **`0x0034`**. Although the tested context
14 still classifies it as 6, its high nibble `0x30` takes a **different
branch**, `0x60750a54 -> 0x60750830`.

That fit helper obtains a size class via `0x607491d5`, table
`0x608bf07a`, whose four width/height rows are 640×480, 640×480,
800×600, 1024×768. It hardcodes **aspect ID 3** at `0x6075083e`, then fits
and rounds to even using the ratio code bytes. The tested size class 0
therefore yields **640×360**, including when the input frame kind gives
aspect 1. The replay does not establish this as the encoder's primary
pixel raster. This small-size path must not be confused with the fixed
FHD branch or with the separate processing request at `0x60725560`.

### What the joined host replay proves

The new probe executes the native packer, mailbox stores/load, operation
mapper, type producer, context converter, API field copies, constructor
parameter-copy fragment, classifier and dimension wrapper on shared host
memory. The harness supplies stage arguments and omitted services' entry
states. No software callees are installed. It is **not an uninterrupted
camera/RTOS call chain**, and it neither completes a constructor allocation
nor processes pixels. Source frame kind, input operation, J+808=1 and the
global selector are explicitly synthetic inputs.

For operation input 4, J+818=0, J+273=0 and size class 0:

| Frame-header kind | Global selector | Type / aspect | Classifier context | Native dimensions |
| --- | ---: | --- | ---: | --- |
| 6 | 1 | `0x2004` / 3 | 14 | **1920×1080** |
| 4 or 7 | 1 | `0x2002` / 1 | 14 | **1280×720** |
| 3 | 1 | `0x2003` / 3 | 14 | 1280×720 |
| 8 or 9 | 1 | `0x2005` / 3 or 10 | 14 | 3840×2160 |
| 6 | 0 | `0x0034` / 3 | 14 | 640×360 |
| 4 | 0 | `0x0032` / 1 | 14 | 640×360 |

Two controls change only aspect 3's height word in a host table shadow;
they leave 1920×1080 and 1280×720 unchanged. Another control stops the
fixed-FHD path just before its native height store at **`0x60750a6a`**,
sets host register d0 to 1440, then resumes the unchanged native stores
and returns. It produces **1920×1440**. This locates an effective output
height boundary; it does not deliver the additional sensor lines or
constitute a firmware edit. A further operation-input-6 case verifies
J+902=13 and classifier context 21 without changing type `0x2004`'s
fixed 1920×1080 output.

### Coordinating a candidate 1920×1440 mode

These results support an **explicit, mode-scoped geometry override** as an
offline prototype direction. Reusing a 4:3 frame-kind code alone also changes
type classification and can select the 1280×720 family. Globally replacing
1080 constants or aspect row 3 would affect unrelated existing paths.
The source kind should continue describing the actual source; the new
mode needs a separately propagated target raster.

The coordinated boundaries to implement and verify are:

- Actual full usable 4:3 acquisition at 60 fps and its descriptor origin,
  not just aspect ID 1. The unchanged FULL/60 TG lookup still falls back;
  the HSSC/60 entry still has unverified field coverage and route binding.
- Output dimensions after the active dimension selector, including the
  separate fit/preview path if the new mode uses it. The sensor's real
  descriptor and origins must remain consistent with the incoming pixels.
- The conditional `0x60725560` raster switch, plane offsets and pitch;
  command 257's active/max size fields, source aspect and encoder geometry.
- Verified output-pool extent/lifetime and optional temporary storage.
  The earlier candidate footprints remain 4147200 bytes per packed 8-bit
  4:2:0 output and, conditionally, 5529600 bytes for the intermediate.

The unresolved join is now narrower: normal FHD60's actual configuration
must select a concrete global/J+808 state, input operation and frame header,
and that instance must be connected to the `0x60725560` pixel request and
the nested source configuration entering `0x6072beb8`. Changing the video
container dimensions, or reaching this helper with synthetic values, does
not close that join. No gyro/exposure-to-MOV identity claim changes here.

### Reproduction

The geometry audit adds 12 processing-route comparisons while retaining
the 18 earlier aspect cases and all earlier geometry probes. Listings are
locally decoded or cached, then checked byte-for-byte against the hashed
image. Output remains under ignored `local/`:

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --listing-dir local/video-geometry-processing-listings-20261107-v3 --out local/video-geometry-processing-20261107-v3
```

The saved replay checks **172 instruction anchors in 51 windows**, 23 ROM
dispatch words and the fit-size rows. The 15 existing video tests and 31
CPU subset/call tests pass. No firmware image, listing instructions, camera
state or SD card was changed; the documented height override affects only
a host CPU register in one explicitly marked control case.

## November 7 follow-up: capture-state producers and the scaler dispatch

### Result and evidence boundary

The producer of **J+808 is now traced back to the acquisition callback**,
and J+902 back to its original request kind. The first global-selector
enable also has a caller: **`0x607247f2 -> 0x60726d49`**. This corrects the
previous unresolved-caller boundary. Its callable entry skips the MOVM
instruction at `0x60726d47`; searching only that address missed the call.

The same preparation routine later calls the scaler path. This establishes
a conditional local connection, **not that stock FHD60 takes it**. The
processing dispatcher has additional inputs J+268/J+800/J+896, and neither
these inputs nor the capture flag/property have been bound to an actual
ordinary FHD60 instance. No newly found selector tests 5994/6000 directly.

All findings use the unchanged E-PL9/model 1330, displayed version 1.1,
main build 1101 input identified above: container 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`;
decoded main 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`,
base `0x60400020`. Local branch/HEAD remain `main` /
`1f4dc523fc8db1a61863da66a09413627d5eb8e8`; unrelated dirty work is preserved.
These are image-derived results and bounded host executions, not camera
measurements. No firmware or camera was written.

### J+808: a cached acquisition-state flag

Let D be the acquisition descriptor at callback `0x6091b61b`, W its accepted
image-work owner, and **P = W+60**. The newly located path is:

| Stage | Native operation |
| --- | --- |
| `0x60925b0a` | Return 1 when byte `0x6261ea26` equals 1; otherwise query property `0x8551` through `0x6043e62b` and return whether its value equals 1 |
| `0x6091b397..0x6091b39e` | Cache the result as byte `0x62616d62`, during `0x6091b377` |
| `0x6091b63c..0x6091b670` | Acquisition callback snapshots that cached byte through stack +47 into word stack +16 |
| `0x6091b840..0x6091b844` | Copy the snapshot to **P+332** |
| `0x60701a4f..0x60701a55` | Copy P+332 to processing-ring **J+172** |
| `0x60715d3f..0x60715d43` | Copy J+172 to the getter's output word 0 |
| `0x606ff252..0x606ff25c` | Call that getter, then copy output word 0 into **J+808** |

Thus J+808 is not a width/height setting or a proven frame-rate bit. It is
also a **snapshot**, rather than a fresh property read on every callback.
The getter's second output word, eventually J+812, is a different value:
J+304 equal to 5, 6 or 21 produces 1; zero produces 0; other values log an
error and produce 0. Do not merge the two words' meanings.

One source-state writer is `0x60699e64`: configuration word +52 equal to 2
sets byte `0x6261ea26` to 1 at `0x60699ea9`. Startup clears it at
`0x60699df0`; a separate cleanup branch clears it at `0x6069b49a` when its
configuration +52 differs from 2. The configuration enum and property
`0x8551` have **not been named reliably**. In particular, neither is yet
established as an ordinary-FHD60 or electronic-shutter selector.

### J+902 and J+874 remain separate inputs

The callback directly copies **D+0 -> P+4** at `0x6091b82c..0x6091b831`.
The existing mapper `0x607031f0`, called at `0x60701b03`, then creates
J+902. Its supported operation inputs are:

| D+0 / P+4 | J+902 |
| ---: | ---: |
| 0 | 1 |
| 1 | 3 |
| 2 | 5 |
| 3 | 8 when P+332=0; otherwise 9 |
| 4 | 6 |
| 5 | 4 |
| 6 | 13 |
| 7 | 12 |

This closes a field-provenance gap; **it does not assign operation 4 to
ordinary video**. The callback handles other request types and has early
returns and mode-dependent acceptance tests. The host probe starts after
those decisions. Its separate call `0x60925691` converts D+0 into a request
code for filtering; that conversion must not be substituted for D+0 itself.

J+874 still comes from the camera settings/plane header, through the
32-byte mailbox at `0xa2aed574`, as described in the preceding pass.
Neither the new capture flag nor D+0 supplies that header byte. In
particular, the synthetic header-kind-6 case that yields `0x2004` is still
not a demonstrated stock FHD60 configuration.

### Who enables the global selector, and when the scaler is reached

Dispatcher `0x607235e1` calls `0x60714ff2` to classify the current J using
**J+268, J+800 and J+896**. Its native helper `0x60715009` returns:

| J+268 | If J+800 is nonzero and J+896=2 | Otherwise |
| ---: | ---: | ---: |
| 0 | 1 | 3 |
| 1 | 2 | 3 |
| 2 | 2 | 0 |
| 3 or other | 3 | 0 |

Case 0 calls **`0x607246e1`** at `0x6072367f`. Cases 1 and 2 call
`0x6072a355` and `0x6072a585`; case 3 takes a different completion/error
path. These numeric cases are not recording-mode enums. J+268 itself is
copied from P+20 at `0x607017d8..0x607017dd`; in the acquisition callback
that value depends on D+8's auxiliary record, or defaults to 3 when absent.
Its ordinary-recording instance, and producers of J+800/J+896, remain open.

In `0x607246e1`, distinguish the control request **U** (saved at stack +20)
from the render record **R** (saved at stack +24). On successful preparation,
**U's halfword +0 must equal 3** to reach `0x607247f2 -> 0x60726d49`.
That setup has more resource/state gates before `0x60726f27` sets global
`0x62a24d14` to 1. U+0=4 instead clears U+22 in this section. U+0 is neither
the plane-header kind at J+874 nor the native TG sensor-mode enum.

The later, conditional continuation in the **same routine** is now explicit:

```text
0x607246e1 preparation
  -> 0x607247f2 -> 0x60726d49 -> ... -> 0x60726f27: global = 1
  ... intervening checks and preparation ...
  -> 0x60724a13 -> 0x60724e3d
       -> 0x60724f4e -> 0x60725229
            -> conditional raster builder 0x60725560
```

Reaching the enable call does not guarantee reaching the raster builder.
The latter separately requires **R+10=2**, no preceding error, source
configuration **F+0=3**, **R+77=0**, and successful source/destination-plane
services at `0x607121bc`, `0x60711d54` and `0x6071184a`. The independent
global=1 writer beside Q construction remains as documented previously.

### Connection to the pool and the proposed height

When its own pool-selection state allows it, destination service
`0x6071184a` uses key getter `0x60719c8a` and address getter `0x60719ccb`.
The latter has native bounds checking and computes:

```text
address = 0xa45f82c0 + (key - 1) * u32[0xa2af4a00]
valid key: 1 .. u16[0xa2af4a04]; otherwise return 0
```

Initializer `0x60719c60` sets stride **1382400** and count **86**. Native
host executions verify keys 0, 1, 2, 86 and 87, including both invalid
boundaries. This does **not establish one slot as one complete movie
frame**, its pixel format, the active allocation policy or its FHD60 use.
It would be incorrect to equate this pool with the separate Q pool or
declare capacity solely by comparing a slot stride with a frame footprint.

For 1920×1440, the already tested raster override must agree with plane
offset/pitch, any intermediate allocation, command 257's source and encoder
configuration, and the active pool's actual allocation contract. A packed
8-bit 4:2:0 output would occupy **4147200 bytes**, with luma extent
**2764800 bytes**; the conditional intermediate remains **5529600 bytes**.
These are layout calculations, not measured camera allocations.

The unresolved implementation boundary is therefore concrete: bind stock
FHD60's D/header, J dispatch inputs, U and F to one source instance, then
carry an explicit 1920×1440 target through its selected raster and buffer
contract. Full-field acquisition at 60 fps is still independently
unverified; changing these output dimensions cannot restore sensor lines
already excluded upstream. TG timing and gyro/exposure-to-MOV joins are
unchanged by this pass.

### Reproduction and checks

`scripts/epl9_video_geometry_audit.py` now verifies **194 instruction anchors
in 68 byte-checked windows**, retaining all previous geometry probes. It
adds **16 capture-state propagation cases**, **3 flag-source branch cases**,
**24 processing-dispatch cases** and **5 pool-address cases**. Stage arguments
and source state are synthetic; no callback acceptance, property service,
RTOS, pixels or live recording is emulated by these additions.

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --listing-dir local/video-geometry-state-listings-20261107-v4 --out local/video-geometry-state-20261107-v6
```

The saved report and listings remain in ignored `local/`. Exact firmware
hashes and listing bytes are checked on every audit run.
The audit completed successfully; the 15 existing video-audit tests and
31 MN103 subset/call tests also pass. Targeted whitespace checks pass for
both updated files.

## November 7 follow-up: J dispatch inputs, display devices and property 0x8551

### Result

All three dispatch inputs now have concrete producers. **J+268** comes
from the acquisition auxiliary record's byte +74, **J+800** from property
**`0xf161`**, and **J+896** from the display subsystem's open-device mask.
The test for J+896=2 is associated with the **BI_EVF device family**, not
with 60 fps. The TFT device bit is 1. This materially narrows the branch
interpretation: the two alternative dispatch cases require the EVF-only
mask and nonzero `0xf161`; changing the movie frame rate alone does not
select them.

For **`0x8551`**, a precise operational role is established: value 1
enables a capture-parameter branch that reads movie preset `0xf021` and
format `0xf031`. That role does not establish whether its public/UI name
means selected movie mode, a recording state or another broader state.
The exact stock FHD60 values have still not been observed or completely
derived from the application producer. No unconditional claim about the
active primary movie scaler or full-field 60 follows from these results.

This pass uses the same unchanged **E-PL9/model 1330, displayed 1.1, main
build 1101** input: container 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`;
decoded main 26214336 bytes, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`,
analysis base `0x60400020`. Local `main`/HEAD are unchanged at
`1f4dc523fc8db1a61863da66a09413627d5eb8e8`. Other dirty work was preserved.
No camera access, property command or firmware mutation occurred.

### J+268: acquisition auxiliary kind, including the absent-record case

In callback `0x6091b61b`, D+8 points to an optional auxiliary record C.
At `0x6091b7c8..0x6091b7d2`, **C+74** is passed to `0x6091c079` and its
result retained in d3. If C is absent, `0x6091b7d5..0x6091b7d9` instead
selects 3. The callback stores d3 at **P+20** at `0x6091b83d`; the processing
builder copies it to **J+268** at `0x607017dd`.

| C+74 | J+268 |
| --- | ---: |
| 1 | 0 |
| 2 | 1 |
| 3 | 2 |
| Other byte, or no auxiliary record | 3 |

This is the native mapping. The semantic names and producer of C+74 on
ordinary FHD60 are still unresolved. The replay executes the null/present
selection and both native mappings, but starts after the callback's
acceptance/owner-allocation decisions. It does not imply that every input
combination could reach that point on a camera.

### J+800: property-copy table, not a direct field store

The missing writer was hidden behind a table-driven copy:

1. `0x606fe8c5` binds 25 property cells through `0x60715da0`, using ROM
   descriptors at **`0x608b5afc`** and a pointer vector at **`0xa2aefe7c`**.
   The binder reads each halfword property key and resolves its scalar
   data pointer with `0x6043e601`.
2. Caller `0x60700fe4..0x60700ffb` supplies **J+660** to `0x60701025`.
   At `0x60701037`, that routine invokes **`0x60715dce`** with the same
   25 descriptors and pointer vector.
3. Descriptor **20**, at **`0x608b5b9c`**, is
   `{u16 key=0xf161, u8 type=2, u8 reserved=0, u32 offset=140}`.
   Pointer vector element 20 is **`0xa2aefecc`**. The native helper reads
   a byte from that cell's data pointer and writes to destination +140.
   Since its destination is J+660, this is exactly **J+800**.

The ROM object-list record at `0x6049b464` has kind `0xf161`, count 1 and
initial scalar value 0. That is a stock initialization value, **not a
measurement or proof of its value during FHD60**. A second direct reader
at `0x606feabf` queries `0xf161` before calling the same dispatch helper,
corroborating the table's association. A public name for `0xf161` and its
ordinary-recording setter remain unresolved; describing it as a sensor
frame-rate control would exceed the evidence.

### J+896: display-open device mask

The native producer is now complete:

```text
0x606ff27b: destination = J+896
  -> 0x6071a1b9
       -> 0x605f0f9f: read u32[0xa2ae7b40]
       -> store the returned word at destination
```

The surrounding stock code identifies this as **display state**. The
request handler `0x605f0c23` logs `display_open_device req_dev`, updates
the requested-device mask at `0xa2ae7b3c`, and dispatches individual
devices. Its bit-1 branch calls `0x605f221d`, the TFT-open implementation;
bit 2 calls `0x605f1262`, in the BI_EVF implementation family. The aspect
getter `0x60557d4e` also translates device 8 to 2 with diagnostic
`ERR MODE_DISPLAY_BI_EVF`, and 16 to 4 with
`ERR MODE_DISPLAY_HDMI`. Reopening selected devices in `0x605f0987`
rebuilds the open mask `0xa2ae7b40`; other paths can clear bits.

The processing comparison is **exactly `mask == 2`**, not `mask & 2`.
For example, synthetic mask 3 does not enable these alternative cases,
even with `0xf161=1`. Presence of shared BI_EVF code in this firmware does
not demonstrate that this E-PL9 has or uses that hardware. The live device
mask during recording remains unmeasured.

### Consequence for the ordinary TFT processing path

With a **TFT-only mask of 1**, the native dispatcher has these outcomes
for either tested value of `0xf161`:

| Acquisition auxiliary input | J+268 | Dispatch case |
| --- | ---: | ---: |
| Missing C, or C+74 other than 1/2/3 | 3 | 0 |
| C+74=3 | 2 | 0 |
| C+74=1 or 2 | 0 or 1 | 3 |

Thus an accepted ordinary TFT request with J+268=2 or 3 reaches case 0:
**`0x6072367f -> 0x607246e1`**. This is a conditional statement about the
real native dispatch, not a full normal-recording run. The preceding
pass's continuation to `0x60724e3d -> 0x60725229 -> 0x60725560` remains
guarded by control request U, render R and source configuration F.
Cases 1 and 2 now have a concrete EVF-related gate; they should not be
assumed necessary for normal recording or used as a way to obtain sensor
lines that are absent upstream.

This also keeps the two geometry paths distinct. J's type/dimension
selection can serve a small fitted output; it is not automatically the
encoder's raster. The separate F+1 switch at `0x60725560` still fixes
1920×1080 for layout keys 5/6. Its destination service can reach the
`0xa45f82c0` pool through `0x60719c8a/0x60719ccb`, but its own allocation
state must be bound before calling it the active FHD60 movie pool.

### What property 0x8551 proves about movie parameters

At **`0x609237c6`**, a separate per-work byte +53 equal to 1 immediately
selects the following branch. Otherwise `0x609237d9` queries `0x8551`;
only a returned value of **1** selects it. The selected branch queries
**`0xf021`**, uses the selected preset as the index for **`0xf031`**, and
maps that format into a capture-parameter value. The unset path supplies
zero for this selection. This is direct E-PL9 code evidence that `0x8551`
participates in selecting the **movie parameter family**.

The ROM object record at `0x60478874` has kind `0x8551`, count 1 and
initial value 0. As in the previous pass, the acquisition flag getter
`0x60925b0a` additionally accepts the separate forced state
`u8[0x6261ea26]==1`; it can therefore return 1 without consulting
`0x8551`. **J+808 cannot be equated to the current raw property value.**

The supported conclusion is its movie-parameter selection role. Whether
it represents the dial's movie choice, active recording, or another
application condition is still open. In particular it does not itself
identify FHD, 60 fps, full sensor coverage or an exposure time.

### 1920×1440/60 integration boundary and verification

The useful next join is now the **TFT/case-0 acquisition instance**, its
control request U and nested configuration F. Display flags should retain
their device semantics; an explicit target raster must reach the actual
movie source, scale request, plane layout, allocation contract and encoder.
The missing application producer must establish both the active ordinary
FHD60 settings and the sensor field actually supplied at 60 fps. The FULL
TG fallback and lack of verified full-field/60 readout evidence remain.
The new display/property findings do not alter gyro timing conclusions.

The expanded geometry audit retains earlier probes and adds **36 joined
native producer-to-dispatch cases** and **4 movie-property gate cases**.
The former execute the auxiliary mappings, table-driven scalar copies,
display-mask snapshot and native dispatcher on shared host memory. The
latter explicitly inject a property-service return at its boundary; no
property service or camera is emulated. Host property-cell pointers,
auxiliary records and display masks are synthetic inputs. These probes
are not an uninterrupted RTOS or physical recording execution.

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --listing-dir local/video-geometry-device-listings-20261107-v1 --out local/video-geometry-device-20261107-v1
```

The saved report checks **213 instruction anchors in 85 byte-checked
windows**, the 25 settings-copy descriptors and both object-list defaults,
in addition to previous ROM checks. It remains under ignored `local/`.
The final repeated audit is `local/video-geometry-device-20261107-v2/`:
all comparisons pass. The 15 existing video-audit tests and 31 MN103
subset/call tests pass; targeted whitespace checks pass for the two
updated research files. No changes were staged or published.

## November 7 follow-up: source configuration and resource-backed pixel buffers

This pass identifies the producer of the nested source configuration and
the resource objects used by one destination-buffer branch. It does **not**
yet identify every live setting of an ordinary TFT/FHD60 session. The new
native replays have explicit synthetic metadata, property returns and slot
occupancy. There is no camera access, changed firmware image or recording.

Exact input remains Olympus PEN E-PL9, model 1330, owner-reported displayed
version 1.1, downloaded stock main build 1101:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| Decoded main `00_0100_406e0020.decoded.bin`, base `0x60400020` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |

These are stock-download identities, not a readback of the installed body.

### J now reaches the source configuration F

The earlier TFT result remains conditional: display-open mask 1 selects the
non-EVF dispatch rule; with J+268 equal to 2 or 3 it reaches case 0 and
`0x607246e1`. TFT alone does not select that case, the processing-enable
state, a movie format, or a frame rate.

The missing configuration producer is **`0x6072818d`**, called at body
entry `0x60728192` by state-table handler **`0x6072a2e0`**. Its handler
pointer occurs at ROM `0x608b8b20`. The routine obtains J through
`0x606ff32c(1)`, refreshes its acquisition/header information through
`0x606ff1c1` and, on success, `0x606ffdbe`, then builds static G at
**`0x62a25cfc`**:

| Configuration field | Producer input | Source publication |
| --- | --- | --- |
| G+0 | J+818 | F+0 at `0xa2af3e6a` |
| G+1 | J+874, acquisition header kind | F+1, the conditional raster layout selector |
| G+2 | J+824 | F+2 |
| G+4 halfword | J+822 when G+0 != 1; separate helper for family 1 | Truncated to byte F+6 |
| G+8/+9 | J+291/+292 | F+3/+4 |
| G+14 halfword | J+798 | F+8 halfword |
| G+18 | J+903 | F+12 |

The family is not supplied by the TFT mask. Movie metadata builder
`0x60702f7d`, called by `0x607006fe`, reads selected preset `0xf021`, then
`0xf031[preset]` into N+28 and **`0xf051[preset]` into N+29**. Header
construction copies N+29 to J+796 at `0x6070108a`; `0x606ff223` forwards it
to J+818. Consequently **F+0 derives from the selected `0xf051` family**.
Family 3 invokes source initialization `0x60710c4c`, while family 1 invokes
`0x6070e6e5`. The public name of `0xf051` and its actual selected value in
the owner's ordinary FHD60 configuration are still open. J+798/G+14 is
not assigned a frame-rate meaning here.

The message association is now explicit:

1. `0x6072848e..496` sends command **1** with d1=G through
   `0x60723d11`. The sender's **16-byte message** has command at +8 and
   **G pointer at +12**; destination queue ID is read from `0x60421336`.
2. Source mapper `0x6072af5b` accepts that queue and maps command 1 through
   ROM `0x608baca4` to `0x6072afd1`. This branch retains event **0**.
3. Source state/event dispatch uses ROM base `0x608b9d24`, a 224-byte row
   per state and an 8-byte entry per event. State 0/event 0 contains handler
   **`0x6072beb8`**.
4. That handler reads message +12 at `0x6072bef3` and calls
   `0x6071382b(G)`. On its accepted family/initialization path,
   `0x6071388a -> 0x60714652` publishes F.

The source configuration is therefore connected to the earlier F consumer.
The RTOS transition selecting the MaRS producer and the concrete values
of selected movie properties for ordinary FHD60 remain outside the replay.
Another producer at `0x60728fd3` has explicit 5/10/15/30 rate acceptance;
it must not be used as evidence for the requested 60 fps path.

### The cyclic-pool switch comes from a special preset selector

The source's destination-buffer gate `u32[0xa2af3c80]` is now traced back
to the processing header:

```text
selected preset -> 0x60715ee5 -> J+670
  -> stack parameter record +8 in 0x6072843a..46d
  -> 0x60714037 -> 0x6071475c -> u16[0xa2af3eb6]
  = L+58, where L = 0xa2af3e7c from 0x607147a6
  -> 0x6072c15c -> d1 of 0x60710c74
  -> u32[0xa2af3c80] at 0x60710c8e
```

With no explicit override record (`d3==0` at `0x60701148`), helper
**`0x60715ee5` returns zero for every preset other than 8**. For preset 8
it reads `0xf072[8]`: values 25, 12 and 6 map to 120, 240 and 480;
other values log an error and leave the result zero. These are observed
numeric transformations, not a measurement of sensor rates. With an
override record, `0x60701199` copies its +6 halfword to J+670 instead.
The ordinary-session absence of that override is not yet established.

The source-start consumer also has gates: family 3, successful earlier
status and source-context +24 equal to 1 before `0x6072c160`. Family-3
initialization clears the old pool gate; the later start sets it from L+58.

Thus the 1382400-byte cyclic stride previously found is **not a general
FHD60 frame-allocation limit**. It belongs to the nonzero-gate destination
branch. For a non-8 preset without an override the traced selector is zero
and destination service `0x6071184a(d0=0)` instead takes a resource branch.
This conditional distinction does not establish which preset is live on
the camera.

### Resource-backed destinations have concrete stock objects and strides

When the gate is zero, `0x607118fa` reads F+1. Layout 8 requests resource
class **`0x5600`**, and the other layouts request **`0x2f00`**. These are
resource identifiers, not byte sizes. `0x60719509` asks the resource
manager for a handle; `0x607196ee -> 0x607c56b5` resolves its address.
On success the destination record gets its handle at +26 and address at
+12. Both manager errors and source-start errors must remain respected.

The resource registry and constructors now identify the sizes independently
of the separate Q route:

| Class | Registry entry | Object | Constructor setup | Base | Slot stride | Count |
| --- | --- | --- | --- | --- | ---: | ---: |
| `0x2f00` | `0x60908ad4` | `0xa2a5a220` | `0x607c4e79..e9b` | `0xa45f82c0` | 3133440 | 9 |
| `0x5600` | `0x60908c0c` | `0xa2a5ba78` | `0x607c5e13..e35` | `0xa45f82c0` | 13271040 | 9 |

Constructor `0x607c756e -> 0x607c6d44` stores base at object +8, stride at
+12, class at +22 and count at +24. The derived vtable is `0x60908f84`;
its +8 method `0x607c7737` calculates **base + (low-byte(handle)-1) ×
stride**. This verifies that the constructor's d1 is used as the slot
address step. A synthetic occupied slot returns status 0. An unowned or
out-of-count slot can still produce an address with status 2; the caller's
status check is essential. A calculated address alone is not an allocated
or valid movie buffer.

These are stock initialization fragments and handle/address consumers.
The full constructor's software dependencies, allocator lifecycle,
subsequent reconfiguration, simultaneous owners and DMA are not executed
or proven by the probe. The common base does **not** mean both pool layouts
can be active together. No claim of Q aliasing follows from matching size
constants.

### Consequences for 1920×1440/60

The native shared-memory replay now joins supplied movie family 3 and
camera header kind 5/6 through J, G and F to the existing raster consumer.
It returns **1920×1080**, with a **2088960-byte luma-plane delta**, matching
1920×1088 padding. Resource class `0x2f00`'s 3133440-byte step equals that
delta × 3/2. This is a consistent conditional FHD420 layout, not proof of
all acceptance gates or an actual FHD60 instance.

For the target, coordinated geometry must provide at least:

| Quantity | Existing FHD candidate | Target candidate |
| --- | ---: | ---: |
| Raster | 1920×1080 | 1920×1440 |
| Luma-plane extent | 2088960, padded height 1088 | 2764800, height 1440 |
| Packed 4:2:0 frame extent | 3133440 with existing padding | 4147200 minimum |
| Nine such slots | 28200960 | 37324800 minimum |
| Optional 2×pitch×height intermediate | 4147200 | 5529600 |

Simply changing the raster leaves the candidate target frame **1013760
bytes larger than the stock `0x2f00` slot**. Changing its stride also moves
every subsequent slot; preserving nine requires 9123840 more bytes before
other alignment/metadata requirements. The memory map and live owners must
be reconciled before choosing a new count or base.

The larger stock `0x5600` class is a concrete **allocation alternative to
investigate**, since its stride exceeds the target extent. Its shared base,
ownership and lifetime must first be checked. Setting F+1 to 8 merely to
obtain it is insufficient: the same selector makes the raster consumer
produce 3840×2160. Allocation class and intended raster would need an
explicitly coordinated change; these findings are not a ready patch.

Remaining joins, in priority order for this video investigation:

1. Bind the MaRS state/event and ordinary FHD60 property/override values to
   the TFT/case-0 source instance, including the processing-enable gate and
   raster acceptance conditions. Current probes deliberately label this
   binding unverified.
2. Close that instance's input crop, scale-job configuration, destination
   allocation/release, encoder input and completed pixel identity. The
   generic scaler request copies dimensions; its actual full-field FHD60
   input and hardware schedule are still missing.
3. Reconcile all 1440-line geometry, plane extents, optional intermediate,
   resource count/ranges and encoder output/SPS/MOV fields. Preserve callbacks
   and all error/ownership checks.
4. Establish actual full usable 4:3 sensor readout at 60 fps. The native FULL
   TG fallback still does not prove this, regardless of downstream capacity.

The exposure/pixel-generation/MOV PTS/CTTS association and gyro clock join
remain open; these geometry findings do not change their status.

### Reproducible offline checks

`scripts/epl9_video_geometry_audit.py` now verifies **240 instruction anchors
in 115 byte-checked windows**, plus the new source-message/resource ROM
words. It retains all earlier geometry, dispatch and header checks and adds:

- **21 source-configuration cases:** supplied family 3, layout 5/6/8,
  presets 0/1/7/9 and preset 8 with three declared property returns; native
  copies and selector calls run on shared host memory through G/F, the
  live-context pool gate and conditional raster.
- **10 resource-definition/address cases:** both classes, constructor
  arguments and base-field stores, occupied keys 1/2/9 and invalid/unowned
  keys 0/10. Constructor execution stops before its memset dependency;
  a separate native fragment installs the derived vtable. No allocator or
  physical memory initialization is claimed.

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --listing-dir local/video-geometry-source-listings-20261107-v1 --out local/video-geometry-source-20261107-v2
```

The ignored report `local/video-geometry-source-20261107-v2/audit.json`
passes every comparison. The 15 video-audit tests and 31 MN103 subset/call
tests also pass. Firmware and package inputs remain unchanged; no camera
commands, staging or publication occurred.

## November 10 follow-up: recording command binding and overlapping resource pools

The source-configuration producer now has a specific public recording
command association. The larger pool also passes native allocation,
address-resolution and release controls. However, those same controls
show why a larger slot cannot be selected safely on size alone: the FHD
and 4K classes can both allocate the same physical address using separate
ownership bitmaps. The ordinary TFT/FHD60 property/state instance and
external exclusion of overlapping memory remain unverified.

This is continued offline analysis of the **same E-PL9 model 1330,
displayed 1.1, stock main build 1101** inputs identified in the preceding
section: container 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`;
decoded main 26214336 bytes, base `0x60400020`, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
No camera, network, modified firmware image or package was used.

### Public recording command 16 reaches the source setup callback

The precise command is **16**. An intermediate work update incorrectly
called it 3; 3 is not the command-table entry for this event.

At **`0x6067b070..07a`**, the application path reads queue ID from
`0x60421332`, sets d1=16, passes its request in a0 and calls
`0x6091abd2`. That adapter either calls the common sender
`0x60434a21`, or uses `0x605fa059` for the special calling-task case.
This is the same larger application path that prepares recording data
and then conditionally calls `0x6067ffd3` after success.

The processor's public command mapper `0x607236f8` uses ROM table
`0x608b9a98`. Entry **16**, at **`0x608b9ad4`**, is `0x60723740`;
its branch assigns **event 2** at `0x6072374f`.
Do not confuse this public command table with the different table at
`0x608b9a08` for the processing-completion queue.

The MaRS dispatcher uses `0x608b88ac + state*304 + event*8`.
For **state 2/event 2**, the first callback at `0x608b8b1c` is zero;
the second at **`0x608b8b20`** is **`0x6072a2e0`**. Native dispatcher
fragments select this second callback; it calls `0x60728192`, the G
producer traced in the previous pass. States 0, 1 and 3 have no callback
for this event in the tested cells.

```text
application recording preparation
  -> public queue [0x60421332], command 16
  -> public command table, event 2
  -> MaRS state 2, second callback 0x6072a2e0
  -> 0x60728192 builds G
  -> source command 1, state 0/event 0
  -> 0x6071382b -> 0x60714652 publishes F
```

State 2 has a concrete writer at `0x60728e83..e87`, in callback
`0x60728deb`. It is conditional on earlier status and reply-kind checks;
its first application initialization callback `0x607280cb` instead writes
state 1. Therefore replaying event 2 with a supplied state 2 is **not** an
execution of all initialization/transitions into that state.

This closes the local public-command-to-source-producer association.
It does not close the complete active FHD60 path: the actual movie family,
camera header kind, optional override and accepted acquisition auxiliary
kind still need to be established together with the TFT mask. The earlier
TFT/case-0 rule and FHD5/6 raster results remain conditional. No new probe
labels the owner's live session or physical sensor readout as verified.

### The stock allocator does not enforce exclusion between these classes

Resource manager `0x607c5453` selects the object by the high byte of the
requested class using registry `0x6090895c`. It calls the object's
allocator `0x607c6dcd`, which checks its own free count and slot bitmap,
returns a class-prefixed handle, decrements its free count and increments
its own slot reference byte. Manager `0x607c56b5` resolves the handle
through the virtual address method. Native release
`0x607c554a -> 0x607c6ea7 -> 0x607c7913` clears that object's ownership
and restores its count. Thus a `0x56xx` handle retains its class through
these tested generic allocation/address/release fragments.

The replay supplies two explicit initialized-object snapshots, with the
constructor-checked base, stride, class, count=9, zero ownership, zero
object lock word and disabled diagnostic flags. It executes the native
manager and virtual methods, not a Python allocator. In both request
orders the results are:

| Requested class | Native handle | Native resolved address | Allocation status |
| --- | --- | --- | --- |
| FHD `0x2f00` | `0x2f01` | `0xa45f82c0` | success |
| Larger `0x5600` | `0x5601` | `0xa45f82c0` | success |

Releasing the two handles succeeds and restores each free count to 9.
This is a **counterexample to cross-class exclusion inside these leaves**.
It is not an observed simultaneous allocation during a real recording and
does not show that the stock application permits that sequence.
Diagnostic gate `0x607c4671` and object flag getter `0x607c713d` do not
provide cross-object memory ownership in this tested branch.

Both constructor groups occur in the same ROM initializer list:
`0x6092c684 -> 0x607c4df1` for the group containing `0x2f00`, and
`0x6092c694 -> 0x607c5deb` for the group containing `0x5600`.
The initializer-list loop is at `0x6056839a`. This identifies their
initialization mechanism; it does not execute startup or prove the
current objects' lifetime on the camera.

Their full nine-slot address ranges, with exclusive ends, are:

| Class | Base | End | Reserved slot extents |
| --- | --- | --- | ---: |
| `0x2f00` | `0xa45f82c0` | `0xa60dd2c0` | 28200960 bytes |
| `0x5600` | `0xa45f82c0` | `0xab7e02c0` | 119439360 bytes |

Other stock constructor ranges overlap this area too. For example,
`0x607c4ea0..ec2` initializes class `0x3000` at `0xa4f816c0`, with
8294400-byte stride and count 18. This is a static overlapping reservation,
not evidence of an application bug or concurrent ownership. It reinforces
the need to trace the active memory mode and users before repurposing it.

### What the larger pool can and cannot establish for the target

The `0x5600` slot's 13271040-byte stride exceeds both the 4147200-byte
minimum target YUV420 frame and the 5529600-byte optional intermediate.
That is a capacity comparison; those two objects may have distinct
lifetimes and cannot automatically share one allocation.

There is a concrete generic handle lifecycle compatible with this class.
However, the current FHD layout 5/6 destination selector requests `0x2f00`;
layout 8 requests `0x5600` and also selects a 3840×2160 raster. A proposed
1920×1440 integration must independently coordinate the resource class
and raster/plane geometry and prove the completed buffer reaches the
encoder. It must preserve the native status and reference-count checks.

**Current verdict:** reusing the larger pool remains a plausible candidate,
but a direct class substitution is not qualified. It requires exclusion
of other owners of its overlapping range, a compatible active memory mode,
correct downstream ownership/release and the 1440-line scaler/encoder
configuration. Allocation success alone now has an explicit counterexample
as a safety criterion. Full-field sensor input at 60 fps remains a separate
unresolved requirement; neither this pool nor the command association
supplies a new sensor schedule. Gyro/exposure/MOV synchronization is unchanged.

### Verification

The expanded geometry audit checks **246 instruction anchors in 131
byte-checked windows** and the new public command, callback, registry,
virtual-method and initializer-list ROM words. Earlier probes remain.
Four new state-selection cases test state 2 versus 0/1/3; two new manager
sequences execute both class orders and release the allocations.
Synthetic object initialization and diagnostic state are explicit; no
kernel startup, RTOS recording session, DMA or pixel writes are modeled.

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --listing-dir local/video-geometry-pool-listings-20261110-v1 --out local/video-geometry-pool-20261110-v2
```

The saved ignored report passes. The 31 MN103 subset/call tests pass.
The standard video-test invocation initially hit a Windows sandbox ACL
error creating the disposable synthetic input in Python's owner-only
temporary folder. All 15 video tests then passed in a host harness that
uses inherited workspace ACLs for those temporary directories (mkdir mode
0777 instead of 0700). Test sources and assertions were unchanged. This
workaround is limited to synthetic temporary files, not firmware or camera
permissions. No files were staged or published.

## November 10 follow-up: ART/ISO ownership and a smaller-footprint target pool

The newly investigated global image-work mode is **not identified as the
FHD/4K selector**. Its named objects are ART and ISO working memory. It
does expose another owner overlapping the larger video pool, and a
deferred-release mechanism. The specific application invariant excluding
all simultaneous FHD/4K owners is still not closed.

This pass uses the same exact downloaded E-PL9/model 1330, displayed 1.1,
main build 1101 inputs: container 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`;
decoded main 26214336 bytes, base `0x60400020`, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
No camera access, firmware/package mutation or network lookup occurred.

### What the image-work mode actually controls

Setter **`0x607c5f0b`** accepts mode 0/1/2 and stores the requested value
in `u16[0xa2a5c0a4]`. Allocation state uses a separate mode snapshot at
`0xa2a5c0a6` and flags at `0xa2a5c0a8`; they must not be conflated.
The path obtains lock ID `0x201` through `0x607c6b95`, updates parent
reservation through `0x607c5bf0`, and checks outstanding image-work
allocations through `0x607c6075`. It does not directly iterate the
`0x2f00` or `0x5600` slot bitmaps.

`0x607c6075` indexes the pointer pair at **`0x60908c78`**:

| Index | Object | Stock base | Stock extent | Named role |
| --- | --- | --- | ---: | --- |
| 0 | `0xa2a5c0ac` | `0xa8d62ec0` | 206209024 | ART working memory |
| 1 | `0xa2a5c100` | `0xb084bec0` | 77328384 | ISO working memory |

Constructor `0x607c6402` initializes these objects through `0x607c3db6`.
ROM immediately following the pointer table contains the diagnostic names
`BUFF_IMGWORK_MEMORY_ART` and `BUFF_IMGWORK_MEMORY_ISO`.
Mode 1 selects pointer index 0; the other branch selects index 1 at
`0x607c6130..63b`. The busy-count function itself takes the **pointer
index**, not the public mode: 0 and 1 are valid, whereas index >=2 returns
zero. This is another distinct enum boundary.

Native helper `0x607c3fef` computes **object halfword +16 minus halfword
+80**, the outstanding count checked here. In the setter, a nonzero count
causes bit 1 (`0x2`) to be set in flags `0xa2a5c0a8`; it does not prove
the old owner has been released. When the count is zero and the old
reservation flag is present, the setter calls `0x607c5bc5`. The later
release path `0x607c63ce..3f1` rechecks the count before releasing that
reservation and clearing flags. These are concrete **deferred image-work
handover fragments**, not a completed movie drain or exclusion proof.

Six native busy-count controls cover indices 0/1/2 with supplied outstanding
counts 0/5. The FHD/4K coallocation controls were also repeated with
supplied global image-work mode snapshots 0/1/2. Both classes still
allocate the shared first address and release successfully in all six
order/mode combinations. This confirms that **changing those mode words
alone does not add cross-class exclusion to the tested allocator leaves**.
The mode setter, parent reservation and kernel lock are not executed by
the coallocation controls; no full mode-transition claim follows.

### The ART working region overlaps later 4K slots

Both image-work ranges end at `0xb520aec0`. The ART range intersects
`0x5600` slots 6 through 9: slot 6 intersects by 4740096 bytes and slots
7/8/9 each intersect by their full 13271040-byte extent. ISO working
memory begins beyond the end of the nine-slot `0x5600` reservation.

These are address-interval calculations from verified constructor constants.
They do not establish ART activity during ordinary FHD60, or simultaneous
allocation in stock firmware. They show why qualifying the larger pool
requires more than draining the small FHD pool: image-work owners and
other overlapping stock pools must be reconciled too. The known generic
resource allocator does not check these physical intersections.

### A target candidate within the old FHD reservation

There is a second memory candidate to investigate: retain class `0x2f00`
and its base, change the **host candidate** stride to 4147200 and reduce
the count from 9 to **6**. This is an offline object configuration, not
an emitted patch or selected native recording mode.

| Configuration | Stride | Count | Total slot extent |
| --- | ---: | ---: | ---: |
| Stock FHD constructor | 3133440 | 9 | 28200960 |
| Target candidate | 4147200 | 6 | 24883200 |

The candidate remains inside the original FHD address interval, leaving
3317760 bytes of its extent unused. Thus it does not enlarge that
particular memory reservation or adopt the much wider 4K range. It still
inherits all original FHD ownership assumptions and other overlapping
uses; a smaller footprint alone is not a safety proof.

The native pool leaves were executed with the six-slot host object:

- Six allocations return handles `0x2f01..0x2f06`; native address
  calculation advances by 4147200 bytes without intersecting adjacent slots.
- The seventh allocation returns native status 1 (no free slot).
- Native reference release returns the free count to six and clears the
  bitmap; the next allocation reuses `0x2f01` successfully.

This establishes that the generic native pool logic is not intrinsically
fixed at nine slots. **It does not establish that the movie pipeline can
run at 60 fps with six available buffers.** Encoder reordering, retained
frames, simultaneous scaler jobs, completion delays and backpressure may
require more. The optional 5529600-byte intermediate must also be placed
and owned separately; it is not covered by this six-frame calculation.
Any reinitialization would require a drained pool with no outstanding
handles, references or DMA; it cannot be applied to live allocated slots.

### Active TFT/FHD60 boundary

The public command-16/event-2/source-configuration association from the
preceding pass remains verified locally. The native TFT dispatch rule,
movie-family copy, conditional FHD5/6 geometry and resource selector also
remain valid. This pass does **not** supply the missing runtime values
that select all of them in one ordinary FHD60 instance. In particular,
an ART/ISO memory mode must not be relabelled as that missing video mode.

The unresolved integration checks are now more specific:

1. Identify the application's exclusion/drain invariant for resource
   classes `0x2f00`, `0x5600` and overlapping working objects, preserving
   the deferred release/status behavior above.
2. Join selected movie properties, acquisition header/auxiliary kind,
   TFT dispatch and enabled scaler in the same FHD60 instance.
3. Compare the larger-pool option against a six-slot target in the old
   FHD footprint, including actual pipeline occupancy and all 1440-line
   plane/intermediate/encoder layouts.
4. Establish full-field 4:3 sensor readout at 60 fps. Neither memory
   candidate changes the unverified TG/readout schedule or gyro timing.

### Verification

The geometry audit now passes **253 instruction anchors in 135 byte-checked
windows**, plus existing ROM checks. It adds six ART/ISO busy-count cases,
extends coallocation/release to six class-order/mode cases, and executes
the candidate six-slot allocation/exhaustion/release/recycle lifecycle.
All candidate state and absent kernel/startup dependencies are explicit.
The 31 MN103 subset/call tests pass. No unrelated tests were modified.

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --listing-dir local/video-geometry-ownership-listings-20261110-v1 --out local/video-geometry-ownership-20261110-v2
```

Results are retained under ignored `local/`; nothing was staged or published.

## November 10 follow-up: source retention, codec counts and final cleanup

**Six target buffers are still not qualified for 60 fps.** This pass reaches
the source's nine-record ownership layer above the generic pool and identifies
its last-return and retained-frame conditions. It also distinguishes normal
reclamation from final cleanup, which relies on an earlier quiescence contract.
The missing bound is the number of distinct input pixel buffers retained across
the actual source/codec instance, not the number of generic slots it can create.

The inputs remain E-PL9/model 1330, displayed 1.1, stock main build 1101:
container 104552480 bytes, SHA-256
`aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`;
decoded main 26214336 bytes, base `0x60400020`, SHA-256
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
All replay state is host-owned; no camera commands, recordings, firmware or
package changes occurred.

### A pool slot has another source-level owner

The noncyclic destination branch registers allocated frame handles in a
**nine-entry array at `0xa2af3ac8`, stride 12**, at `0x60711987..9bf`.
Each record has a handle at +0, pixel address at +4 and state word at +8.
Separate bytes at **`0xa2af3c64 + index`** track returns/retention, and
**`0xa2af3c6d`** selects the retained source record. The initial value 8 is
a record index, not an assertion that eight buffers are occupied.

`0x60712733` reads that selected record; its noncyclic branch writes state
2 and the supplied byte count to the per-record byte at `0x60712773..778`.
The alternate selector `0x60712643` finds a handle in the nine records,
changes the selected index, and can mark the old record state 1 if it has
a handle and its retention byte is zero. Thus preserving the old pixel
address can keep an allocation unavailable after one supply notification.

The return handler **`0x6072caf4`** reaches **`0x607116c6`** through the
received request/descriptor. That function finds a matching pixel address.
Its tested local last-return fragment has these conditions:

| Retention byte before return | Record selected? | Result |
| --- | --- | --- |
| >1 | Either | Decrement byte; leave record state unchanged |
| <=1 | Yes | Clear byte; leave record state unchanged |
| <=1 | No | Clear byte; mark state 1 |

Normal reclamation **`0x60711b03`**, with cyclic gate zero and d0=0, scans
the nine records. Only **state word +8 == 1** reaches
`0x607195a6` to release the resource handle. The record's handle/address/state
are cleared only after successful release. The second d0=1 branch scans a
different 25-record array at `0xa2af3b34`, used by another destination class;
it must not be counted as 25 additional full-resolution FHD frame buffers.

The 18 new return-fragment cases cover retention bytes 1/2/3, selected
indices 0/8 and tested record indices 0/5/8. Nine sweep cases test states
0/1/2 at those indices. They verify the native local gates, not delivery
of callbacks during an actual ordinary FHD60 session.

### Codec metadata/reordering does not directly supply a pixel-hold bound

The encoder input routine `0x616a9e31` acquires an input packet through
`0x6169e6e2`; later paths return packets through virtual buffer interfaces.
The codec's 40-byte metadata ring, its wrap limit and MOV CTTS are distinct
from the application source's pixel-slot ownership. Neither the ring's
entry count nor the three-frame CTTS offsets of the checked MOV prove a
three-pixel-buffer retention bound.

One explicit codec count helper, **`0x6169e6a9`**, now has native controls:
it returns 0 unless object +200==1 and +100!=2. In that branch it returns
2 when +168==0, +156==1 and +56==0; otherwise it returns 6. Field +216==1
doubles the result, allowing 4 or 12. Callers include `0x6169cae2`,
`0x616a1803` and `0x616a21cc`; the last stores it into +12 of a separate
44-byte driver/configuration record.

Eight probes preserve these arithmetic branches. **The public meanings
of these fields and this count's relationship to simultaneous raw input
pixels are not established here.** In particular, finding the constant 6
does not qualify a six-slot movie pool, and finding 12 does not prove that
ordinary FHD60 requires twelve full source frames.

For a six-slot candidate, before allocating a fresh destination the union
of all still-owned source pixel slots must contain at most **five distinct
slots**, and the pipeline must return progress under that limit. This union
includes the retained source frame, processing/DMA jobs, queued inputs and
codec-held input packets. Multiple references to the same slot count as one
occupied slot, while one supply ordinal need not mean a newly written slot.
The maximum union and its progress/backpressure behavior remain unknown.
The nine-record source table is a capacity, not proof that all nine are
simultaneously necessary.

### Final source cleanup has a different precondition

ROM cell **`0x608ba448`** selects source callback **`0x6072c7f6`** as the
second callback for **state 8/event 4**. Source command **4** maps to event
4 through `0x6072affb`; public command 16 from the previous pass is a
different command namespace.

When source-context +24==1, this callback calls:

```text
0x6071131d       source request/completion operations
0x60707429       conditional processing completion/teardown
0x60711c3c       final resource-record cleanup
state := 0      then sends completion
```

`0x6071131d` sends operations 5 and 6 using queue-ID storage `0x60421340`,
via `0x60718c12`, followed on successful submission by `0x60718e02`.
`0x60707429` conditionally calls `0x6071c52f`. The meanings and full downstream
completion barriers of these calls remain open; their names above describe
control-flow roles, not proven hardware/DMA quiescence.

Unlike normal reclamation, **`0x60711c3c` frees each nonzero handle without
checking the record's state, retention byte or selected index**. It scans
both arrays and respects individual release failures when clearing records.
Nine final-cleanup gate probes reach the release call even with a selected
record, state 2 and a supplied retention byte of 3. This is evidence that
final cleanup requires an **external drain/quiescence precondition**.

The state-8 callback logs and records errors from earlier stages but still
continues toward final cleanup and the state reset. Therefore observing state
0, a cleanup invocation or a completion event alone does not establish that
every previous operation succeeded or that all owners are drained. The
caller's status handling and actual completion guarantees must be traced
before reinitializing either overlapping pool.

This narrows the release conditions but does not establish exclusion of
`0x2f00`, `0x5600` and ART/ISO owners in the active TFT/FHD60 instance.
A qualified switch must first stop new submissions, complete processing
and codec uses, account for retained frames and returned references, verify
release status and zero outstanding owners, then change the geometry/pool
configuration. This is the required integration contract, not an installed
drain implementation. Full-field sensor readout at 60 fps remains unproved.

### Verification

The saved geometry audit passes **264 anchors in 142 byte-checked windows**,
with all earlier probes retained. New controls total **44**: 18 return
reference gates, 9 normal sweep gates, 8 conditional codec-count cases and
9 final-cleanup gates. Native release calls in the two gate probes are
boundaries, not mocked successful services. The earlier generic-pool
allocation/release/recycle controls remain separately valid.
The 31 MN103 subset/call tests pass.

```powershell
.venv/Scripts/python.exe scripts/epl9_video_geometry_audit.py --listing-dir local/video-geometry-holds-listings-20261110-v1 --out local/video-geometry-holds-20261110-v2
```

The report remains in ignored `local/`; no files were staged or published.
