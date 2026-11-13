# E-PL9 ART source mode commit: bounded native evidence

Follow-up to PR #13, 2026-11-13. **Research only; no install or video-effect qualification.** Frozen packages, recipes and camera are unchanged.

## New verified connection

The source selector's global mode byte at `0xa2af2acc` has a native commit path:

1. The local flag gate at `0x60724502` selects the call at `0x60724508` to `0x607273d0` only when input flags bit 0 is set. Flags 2 and 0x800 alone do not select it. This is a local gate, not execution of the whole enclosing dispatcher.
2. `0x607273d0` calls property-state getter `0x606ff32c` with selector **0**. Its ring slot index comes from halfword `0xa2aed63e`; the slot is `0xa2aed68c + index * 1020`.
3. It passes `state0 + 912` and the byte at `state0 + 576` into `0x6070ded0`.
4. That native helper returns without committing when the status byte is nonzero. With zero status, it copies object `+19`, therefore `state0 + 931`, into `0xa2af2acc`, along with other native configuration fields.
5. Feeding that committed global byte into the already qualified selector fragment `0x6070665b` selects source-property `+296` for mode 3 and producer index 1; otherwise `+290`.

The **property source** in PR #13 uses selector **1**, indexed by halfword `0xa2aed640`. Do not silently equate that source slot to the mode-commit slot from selector 0. The probe tests distinct as well as identical indices.

## Reproduce

Requires the qualified MN103 reader and the privately held exact original main with SHA256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`. No OEM image or decoded listing is supplied here.

```sh
python scripts/epl9_movie_mode_commit_probe.py \
  --main /private/path/main.bin \
  --out docs/evidence/movie-mode-commit-20261113.json
```

Result: **8 local bit-gate cases and 27 native commit/selection cases pass**. The latter cover three state0/state1 slot pairs, requested modes 0/3/4 and inhibit statuses 0/1/255. Previous mode is deliberately 2. Nonzero status preserves it; zero status commits the requested mode. Native getter, commit helper and selector instructions execute in the subset machine without replacing their work with host implementations.

The host seeds synthetic ring contents and explicitly connects two separately executed fragments by setting selector stack inputs to the same mode address and selected source slot. This is not a continuous movie-start execution. Evidence records exact native PC traces, inputs and results, not firmware bytes.

## Still open

- Meaning and producer of `state0 + 931`, and the caller/event chain that invokes the flag dispatcher during actual movie start.
- Runtime relation between selector0 and selector1 slots.
- Real recording request classification, WB/COLOR/gamma gates and pixel generation through the encoder. PR #13's conditional request-type exclusions remain conditional; they do not prove that ART recipes fail or succeed in video.
- TruePic hardware effects, physical frame output, frame rate, recovery and installation safety.

Next useful trace: follow the producer of state0+931 and the actual movie event into this dispatcher, then join its property source to the render/encoder owner. Do not expand firmware functionality on the strength of these local synthetic tests.
