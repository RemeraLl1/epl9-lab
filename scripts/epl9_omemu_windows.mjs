// Windows path adapter for OM-Emu 147ca89c. Host paths only; no CPU/firmware changes.
// Use node --import ./scripts/epl9_omemu_windows.mjs <OM-Emu entry point> ...
import { registerHooks } from 'node:module';
import { createHash } from 'node:crypto';

const root = new URL('../references/om-emu/', import.meta.url).href;
const pinned = new Map([
  ['emu/host/blobs.mjs', 'cf7937faba7c6ecb88ab2e5598e6faef1e4ae7101bb74bf3fa1511f34ccdd3e6'],
  ['emu/checks/lib/env.mjs', '1be8a9ddaded24f0cbfce1c61c19efb3bb2668619c046337f4c7a99f84299bd0'],
]);

if (process.platform === 'win32') registerHooks({
  load(url, context, nextLoad) {
    const loaded = nextLoad(url, context);
    const expected = url.startsWith(root) && pinned.get(url.slice(root.length));
    if (!expected) return loaded;
    const text = typeof loaded.source === 'string' ? loaded.source : Buffer.from(loaded.source).toString('utf8');
    if (createHash('sha256').update(text).digest('hex') !== expected)
      throw new Error(`OM-Emu Windows adapter: upstream source changed: ${url}`);
    const pattern = /new URL\(('(?:\.\.\/)+'), import\.meta\.url\)\.pathname/g;
    if ([...text.matchAll(pattern)].length !== 1)
      throw new Error(`OM-Emu Windows adapter: expected one root path: ${url}`);
    return { ...loaded, source: "import { fileURLToPath as epl9FilePath } from 'node:url';\n" +
      text.replace(pattern, 'epl9FilePath(new URL($1, import.meta.url))') };
  },
});
