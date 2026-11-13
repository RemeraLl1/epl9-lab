# Gyro timing: snapshot-order follow-up

2026-11-13. This is a bounded CPU experiment, not a timestamp logger, device race report or safe acquisition hook. The frozen ART firmware is unchanged.

## What was established

On the exact build-1101 stabilizer component, the deferred drain stores `pending - 1` at `0x4001d38c`, then calls the tick function at `0x4001d38f`. The tick function enters its own PSW save/restore bracket and increments the low epoch word before the high carry word.

The new probe executes nine combinations of native arithmetic: epoch 10, low-word carry and full 48-bit wrap, each with pending counts 1, 2 and 255. It observes the state before drain, between pending decrement and tick, between low-word store and high carry, and after arithmetic. All nine pass their exact expected-state checks.

The result rules out a tempting shortcut **unless execution exclusion is separately proved**: simply replacing epoch with `epoch + pending` does not establish a coherent clock. During the deferred transfer, the sum is temporarily one tick smaller. On low-word carry, the partially updated epoch can be much smaller. These are original instruction effects on synthetic RAM; the observers are injected, not known to be permitted by real interrupt priority/masking.

Two clearly labelled host read-protocol counterexamples are included:

- Two identical reads of all fields while the producer is paused in the drain gap agree, but still undercount. Stability alone does not establish completion of a multi-store update.
- A high-low-high read while the producer is paused after the low store but before its high carry sees equal high words and can accept an incoherent value. This is not evidence that such preemption occurs on the camera.

## Interrupt-mask boundary

The probe statically verifies the tick's call to `0x4001d418`, which saves PSW through a caller-provided address, and its later call to `0x4001d42c`, which restores PSW. It also verifies the phase reader's 16-bit MMIO read at `0x9c050010`. The subset interpreter does not model PSW/interrupt scheduling, bus atomicity, timer progression or event acknowledgement. Thus the partial-state observations cannot be called reachable production races.

The drain-to-epoch gap and high-carry gap also differ: the latter is inside the tick's bracket. Determining exactly which prospective sample callback can observe either requires its interrupt class and actual mask semantics. A blanket claim that “disable interrupts fixes it” is not justified. A hardware phase can continue changing while software interrupts are masked; a hardware event may also exist before software pending is incremented.

## Reproduction

Use the virtual-updater branch dependencies and the exact private stabilizer component identified by SHA-256 `1c942d2fb6b8830f0195a0be7464880838ddf08c5f038bad626aed8e72789678` (219104 bytes). No OEM binary or disassembly is included.

```sh
python scripts/epl9_gyro_snapshot_probe.py --aux /private/stabilizer.bin --out /tmp/new-snapshot-result.json
```

The script validates the component and pinned reader, four instruction windows and ten semantic anchors. It enters arithmetic fragments independently and explicitly bridges the call boundary. It does not emulate the complete tick function. It refuses an existing output.

## Next useful experiment

1. Trace timer event acknowledgement and callback delivery relative to phase rollover; determine what hardware status survives a masked event.
2. Establish the interrupt class of actual gyro acquisition and which events the existing PSW helpers exclude.
3. Only then evaluate a snapshot protocol that includes hardware pending and discontinuity/reset state. Do not deploy the host counterexamples as a proposed algorithm.
4. Establish absolute clock frequency and the acquisition-to-exposure/main-domain join separately.

No synchronized XYZ samples, actual time units, camera access or physical timing measurement resulted from this probe. The result narrows the design requirements; it does not make gyro logging ready.
