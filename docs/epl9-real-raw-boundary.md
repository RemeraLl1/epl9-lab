# E-PL9: real RAW input and the remaining TruePic pixel executor

## Result, 2026-11-04

The owner's ORF is now mapped as actual decoded mosaic samples into the native job probe. Eight cases cover the two Watercolor replacement identities, selectors 0/2 and candidate 12-bit formats `0x0108`/`0x0109`. Native object construction, COLOR configuration and geometry execute, with the previous 5200-byte configuration oracle and output-base checks intact. Every case still reaches the first peripheral stop without writing output pixels.

An instruction-level observer records **zero native source-pixel reads** before that stop. Two controls replace the actual mosaic with all zeros: configuration remains identical for the same slot, and output remains poisoned. This establishes that the currently executed CPU prefix configures the image engine and does not develop the RAW. Extending queue/cleanup models alone cannot turn these runs into complete images.

**No Gold 200 or Portra 400 image was produced by modified firmware.** The slot tables still carry the previously declared diagnostic saturation markers, not calibrated film recipes. Both the pixel executor and final numerical recipes remain unfinished.

## Exact firmware and source

Olympus E-PL9; owner-reported body version **1.1**; downloaded main build **1101**, not a dump of the installed body. Stock container `OLY_E_133_1101_0000_0000.BIN`: **104552480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`. Decoded main: **26214336 bytes**, SHA-256 `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267`, base `0x60400020`. The existing hash-pinned GNU reader and byte/overlap checks remain active.

The user supplied an ORF/JPEG pair in the project directory. Decoded mosaic dimensions, white level and identity are taken from the [previous RAW reference](epl9-hardware-completion.md#owner-provided-rawjpeg-reference). Original-file hashes, expanded sample data and reports stay in ignored `local/`; original media are not published. No input files or camera state were modified.

## RAW memory layout candidates

The complete decoded **4640×3472 uint16** mosaic is retained, with 32 zero-padding samples added to each row. The declared memory width is **4672**, the allocation is **32442368 bytes**, and no raw samples are rescaled, black-subtracted or demosaiced by the input adapter. The parser rejects a different measured shape, samples above the declared 4095 range, mutable/truncated backing, unsupported formats and unaligned or oversized extents.

The native source descriptor declares area **4640×3472**, active test window **4608×3456 at (0,0)** and memory width 4672. All decoded rows/columns are present in backing; this test window is explicit and **does not establish the camera's real crop**. Source offsets remain zero and the true CFA/WB/black-level/calibration setup has not been reconstructed from the actual camera caller. A uint16 LibRaw array must not automatically be treated as the camera's exact memory representation.

The native diagnostic subtype printer and stride configuration distinguish three 12-bit family entries:

| Format | Native label | ROM packing factor | Calculated row step at memory width 4672 |
| --- | --- | --- | --- |
| `0x0107` | BayerBit: 12 | 40 | 7424 bytes under the native grouping formula |
| `0x0108` | BayerBit: 12 | 32 | 9344 bytes |
| `0x0109` | BayerBit: 12 | 32 | 9344 bytes |

The row formula here is the executed native grouping calculation, not a generic packed-12 formula. Only `0x0108`/`0x0109` are accepted by the explicit expanded-source adapter. Their differing native control words select different hardware modes; **sample bit alignment and the correct choice between them remain unverified**. The same unshifted uint16 bytes are supplied to both as candidate tests, not as two certified formats.

Real area dimensions expose an extra geometry call at `0x60738fc9 → 0x60790030`. The probe now executes that helper and its bounded ROM lookup at `0x6078ffb0`; it does not stub or bypass the new dependency. Both candidate variants proceed through it to the existing peripheral boundary.

## CPU configuration versus pixel processing

The native source-memory configuration starts at workspace+112. A separate native transfer test executes `0x60740cad`, called by the ordinary input-upload path at `0x60740575`: it copies exactly **24 configuration words** into declared device addresses `0x9f00026c…0x9f0002c8`. Every address/value matches the words produced for the real-RAW case. The finite register recorder supplies no ready responses and performs no image transformation.

All eight real-input cases:

- preserve the actual source backing and produce no source-pixel instruction reads before the peripheral stop;
- construct the parameter object and pass the entire COLOR configuration comparison;
- preserve valid native output bases and allocation guards;
- stop at `0x6073eafa`, writing `0x800` to unmapped `0x9880014c`;
- leave output pixels unchanged, with `full_pixel_cycle_passed=false`.

The zero-payload controls independently confirm data-insensitivity of this prefix. They do not predict results after hardware execution. Color table pointers, gamma, matrices and tone curves configure hardware units; their existence is not a complete executable implementation of demosaic/color/noise/tone/output processing on the host CPU.

## Other executors investigated

- The ignored E-P7 checkout at `7d42c1f258737b7196c6b17cec5d643b5080ece6` calls `sim/pipeline.py` an approximation, not a bit-exact ISP emulator. It uses LibRaw and explicit calibration assumptions. Its source has not been copied into this project or used as proof of E-PL9 pixels.
- The ignored PEN-F reference checkout's processing-job map explicitly distinguishes native CPU configuration from unexecuted ISP pixels. PEN-F addresses/patches are not E-PL9 implementations.
- The installed OM Workspace contains image-processing libraries, ART interfaces and separate decode helper processes. A read-only export/embedded-string inventory was retained locally. It did **not** establish a supported call that accepts our native E-PL9 firmware parameter object or its 5200-byte register image. No unknown private C++ methods were invoked and no installed binaries were changed. Ordinary Workspace rendering could be a reference image, but would not by itself execute the modified camera route.
- The official [OM Workspace overview](https://software.omsystem.com/omworkspace/en/), checked 2026-11-04, lists the supported USB RAW cameras in its dedicated USB RAW section. E-PL9 is absent from that list. A verified USB offload route for this body cannot be assumed.

No verified pixel backend for these modified native jobs was found in the examined tools. This is a scoped investigation result, not proof that no implementation could ever be written. A desktop approximation would need separate labeling and calibration; it would not satisfy a claim of exact TruePic execution.

## Reproduction and validation

```powershell
# Optional RAW dependencies were already installed in the project venv.
.\.venv\Scripts\python.exe scripts/epl9_raw_input_audit.py --raw <owner.orf> --out local/new-raw-input-audit
.\.venv\Scripts\python.exe scripts/epl9_job_probe.py --out local/new-job-regression
```

Final reports: `local/raw-input-audit-20261104-final/results.json` and `local/job-raw-regressions-20261104/results.json`. The raw audit also retains `expanded-bayer-candidate.bin`; it is private source data, not a firmware patch. Source code and input hashes are recorded in the report.

The new native audit passes eight real-input configuration cases, two zero-payload controls, three native subtype checks and one exact 24-word native upload. All previous job checks pass. **128 workspace unit tests** pass, including three new expanded-input contract tests; independent Wi-Fi/video work contributes to the workspace total.

The remaining work for an actual Gold/Portra image is substantial: qualify real caller crop/CFA/WB and sample packing, provide actual TruePic execution and coherent output, establish/validate the executable replacement hook, then tune the two numerical film recipes against output pixels. The current offline phase has not achieved that full cycle. Signal replay and LibRaw reference images must remain separate from modified-firmware output.
