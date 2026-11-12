# E-PL9 movie ART source provenance, 2026-11-12

## Result, not a recording claim

Fifteen byte-checked native source-selection/normal-mapper executions pass.
Three additional upstream override cases pass. The firmware and frozen candidate
are unchanged. This is synthetic bounded execution, not a camera recording or
full RTOS emulation. Actual movie-start binding remains **unproven**.

The producer at `60706502` reads a mode object from the getter `6070d12d`,
which returns `a2af2acc`. The state getter `606ff32c` called with selector 1
reads the halfword index at `a2aed640`, multiplies it by 1020 and adds
`a2aed68c`. These are concrete instrumentation locations for a future trace,
not labels inferred from "movie" in a string.

At `6070665b`, mode byte 3 AND producer index 1 chooses state+296; every other
tested pair (mode 0..4, index 0..2) chooses state+290. Giving the two records
ART120 variants 2 and 1 respectively yields headers `00780201` and `00780101`
through the actual normal mapper and property converter. Mode 3 is not yet
proven to mean movie recording.

Upstream overrides matter: with state+274=1 and the modeled external getter
returning zero, the same ART120 property is replaced by header `00020000`.
State+817=143 replaces it with `000c0002`. The special conjunction
+274=1, +804=1, +896 bit 2 set, +172=1 bypasses the former override and
preserves `00780101`. A valid stored recipe therefore does not by itself
prove the recipe reaches processing during recording.

## Callers and remaining gap

A raw relative-call candidate scan found three calls to the producer, all
confirmed by decoding the call and immediately preceding setup:

- `6070dde1`: explicitly passes index 1.
- `60724d23`, `60724d39`: pass the low halfword from caller owner+32.

The first belongs to the wrapper starting `6070ddcf`. None has yet been
bound to a real movie-start event and corresponding encoder session. Indirect
calls are outside this scan. Literal references to mode storage include reset
writes at `6070c935` and `6070cebd`; those reset the mode to zero, not evidence
of a movie-start write of 3. Pointer-based writes require further tracing.

Earlier bounded processing experiments showed valid recipe headers survive
API/job/request copies while request kinds 003x/200x remain outside the frozen
recipe gate. Neither broadening that gate nor treating frame-kind enums as
movie/sensor enums is justified. The next step is to connect the mode setter,
owner+32 and real recording event, then upstream processing and encoder input.
No claim is made that recipes work, or cannot work, on saved video.

## Reproduce

Run from repository root with the exact private decoded main:

```sh
python scripts/epl9_movie_source_probe.py --main /private/main.bin --out /tmp/movie-source.json
```

The required main SHA-256 is pinned by the script. A checked MN103 reader is
required as in the existing repository probes. Public output contains scalar
addresses, input states and traces, no OEM binary or disassembly bytes.
Getter output is explicitly modeled zero; the external getter, intervening
scheduling, real movie-start and encoder are not executed. Initial harness
attribute naming was corrected before the passing run, not firmware code.
