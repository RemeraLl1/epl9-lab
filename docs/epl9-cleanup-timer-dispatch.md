# Native cleanup and timer-dispatch continuation, 2026-11-13

Private input files and frozen firmware are unchanged. No camera access. These findings extend PR17 and PR15; they do not qualify OpenGate or gyro logging.

## OpenGate cleanup

32 native cases executed four cleanup functions, with refs 0/1/2/65535 and inner allocation present/absent. Main SHA checked by `verified_input`; decoded instructions byte-checked against main, BASE=0x60400020.

| Entry | Refcount offset | Active offset | Inner descriptors |
|---|---|---|---|
|6076681c|96|98|8|
|607668d4|400|402|8,92,176,260|
|6076692a|176|178|8,92|
|60766988|180|182|8,92|

All four acquire through 60766a77 and release through 60766a93. For refs>1 they decrement only; refs<=1 release each inner descriptor through 6074ad9f, then clear active. 6074ad9f skips an inner descriptor when its +64 field is zero. Otherwise it calls 6073eab3 with command20, then clears all 84 descriptor bytes. Zero refs also selects this branch; that is a synthetic input, not a demonstrated real invalid object state.

Static continuation: 6073eab3 is an indirect dispatch adapter: function pointer at owner+0 and context at owner+4; absent function returns1. Thus the missing drain proof is now the real callback binding and its command20 implementation, not the four cleanup wrappers. Clearing the descriptor after the call does not prove callback completion.

Lock wrapper 60766a77 retries resource832 with 607a17b7, delaying1 via60411401 when zero. 607a17b7 maps resource832 to mask0x40, byte 0x8ff001c7; acquire/release use bit set/clear inside other critical-section calls. This is local mutual exclusion, not evidence of an outstanding-frame drain. The new 32 controls explicitly modeled acquire/release and the command dispatcher, not IRQ or hardware.

## Gyro

32 native timer dispatcher cases: all low-nibble status values0..15, primary callback present/absent. Timer0 callback record at0x824: +4 primary, +8 secondary, +12 argument. Status bit4 calls primary first, bit2 calls secondary second; null callback skipped. Configured primary is40017578, leading to deferred tick enqueue. The test stops at modeled callbacks, not a physical timer.

Exact timer0 ROM register descriptor at4000ecb8 contains9c050000/004/005/008/00c/010/014/018. Timer setup writes50000 to comparator offset+12 and reads phase from+20. Generic interrupt dispatcher4000a90f derives selected slot from RAM8a00 and reads status low nibble from table-selected16-bit register; clears corresponding bits shifted4 before calling handler. Its PSW write precedes this operation. The relation of register semantics to hardware rollover, actual IRQ priority, sample hook and full main/aux timestamp join remain unresolved.

Consequently a snapshot cannot simply test the hardware status and pending software tick and assume no gap: the generic sequence has an ACK-before-callback window. This is a static ordering observation, NOT a demonstrated reachable preemption or camera race. Need link actual configured IRQ slot and determine masking/priority before proposing an atomic timestamp.

## IRQ linkage follow-up

The startup copy at400100d6 copies536 bytes from ROM4001ed28 to RAM0ac4. The ROM pair at4001eed8 is{0x6001,40009db7}; it therefore lands at0c74/0c78, IRQ table index34 relative to0b64. This identifies the default timer0 binding. Later registration APIs may replace it; no full startup/live table is measured.

Sixteen additional native controls connected generic IRQ dispatch to this timer0 handler and timer callback. Synthetic selected slot34 at8a00, synthetic16-bit controller register8988, copied handler pointer0c78, callback pointer0828. Each control stopped before the unsupported PSW instruction4000a938 and explicitly resumed4000a93c. Original instructions cleared `status_low_nibble <<4` from the controller register before reaching the timer callback. No PSW semantics, hardware register semantics or physical event evolution is modeled. The primary callback occurs exactly when status bit4 is set. All 90 controls are included in scripts/epl9_cleanup_timer_probe.py and docs/evidence/cleanup-timer-dispatch-20261113.json.

This closes the default ROM-to-RAM timer0 binding, but not actual gyro acquisition interrupt priority or whether the ACK-before-enqueue window is preemptible. Keep the latter unresolved rather than claiming a production race.

## Reproduce

Requires the native interpreter dependencies from PR5 and the private exact stock components. No firmware is redistributed.

```sh
python scripts/epl9_cleanup_timer_probe.py --repo . --main /private/main.bin --aux /private/stabilizer.bin --out /tmp/fresh-cleanup-timer.json
```

`--repo` locates scripts and its qualified local MN103 reader. All peripheral state is synthetic. PSW bridging and all modeled services are explicit. This report does not claim whole-program concurrency safety or physical throughput.

## Movie command20 binding

Static trace:607072df installs callback606fbc6c and contexta2af1e1c into parameters passed through6071c506 /6074eac5. Constructor6074ec4f copies this pair into object+4/+8. Callback event20 selects ROM table row608b4854, branch606fbcfa, then606fbf10. The latter uses descriptor+68 as a1-based class selector, passes descriptor+64 as the release address, and calls6071949e. That helper enters synchronization via6071784e and leaves via60717864; actual release continues into607c601c for class34/flag0 or607c67d6 otherwise. These interiors and full callback-to-restart ownership remain unresolved.

Ten new native release-body controls use selectors0..9. Selectors1..7 produce release classes3/12/10/34/5/25/26. Invalid0/9 log and return0 without release. Selector8 passes the local range check, but its12-byte metadata overlaps the next jump table at608b4838: class48761, flag111. This is a synthetic out-of-contract possibility, NOT evidence that a real producer emits8 or that camera release is broken. Do not describe all eight as valid resource types merely because the local check accepts them. Follow actual producer writes to descriptor+68 before changing this range.

The90 total controls preserve explicit external service models. A zero return and dispatch to allocator routines are not proof of outstanding-frame drain.
