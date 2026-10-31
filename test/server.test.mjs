// Whole backend against a local mock of the Meta Model API: no key, no paid request.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';

const seen = [];
let checkResult = 'found', second = '我看到鏈條掉了。';   // the fix turn's verdict and its second call (null: that call fails)
// the lossless 27×60 example from @meta-sam/parser's README, decoded by the real parser
let samText = "<0f>0<|box;x1=211;y1=228;x2=270;y2=254;w=320;h=334|><|mask;x=0;y=0;data=27,60,~!!!!M!0c[0o91w?q1!pIH4pPRVp2B3'7`e.ioeAf6-k/#Xd8%dX9x(|>";
const meta = createServer(async (req, res) => {
  const chunks = []; for await (const c of req) chunks.push(c);
  const raw = Buffer.concat(chunks), b = /json/.test(req.headers['content-type'] || '') ? JSON.parse(raw) : null;
  seen.push({ url: req.url, auth: req.headers.authorization, b, raw });
  const msg = (message) => res.end(JSON.stringify({ choices: [{ index: 0, message }], model: 'muse-spark-1.3' }));
  if (req.url === '/tts/v1/voice:stream') {   // NDJSON, audio split over two lines, the last line without a newline
    const b64 = Buffer.from(`ID3 ${req.headers.authorization} ${raw}`).toString('base64'), half = Math.ceil(b64.length / 8) * 4;
    return res.end(`{"result":{"audioContent":"${b64.slice(0, half)}"}}\n{"result":{"audioContent":"${b64.slice(half)}"}}`);
  }
  if (req.url === '/cognitiveservices/v1') return res.end(Buffer.from(`ID3 ${req.headers['ocp-apim-subscription-key']} ${raw}`));
  if (req.url === '/v1/asr/transcribe') return res.end(JSON.stringify({ transcript: '链条怎么带动后轮' }));
  if (req.url === '/v1/responses') return res.end(JSON.stringify({ status: 'completed', output: [{ content: [{ type: 'output_text', text: b.input[0].content[0].text === 'bicycle chain' ? '' : samText }] }] }));
  const sys = b.messages[0].content, user = b.messages.at(-1).content;
  if (sys.includes('工具已經跑完')) { if (second) return msg({ content: second }); res.statusCode = 500; return res.end('{}'); }
  if (b.tools?.some((t) => t.function.name === 'check')) return msg({ content: '你說得對，鏈條掉了。', tool_calls: [
    ['check', { result: checkResult, suspect: ['chain', 'nope'] }], ['isolate', { parts: ['chain', 'chainring'] }], ['drive', { drive: 'pedal', duration: 3, at: 0.5 }],
  ].map(([name, a], i) => ({ id: 'k' + i, type: 'function', function: { name, arguments: JSON.stringify(a) } })) });
  if (b.tools?.some((t) => t.function.name === 'grade')) return msg({ content: '對一半：鏈條沒錯，但力量先到齒盤。', tool_calls: [
    ['grade', { verdict: 'partial', concept: '鏈條傳動', gap: '漏了齒盤' }], ['isolate', { parts: ['chainring', 'chain'] }],
    ['ask', { question: '齒盤轉一圈，後輪轉幾圈？', choices: ['不到一圈', '大約三圈', '', 'x', 'y'] }],
  ].map(([name, a], i) => ({ id: 't' + i, type: 'function', function: { name, arguments: JSON.stringify(a) } })) });
  if (b.tools) return msg({ content: '踩踏板時大盤拉動鏈條，鏈條再帶飛輪和後輪。', tool_calls: [
    ['isolate', { parts: ['chainring', 'chain', 'cassette', 'rear_wheel', 'seat'], at: 0 }],
    ['drive', { drive: 'pedal', speed: 9, duration: 5, at: 1 }],
    ['drive', { drive: 'launch', at: 2 }],
    ['detach', { parts: ['nope'] }],
    ['rotate', { parts: ['rear_wheel'], degrees: 99999, at: 50 }],
  ].map(([name, a], i) => ({ id: 'c' + i, type: 'function', function: { name, arguments: JSON.stringify(a) } })) });
  if (sys.includes('講一遍')) return msg({ content: '{"covered":[true,"yes",false],"wrong":"","say":"你講對了踩踏板。"}' });
  if (sys.includes('語音辨識')) return msg({ content: '鏈條怎麼帶動後輪' });
  if (JSON.stringify(user).includes('Y2F0')) return msg({ content: '{"match":false,"say":"這是一隻貓。"}' });
  return msg({ content: '```json\n{"match":true,"exhibit":"bike","confidence":0.9,"machine":"公路車","parts":["chain","rear_derailleur","made_up","chain"],"say":"這是公路車，看看鏈條。"}\n```' });
});
await new Promise((ok) => meta.listen(0, ok));
Object.assign(process.env, { INWORLD_API_KEY: 'aW53b3JsZA==', INWORLD_BASE_URL: `http://127.0.0.1:${meta.address().port}`, AZURE_SPEECH_KEY: 'speech-key', AZURE_SPEECH_ENDPOINT: `http://127.0.0.1:${meta.address().port}`, META_API_KEY: 'test-key', META_BASE_URL: `http://127.0.0.1:${meta.address().port}/v1`, DAILY_LIMIT: '17' });
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

  // tutor turn: grade + demo + next question, choices capped at 3; the learner's record reaches the prompt
  r = await (await post('/api/tutor', { exhibit: 'bike', answer: '鏈條帶後輪', known: [{ concept: '棘輪', verdict: 'wrong' }, { verdict: 'right' }], focus: 'chain' })).json();
  assert.deepEqual([r.grade, r.question, r.steps], [{ verdict: 'partial', concept: '鏈條傳動', gap: '漏了齒盤' }, { q: '齒盤轉一圈，後輪轉幾圈？', choices: ['不到一圈', '大約三圈', 'x'] }, [{ do: 'isolate', at: 0, parts: ['chainring', 'chain'] }]]);
  assert.match(seen.at(-1).b.messages[0].content, /棘輪：答錯[\s\S]*拍了真的鏈條/);
  assert.equal(seen.at(-1).b.messages.at(-1).content, '我的回答：鏈條帶後輪');
  assert.equal((await post('/api/tutor', { exhibit: 'nope' })).status, 400);

  // explain it back: one verdict per lesson step, anything but true counts as missed
  r = await (await post('/api/explain', { exhibit: 'bike', lesson: 'drive', text: '踩踏板曲柄帶齒盤' })).json();
  assert.deepEqual([r.covered, r.say], [[true, false, false, false], '你講對了踩踏板。']);
  assert.match(seen.at(-1).b.messages[0].content, /4 個因果環節[\s\S]*1\. 腳踩踏板/);
  assert.equal((await post('/api/explain', { exhibit: 'bike', lesson: 'nope', text: 'x' })).status, 400);

  // repair challenge: the guess is checked on the model (the answer stays in the system prompt), then the explanation is graded
  r = await (await post('/api/fix', { exhibit: 'bike', fault: 'chain_off', stage: 'diagnose', text: '鏈條掉了吧', pointed: 'chain' })).json();
  assert.deepEqual([r.result, r.suspect, r.steps.map((x) => x.do)], ['found', ['chain'], ['isolate', 'drive']]);
  assert.match(seen.at(-1).b.messages[0].content, /鏈條脫落[\s\S]*壞的零件：鏈條。故障時不會動的零件：飛輪、後輪、前輪/);
  // a miss with no question ends on the exhibit's own clue; a found turn and the explain stage are left alone
  const { withClue } = await import('../server/ai.mjs'), f = { observe: '哪裡斷掉了？' };
  assert.deepEqual([withClue('我看了飛輪。', f, 'close'), withClue('', f, 'not_it'), withClue('飛輪有轉嗎？', f, 'close'), withClue('找到了。', f, 'found'), withClue('好。', f, undefined)],
    ['我看了飛輪。 哪裡斷掉了？', '哪裡斷掉了？', '飛輪有轉嗎？', '找到了。', '好。']);
  assert.equal(seen.at(-2).b.messages.at(-1).content, '我的猜測：鏈條掉了吧（我點了：鏈條）');
  // the spoken line comes from a second call that knows what the model showed; losing that call or leaking the fault keeps the turn
  assert.equal(r.say, '我看到鏈條掉了。');
  assert.match(seen.at(-1).b.messages.at(-1).content, /檢查結果：found。模型上演的：isolate 鏈條、齒盤；drive pedal。運轉時這些零件停著：飛輪/);
  assert.ok(!seen.at(-1).b.tools);
  const guess = async () => { const res = await fetch(app + '/api/fix', { method: 'POST', headers: { 'Content-Type': 'application/json', 'cf-connecting-ip': 'fix-test' }, body: JSON.stringify({ exhibit: 'bike', fault: 'chain_off', stage: 'diagnose', text: '煞車卡住' }) }); assert.equal(res.status, 200); return (await res.json()).say; };
  second = null;
  assert.equal(await guess(), '你說得對，鏈條掉了。');
  checkResult = 'not_it';
  assert.notEqual(await guess(), '你說得對，鏈條掉了。');   // first line named the fault: only the exhibit's clue is left
  second = '鏈條掉了，對吧？';
  assert.ok(!(await guess()).includes('鏈條'));
  second = '煞車有放開，飛輪卻停著。力量到哪裡斷了？';
  assert.equal(await guess(), second);
  checkResult = 'found'; second = '我看到鏈條掉了。';
  const { cleanFix } = await import('../server/ai.mjs'), right = (next, solved) => cleanFix([{ name: 'grade', args: { verdict: 'right', next } }], { id: 'bike', parts: [] }, 'explain', solved).next;
  assert.equal(right('bike/chain_off', ['bike/chain_off']), null, 'the fault just repaired is not next');
  assert.equal(right('heli/tail_shaft', ['bike/chain_off']), 'heli/tail_shaft');
  const { leaks } = await import('../server/ai.mjs'), bare = { parts: [{ id: 'chain', name: 'Chain', aliases: ['bike chain'] }] };
  assert.deepEqual(['The chain slipped', 'Look at the chainring', 'bike chain?'].map((t) => leaks(t, bare, { broken: ['chain'] })), [true, false, true]);
  r = await (await post('/api/fix', { exhibit: 'bike', fault: 'chain_off', stage: 'explain', text: '鏈條把力量傳到後輪', solved: ['bike/chain_off'] })).json();
  assert.deepEqual([r.grade, r.next], [{ verdict: 'partial', gap: '漏了齒盤' }, null]);
  assert.ok(seen.at(-2).b.tools.find((t) => t.function.name === 'grade').function.parameters.properties.next.enum.includes('heli/tail_shaft'));
  assert.equal((await post('/api/fix', { exhibit: 'bike', fault: 'nope', stage: 'diagnose', text: 'x' })).status, 400);

  // speech: Inworld first (Taiwan Mandarin for Chinese, English otherwise), its NDJSON chunks decoded back into one MP3; repeats come from the cache
  let a = await fetch(app + '/api/tts?text=' + encodeURIComponent('這是曲柄'));
  assert.equal(a.headers.get('content-type'), 'audio/mpeg');
  assert.match(await a.text(), /^ID3 Basic aW53b3JsZA== .*"modelId":"inworld-tts-2-flash","language":"zh-TW"/);
  const calls = seen.length;
  a = await (await fetch(app + '/api/tts?text=' + encodeURIComponent('這是曲柄'))).text();
  assert.equal(seen.length, calls, 'cached line makes no new request');
  assert.match(await (await fetch(app + '/api/tts?text=This%20is%20the%20crank')).text(), /"language":"en-US","voiceId":"Ashley"/);
  // without an Inworld key: Azure, text escaped into SSML
  delete process.env.INWORLD_API_KEY;
  assert.match(await (await fetch(app + '/api/tts?text=' + encodeURIComponent('鏈條 <b>'))).text(), /^ID3 speech-key .*zh-TW-HsiaoChenNeural.*鏈條 &#60;b&#62;/);
  assert.match(await (await fetch(app + '/api/tts?text=The%20chain')).text(), /en-US-AvaMultilingualNeural/);
  assert.equal((await fetch(app + '/api/tts?text=')).status, 400);
  assert.equal((await (await fetch(app + '/api/status')).json()).tts, true);

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
