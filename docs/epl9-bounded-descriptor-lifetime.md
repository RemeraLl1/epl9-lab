# Bounded descriptors: ownership experiment (2026-11-12)

Research branch only. No installation artifact, allocator hook, Delete handler,
SD load hook, ART menu mapping, or OEM firmware is changed here.

## Evidence and distinction

The existing authored native prototype `firmware_src/epl9_sd_processing.s.in`
allocates 8192 bytes through `0x60402373` in `sd_prepare_session` and prepares two
4096-byte descriptors once. This is **prototype source evidence**, not proof that
a new allocation succeeds on hardware or proof of a native completion callback.
The source deliberately retains that arena for the session; it has no dynamic
replacement/free protocol. Do not add eviction merely because configuration has
returned.

`sd_descriptor` compares descriptor offset +12 with the loader's raw pointer.
`sd_pipeline_color` also inspects a gamma pointer retained in a configuration
object (+2596 in `pipeline_exit_check`). Thus lifetime is not just the call that
constructed a descriptor. A raw backing record must remain owned too. Source
pointer identity and stable gamma/HSL address both matter. We have **not** traced
all asynchronous consumers to a last-reader event on E-PL9.

## Implemented reference

`scripts/epl9_descriptor_cache.py` is a single-owner Python specification, not
camera code. Two slots hold 4096 descriptor bytes plus 660 raw backing bytes
each: **9512 payload bytes**, versus 126976 expanded bytes for 31 descriptors.
Serialized bank(s), allocator metadata, leases, program/stack/template memory
are extra. This does not assert 9512 bytes are available in camera RAM. Synthetic
addresses do not describe a physically allocated region.

Content hash plus ordinal keys prevent same-ID edited banks returning stale
entries. Every consumer obtains a lease before accessing any pointers. Multiple
readers share one resident. Only an unpinned slot can be replaced; a full pinned
cache returns `CacheBusy` and must defer the request. Replacement is prepared
before committing, raw bytes remain with the resident, and stale/foreign/double
releases are rejected. Bank switching may coexist in this model only while old
slots stay pinned; the existing BankController intentionally remains stricter
and defers a switch until capture leases drain.

A two-slot cache can process 31 recipes sequentially, but does not guarantee two
slots suffice for burst capture, live-view, video, brackets, or overlapping
pipeline jobs. It must not silently substitute another recipe on exhaustion.

The Python object owns backing *bytes* and validates synthetic addresses; it does
not publish these pointers into an emulator Memory object or native consumer.
This is a lifetime/state specification, separate from the previous native
materializer proof. `release` is supplied by the test, not found in the firmware.

## Tests / reproduction

`python -m unittest discover -s scripts -p 'test_epl9_descriptor_cache.py'`

Seven functional cases cover overlapping leases/backpressure, raw pointer
identity, generation changes, all 31 serial recipes, same-ID edits, rejected
input, double/foreign release and capacity boundaries. Synthetic parameters only.

## Required bridge before native use

1. Trace descriptor/gamma/HSL pointers through enqueue, worker, completion,
   cancellation and error paths on the exact decoded firmware. Find the **last**
   reader, including live-view/video. Returning from config is insufficient.
2. Prove owner task/locking, acquire before publication and balanced completion
   for each path. Unknown completion means retain the slot, not evict it.
3. Qualify actual allocation extent/alignment/failure and session teardown.
   If bounded capacity is exhausted, defer in owner task, never key/IRQ handler.
4. Run native consumers with mapped raw+descriptor arenas and delayed reads,
   then hardware validation. Host tests cannot prove camera concurrency.

Until these are demonstrated, keep the existing two immutable native descriptors
and do not enable dynamic 31-recipe eviction on the frozen candidate.
