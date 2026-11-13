# Future recipe banks: host contract, not an installable update

The frozen native-source-v1 Gold/Portra candidate is unchanged. This branch
adds no firmware hooks, patch bytes, native addresses or files for flashing.

## Release split clarified on 2026-11-13

All 31 recipes belong to the built-in V2 replacement for ART. SD/Delete is a
later additional library, not where those 31 recipes must live. See
[the V2 release scope and native coverage result](epl9-embedded31-v2.md). The
31-record bank format limit is per bank, not a global limit across embedded
and additional card recipes.

## What exists

`scripts/epl9_recipe_banks.py` implements a bounded **host reference** for banks
of 1–31 existing E9R0 records. It reuses the existing per-record model/build/ABI
validation. E9B1 adds a 24-byte header and CRC over the complete bank; maximum
serialized size is **20,484 bytes** (24 + 31 × 660). This is a format size, not a
measurement of available camera RAM, flash space or executable overhead. CRC
finds accidental corruption; it does not authenticate untrusted recipes.

The single-owner event-loop model keeps an immutable embedded bank and switches
all records together. A fresh Delete press in idle still capture queues a
switch. The key callback does no file IO. A worker services it only while idle
and after capture leases drain. Holding/repeating a key cannot cycle repeatedly.
Playback, image review, menu, movie and unknown contexts retain stock handling;
the owner of an entire down/hold/up gesture stays the same even if context changes.
A missing/bad SD bank leaves the embedded bank active. Switching back needs no
card. Card removal cannot mutate an already-loaded snapshot. A subsequent
activation reloads the file. Pending presses coalesce into one request.

This is the proposed interaction requested by the owner, **not proof of a native
Delete event mapping, task ownership, locking, safe pointers, or camera behavior**.

## Developer use

From the repository root:

```sh
python -m unittest discover -s scripts -p 'test_epl9_recipe_banks.py' -v
python scripts/epl9_recipe_banks.py pack --bank-id 1 \
  --out local/future-bank/RECIPES.RBK local/compiled/first.RCP local/compiled/second.RCP
python scripts/epl9_recipe_banks.py inspect local/future-bank/RECIPES.RBK
```

Inputs must already be validated E9R0 files produced by the existing compiler.
The new CLI creates only a new file under ignored `local/`, not a physical SD
card. The model reads `EPL9MOD/RECIPES.RBK` beneath a supplied test card root.
There is no firmware consuming that path in the frozen release. Do not put it
on a camera expecting the feature to work. Test records are explicitly
synthetic, not real film recipes or native ART slot assignments.

## Recovered recipe design: V6, not a native port

The separate cloud colour-development conversation was read on 2026-11-12.
It describes 29 desktop-renderer looks plus the separate Gold/Portra pair.
V6 replaced Pro Image 100 and Vision3 250D with Neon City and Astra. The latest
Astra R3 report strengthens blue-violet sky and pink/gold Milky Way accents,
retaining R2 brightness/contrast; it was judged on two original night frames.
These are that conversation's reports, not independently reproduced here.

The 31-name design roster recovered from its V5 discussion plus explicit V6
replacements is below. **Order is descriptive, not a numbered ART/recipe-ID map.**

- Gold 200; Portra 400; Superia 400; Ektar 100; Kodachrome 64
- Tri-X; Vision3 500T; Double-X; HP5; Ultramax 400
- Pro 400H; Portra 160; Portra 800; C200; ColorPlus 200
- Velvia 50; Provia 100F; Agfa Ultra 100; Agfa Vista 200
- Instax; Polaroid SX-70; Lomo CN100; Lomo CN400; Lomo CN800
- XP2 Warm; Bleach 250D; Bleach 500T; Purple; Turquoise
- Neon City; Astra

The V6 renderer ZIP and later Astra source remain in that conversation's
workspace and have **not been recovered into this checkout**. No numerical
recipe parameters or IDs were reconstructed from prose. Source recovery and
version/hash verification are prerequisites to porting. Private input photos
and firmware are intentionally not included here.

## Port boundaries

| Desktop behavior | Existing E9R0 representation | Remaining work |
|---|---|---|
| Global tone curve | 256-point gamma | Fit against native input/output domains, not copy sRGB samples blindly |
| Hue-sector changes | 12 HSL triples | Establish native sector response; validate against neutral references |
| WB, contrast, H/M/S tone | Bounded fields | Confirm actual native handoff per ART mode |
| Neutral midtone tint, palette operations, chroma limits | No equivalent guaranteed | Determine expressibility; report approximation/error |
| Grain, vignette, halation, local contrast, adaptive Astra structure | Not represented | Separate effect pipelines and native evidence; never silently discard |
| All 31 ART positions | No map in this bank | Verify each existing mode and dispatch/lifetime; bank order is not ART ID |

V6 keeps grain/vignette separate. Astra excludes grain/blur and does not imply
Adobe denoise inside the camera. None of the desktop tests certify hardware.

## Next implementation gates

1. Recover the actual V6 + Astra R3 source bundle, identities and parameters.
2. Recover later SD/button work before writing competing hooks. Earlier public
   two-slot prototype is not evidence for a complete 31-mode integration.
3. Build an explicit per-ART capability map; port representable transforms and
   quantify unsupported differences using small lawful non-personal fixtures.
4. Prove native idle context, Delete event routing, capture ownership/drain,
   bounded filesystem IO and actual allocation budget from the exact build.
5. Add a native adapter only in a future branch; run targeted emulation and
   then a separately authorized hardware trial. Frozen Gold/Portra remains
   the current test candidate until the owner tests it.
