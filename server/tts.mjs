// Spoken answers with Azure neural voices (Meta Model API has no text-to-speech yet).
// Taiwan Mandarin for Chinese, a multilingual English voice otherwise; the browser's own voice is the fallback.
const env = (k, d = '') => (process.env[k] || '').trim() || d;
export const configured = () => !!env('AZURE_SPEECH_KEY') && !!(env('AZURE_SPEECH_REGION') || env('AZURE_SPEECH_ENDPOINT'));
const endpoint = () => env('AZURE_SPEECH_ENDPOINT', `https://${env('AZURE_SPEECH_REGION')}.tts.speech.microsoft.com`).replace(/\/$/, '');
const fail = (message, status = 502) => { const e = new Error(message); e.status = status; return e; };

export const isZh = (text) => /[㐀-鿿]/.test(text);
const xml = (s) => s.replace(/[<>&'"]/g, (c) => `&#${c.charCodeAt(0)};`);

// The same lines (intros, lesson steps) come back again and again: keep their audio, spend the free tier once.
const cache = new Map();
let chars = { day: '', n: 0 };

// -> MP3 bytes as an async iterator, so playback can start on the first chunk
export async function* speech(text, ms = 8000) {
  if (!configured()) throw fail('AZURE_SPEECH_KEY not set', 503);
  const zh = isZh(text), key = `${zh}|${text}`;
  if (cache.has(key)) return yield cache.get(key);
  const day = new Date().toISOString().slice(0, 10);
  if (chars.day !== day) chars = { day, n: 0 };
  if ((chars.n += text.length) > Number(env('TTS_CHARS_PER_DAY', '15000'))) throw fail('daily speech budget used up', 429);
  const voice = zh ? env('AZURE_TTS_VOICE_ZH', 'zh-TW-HsiaoChenNeural') : env('AZURE_TTS_VOICE_EN', 'en-US-AvaMultilingualNeural');
  const lang = zh ? 'zh-TW' : 'en-US';
  const res = await fetch(`${endpoint()}/cognitiveservices/v1`, {
    method: 'POST', signal: AbortSignal.timeout(ms),
    headers: { 'Ocp-Apim-Subscription-Key': env('AZURE_SPEECH_KEY'), 'Content-Type': 'application/ssml+xml', 'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3', 'User-Agent': 'mechanica' },
    body: `<speak version="1.0" xml:lang="${lang}"><voice name="${xml(voice)}"><prosody rate="+5%">${xml(text)}</prosody></voice></speak>`,
  });
  if (!res.ok) throw fail(`Azure TTS HTTP ${res.status}`, [401, 403].includes(res.status) ? 503 : 502);
  const parts = [];
  for await (const c of res.body) { parts.push(c); yield c; }
  if (cache.size >= 300) cache.delete(cache.keys().next().value);
  cache.set(key, Buffer.concat(parts));
}
