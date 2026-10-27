// Whole backend against a local mock of the Meta Model API: no key, no paid request.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';

const seen = [];
// the lossless 27×60 example from @meta-sam/parser's README, decoded by the real parser
let samText = "<0f>0<|box;x1=211;y1=228;x2=270;y2=254;w=320;h=334|><|mask;x=0;y=0;data=27,60,~!!!!M!0c[0o91w?q1!pIH4pPRVp2B3'7`e.ioeAf6-k/#Xd8%dX9x(|>";
const meta = createServer(async (req, res) => {
  const chunks = []; for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks), b = /json/.test(req.headers['content-type'] || '') ? JSON.parse(raw) : null;
  seen.push({ url: req.url, auth: req.headers.authorization, b, raw });
  const msg = (message) => res.end(JSON.stringify({ choices: [{ index: 0, message }], model: 'muse-spark-1.3' }));
  if (req.url === '/v1/asr/transcribe') return res.end(JSON.stringify({ transcript: '链条怎么带动后轮' }));
  if (req.url === '/v1/responses') return res.end(JSON.stringify({ status: 'completed', output: [{ content: [{ type: 'output_text', text: b.input[0].content[0].text === 'bicycle chain' ? '' : samText }] }] }));
  const sys = b.messages[0].content, user = b.messages.at(-1).content;
  if (b.tools) return msg({ content: '踩踏板時大盤拉動鏈條，鏈條再帶飛輪和後輪。', tool_calls: [
    ['isolate', { parts: ['chainring', 'chain', 'cassette', 'rear_wheel', 'seat'], at: 0 }],
    ['drive', { drive: 'pedal', speed: 9, duration: 5, at: 1 }],
    ['drive', { drive: 'launch', at: 2 }],
    ['detach', { parts: ['nope'] }],
    ['rotate', { parts: ['rear_wheel'], degrees: 99999, at: 50 }],
  ].map(([name, a], i) => ({ id: 'c' + i, type: 'function', function: { name, arguments: JSON.stringify(a) } })) });
  if (sys.includes('語音辨識')) return msg({ content: '鏈條怎麼帶動後輪' });
  if (JSON.stringify(user).includes('Y2F0')) return msg({ content: '{"match":false,"say":"這是一隻貓。"}' });
  return msg({ content: '```json\n{"match":true,"exhibit":"bike","confidence":0.9,"machine":"公路車","parts":["chain","rear_derailleur","made_up","chain"],"say":"這是公路車，看看鏈條。"}\n```' });
});
await new Promise((ok) => meta.listen(0, ok));
Object.assign(process.env, { META_API_KEY: 'test-key', META_BASE_URL: `http://127.0.0.1:${meta.address().port}/v1`, DAILY_LIMIT: '10' });
const { server, overBudget } = await import('../server/serve.mjs');
await new Promise((ok) => server.listen(0, ok));
const app = `http://127.0.0.1:${server.address().port}`;
const post = (path, body, type = 'application/json') => fetch(app + path, { method: 'POST', headers: { 'Content-Type': type }, body: type === 'application/json' && typeof body !== 'string' ? JSON.stringify(body) : body });

try {
  // photo -> exhibit + visible parts (unknown and duplicate ids dropped); the key went in the header
  let r = await (await post('/api/identify', Buffer.from('bike'), 'image/jpeg')).json();
  assert.deepEqual([r.match, r.exhibit, r.parts, r.say], [true, 'bike', ['chain', 'rear_derailleur'], '這是公路車，看看鏈條。']);
  assert.equal(seen.at(-1).auth, 'Bearer test-key');
  assert.match(seen.at(-1).b.messages[1].content[1].image_url.url, /^data:image\/jpeg;base64,YmlrZQ==$/);
  r = await (await post('/api/identify', Buffer.from('cat'), 'image/jpeg')).json();
  assert.deepEqual([r.match, r.say], [false, '這是一隻貓。']);

  // photo + parts -> one SAM call per part, in parallel; a part with no mask is left out
  const before = seen.length;
  r = await (await post('/api/segment?exhibit=bike&part=rear_derailleur&part=chain', Buffer.from('bike'), 'image/jpeg')).json();
  assert.equal(seen.length - before, 2);
  assert.deepEqual(r.results.map((x) => x.part), ['rear_derailleur']);
  assert.match(r.results[0].masks[0].path, /^M/);
  assert.equal((await post('/api/segment?exhibit=bike&part=engine', Buffer.from('x'), 'image/jpeg')).status, 400);
  samText = "<0f>0<|box;x1=1;y1=1;x2=2;y2=2;w=9;h=9|><|mask;x=0;y=0;data=5000,5000,!!|>";
  r = await (await post('/api/segment?exhibit=bike&part=rear_derailleur', Buffer.from('bike'), 'image/jpeg')).json();
  assert.deepEqual(r.results, [], 'an oversized mask is refused before decoding');

  // question -> demonstration: only known parts / drives, numbers clamped, sorted by time
  r = await (await post('/api/ask', { exhibit: 'bike', text: '鏈條怎麼帶動後輪？' })).json();
  assert.equal(r.say, '踩踏板時大盤拉動鏈條，鏈條再帶飛輪和後輪。');
  assert.deepEqual(r.steps, [
    { do: 'isolate', at: 0, parts: ['chainring', 'chain', 'cassette', 'rear_wheel'] },
    { do: 'drive', at: 1, drive: 'pedal', speed: 1, duration: 5 },
    { do: 'rotate', at: 20, parts: ['rear_wheel'], degrees: 1080, duration: 3 },
  ]);
  const tools = seen.at(-1).b.tools.map((t) => t.function.name);
  assert.deepEqual(tools, ['isolate', 'highlight', 'hide', 'show', 'detach', 'rotate', 'drive', 'reset']);
  assert.equal(seen.at(-1).b.reasoning_effort, 'minimal');
  assert.equal((await post('/api/ask', { exhibit: '__proto__', text: 'x' })).status, 400);
  assert.equal((await post('/api/ask', '{bad', 'application/json')).status, 400);

  // speech -> traditional text with the part vocabulary
  r = await (await post('/api/stt?exhibit=bike', Buffer.from('RIFF'), 'audio/wav')).json();
  assert.equal(r.text, '鏈條怎麼帶動後輪');
  assert.match(seen.at(-1).b.messages[0].content, /鏈條/);
  assert.match(seen.at(-2).raw.toString(), /PUSH_TO_TALK/);

  // spend guard: per-visitor cap, then the whole-server cap; resets the next day
  assert.equal((await post('/api/ask', { exhibit: 'bike', text: 'x' })).status, 200);
  assert.equal((await post('/api/ask', { exhibit: 'bike', text: 'x' })).status, 429);
  assert.equal(overBudget('someone', '2099-01-01'), false);
  process.env.CAP_PER_DAY = '1';
  assert.equal(overBudget('someone-else', '2099-01-01'), true);
  assert.equal((await fetch(app + '/api/status')).status, 200);
  // a missing static file answers 404 and the server stays up (it used to crash with headers already sent)
  assert.equal((await fetch(app + '/assets/missing.js')).status, 404);
  assert.equal((await fetch(app + '/api/status')).status, 200);
  console.log('server ok');
} finally { server.close(); meta.close(); }
