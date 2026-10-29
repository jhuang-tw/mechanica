// Spoken answers (Meta Model API has no text-to-speech yet): Inworld TTS-2 Flash when INWORLD_API_KEY is set,
// else Azure neural voices. Taiwan Mandarin for Chinese, English otherwise; the browser's own voice is the fallback.
const env = (k, d = '') => (process.env[k] || '').trim() || d;
const inworld = () => !!env('INWORLD_API_KEY');
const azure = () => !!env('AZURE_SPEECH_KEY') && !!(env('AZURE_SPEECH_REGION') || env('AZURE_SPEECH_ENDPOINT'));
export const configured = () => inworld() || azure();
const fail = (message, status = 502) => { const e = new Error(message); e.status = status; return e; };

export const isZh = (text) => /[㐀-鿿]/.test(text);
const xml = (s) => s.replace(/[<>&'"]/g, (c) => `&#${c.charCodeAt(0)};`);

// The same lines (intros, lesson steps) come back again and again: keep their audio, pay for them once.
const cache = new Map();
let chars = { day: '', n: 0 };

// -> MP3 bytes as an async iterator, so playback can start on the first chunk
export async function* speech(text, ms = 8000) {
  if (!configured()) throw fail('no TTS key set', 503);
  const zh = isZh(text), key = `${zh}|${text}`;
  if (cache.has(key)) return yield cache.get(key);
  const day = new Date().toISOString().slice(0, 10);
  if (chars.day !== day) chars = { day, n: 0 };
  if ((chars.n += text.length) > Number(env('TTS_CHARS_PER_DAY', '15000'))) throw fail('daily speech budget used up', 429);
  const parts = [];
  for await (const c of (inworld() ? fromInworld : fromAzure)(text, zh, ms)) { parts.push(c); yield c; }
  if (cache.size >= 300) cache.delete(cache.keys().next().value);
  cache.set(key, Buffer.concat(parts));
}

// Inworld streams NDJSON lines, each carrying a base64 MP3 chunk in result.audioContent (an error can follow a 200)
async function* fromInworld(text, zh, ms) {
  const res = await fetch(`${env('INWORLD_BASE_URL', 'https://api.inworld.ai').replace(/\/$/, '')}/tts/v1/voice:stream`, {
    method: 'POST', signal: AbortSignal.timeout(ms),
    headers: { Authorization: `Basic ${env('INWORLD_API_KEY')}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text, modelId: env('INWORLD_MODEL', 'inworld-tts-2-flash'), language: zh ? 'zh-TW' : 'en-US',
      voiceId: zh ? env('INWORLD_VOICE_ZH', 'Xinyi') : env('INWORLD_VOICE_EN', 'Ashley'),
      audioConfig: { audioEncoding: 'MP3', sampleRateHertz: 24000, bitRate: 48000 },
    }),
  });
  if (!res.ok) throw fail(`Inworld TTS HTTP ${res.status}`, [401, 403].includes(res.status) ? 503 : 502);
  let buf = '';
  const line = (l) => {
    if (!l.trim()) return null;
    const m = JSON.parse(l);
    if (m.error) throw fail(`Inworld TTS ${m.error.code}: ${String(m.error.message).slice(0, 80)}`);
    return m.result?.audioContent ? Buffer.from(m.result.audioContent, 'base64') : null;
  };
  for await (const c of res.body.pipeThrough(new TextDecoderStream())) {
    const lines = (buf += c).split('\n'); buf = lines.pop();
    for (const l of lines) { const a = line(l); if (a?.length) yield a; }
  }
  const a = line(buf); if (a?.length) yield a;
}

async function* fromAzure(text, zh, ms) {
  const voice = zh ? env('AZURE_TTS_VOICE_ZH', 'zh-TW-HsiaoChenNeural') : env('AZURE_TTS_VOICE_EN', 'en-US-AvaMultilingualNeural');
  const lang = zh ? 'zh-TW' : 'en-US';
  const res = await fetch(`${env('AZURE_SPEECH_ENDPOINT', `https://${env('AZURE_SPEECH_REGION')}.tts.speech.microsoft.com`).replace(/\/$/, '')}/cognitiveservices/v1`, {
    method: 'POST', signal: AbortSignal.timeout(ms),
    headers: { 'Ocp-Apim-Subscription-Key': env('AZURE_SPEECH_KEY'), 'Content-Type': 'application/ssml+xml', 'X-Microsoft-OutputFormat': 'audio-24khz-48kbitrate-mono-mp3', 'User-Agent': 'mechanica' },
    body: `<speak version="1.0" xml:lang="${lang}"><voice name="${xml(voice)}"><prosody rate="+5%">${xml(text)}</prosody></voice></speak>`,
  });
  if (!res.ok) throw fail(`Azure TTS HTTP ${res.status}`, [401, 403].includes(res.status) ? 503 : 502);
  yield* res.body;
}
