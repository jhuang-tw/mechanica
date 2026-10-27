// Thin client for the Meta Model API (https://dev.meta.ai/docs). The key stays on the server.
// chat(): muse-spark chat completions (text, image, tools); sam(): SAM 3.1 through /responses; asr(): Muse Voice Transcribe.
const env = (k, d = '') => (process.env[k] || '').trim() || d;
const base = () => env('META_BASE_URL', 'https://api.meta.ai/v1').replace(/\/$/, '');
export const configured = () => !!env('META_API_KEY');
const fail = (message, status = 502) => Object.assign(new Error(message), { status });

async function call(path, init, ms) {
  if (!configured()) throw fail('META_API_KEY not set', 503);
  const res = await fetch(base() + path, { ...init, headers: { Authorization: `Bearer ${env('META_API_KEY')}`, ...init.headers }, signal: AbortSignal.timeout(ms) });
  if (!res.ok) throw fail(`Meta HTTP ${res.status}`, [401, 403].includes(res.status) ? 503 : 502);
  return res.json();
}
const post = (path, body, ms) => call(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, ms);

// messages: [{ role, content, image?: { mime, data(base64) } }]; tools: [{ name, description, parameters }]
// muse-spark always reasons and max_tokens includes the reasoning, so every call gets room on top of the answer.
export async function chat({ system, messages, tools, json, maxTokens = 400, quick = true, ms = 15000, temperature = 0.2 }) {
  const r = await post('/chat/completions', {
    model: env('META_MODEL', 'muse-spark-1.3'), temperature, reasoning_effort: quick ? 'minimal' : 'low', max_tokens: maxTokens + 2000,
    messages: [{ role: 'system', content: system }, ...messages.map((m) => ({ role: m.role,
      content: m.image ? [{ type: 'text', text: m.content }, { type: 'image_url', image_url: { url: `data:${m.image.mime};base64,${m.image.data}` } }] : m.content }))],
    ...(tools ? { tools: tools.map((t) => ({ type: 'function', function: t })), tool_choice: 'auto' } : {}),
    ...(json && !tools ? { response_format: { type: 'json_object' } } : {}),
  }, ms);
  const msg = r.choices?.[0]?.message || {};
  const calls = (msg.tool_calls || []).flatMap((t) => { try { return [{ name: t.function.name, args: JSON.parse(t.function.arguments || '{}') }]; } catch { return []; } });
  return { text: typeof msg.content === 'string' ? msg.content.trim() : '', calls, model: r.model };
}

// SAM 3.1: one text prompt + one image -> the provider's mask text (parsed by segment.mjs)
export async function sam({ prompt, mime, image, ms = 20000 }) {
  const r = await post('/responses', { model: 'sam-3.1', stream: false, metadata: { mask_encoding: 'one_bit' },
    input: [{ type: 'message', role: 'user', content: [{ type: 'input_text', text: prompt }, { type: 'input_image', image_url: `data:${mime};base64,${image}` }] }] }, ms);
  if (r.status !== 'completed') throw fail('SAM did not complete');
  return (r.output || []).flatMap((o) => o.content || []).filter((c) => c.type === 'output_text').map((c) => c.text || '').join('');
}

// Muse Voice Transcribe: multipart settings + 16 kHz mono WAV (made in the browser)
export async function asr(wav, ms = 7000) {
  const fd = new FormData();
  fd.append('request', new Blob([JSON.stringify({ model: env('META_STT_MODEL', 'muse-voice-transcribe-1.0'), audioEncoding: 'WAV', mode: 'PUSH_TO_TALK' })], { type: 'application/json' }));
  fd.append('audio', new Blob([wav], { type: 'audio/wav' }), 'clip.wav');
  return String((await call('/asr/transcribe', { method: 'POST', headers: { Accept: 'application/json' }, body: fd }, ms)).transcript || '').trim();
}
