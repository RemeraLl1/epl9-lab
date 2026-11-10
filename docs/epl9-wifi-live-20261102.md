# E-PL9 Wi-Fi: measured original transfers, 2026-11-02

The owner connected the workstation to the camera and explicitly authorized read-only speed/pause measurements on stock firmware. No firmware, settings, ART mode, camera files or remote-operation state was changed. No setter, erase, trim, power-off, mode-switch or update command was sent. All HTTP requests were GETs to the established metadata/original-file paths.

**Measured baseline: about 1.8 MiB/s (1.9 MB/s) for both ORF and MOV.** The capture shows the 16 KiB block boundaries identified offline. The clean baseline is not dominated by TCP data retransmissions or a full receiver window. This narrows the investigation but does not directly measure internal SD/ISC/ARM execution time or prove which optimization will help.

## Session and link

- Workspace: `D:\EPL9Lab`, branch `main`; HEAD at start `0ffe98ad7807c268fe2bf29e5a6251a063773835`. Other chats' work was preserved.
- Date in the owner's timezone: **2026-11-02, America/New_York**. Baseline 17:05:17–17:05:59 EST, also recorded as `22:05:17–22:05:59 UTC` in the manifest.
- Camera HTTP endpoint: `192.168.0.10`; User-Agent `OI.Share v2`; fresh connection mode **private**.
- Before and after the tests: **2.4 GHz, channel 6, 802.11n, negotiated receive/transmit rate 72.2 Mbit/s, signal 100%**, as reported by Windows. These are link readings, not measured file goodput or proof of an interference-free radio channel.
- Fresh command-list response: 11,273 bytes, API **4.00**, SHA-256 `f0093e0cfd0974f8979397f2d600711bbf6bf8bdd963685e39ba4209fca47c4b`; byte-identical to the XML extracted from the identified E-PL9 build 1101. API version is not body firmware version, and this XML match is not an installed-firmware dump.
- Body version **1.1** and stock status remain owner reports. No firmware was flashed by this project.

The offline input identity remains E-PL9 stock `OLY_E_133_1101_0000_0000.BIN`, 104,552,480 bytes, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`. Native-code addresses and component identities are in the [offline limits report](epl9-wifi-transfer-limits.md).

## Baseline: three serial rounds

Each round downloaded ORF, JPG, then MOV. One connection at a time; client read ceiling 65,536 bytes; `HTTPConnection` direct to camera, without a proxy; `Accept-Encoding: identity`, `Connection: close`. JPG was a size/type control. Hashing and disk output occurred after each transfer timer. Each response was HTTP 200 and had the expected complete byte count.

| Original | Bytes | Three total times, seconds | Median MiB/s | Median decimal MB/s |
| --- | ---: | --- | ---: | ---: |
| `PB020001.ORF` | 14,692,005 | 7.630 / 7.623 / 7.716 | **1.836** | **1.926** |
| `PB020002.MOV` | 8,105,416 | 4.249 / 4.374 / 4.157 | **1.819** | **1.908** |
| `PB020001.JPG` | 3,249,056 | 1.673 / 1.752 / 1.776 | 1.768 | 1.854 |

MiB = 1,048,576 bytes; MB = 1,000,000 bytes. Timing includes connection setup, HTTP headers and the complete response read. Median ORF and MOV body-start times were approximately **32 ms** and **36 ms** from connection start. There is no large first-versus-later speed increase across these three rounds.

The similar rates across ORF/MOV/JPG do not support a distinct extension-specific throttle in this test. They do not rule out a shared CPU, storage, ISC or radio bottleneck.

## Pauses and 16 KiB boundaries

The first capture used Npcap/dumpcap on the Wi-Fi interface, a filter of **`host 192.168.0.10 and tcp port 80`**, snap length **160 bytes**, and a 150-second limit. It recorded **112,635 packets with zero capture-driver drops**. The snap length preserves protocol headers/timing while truncating most media payload; full-file identity was checked separately by the downloader.

On clean ORF/MOV streams, the common camera TCP payload sizes were **1460 bytes** and **324 bytes**. The pattern `11 × 1460 + 324 = 16384` repeatedly ends at exact file-body offsets that are multiples of 16 KiB. HTTP header length was inferred from complete, contiguous response sequence coverage minus known file size: 104 bytes for ORF and 94 bytes for MOV. Gaps were classified using **body offsets**, not raw response offsets.

| Clean baseline stream | Median gap after a captured exact 16 KiB boundary | 95th percentile boundary gap | Largest camera-data arrival gap anywhere |
| --- | ---: | ---: | ---: |
| ORF round 1 | 2.303 ms | 5.127 ms | 82.917 ms |
| ORF round 2 | 2.269 ms | 4.736 ms | 48.742 ms |
| ORF round 3 | 2.283 ms | 5.249 ms | 38.207 ms |
| MOV round 1 | 2.312 ms | 5.064 ms | 28.901 ms |
| MOV round 2 | 2.209 ms | 5.093 ms | 70.720 ms |
| MOV round 3 | 2.360 ms | 4.871 ms | 23.580 ms |

Within blocks many captured packet arrivals are batched, with median spacing about 0–1 microsecond; other intra-block gaps also reach milliseconds. The boundary gaps are a runtime correspondence with the native file-read/send loop, **not an isolated measurement of removable ISC or SD delay**. PC timestamps include radio and driver delivery effects. They cannot be summed as a promised optimization gain.

Application read completion gaps tell the same broad story: baseline ORF/MOV medians about **2.0–2.1 ms**, 95th percentiles about **5.3–5.6 ms**, maxima **83.1 ms ORF** and **70.8 ms MOV**. No baseline ORF/MOV application gap exceeded 100 ms. Application read sizes are not TCP segments or native firmware block sizes.

## TCP flow control and transient loss

For all nine baseline original transfers:

- **Zero TCP data-retry frames**, zero duplicate-ACK events, zero zero-window/window-full events, and no lost/out-of-order segment flags in TShark's analysis.
- Some streams contain one repeated **FIN with zero payload**. These are connection-close control retries, not retransmitted original-file bytes; they must not be counted as a media-loss bottleneck.
- The PC's advertised receive window stayed around **65,211–65,535 bytes** on the baseline ORF/MOV streams. TShark's maximum observed bytes in flight ranged from **22,224 to 32,768 bytes**. No observed receiver-window blockage explains the steady baseline rate. Capture-derived flight estimates are not a direct readout of the camera's TCP queue occupancy.

One later MOV test with an 8 KiB client read ceiling took **6.532 s / 1.183 MiB/s**. Capture stream 13 had a **991.547 ms** camera-data arrival gap, **six data-retry frames**, 21 duplicate ACKs and lost/out-of-order flags. Two repeated payload intervals added 2,920 duplicate captured bytes. This is a distinct transport disturbance; it must not be treated as proof that an 8 KiB read ceiling itself causes a 1.18 MiB/s limit. The capture cannot identify whether the loss originated in RF, a driver, or another transport component.

The second, 90-second capture recorded **44,668 packets with zero capture-driver drops**. All six repeat MOV responses were fully captured and had zero data-retry, duplicate-ACK, zero-window/window-full or lost/out-of-order flags. One 8 KiB repeat still had a **119.1 ms** arrival gap without TCP retry flags, demonstrating that an occasional pause is not by itself proof of retransmission or one particular firmware wait.

## Client read-size checks

Initial checks, always sequential:

| Client read ceiling | MOV seconds / MiB/s | ORF seconds / MiB/s |
| --- | --- | --- |
| 8 KiB | 6.532 / 1.183, transport-disturbed | 7.587 / 1.847 |
| 256 KiB | 4.114 / 1.879 | 7.493 / 1.870 |

To resolve the disturbed MOV result, another six MOV transfers used the order **8 / 64 / 256 / 256 / 64 / 8 KiB**:

| Client read ceiling | Repeat times, seconds | Repeat rates, MiB/s |
| --- | --- | --- |
| 8 KiB | 4.399 / 4.202 | 1.757 / 1.840 |
| 64 KiB | 4.156 / 4.169 | 1.860 / 1.854 |
| 256 KiB | 4.219 / 4.269 | 1.832 / 1.811 |

There is **no large, consistent acceleration from enlarging the PC read ceiling** in these checks. The small differences are not a controlled attribution: RF, camera state, capture overhead and other workstation activity were not held constant. This parameter also does not change the native camera's 16 KiB send block. Parallel downloads were not repeated; the owner's prior no-benefit result remains accepted.

## File identity

Across the session, **19 complete original downloads, 172,366,769 bytes total**, passed size/HTTP checks and matched per-file SHA-256:

| Original | Copies | SHA-256 |
| --- | ---: | --- |
| ORF | 5 | `1deed5a996e6b3d0d724425ef76b8703a37b8130a3a4cb2c9344c6b691a79946` |
| JPG | 3 | `9d0971d1ea3972057276072d136ed3b50907c8d68704de449578c185116ad262` |
| MOV | 11 | `2adb950f5ae41bf92fa01f921fb8ca06056ee8094e389e83dc266e3ad4877ad0` |

The previously supplied 42-character text is exactly the **prefix of this freshly computed full MOV SHA-256**. The full value above was calculated from downloaded bytes, not guessed by extending that prefix.

No card-reader originals were available under the project's sample directories. Therefore this establishes repeated download consistency, **not a new independent card-reader comparison**. Media and packet captures remain ignored/local.

## Consequence for the offline candidates

The stock 16 KiB loop is now visible in actual transfer behavior. It remains useful to qualify the narrow **HTTP `r → rd` route** and **reuse of ISC reply resources**, then local TCP enqueue batching, as described in the [offline limits report](epl9-wifi-transfer-limits.md). None was applied in this session.

The clean baseline weakens explanations based on sustained TCP loss or the PC exhausting its advertised receive window. It does not prove that the 2.3 ms boundary gaps belong entirely to file reads/ISC, nor exclude radio/driver airtime or internal scheduling as shared limits. There is no measured speedup for a firmware change and no justification to bypass completion or queue-capacity waits.

## Local evidence and reproduction

All raw files are under ignored `local/wifi-live-20261102-session1/`:

- `preflight.json`, four `preflight-*.body` files, `wlan-before.txt` and `wlan-after.txt`.
- `baseline/measurements.json`: nine original trials, metadata responses, headers, checksums and application read events.
- `client-read-size/measurements.json`: four initial client-ceiling trials.
- `mov-client-check/measurements.json`: six interleaved MOV repeats.
- `baseline-http.pcapng`, `client-check.pcapng`; the first capture ends during the final additional ORF transfer. **Its stream 16 is incomplete as a capture**, while the separately measured HTTP download completed and matched SHA-256. This distinction is preserved by the analyzer.
- `tcp-packets.tsv`, `client-check-packets.tsv`: TShark fields including frame time, IP direction, TCP stream/sequence/length/flags, payload prefix, window, flight estimate and analysis flags.
- `analysis-v1/analysis.json` and `transfers.csv`: derived results and raw-evidence SHA-256 inventory.

Re-run the offline analysis without accessing a camera:

```powershell
.\.venv\Scripts\python.exe .\scripts\epl9_wifi_trace.py `
  --session .\local\wifi-live-20261102-session1 `
  --out .\local\wifi-live-20261102-session1\analysis-new
```

Baseline downloader: `scripts/epl9_wifi_bench.py --repeats 3 --parallel 1 --read-size 65536` with the new ignored output directory above. The additional checks called its same bounded `fetch()` and integrity classifier with the documented read sizes/order. No range probes or remote setters were used.

The trace analyzer passed **six synthetic tests** covering sequence-range merging, data versus FIN retries, incomplete capture handling, body/header offset correction at 16 KiB boundaries, and missing sequence intervals. These validate analysis logic, not the camera's internal execution. The downloader's earlier fourteen synthetic checks remain applicable; its source was unchanged for these measurements.
