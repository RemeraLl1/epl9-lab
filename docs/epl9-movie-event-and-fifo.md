# E-PL9 ART mode event producer: 2026-11-13

Research continuation of PR16. Original main SHA256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`; mapped base `0x60400020`. Frozen candidate and firmware files untouched. No OEM bytes included.

## New native execution evidence

21 cases passed through actual decoded instruction fragments, with synthetic pending events and RAM. No external calls modeled. Cases: events `0x1600`, `0x1601`, `0x16ff`, `0x1500`, `0x1301`, `0x1400`, zero, each with auxiliary pending event 0/1/2. The object's initial mode is deliberately invalid sentinel 9.

- Getter `0x6071798b` consumes and clears pending event word `0x62419d9c`; `0x607179b2` similarly consumes auxiliary word `0x62419da0`.
- Dispatcher fragment `0x6071759d` saves the event into object+36, extracts high byte with shift 8 and low byte with AND255.
- High byte 22 (`0x16`) selects call `0x60717606` to initializer `0x6070c9c2`.
- The initializer writes mode **3** to object+19 at `0x6070c9cb`, submode **1** to +18, value **1** to +23, zero to +22. All three event low bytes give the same tested fields. Neighbor event classes select different helpers, not this initializer.
- Execution deliberately stops at `0x6070ca0c`, before its next helper. This proves the producer of mode 3 under those inputs, not completion of initializer, complete dispatcher, movie start, processing or encoder.

## Static caller/dataflow findings, not executed end-to-end

- Handler `0x60728b16` loads `0x1600` at `0x60728b1c`, invokes event-post wrapper `0x6071799f`, then `0x60717931` to copy request context. Wrapper calls generic dispatch `0x60437feb` with callback `0x60717a6c`; callback writes the pending event at `0x60717a99`. RTOS dispatch not modeled in this probe.
- Handler pointer occurs at `0x608b8a3c`, `0x608b8b6c`, `0x608b8c9c`, `0x608b8dcc`, `0x608b8efc`, `0x608b902c`, spacing `0x130`. These are candidate repeated handler tables, **not established movie-event identifiers**.
- Outer call `0x60720d74` passes the +108 half of its config pair to `0x60717552`. The caller of `0x60720c86` at `0x606f925b` supplies pair base `0x62419944`, therefore that specific object's mode byte is `0x624199c3`, not directly PR16 state0+931.
- `0x6070dfa7` is a reverse snapshot: global mode `0xa2af2acc` -> object+19. It must not be mistaken for the initiating mode event.
- Separate ring-copy path `0x607021e4` requests 108-byte current config into stack+60 through `0x60700737`; `0x60702225–0x6070223b` supplies it to memcpy destination `0xa2aed68c + slot*1020 +912`. Getter `0x60700737` reads a different queue: base `0x62419a2c + signed_byte(0x62419d8d)*108`. The bridge from pair `0x62419944`/`0x624199b0` into that queue still needs tracing.

## What remains unproved

No continuous start→encoder path. Do not label mode 3 'movie' or promise Gold/Portra video support from these results. Need: handler-table event semantics; config-pair→queue publication and selector chronology; commit to global mode; property source selection and actual recording classification; WB/COLOR/gamma before encoder.

## Reproduce

Use the existing qualified reader/tool scripts from PR5/PR16; private stock main stays local:

```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/path/epl9-emulator-publication/scripts python probe.py --main /private/main.bin --reader /path/mn103-reader --out result.json
```

The script validates exact input hash and listing bytes, and records native traces and branch stops. The reader's pinned build qualification is inherited from the existing local tool, not independently rerun in this session. These source-only files do not contain OEM firmware.

Credit: project's bounded MN103 machinery and GNU-derived reader, plus upstream research credited in EPL9 Lab CREDITS. No E-P7 addresses were transferred to E-PL9.

## Further native FIFO evidence

`scripts/epl9_movie_config_fifo_probe.py` / `queue-result.json`: **8 full 108-byte enqueue/dequeue transfers and 2 boundary stops passed**, including index7→0 wrapping. Queue has eight physical slots, writer byte `0x62419d8c`, reader byte `0x62419d8d`. Producer is `0x6070302e` with index advance `0x60703051`; consumer is `0x60700737` with advance `0x60703088`. No software helpers are replaced by host models. Synthetic calls and RAM only.

Important observed semantics: data copying precedes full/empty checking. On full, the slot is copied but writer does not advance before external logging; on empty, data is copied out but reader does not advance before external logging. Probe stops at logger `0x60440132`, without inventing its completion. This is not a demonstrated bug in real use, where scheduling/guards may prevent these states.

The exact outer order in `0x60720c86` is:
1. At entry: copy next (+108) to current (0), 108 bytes.
2. Update current via helpers, then enqueue current at `0x60720d25`.
3. Copy current to next at `0x60720d31`.
4. Conditionally process pending event and modify **next** at `0x60720d74`.

Consequently a newly initialized mode3 is not the same cycle's already-enqueued config. A subsequent outer iteration could promote it, but guards and intervening helpers have not been executed continuously, so this remains an explicit temporal gap. The previous paragraph's structural queue bridge is now located, not a continuous movie-start proof.

Reproduce queue test with the same PYTHONPATH and `--main/--reader/--out`, substituting `scripts/epl9_movie_config_fifo_probe.py` and `queue-result.json`.
