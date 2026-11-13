# Late descriptor reader: a necessary lifetime boundary

Status: bounded native-fragment experiment, 2026-11-13. Builds on the host
bounded-cache model. No camera release, no frozen Gold/Portra changes.

## New evidence

The stock main SHA-256 is
`8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`.
Its load base is `0x60400020`. Native function at `0x607414a9` has a later
reader of configuration-held table pointers. The tested fragment starts at
`0x6074151f`, after owner bookkeeping and external calls, and stops at
`0x60741647`, before HSL processing. Caller stack, owner, configuration and
output destination are explicit synthetic memory regions, not inferred
physical allocations.

For the equal-RGB-gamma path, configuration offsets 2596, 2600 and 2604
point to the same descriptor gamma table. The load at `0x60741592` reads
256 halfwords from that retained pointer and expands them into 256 output
words. This takes 1,827 interpreted native instructions in the fixture.
The fixture uses deliberately artificial values, not V6 recipe parameters.

* Keeping both resident leases blocks a third acquire and preserves output.
* Deliberately replacing the source bytes before the reader executes changes
  every output sample despite unchanged configuration pointers.
* Host generation changes reject stale handles, but **native raw pointers do
  not carry that generation**. The generation check alone cannot make native
  eviction safe.

The existing configuration-return boundary is therefore too early to release
these bytes. We found **a real later consumer, not the globally last consumer**.
The fragment does not execute the task scheduler, lock calls, camera ISP or
asynchronous completion.

## Next readers to qualify

Static inspection immediately after the tested fragment shows HSL-pointer
reads at `0x6074167c`/`0x60741680` (configuration 3124/3128), followed by
3132/3140, 3136/3144 and 3148/3152. These paths have not been executed by this
new fixture. Gamma completion does not qualify HSL release. The caller's
output destination, all task aliases and teardown/drain ordering must still
be proven before selecting a native release hook.

For now the native prototype should keep its session-owned arena. Do not
replace that with the two-slot host cache in a camera build. Finite cache
activation requires a proven owner/task lifetime and a hold-or-defer policy
when both slots are pinned.

## Reproduction

Use the private decoded stock main and an independently built, receipt-verified
MN103 reader. Nothing here contains or publishes the OEM binary:

```sh
python scripts/epl9_descriptor_reader_probe.py \
  --main /private/main.bin \
  --reader /path/to/mn103-reader \
  --output local/late-reader-result.json
python -m unittest discover -s scripts -p test_epl9_descriptor_cache.py
```

The probe verifies the stock hash and tooling receipt and decodes the native
fragment anew. Output includes only scalar evidence, not OEM instruction bytes.

## Recipe-source handoff

The existing recipe research chat was re-read on 2026-11-13. Its latest
completed result is **Astra V6 R3**, a colour-layer revision retaining R2
brightness/contrast. It advertises a renderer ZIP in its own isolated
workspace. Reading that message does not retrieve the ZIP or numerical
parameters into this repository. Thus the 31-slot fixtures remain synthetic;
no claim is made that all V6/Astra R3 recipes are integrated into firmware.

## Follow-up: native HSL setters and both upload destinations

The additional `scripts/epl9_descriptor_hsl_reader_probe.py` runs the native
HSL setter `6079e50e` and gamma setter `6079d7a0`, then the bounded late reader
from `6074151f` to `6074178d`. The source is a synthetic recipe descriptor;
the configuration pointers are produced by native setters, not guessed.

The run executes **10,214 reader instructions**, with **1,536 descriptor
reads**. All copied output agrees with an independently reconstructed
halfword-to-word/block-copy oracle. A premature HSL-byte overwrite after
configuration changes the HSL output; the negative control also matches the
changed-source oracle. The final source read in this tested branch is a
halfword at descriptor+`0xc4e`, not the gamma loop's final sample.

Native optional table `config+3164` is null in this fixture and its independent
copy branch is explicitly skipped by a modeled caller flag. The test does not
qualify that table's lifetime, the external bookkeeping calls, a successful
physical ISP run, or asynchronous completion.

Static call operands establish two destinations for the same reader:

| Call site | Destination loaded into a0 | Gate |
|---|---|---|
| `6074060d` | `9f00a400` | flag 8 |
| `6074062f` | `9f00d000` | flag 262144 |

These are hardware-address-space destinations; describing them as two ISP
banks is an interpretation, not measured hardware documentation. The parent
routine starts at `60740530`. A direct call at `6073f801` connects it to the
existing processing-start path (`6073f74f`). Thus this consumer is downstream
of preparation, rather than evidence that returning the configuration helper
ends ownership. A byte scan found no literal pointer to `607414a9`, but that
cannot exclude computed calls or aliases.

The owner/task audit remains open: the existing task31/task2015 and ISEQ
construct/execute/drain/destroy sequences must be connected to **this exact
configuration and all its aliases**, including both upload paths, retry and
cancellation paths. Neither a copy-loop return nor a synthetic hardware-status
notification establishes that contract. Keep the session-owned arena and
refuse native slot reuse until that identity/lifetime link is proven.

```sh
python scripts/epl9_descriptor_hsl_reader_probe.py \
  --main /private/main.bin --reader /path/to/mn103-reader \
  --output local/hsl-reader-result.json
```

This source-only extension does not change the frozen candidate or introduce
SD/Delete hooks. It reads the private stock input and distributes no OEM bytes.

### Constructor identity and cache lifetime, further bounded evidence

The extended probe now executes the constructor's alias fragments. Initially
context+12/16/20 reference workspace+1692/5372/6080. But when request+1484 is
non-null, `6073f0e8..6073f107` replaces these with external-cache+0/3680/4388
and stores that cache at context+56. The fragment stops before the comparator
call. **Consumer workspace destruction therefore does not, by itself, prove
that the configuration holding recipe pointers is dead.**

The existing native cache comparator/update experiment is now also reproduced
by this probe. Its cold result is `ffffffbe`, warm result `80800000`. Changing
only the table pointer leaves `80800000`; changing the table token yields
`90800000`. This is a measured comparator contract, not permission to reuse or
repurpose the token without the real owner's agreement. The existing job
fixture identifies cache at job+12316, but that alone is not a global ownership
or alias proof.

The next integration requirements are now separate and explicit:

1. Hold descriptors across the lifetime of every configuration/cache that can
   retain their pointers, not just a single upload or consumer workspace.
2. Prove native cache invalidation for changed recipe content. A new host
   generation or a changed native pointer does not automatically invalidate it.
3. Connect successful drain, cancellation, diagnostic repeated execution and
   final job/cache destruction, before allowing slot reuse.

No native hook is enabled by these tests. All static/direct-call scans remain
incomplete for computed dispatch and all runtime aliases.

The [parameter-owner follow-up](epl9-parameter-owner-lifetime.md) now qualifies
native three-slot initialization/selection, parameter borrowing into job+12320,
publication waiting while borrowed, and the job+12316 cache-destruction alias.
It distinguishes parameter publication lifetime from retained descriptor/cache
lifetime; it does not enable native eviction or change the frozen candidate.
