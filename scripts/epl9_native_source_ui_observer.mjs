// Passive native-source-v1 observer extension for the unchanged E133 UI runner.
// node --import ./scripts/epl9_native_source_ui_observer.mjs scripts/epl9_omemu_ui.mjs ...
// Host-only changes bind the exact parsed patch bytes, runtime and written PNGs
// to session metadata, and add a passive WB observer. No CPU, firmware,
// resource, device or successful-return model is replaced here.
import fs from 'node:fs';
import { registerHooks } from 'node:module';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const runner = new URL('./epl9_omemu_ui.mjs', import.meta.url).href;
const expected = 'e58bd4039fb55ca1388dd287bc2139d0fa67d7015d369c8393429a7004a0a047';
const digest = text => createHash('sha256').update(text).digest('hex');
const upstream = new URL('../references/om-emu/', import.meta.url).href;
const dependencies = [];
const dependencyUrls = new Set();
const dependencyKey = Symbol.for('epl9.native-source-v1.ui-runtime-dependencies');
if (globalThis[dependencyKey]) throw new Error('native-source UI observer registered twice');
globalThis[dependencyKey] = dependencies;
const metadata = {
  name: 'native-source-v1-ui-input-frame-binding-v2',
  source_sha256: digest(fs.readFileSync(fileURLToPath(import.meta.url))),
  base_runner_sha256: expected,
  extra_observed_sites: ['0x60761c9e'],
  input_and_frame_binding_schema: 'epl9-ui-input-frame-binding-v2',
  cpu_or_firmware_modified: false,
};
const sites = 'const filmSites = [0x60752202,0x6079d7f4,0x6079fb88,0x6074f352,0x6079c017];';
const report = "report.film_hook_observation = 'after Player.open_session, counts include stock call sites';";
const firmware = 'const firmware = patchArg ===';
const patches = 'patchedFirmware(readPatchFiles([path.resolve(patchArg)]));';
const png = "write_png(path.join(out, name + '.png'), w, h, words_to_rgb(words));";
const pngField = "png: name + '.png',";
const binding = `const epl9PatchPath = patchArg === '-' ? null : path.resolve(patchArg);
const epl9PatchBytes = epl9PatchPath && fs.readFileSync(epl9PatchPath);
const epl9PatchRows = epl9PatchBytes && (await imp('src/fw/patch.mjs')).readPatchText(epl9PatchBytes.toString('utf8'), epl9PatchPath);
const epl9NodeBytes = fs.readFileSync(process.execPath);
const epl9InputBinding = { schema: 'epl9-ui-input-frame-binding-v2',
  patch_files: epl9PatchBytes ? [{ path: epl9PatchPath, bytes: epl9PatchBytes.length,
    sha256: createHash('sha256').update(epl9PatchBytes).digest('hex') }] : [],
  node_executable: { path: process.execPath, bytes: epl9NodeBytes.length,
    sha256: createHash('sha256').update(epl9NodeBytes).digest('hex') },
  frame_binding: 'PNG file bytes and native words_to_rgb bytes hashed immediately after each write' };
`;

registerHooks({
  load(url, context, nextLoad) {
    const loaded = nextLoad(url, context);
    if (url.startsWith(upstream) && loaded.source == null)
      throw new Error('native-source UI observer: loaded runtime source unavailable: ' + url);
    if (url.startsWith(upstream) && !dependencyUrls.has(url)) {
      const bytes = typeof loaded.source === 'string' ? Buffer.from(loaded.source) : Buffer.from(loaded.source);
      dependencies.push({ path: fileURLToPath(url), bytes: bytes.length, sha256: digest(bytes) });
      dependencyUrls.add(url);
    }
    if (url !== runner) return loaded;
    const source = typeof loaded.source === 'string' ? loaded.source : Buffer.from(loaded.source).toString('utf8');
    if (digest(source) !== expected || [sites, report, firmware, patches, png, pngField].some(s => source.split(s).length !== 2))
      throw new Error('native-source UI observer: expected unchanged pinned UI runner');
    return { ...loaded, source: source
      .replace(sites, sites.replace('];', ',0x60761c9e];'))
      .replace(firmware, binding + firmware)
      .replace(patches, 'patchedFirmware(epl9PatchRows);')
      .replace(png, "const epl9Rgb = words_to_rgb(words);\n    write_png(path.join(out, name + '.png'), w, h, epl9Rgb);\n    const epl9Png = fs.readFileSync(path.join(out, name + '.png'));")
      .replace(pngField, pngField + "\n      png_bytes: epl9Png.length, png_sha256: createHash('sha256').update(epl9Png).digest('hex'),\n      png_rgb_sha256: createHash('sha256').update(epl9Rgb).digest('hex'),")
      .replace(report, report + '\n  report.runner_adapter = ' + JSON.stringify(metadata) + ';\n  report.input_binding = epl9InputBinding;\n  report.runtime_dependencies = globalThis[Symbol.for("epl9.native-source-v1.ui-runtime-dependencies")];') };
  },
});
