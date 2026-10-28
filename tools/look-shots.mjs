// Screenshot every exhibit as the app renders it (dev server + headless Chrome), for before/after look comparisons.
// usage: node tools/look-shots.mjs <out dir> [ids,comma,separated]; `moto:piston_r+crankshaft` shows only those parts, close up   (needs playwright, e.g. NODE_PATH or a global install)
import { createServer } from 'vite';
import { mkdirSync } from 'node:fs';
const { chromium } = await import(process.env.PLAYWRIGHT || 'playwright');

const [out = 'shots', only] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const ids = only?.split(',') ?? (await import('../public/exhibits/index.json', { with: { type: 'json' } })).default.exhibits;
const server = await createServer({ server: { port: 8187 }, logLevel: 'error' });
await server.listen();
const url = server.resolvedUrls.local[0];
const browser = await chromium.launch({ channel: 'chrome', args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on('pageerror', (e) => console.error('page:', e.message));
try {
  for (const shot of ids) {
    const [id, parts] = shot.split(':');
    await page.goto(`${url}?ex=${id}`);
    await page.waitForFunction(() => window.viewer?.rig, null, { timeout: 60000 });
    await page.evaluate(() => { document.getElementById('sheet').style.visibility = 'hidden'; window.viewer.frame(); });
    if (parts) await page.evaluate((p) => {   // only those parts, close up
      const keep = new Set(p.split('+')), v = window.viewer;
      for (const [id, x] of v.rig.parts) if (!keep.has(id)) x.obj.visible = false;
      v.focus([...keep]);
    }, parts);
    await page.waitForTimeout(parts ? 3000 : 1500);
    const name = parts ? `${id}_parts` : id;
    await page.locator('#c').screenshot({ path: `${out}/${name}.png` });
    console.log(name);
  }
} finally { await browser.close(); await server.close(); }
