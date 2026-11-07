# Offline browser client: architecture decision

Current source status, 2026-11-04: [project status](project-status.md) summarizes newer reported Wi-Fi rd/ISC work and its unpublished-source/throughput limits. The architecture distinction below remains valid; byte-preserving offline optimizations do not establish faster camera downloads or phone/browser firmware installation.

This is the second research priority, after in-camera film looks and ART.

The requested model is feasible for the interface: load a small HTTPS web app once, cache its HTML/CSS/JavaScript and recipe data with a service worker, then open it while connected to the camera's Wi-Fi without internet access. A cached interface still needs a working transport to the camera for new listings and downloads.

The separate question is whether browser JavaScript can read the camera's HTTP API. Before choosing a browser-only implementation, measure the E-PL9's actual response headers, required request headers, redirects, range handling and behavior in the target phone's browser.

Current Chromium [Local Network Access](https://developer.chrome.com/docs/modern-web-guidance/guides/security/local-network-access) can allow an HTTPS page to contact an HTTP device on the local network after user permission. Standard CORS still applies when reading cross-origin responses. A service worker cache does not remove that restriction.

Preferred path if the stock camera supports the required browser requests:

1. Cache a dependency-light app shell and recipe library.
2. Connect to the camera on an explicit user action.
3. Load the catalog separately from lazy thumbnails and selected original files.
4. Cache metadata/previews and record completed downloads.
5. Measure one transfer against bounded concurrency; add resume only if actual Range behavior supports it.

If the stock API is not readable cross-origin, evaluate a local companion service or a separately researched camera HTTP-server change. Do not promise a fully browser-only client until this is tested. No site has been built or deployed in this phase.
