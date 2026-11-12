# OpenGate: practical signal-free parameter experiment, 2026-11-12

## What ran

`epl9_opengate_parameter_experiment.py` ran original, byte-checked E-PL9
1.1/build1101 MN103 fragments in the existing bounded CPU interpreter.
142 windows and 264 instruction anchors were checked against decoded main
SHA256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
The reader is qualified separately; its hash and this script's hash are in
[the scalar/trace receipt](evidence/opengate-parameter-experiment-20261112.json).
No OEM bytes, image, frames or disassembly are included in the receipt.

This is **not** a connected boot-to-record run. Host objects are supplied at
reviewed entry boundaries; geometry, aspect, render, MOV and pool probes are
independently entered. There is no sensor, ISP, encoder, DMA, interrupt cadence,
clock or SD model. Frames generated: **0**. Measured camera fps: **none**.
No firmware image or frozen Gold/Portra candidate changed. `install_ready=false`.

## Results

30 geometry/rate/bitrate cases cover FHD, target 1920x1440, 1536x1152, UHD,
and odd 1921x1441; rate keys 2997, 5994, 6000; bitrate arguments 30M and 60M.
The native configuration copies retain the supplied dimensions and rate keys.
Native alignment rounds geometry to 16-pixel units. These are configuration
results, not accepted sensor modes.

| Host input, rate key 6000 | Native class | Macroblocks/frame | Nominal macroblocks/s | Selected table budget |
|---|---:|---:|---:|---:|
| 1920x1080, 30M | 6 | 8160 | 489600 | 522240 |
| 1920x1440, 30M | 6 | 10800 | 648000 | 522240 |
| 1920x1440, 60M | 7 | 10800 | 648000 | 589824 |

**Raising bitrate alone does not eliminate the table-budget mismatch for
1440/60.** These internal classes/budgets are not proven AVC levels or physical
throughput ceilings. This result neither proves impossibility nor permits a
ready-to-flash 60fps claim. 30fps cases are controls, not a replacement target.

Aspect helper: ID1 preserves 1920x1440; ID2 gives 1920x1280; ID3 gives
1920x1080; ID4 gives 1440x1440. A declared host-only ID3 table shadow gives
1920x1440. Changing a crop descriptor does not establish full-field readout.
Receiver copies, conditional render planes and MOV dimension copies also run;
MOV avcC uses an explicitly supplied synthetic SPS prefix, not encoder output.

Six host-configured 4,147,200-byte slots fit in the arithmetic footprint of
nine stock 3,133,440-byte slots: 24,883,200 versus 28,200,960 bytes. Native
allocation returns six handles, rejects the seventh, releases all and reuses
the first. This does not allocate camera memory, establish DMA ownership,
prove six buffers suffice or produce pixel contents. Alignment, pending owners,
source/destination aliasing and runtime pool binding remain separate questions.

Three invalid dimension/rate cases are rejected by the **host validator**, not
camera firmware. A deliberately unprovisioned driver continuation stops on
unmapped address zero at 0x6169f4f2. This is a negative fixture control, not an
observed camera failure or a complete driver-open execution.

During probe development unsupported aspect ID0 and render selector0 stopped
at missing context/unsupported branch respectively. Final comparisons use
reviewed aspect IDs1–4 and render selectors5/6/8. No missing hardware call was
replaced with fabricated success to obtain these results.

## Reproduction

Supply your own exact decoded main privately, and build/qualify the GNU reader
using the repository's tooling instructions. Then:

```
python scripts/epl9_opengate_parameter_experiment.py \
  --main /private/path/main.bin \
  --out local/opengate-parameter-new-run/result.json
```

The output must not already exist. The script checks exact input hash and size,
reader identity, instruction bytes/anchors and key regression assertions.
It does not modify the input or connect to a camera.

## Next useful experiment

Connect the actual caller-owned source and driver objects rather than combining
independent success receipts. Track slot plus write generation and capture/
exposure key through source, completion, encoder and MOV; exercise exhaustion,
stop and reset without inventing a completion. Then identify the sensor schedule
and physical clock parent/divider. A surviving size copy is not evidence for
full-sensor 4:3 at 60fps.

## Caduceus atlas and gyro follow-up

Inspected upstream [ATLAS.md](https://github.com/cakelesscoder/caduceus-ep7/blob/main/docs/ATLAS.md)
on 2026-11-12: the document reports 766 symbols, including 137 static tasks.
Its Git blob is `0dbb88e2617cbed72d1f6fee37c8f3d7e7b9f9d3`.
It distinguishes code/emulator evidence from camera evidence and inference;
all addresses belong to E-P7, not E-PL9. Most useful transfer is the **method**:
settings message -> live-view/movie record -> constructor -> stage list ->
request pack, with a confidence/source tag at each edge. A table of names is
not automatic full firmware emulation.

The inspected atlas does not describe raw gyro acquisition or a gyro timestamp
stream. Its orientation getter/rotation task is not interchangeable with a
high-rate gyro logger. [VIDEO_HIDDEN.md](https://github.com/cakelesscoder/caduceus-ep7/blob/main/docs/VIDEO_HIDDEN.md)
(blob `4043cbe91ec39244ce66ce3b10b6160401741f74`) still separates hidden menu
values from an established sensor/encoder configuration. It does not supply an
E-PL9 OpenGate schedule or validate restoring a hung E-PL9.

Our [gyro findings](epl9-gyro-logging.md) remain: sequential diagnostic axis reads
are not simultaneous, CSV counter is not a timestamp, and diagnostic selector150
changes state. Do not invoke that routine as a passive movie logger. Next raw
work must resolve the auxiliary processor timer clock and cross-clock mapping,
carry per-axis completion timestamps and lost-sample markers, and join them to
actual exposure identity. No newly measured gyro frequency is claimed here.
