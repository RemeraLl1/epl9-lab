# E-PL9: diagnostic initialization and read-maintenance follow-up

2026-11-07. This extends the [private-COLOR deployment investigation](epl9-v3-private-deployment.md).
**The diagnostic session is not qualified as a harmless memory-access gate,
and bulk reads do not remove NAND maintenance.** Two new bounded probes pass
75 native control cases: 21 initialization/lens fragments and 54 read-path
cases. No camera, USB transport, SD card or physical flash was accessed.

Gold 200 / Portra 400 v3, both generations of decoded components, icons and
encoded installation/stock-return files are unchanged. The separate SD loader
prototype is outside this investigation. `install_ready` remains false.

## Exact input and evidence

Olympus E-PL9 / IM008 / model 1330; displayed body 1.1 reported by the owner;
downloaded main build 1101, **not a camera dump**.

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `firmware/OLY_E_133_1101_0000_0000.BIN` | 104552480 | `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028` |
| `local/epl9-1101-analysis/decoded/00_0100_406e0020.decoded.bin` | 26214336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| `local/mn103-tooling/mn103-reader.exe` | 71168 | `e1c9bcb2b2467a44b8f6e2b6910c9868eff6ce571c36d5b9ad41d1d8693a76ae` |

The native main base is `60400020`. Listings are byte-checked against that
exact main. Retained evidence is under
`local/epl9-v3-diagnostic-init-20261107/`: `init-results-final.json`,
`maintenance-results.json`, source listings and `manifest.json`. The earlier
`init-results.json` is a preliminary 19-case run; the final 21-case report adds
two post-wait lens-state fragments and uses the final source hash.

## Diagnostic open and close: service ownership and waits

The previously resolved payload 2 selects initializer `605f96c0(d0=0)` and
teardown `6067d641(d0=0)`. This pass follows those mode-zero paths. It does not
generalize other initializer modes or model a successful complete session.

Exact native name records identify queue 48 as `LENS_EXEC`, handled by task
102 `LENS_MAIN` at `605cec08`; queue 101 is `TAKE_FUNC_CP_POST`.

| Stage | Open initializer | Close initializer |
| --- | --- | --- |
| Owned request allocation | 16 bytes | 16 bytes |
| Destination queue | 48 (`LENS_EXEC`) | 48 (`LENS_EXEC`) |
| Four-word packet | reply queue 101, mask 1, command 1, allocated pointer | reply queue 101, mask `20`, command 2, allocated pointer |
| Pending mask at `626155a0` | OR 1 | OR `20` |
| Reply | 12 bytes from queue 101, timeout -1 | 12 bytes from queue 101, timeout -1 |
| Matching reply | clears pending bits; retains first nonzero 16-bit status | clears pending bits; retains first nonzero 16-bit status |

Open first calls `606817fa`, which only clears byte `62618550` and halfword
`62618552` in the reviewed function. It then sends the lens request and waits
for readiness word `a2ae44d8` through `604d59f1`. A zero value reaches the
one-tick delay at `605f97c5` and loops; it is not a timeout or a completed open.

The prefix tests supply queue-wrapper results 0/-1 explicitly. If that wrapper
returns, the initializer still sets the pending bit and proceeds to a wait;
the wrapper's error/logging behavior is not replaced by a claim that actual
queue failure safely returns. A reply with the wrong completion mask leaves
the request pending and does not free it, in both open and close controls.

Close with an injected matching reply frees its sole 16-byte allocation and
preserves reply status 0 or `310d`. If byte `6261558e` is already 1, native close
first calls `605f931e(5)`; the corresponding control stops before that call.
This additional state-dependent path is still unqualified.

## Open can discard a completion error

After the matching lens reply, mode-zero open allocates an 8-byte callback
record containing `605f99da` and zero, and registers it through `60451dd9`.
It frees the first 16-byte request before waiting through `6091acb5(-1)`.

The native wait helper calls event wait `60431138`, maps injected kernel result
-2 to `4b06`, and otherwise returns the halfword at `626155a8`. The initializer
does not propagate that return. Its final d0 comes from the earlier service
reply status in d2.

The four tail controls explicitly exercise the **still-pending callback
cleanup branch**, not a successful asynchronous callback:

| Injected service status | Injected event result | Injected callback status | Native wait result | Native initializer result |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 0 |
| 0 | 0 | `310d` | `310d` | 0 |
| 0 | -2 | 0 | `4b06` | 0 |
| `310d` | 0 | 0 | 0 | `310d` |

In all four fixtures, pending-callback byte `6261558f` remains set until native
cleanup clears it, frees the 8-byte record and calls error reporting with
`38b4`. Terminal bytes `6261558c/8d` become 1. Thus a zero returned status can
coexist with error reporting; these bytes and d0 cannot independently certify
successful session initialization. Kernel events, scheduler, allocations,
queue replies and error reporting are explicit models. Physical asynchronous
ordering and concurrent ownership have not been established by these tests.

## Lens commands are stateful

Native gate `605cec9b` returns immediately for command 1 when lens-state
halfword `625a405c` is already 1, and for command 2 when it is already 0.
Opposite-state controls proceed to a property query and further work.

The separate inner dispatcher `605cee49` selects `605cef22` for command 1
and `605cf0c9` for command 2. These are substantial, different service chains;
they are not modeled as successful lens hardware operations. The native
post-wait fragment `605ced41` writes state 1 for command 1 and state 0 for
command 2, then returns zero.

These are conditional fragments, not an end-to-end lens run. In particular,
open/close are not proved to restore the state present before opening: the
observed close fragment writes a fixed zero, not a saved previous value.
Motor/power effects, intermediate callbacks and nonvolatile side effects of
the downstream chains remain unqualified. Other models' lens emulation is not
substituted for exact E-PL9 evidence.

## Page and bulk reads both reach flash maintenance

The new read probe executes native address translation `60401180/604011ad`,
block-map resolution `604008a7` and the three reader bodies. Controller
registers and completion/status calls are synthetic; no flash data is supplied.

| Reader | Read unit | Block-map helper | Register `98d01194` low nibble | Maintenance branch |
| --- | ---: | --- | --- | --- |
| `604009bf` | 2048 bytes | yes | sampled | `60400ac8 -> 604007b0` when >13 |
| `60400d2f` | 131072 bytes | yes | sampled | `60400e3f -> 604007b0` when >13 |
| `60400c60` | 2048 bytes | no | not sampled in this body | not called in this body |

Forty-eight cases cover both component starts, all three readers, register
values 0/13/14/15, and identity/remapped synthetic block tables. Sixteen reach
the maintenance call and stop before it. This does not establish the physical
meaning or real distribution of that register value.

Two further controls run **all 200 native bulk iterations** for each complete
26214400-byte decoded component envelope, with register value 13. All source
pages and destination increments match; there is no loop acceleration. This
checks address planning, not successful DMA or acquired component bytes.

The direct reader is not a drop-in logical reader: under the same remapping
fixture, it requests the original physical block while both logical readers
request the mapped block. Replacing the function alone could return stale or
wrong data even if its status appears successful.

Three persistent-status controls inject status 1. Each reader repeats the
same physical request twice and returns to its loop without advancing. No
retry bound is present on these tested native failure paths. A timeout around
the host command alone would not demonstrate cancellation of that firmware
loop or safe buffer release.

## Maintenance includes data and mapping-table writes

One additional case executes `604007b0` with synthetic free spare slot 992,
trapping every storage leaf. Native control flow requests:

1. Read the old 128 KiB block through `60400c60` into `a2e95000`.
2. Erase and program the selected spare block through `60401066/60400e55`.
3. Call page-metadata operation `60400f67` for the old source.
4. Erase 393216 bytes starting at logical address `47ec0000`.
5. Program 8192 bytes of the mapping table at each of `47ec0000`,
   `47ee0000` and `47f00000`.

The mapping changes only in synthetic RAM in this test. No storage operation
executes. Nevertheless, the native request sequence disproves the assumption
that ordinary bulk reading necessarily avoids nonvolatile writes. The
metadata helper and device/controller details remain outside this planner test.

## Consequences and next bounded work

The prepared package/comparator is unchanged. This pass narrows the acquisition
requirements rather than qualifying a transport:

- Session success needs actual completion/error evidence; a zero status is
  insufficient, and lens-state restoration must be understood.
- A no-maintenance logical reader must preserve the current block mapping and
  have bounded error handling. Neither changing the selector flag nor directly
  substituting the raw page reader supplies both properties.
- An export needs a demonstrably owned buffer and a working admitted response
  route. The existing CLI global-pointer problem and retail-MTP rejection of
  direct `9021 READ_DATA` remain. No guessed commands are authorized by this report.
- Comparing both full components and repeated reads remains useful only after
  their bytes are acquired through a qualified route. A matching stock-return
  file is still not evidence of physical restoration or recovery from no boot.

The next useful investigation is an exact, bounded acquisition design joining
mapping, error handling, buffer lifetime and an admitted transport, alongside
the remaining session-service effects. It must remain separate from frozen v3.
Actual TruePic output is still a purpose of a later camera test, not an output
invented by these software models. Same-job exclusion and physical code/cache
lifetime retain the limits of the earlier integration reports.

Reproduce into **new** ignored report paths:

```powershell
.\.venv\Scripts\python.exe scripts/epl9_diagnostic_init_probe.py --out local/new-init-results.json
.\.venv\Scripts\python.exe scripts/epl9_read_maintenance_probe.py --out local/new-maintenance-results.json
```

Both scripts reject a changed stock hash, byte-mismatched listings, overwritten
report paths and outputs outside `local/`. No device-access API is used.
