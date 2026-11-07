// Offline E133 UI runner. Uses the pinned, ignored OM-Emu checkout; no camera I/O.
// node --import ./scripts/epl9_omemu_windows.mjs scripts/epl9_omemu_ui.mjs OUT PATCH|- ACTION...
// Actions: button name, mode:ART, mode:P, wait:milliseconds.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import zlib from 'node:zlib';

const [outArg, patchArg, ...actions] = process.argv.slice(2);
const project = fileURLToPath(new URL('../', import.meta.url));
const local = path.resolve(project, 'local');
const out = outArg && path.resolve(outArg);
if (!out || !patchArg || !out.startsWith(local + path.sep) || fs.existsSync(out))
  throw new Error('Usage: new output directory inside local/, patch JSON or -, then actions');
process.env.OM_EMU_MODEL = 'E133';
const upstream = new URL('../references/om-emu/emu/', import.meta.url);
const upstreamCommit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: fileURLToPath(new URL('../', upstream)), encoding: 'utf8' }).trim();
if (upstreamCommit !== '147ca89c60b24774f3145c2813d79714e0f0b7b7') throw new Error('wrong OM-Emu revision');
const imp = p => import(new URL(p, upstream).href);
const { loadImage, loadBlock, loadNand, patchedFirmware, readPatchFiles } = await imp('checks/lib/env.mjs');
const { Player } = await imp('src/lab/player.mjs');
const { MODE_DIAL } = await imp('src/lab/play.mjs');
const { PLAYER_PARSER } = await imp('scenarios/session_replay.mjs');
const { write_png } = await imp('checks/lib/png.mjs');
const { words_to_rgb } = await imp('src/lab/display.mjs');
const { blobs } = await imp('src/lab/resources.mjs');
const { MODEL, MODEL_INFO } = await imp('src/fw/model.mjs');
const { disasm } = await imp('src/lab/hle.mjs');
const firmware = patchArg === '-' ? { rom: loadImage(), resBlock: loadBlock(), summary: null } :
  patchedFirmware(readPatchFiles([path.resolve(patchArg)]));
const env = { rom: firmware.rom, resBlock: firmware.resBlock, nand: loadNand(), createHash,
  deflate: (b, level) => new Uint8Array(zlib.deflateSync(b, { level })),
  inflate: b => new Uint8Array(zlib.inflateSync(b)), wallClock: () => performance.now() / 1000 };
const player = new Player({ ...PLAYER_PARSER, no_browser: true, idle: 'off', a15: 'on',
  out, no_wait_on_error: true, device: 'tft' }, env);
const report = { model: MODEL, version: MODEL_INFO.version, upstream_commit: upstreamCommit,
  runner_sha256: createHash('sha256').update(fs.readFileSync(fileURLToPath(import.meta.url))).digest('hex'),
  stock_main_sha256: MODEL_INFO.rom_sha256, stock_resource_prefix_sha256: MODEL_INFO.res_sha256,
  node: process.version, patch: firmware.summary, actions, frames: [], error: null,
  camera_accessed: false, hardware_pixel_execution: false };
fs.mkdirSync(out);
const save = () => fs.writeFileSync(path.join(out, 'session.json'), JSON.stringify(report, null, 2) + '\n');
try {
  player.open_session();
  const s = player.session, lab = s.lab;
  // MenuLab.harvest clears the engine's diagnostic ring. Capture before each
  // clear as well as at frame boundaries; a current counter alone misses faults.
  const engineErrors = [];
  const clearEngine = lab.engine.clear.bind(lab.engine);
  lab.engine.clear = () => { engineErrors.push(...lab.engine.errors()); clearEngine(); };
  report.engine_error_capture = 'before each diagnostic clear and at frame boundaries, after bring-up';
  // Observe after bring-up only, never replace a stand-in or synthesize execution.
  const filmSites = [0x60752202,0x6079d7f4,0x6079fb88,0x6074f352,0x6079c017];
  const hits = Object.fromEntries(filmSites.map(a => ['0x' + a.toString(16), 0]));
  report.film_hook_observation = 'after Player.open_session, counts include stock call sites';
  for (const at of filmSites) {
    if (lab.hooks.has(at)) throw new Error('film observation conflicts with an emulator hook');
    lab.observe(disasm(at), () => { hits['0x' + at.toString(16)]++; }, 'epl9-film-site-observer');
  }
  // E133 resource banks established by our independent OSD audit. OM-Emu's
  // menudata.image_info assumes another model's word-1 bitmap table layout.
  const banks = blobs(firmware.resBlock);
  if (banks[0][0] !== 0xa3091000 || banks[1][0] !== 0xa3611000)
    throw new Error('unexpected E133 OSD load banks');
  const slots = [[4387,0x158024],[4388,0x15849c],[4420,0x105cdb8],[4421,0x105d4a0],
    [4458,0x15eb24],[4459,0x15ef9c],[4556,0x106d508],[4557,0x106d744]];
  const targets = new Map(slots.map(([id, offset]) => {
    const bank = offset < 0xcaf7e0 ? 0 : 1, base = bank ? 0xcaf7e0 : 0x7e0;
    if (offset - base + 4 > banks[bank][1].length) throw new Error('icon outside OSD bank');
    return [banks[bank][0] + offset - base, id];
  }));
  let firstDraw = 0;
  const idle = ms => s.idle_slice(lab.lab_time() + ms * 1e6);
  const record = action => {
    const [w, h, raw] = s.frame('boundary', true);
    const words = new Uint32Array(raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength));
    const name = String(report.frames.length).padStart(3, '0') + '-' + action.replace(/[^a-zA-Z0-9_-]/g, '_');
    write_png(path.join(out, name + '.png'), w, h, words_to_rgb(words));
    const draws = lab.draw_log.slice(firstDraw); firstDraw = lab.draw_log.length;
    let palette = null;
    // E133's VSC has fewer mapped palette registers than the generic dumper.
    // Retain the diagnostic failure instead of assuming another body's banks.
    if (!report.palette_dump_error) try {
      const dump = lab.dump('tft');
      palette = { displayed: dump.displayed_palette,
        banks: Array.from({length:6}, (_, bank) => Object.fromEntries([0,4,22,103].map(i => [i, dump.palette[bank * 256 + i]]))) };
    } catch (e) { report.palette_dump_error = e.message; }
    const row = { action, gui: '0x' + lab.state().toString(16), state: lab.state_names.get(lab.state()),
      width: w, height: h, sha256: createHash('sha256').update(raw).digest('hex'), png: name + '.png',
      engine_errors_total: engineErrors.length + lab.engine.error_total(), engine_errors: [...engineErrors, ...lab.engine.errors()],
      film_site_hits: { ...hits }, palette,
      a15: s.a15_last, target_draws: draws.filter(d => d.op === 'bitmap' && targets.has(d.data))
        .map(d => ({ ...d, id: targets.get(d.data), lut: d.lut && Array.from(d.lut) })),
      palette_events: draws.filter(d => d.op.startsWith('palette') || d.op === 'GPISetPalette'),
      labels: [...new Set(draws.filter(d => d.op === 'text').map(d => d.text))] };
    row.inline_targets = [...new Set(row.labels.flatMap(t => (t?.match(/@A07[67]@/g) ?? [])))];
    // This exact format-10 draw already fails on unmodified E133 after S1.
    // Keep every occurrence, compare its full history with stock, refuse others.
    row.unexpected_engine_errors = row.engine_errors.filter(e => !(e.code === 18 && e.pc === 1626478003 &&
      e.arg === 536871728 && e.value === 10 && e.words.join(',') === '536871728,2736502948,4280856136,14'));
    report.frames.push(row); save();
    console.log(JSON.stringify({ action, state: row.state, png: row.png, targets: [...new Set(row.target_draws.map(d => d.id))] }));
    if (row.unexpected_engine_errors.length) throw new Error('OSD engine reported errors beyond the exact stock BMP_LUT baseline; see session.json');
  };
  idle(1500); report.mode_dial = MODE_DIAL.names; record('start');
  for (const action of actions) {
    if (action.startsWith('mode:')) {
      const value = action.slice(5);
      const index = MODE_DIAL.names.findIndex(x => x.label === value || x.name === value);
      if (index < 0) throw new Error('unknown mode ' + value);
      s.switch_input('mode_dial', index); s.camapp.pump(); idle(1200);
    } else if (action.startsWith('wait:')) {
      const ms = Number(action.slice(5));
      if (!Number.isFinite(ms) || ms < 0 || ms > 10000) throw new Error('wait must be 0..10000 ms');
      idle(ms);
    } else {
      s.key(action, 'down'); s.camapp.pump(); idle(150);
      s.key(action, 'up'); s.camapp.pump(); idle(1200);
    }
    record(action);
  }
  report.assumptions = [...lab.assumptions_in_use].sort();
} catch (e) {
  report.error = { message: e.message, stack: e.stack }; process.exitCode = 1; console.error(e.stack);
  if (player.session?.lab) {
    const s = player.session, lab = s.lab;
    report.failed_gui = { state: lab.state(), name: lab.state_names.get(lab.state()), a15: s.a15_last };
    report.assumptions = [...lab.assumptions_in_use].sort();
  }
} finally {
  try { player.close_session(); } catch (e) { report.close_error = e.message; process.exitCode = 1; }
  save();
}
