// `node server/serve.mjs` (PORT, default 8098): the built app (dist/) + the AI API. Keys come from .env or the environment, never the browser.
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
try {
  for (const line of readFileSync(join(root, '.env'), 'utf8').split(/\r?\n/)) {
    const [, key, value] = /^\s*([A-Z0-9_]+)\s*=\s*["']?(.*?)["']?\s*$/.exec(line) || [];
    if (value && !(key in process.env)) process.env[key] = value;
  }
} catch { /* no .env */ }
const { identify, segment, choreograph, transcribe, exhibit } = await import('./ai.mjs');
const { configured } = await import('./meta.mjs');

const web = join(root, 'dist') + sep;
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.glb': 'model/gltf-binary', '.ktx2': 'image/ktx2', '.wasm': 'application/wasm' };
const send = (res, code, body) => { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(body)); };
async function body(req, max) {
  const chunks = []; let n = 0;
  for await (const c of req) { if ((n += c.length) > max) throw Object.assign(new Error('body too large'), { status: 413 }); chunks.push(c); }
  if (!n) throw Object.assign(new Error('empty body'), { status: 400 });
  return Buffer.concat(chunks);
}
const str = (v, max) => (typeof v === 'string' ? v : '').slice(0, max);

// Spend guard for a public build: model-backed calls per visitor and per server, per UTC day.
// cf-connecting-ip can be spoofed without Cloudflare in front, so the server-wide cap is the real ceiling.
let spend = { day: '', all: 0, by: new Map() };
export function overBudget(who, day = new Date().toISOString().slice(0, 10)) {
  if (spend.day !== day) spend = { day, all: 0, by: new Map() };
  const n = (spend.by.get(who) || 0) + 1;
  if (n > Number(process.env.DAILY_LIMIT || 200) || spend.all >= Number(process.env.CAP_PER_DAY || 2000)) return true;
  spend.by.set(who, n); spend.all++;
  return false;
}

async function api(req, res, path, q) {
  if (path === '/api/status') return send(res, 200, { meta: configured() });
  if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
  if (overBudget(String(req.headers['cf-connecting-ip'] || req.socket.remoteAddress))) return send(res, 429, { error: '今天的 AI 額度用完了，明天再來。' });
  const [mime] = (req.headers['content-type'] || '').toLowerCase().split(/\s*;/);
  try {
    if (path === '/api/identify' || path === '/api/segment') {   // raw photo upload; photos are never saved
      if (!/^image\/(jpeg|png|webp)$/.test(mime)) return send(res, 415, { error: 'image body expected' });
      const image = (await body(req, 6 << 20)).toString('base64');
      if (path === '/api/identify') return send(res, 200, await identify({ image, mime }));
      return send(res, 200, await segment({ image, mime, exhibit: str(q.get('exhibit'), 20), parts: q.getAll('part').map((p) => str(p, 40)) }));
    }
    if (path.endsWith('/stt')) {
      if (mime !== 'audio/wav') return send(res, 415, { error: 'audio/wav body expected' });
      return send(res, 200, await transcribe({ wav: await body(req, 2 << 20), exhibit: str(q.get('exhibit'), 20) }));
    }
    if (path === '/api/ask') {
      const b = JSON.parse(await body(req, 32 << 10));
      exhibit(str(b.exhibit, 20));   // unknown exhibit -> 400 before any model call
      const history = (Array.isArray(b.history) ? b.history : []).slice(-4).map((m) => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: str(m.content, 400) }));
      return send(res, 200, await choreograph({ exhibit: b.exhibit, text: str(b.text, 300), pointed: str(b.pointed, 60), history }));
    }
    return send(res, 404, { error: 'unknown endpoint' });
  } catch (e) {
    const code = [400, 413, 415, 503].includes(e.status) ? e.status : e instanceof SyntaxError ? 400 : 502;
    console.error(`${new Date().toISOString()} ${path} ${code} ${e.name === 'TimeoutError' ? 'timeout' : String(e.message).slice(0, 120)}`);   // never bodies or keys
    return send(res, code, { error: String(e.message).slice(0, 160) });
  }
}

export const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  let path = decodeURIComponent(url.pathname);
  if (path.startsWith('/api/')) return api(req, res, path, url.searchParams);
  if (path.endsWith('/')) path += 'index.html';
  const file = join(web, normalize(path));
  if (!file.startsWith(web)) { res.writeHead(403); return res.end(); }
  let data;   // read before writing headers: a missing file must still be able to answer 404
  try { data = await readFile(file); } catch { return res.writeHead(404).end('not found'); }
  res.writeHead(200, { 'Content-Type': TYPES[extname(file)] || 'application/octet-stream' }).end(data);
});
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const port = Number(process.env.PORT) || 8098;
  server.listen(port, () => console.log(`Mechanica: http://localhost:${port}  (Meta ${configured() ? 'ready' : 'key not set'})`));
}
