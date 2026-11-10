# E-PL9 Wi-Fi original-file transfer investigation

Date: 2026-11-02. This work is separate from the concurrent ART/film-recipe investigation. No ART script, emulator, patch, recipe or shared routing document was edited. No firmware was modified or flashed, and no vendor write command was sent.

**Live follow-up:** [2026-11-02 original-transfer measurements](epl9-wifi-live-20261102.md) now record the connected camera's rates, pauses, TCP captures and full file hashes. Camera-unavailable statements below describe the earlier offline phase.

The real workspace is `D:\EPL9Lab`, branch `main`, initial HEAD `8bdc281d0caa31130a8a23fae730000f7f48dc6f`. Root `AGENTS.md`, `docs/research-scope.md` and the initial firmware findings were read first. Existing changes to `scripts/mn103_subset.py` and untracked `scripts/epl9_job_probe.py` belong to the other work and were left alone.

## Current conclusion

**A measured cause of slow ORF/MOV transfers has not yet been established.** The camera remains unavailable. In the follow-up, the owner reported that two parallel video downloads each ran at approximately 1 MB/s and gave no benefit. This is an owner observation without captured timing/RF/TCP evidence; it supersedes treating parallel downloads as an untested acceleration recommendation. The [block-size and ISC/TCP follow-up](epl9-wifi-transfer-limits.md) records hard allocator limits and narrower optimization candidates.

The exact binary does establish a useful investigation path:

- The original-file handler reads at most **16,384 bytes** per iteration, then sends that block synchronously through the BSD/ISC transport before the next file read. This is a concrete overhead candidate, not a demonstrated rate limiter.
- The transport reaches an embedded ARM network module, its send handler, and a TCP queue-space wait. TCP queueing can overlap radio transmission; a synchronous API return does **not** mean every byte was acknowledged over Wi-Fi.
- The reviewed file-body loop has no explicit per-block sleep, byte-per-second quota, ORF-specific limiter or MOV-specific limiter. Lower driver scheduling, RF conditions, SD-read latency and host TCP behavior are still unresolved.
- Four HTTP worker tasks are started in the reviewed startup path. Therefore the PEN-F reference's single-worker description must not be transferred to E-PL9. The owner reports no benefit from parallel downloads; no new instrumented camera measurements were made here.
- The reviewed HTTP header parser has no `Range` branch, and the ordinary file-body path has no offset/length selection for a requested range. The main image also has no literal `Range:`, `Content-Range:`, `Accept-Ranges:` or `206 Partial Content`. This strongly argues against ordinary HTTP byte-range downloads on this path, pending a bounded camera test. It does not prove that no separate proprietary transfer interface exists.
- The worker closes its socket after its response, despite recognizing a `Connection` header. Keep-alive parsing alone does not establish persistent transfer support.

There is no validated acceleration patch. Changing only the 16 KiB immediate would be unsafe: matching buffers are also allocated at 16 KiB, and lifetime, allocation and transport constraints need a coordinated change and later validation. Flashing is outside the accepted phase.

## Evidence supplied by the owner

These are historical owner reports, not fresh measurements made by this script:

- Camera at `http://192.168.0.10`; accepted User-Agent `OI.Share v2`.
- `get_commandlist.cgi`: API **4.00**, 37 commands. API version is not body firmware version.
- `get_connectmode.cgi`: `private`.
- Listing works for `/DCIM` and `/DCIM/100OLYMP`.
- Direct GET `/DCIM/100OLYMP/PB020002.MOV` works; two downloaded copies reportedly matched a card-reader original.
- USB Storage through the camera can fail/hang, while the same SD card works in a separate reader. Obtain reference originals using that reader.
- Follow-up: two video downloads in parallel each gave roughly 1 MB/s; the owner reports no acceleration. MB versus MiB, single-download reference, exact videos, duration and RF state were not supplied. Do not turn this into a proven fixed 2 MB/s firmware limiter.

| File | Reported original bytes | Fresh duration | Fresh original hash |
| --- | ---: | --- | --- |
| `PB020001.ORF` | 14,692,005 | unavailable | unavailable |
| `PB020001.JPG` | 3,249,056 | unavailable | unavailable |
| `PB020002.MOV` | 8,105,416 | unavailable | unavailable |

The supplied hash text, `2adb950f5ae41bf92fa01f921fb8ca06056ee8094e`, contains **42 hexadecimal characters**. Standard SHA-1 hex has 40; SHA-256 has 64. Its algorithm/value cannot be repaired by guessing. Preserve the text as supplied, but compute new SHA-1 and SHA-256 values from the actual original and downloaded bytes. It is not a usable integrity reference as written.

The live follow-up independently computed full MOV SHA-256 `2adb950f5ae41bf92fa01f921fb8ca06056ee8094e389e83dc266e3ad4877ad0`; the historical text matches its prefix. No card-reader original was available for an independent comparison in that session.

The initial sandboxed GET failed with Windows socket error 10013. The same read-only request outside that isolation reached a four-second connection timeout. That timeout is an availability observation, not a transfer-speed measurement. After the owner said the camera was unavailable, no further camera request was attempted. No original media or earlier Wi-Fi captures were present in the project's `samples/` or `captures/` at inspection.

## Exact firmware inputs

Model **Olympus PEN E-PL9**; displayed version **1.1**, as reported by the owner. Downloaded main internal build **1101**. These are the identified stock download bytes, **not a dump or byte-level verification of the installed camera**.

Container `OLY_E_133_1101_0000_0000.BIN`: **104,552,480 bytes**, SHA-256 `aefab05396c43ecba0551b94a5d31f7e52350c18d6f4bf1d02d75761108e6028`.

All five decoded inputs were independently rehashed for this investigation:

| Kind | Decoded bytes | SHA-256 |
| --- | ---: | --- |
| `0x0100` | 26,214,336 | `8e39c335d54fd8ddea189db82fe708159f43f9995bba42c2cd47dd22b8814267` |
| `0x0101` | 26,214,336 | `ee9a9c3ad1974dd212483ca7d012e51ae23083ce0119589a3b42996aa13ccf1e` |
| `0x0106` | 38,797,248 | `abd9d3f3e8598b3844b9b8d2c06d07ef49d5dbdb4cf00ca5dcaf096dcca659b8` |
| `0x010e` | 219,104 | `1c942d2fb6b8830f0195a0be7464880838ddf08c5f038bad626aed8e72789678` |
| `0x0102` | 13,107,136 | `a0d6a08e79f8a1c731959695ada1f26d52ea1e1c0fc9f234618f795ced061c0f` |

The main analysis mapping is `address = decoded-main file offset + 0x60400020`. Component header/container addresses are not assumed runtime addresses.

The embedded command-list XML starts at main file offset `0xe5c108`, is 11,273 bytes, SHA-256 `f0093e0cfd0974f8979397f2d600711bbf6bf8bdd963685e39ba4209fca47c4b`, declares API `4.00`, and contains exactly **37 `<cgi>` entries**, agreeing with the owner's historical response at this structural level. No byte-for-byte comparison with a saved camera response was possible. Listed movie trim/resize and stream operations do not establish faster original-file transfer and were not invoked.

## Native main-component path

Names below are research labels derived from diagnostic strings and reviewed control flow, not a recovered symbol table. Addresses use the main analysis mapping.

| Site | Observed behavior |
| --- | --- |
| `0x60f2ef7e` | HTTP start; send-buffer allocation passes `16384` at `0x60f2efe2` and loops over four slots. |
| `0x60f2f0eb..0x60f2f17d` | Starts four subtask IDs with arguments 0, 1, 2 and 3. Unused strings for more workers are not evidence they are started. |
| `0x60f2fdfd..0x60f30155` | Header parser recognizes Connection, Content-Type, Content-Length, Host and User-Agent; unrecognized lines proceed to the next header. No Range field is populated here. |
| `0x60f2e027..0x60f2e06e` | MOV MIME selection; `.MOV`/`.mov` produce `video/quicktime`. |
| `0x60f2e14f..0x60f2e198` | ORF MIME selection; `.ORF`/`.orf` lead to `application/octet-stream`. This is MIME selection, not a transfer-rate branch. |
| `0x60f308be..0x60f308c2` | Ordinary file request calls body handler `0x60f30b8c`. |
| `0x60f30b8c` | `do_file_contents` diagnostic; obtains file size, opens file, creates response header, then enters the ordinary body loop for GET. |
| `0x60f30c6c..0x60f30c81` | Chooses `min(remaining,16384)` and invokes the file-read wrapper `0x609ce357` with element size 1; requires the returned byte count to match. |
| `0x60f30c8f..0x60f30ca5` | Calls send-all wrapper `0x60f30d40`, then returns to the next file block. No explicit sleep inside this loop. |
| `0x60f30d40..0x60f30d6b` | Handles short positive sends by advancing pointer/count; calls `0x60f31542` until the block is consumed, or stops on send error. |
| `0x60f31542` | Builds BSD request **6**, publishes buffer address/length/flags and calls synchronous helper `0x60f31364`. |
| `0x60f31364` | Creates reply resources, submits a message at `0x60f313ba`, waits for reply at `0x60f313d8`, then releases resources. Diagnostic names include `isc_bsdapi` and queue errors. |
| `0x60f3092f..0x60f30936` | Calls socket-close wrapper `0x60f316b3` after response handling. |

Schematic for the reviewed successful body path:

```text
remaining = file_size
while remaining > 0:
    n = min(remaining, 16384)
    require(file_read(buffer, 1, n, handle) == n)
    require(send_all(socket, buffer, n) == success)
    remaining -= n
close file
... worker cleanup ...
close socket
```

There is no second file-read buffer/prefetch visible in this loop. Storage and transport services can have internal buffering; their timing has not been measured. A 16 KiB **application** block is not an HTTP chunked-encoding chunk, TCP segment, radio frame, receive window or a numerical throughput cap.

## Embedded ARM TCP path

Common component `0x0106` has a nested resource directory: top row 9 is container address `0x455b4000`, extent `0x400000`; nested row 1 is `0x455b5000`, length **270,336 (`0x42000`) bytes**. Its exact bytes start at decoded-common offset **`0x1ad4fe0`**, SHA-256 **`11f9fe5b597248fc6cc3748d604d4108a316f59cc4381a4af4cff4d5f7452506`**.

ARM little-endian analysis base **`0x00010000`** is supported by coherent absolute dispatch-table entries and MOVW/MOVT references to diagnostic strings, including `isc_bsdapi_main:ISC_receive_wait ER(%d)`. This is a static mapping, not an observed CPU trace. ARM addresses in this section must not be confused with main MN103 addresses.

| ARM site | Static evidence |
| --- | --- |
| `0x268a4` | ISC receive/dispatch loop; request opcodes 1..16 select a table. |
| `0x269a4 + 5*4` | Request 6 table word is `0x26a78`; that thunk selects handler `0x2667c`. |
| `0x2667c..0x266dc` | Prepares the shared buffer through `0x2bb28`, loads socket/buffer/count/flags, calls `0x12e54`, stores result, sends a reply, then clears the packet-slot busy byte. |
| `0x12e54..0x12f18` | BSD send wrapper dispatches according to socket type; the stream-socket branch reaches `0x12bcc`. |
| `0x12bcc..0x12cf0` | Stream send further divides data using a per-connection limit at TCP object `+0x64`, repeatedly calling `0x1e9a8`. Its actual live value is unknown. |
| `0x1e9a8..0x1ec18` | TCP queue routine compares requested amount with capacity and free space (`capacity - queued` at `0x1ea14..0x1ea24`); waits through `0x35c9c` when space is insufficient, copies data into a circular buffer and schedules transport work. |
| `0x1f138` | Binds buffer pointers/capacities, including send capacity at object `+0xc4`. |
| `0x13e0c..0x13e38` | Initialization fills a bank of ten socket buffer descriptors with `0x8000` (32 KiB) lengths. This is compiled initialization evidence; binding and occupancy of the live HTTP socket have not been observed. |

Thus a whole 16 KiB HTTP block is not necessarily an all-or-nothing TCP queue wait. Lower send code splits it again. Nor is synchronous IPC proof of stop-and-wait radio behavior. A claim that delayed ACK, Nagle, a 32 KiB window or a fixed radio rate is **the** cause would exceed the evidence.

## Reproduce the offline audit

New script: `scripts/epl9_wifi_firmware.py`. It verifies the exact stock container, all five decoded components, embedded module hash/descriptors, XML shape, 20 MN103 instruction anchors, 16 ARM anchors and the request-6 dispatch word. It writes listings and extracted firmware XML only below ignored `local/`.

```powershell
.\.venv\Scripts\python.exe .\scripts\epl9_wifi_firmware.py `
  --out .\local\wifi-firmware-new `
  --arm-package-dir .\local\wifi-python
```

Verified output for this session: `local/wifi-firmware-20261102-v2/audit.json` and twelve TSV windows. Raw listings/XML are deliberately not committed. `--no-disassembly` permits identity/string/XML inspection without the native reader; omit `--arm-package-dir` if Capstone is absent.

The MN103 reader provenance is in `docs/mn103-tooling.md`: pinned GNU binutils 2.45 sources and local adapter. The existing external checkout `references/oly_fw_analysis` remains at `539fcf1fa9eda5fdef8ede4deeab94a4691d94c3`; no PEN-F code offsets or patches were applied to E-PL9.

ARM decoding used the separate local dependency [Capstone 5.0.6](https://github.com/capstone-engine/capstone), packaged as `capstone-5.0.6-py3-none-win_amd64.whl`, SHA-256 `761c3deae00b22ac697081cdae1383bb90659dd0d79387a09cf5bdbb22b17064`. The PyPI wheel was extracted into ignored `local/wifi-python`; the shared project venv was not modified. This is package/hash provenance, not a publisher-signature claim. No third-party source was copied into the project's public scripts.

## Measurement tool and next camera session

`scripts/epl9_wifi_bench.py` uses only four allowlisted metadata GETs and the three exact original paths. It never changes modes/properties, invokes trim/resize/erase/poweroff, mounts camera USB Storage or flashes firmware. It bypasses proxy configuration and sends the established User-Agent. Outputs, headers and media stay in a **new** directory under ignored `local/`.

After copying originals through the **card reader** into an ignored local folder:

```powershell
.\.venv\Scripts\python.exe .\scripts\epl9_wifi_bench.py `
  --out .\local\wifi-measure-new `
  --original-root .\samples\card-reader-20261102 `
  --repeats 3 --range-probe
```

The three expected names/sizes are fixed to the owner's reported test set; a replacement sample requires an explicit edit. If references are omitted, later copies are compared with the first complete camera copy and are explicitly **not** marked verified against a card-reader original.

The tool records connection/header/first-body/total times, body byte count, MiB/s, Mbit/s, SHA-1, SHA-256, response headers and timestamped application read events. Hashing and disk output occur after each network timer. A partial/error result is retained as `.incomplete`; a failed whole-original transfer stops the run. Maximum byte counts and deadlines bound each request. Range probes request both a zero and nonzero 64 KiB interval; a 200/full-body response is capped and recorded as ignored/invalid, never used as evidence of acceleration. A valid 206 additionally needs correct `Content-Range`, total size, exact length and matching reference bytes.

Parallel tests download **different whole files**, with at most three connections. They do not split an original into parts. Group network-span timing and same-files serial comparisons are recorded. Serial trials precede parallel trials, so storage caching, RF drift and camera state can confound a result. Repeat comparisons in a separate session/order before treating a speedup as reproducible. None of these camera behaviors has been tested by this session.

Useful discriminating measurements once the camera is available:

| Question | Required observation | What it would support |
| --- | --- | --- |
| Host client overhead? | Repeat with `--read-size 8192`, `65536`, `262144`; same files, distance and camera state. | A repeatable change implicates client buffering/call overhead; it does not alter the server's 16 KiB block. |
| Shared radio/TCP bottleneck or per-request overhead? | Preserve the owner's no-benefit parallel result; obtain timing/TCP evidence for the same reference transfer when available. | Approximately equal sharing is consistent with a shared limit; it does not identify RF, CPU/ISC, TCP or storage as its cause. Repeating parallelism is not the current optimization priority. |
| Storage/cache cost? | First vs later ORF/MOV downloads and card-reader sequential reads of the same files. | Repeatably faster later downloads supports caching; card-reader speed alone cannot establish the camera's SD speed. |
| RF/link limitation? | Save Wi-Fi signal, channel and negotiated Tx/Rx link rates locally before/after; repeat close to camera. | Correlated goodput change supports an RF/link contribution. A displayed PHY rate is not file goodput. |
| TCP flow control/loss/ACK timing? | Capture the same transfer with Wireshark; inspect `ip.addr == 192.168.0.10 && tcp.port == 80`. | Sender bursts/pauses, retransmissions, advertised windows and ACK timing can distinguish hypotheses. Application read sizes cannot. |
| HTTP range/persistence supported at runtime? | Exact bounded range probes and observed connection close/second-request behavior. | Determines whether a partial/reuse client strategy is available. Static absence is not a substitute for this check. |

The client baseline remains direct original GET with streamed byte handling and hash verification against the reader. Parallelism is not an acceleration recommendation after the owner's report. The follow-up prioritizes the existing `rd` file-read path, reuse of ISC reply resources and qualified TCP enqueue batching. No performance gain is promised.

Synthetic validation: **14 tests passed** with `python -m unittest discover -s scripts -p test_epl9_wifi_bench.py -v`. The tests use an in-memory HTTP transport and exercise short reads, truncation, corruption, ignored and incorrect ranges, incomplete transfers, response caps, forbidden endpoints, malformed ranges and a complete synthetic serial/parallel measurement manifest. They do not contact a camera or establish its behavior.
