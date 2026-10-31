// Browser media helpers: hold-to-talk recording as 16 kHz mono WAV (what Meta speech-to-text takes),
// a phone photo shrunk to a small JPEG, and spoken answers.

export class Recorder {
  async start() {
    this.stream ||= await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    this.chunks = [];
    this.rec = new MediaRecorder(this.stream);
    this.rec.ondataavailable = (e) => this.chunks.push(e.data);
    this.rec.start();
  }
  // resolves to a WAV blob, or null when the clip is too short to be speech
  stop() {
    return new Promise((ok) => {
      if (!this.rec || this.rec.state === 'inactive') return ok(null);
      this.rec.onstop = async () => {
        const blob = new Blob(this.chunks, { type: this.rec.mimeType });
        ok(blob.size < 2000 ? null : await toWav(blob).catch(() => null));
      };
      this.rec.stop();
    });
  }
}

export async function toWav(blob, rate = 16000) {
  const src = await new AudioContext().decodeAudioData(await blob.arrayBuffer());
  const off = new OfflineAudioContext(1, Math.ceil(src.duration * rate), rate);
  const node = off.createBufferSource(); node.buffer = src; node.connect(off.destination); node.start();
  const pcm = (await off.startRendering()).getChannelData(0), v = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  str(0, 'RIFF'); v.setUint32(4, 36 + pcm.length * 2, true); str(8, 'WAVEfmt '); v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true); str(36, 'data'); v.setUint32(40, pcm.length * 2, true);
  pcm.forEach((s, i) => v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, s)) * 0x7fff, true));
  return new Blob([v], { type: 'audio/wav' });
}

// 768 px JPEG (~80 kB): enough for the vision model, quick on a phone connection
export async function shrink(file, max = 768) {
  const img = await createImageBitmap(file), k = Math.min(1, max / Math.max(img.width, img.height));
  const c = Object.assign(document.createElement('canvas'), { width: Math.round(img.width * k), height: Math.round(img.height * k) });
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
  return new Promise((ok) => c.toBlob(ok, 'image/jpeg', 0.8));
}

// Spoken answers: the server's neural voice (Inworld MP3) when it has one, else the most natural voice this browser has.
const zh = (text) => /[㐀-鿿]/.test(text);
let neural = fetch('/api/status').then((r) => r.json()).then((s) => !!s.tts).catch(() => false);
const audio = typeof Audio === 'undefined' ? null : new Audio();
export function unlockSpeech() {   // call from the first tap: phones only let a page play sound it started from a gesture
  window.speechSynthesis?.speak(new SpeechSynthesisUtterance(''));
  if (audio) { audio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA='; audio.play().catch(() => {}); }
}

let said = 0;
// Whole MP3 per line, played from a blob: streaming into <audio> stutters on phones (Safari wants byte ranges a stream can't give).
const clips = new Map();
function clip(text) {
  const key = text.slice(0, 400);
  if (!clips.has(key)) {
    if (clips.size > 60) { const [k, v] = clips.entries().next().value; clips.delete(k); v.then((u) => u && URL.revokeObjectURL(u)); }
    clips.set(key, fetch(`/api/tts?text=${encodeURIComponent(key)}`).then(async (r) => (r.ok && /audio/.test(r.headers.get('content-type')) ? URL.createObjectURL(await r.blob()) : null)).catch(() => null));
  }
  return clips.get(key).then((u) => { if (!u) clips.delete(key); return u; });
}
// resolves when the line has been spoken, or when a newer speak() cut it off
export async function speak(text) {
  const n = ++said;
  audio?.pause();
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  if (!text) return;
  if (audio && await neural) {
    const url = await clip(text);
    if (n !== said) return;
    if (url) {
      audio.src = url;
      try {
        await audio.play();
        return await new Promise((ok) => { audio.onended = audio.onerror = audio.onpause = ok; });
      } catch (e) { if (n !== said || e.name === 'AbortError') return; }
    }
  }
  return browserSpeak(text);   // no neural voice, or it failed
}
// Fetch lines that are about to be spoken (lesson steps), so they start without the synthesis wait.
export async function prefetch(texts) {
  if (audio && await neural) for (const text of texts) await clip(text);
}

// Prefer the cloud "Natural"/"Online"/Google voices browsers ship (Edge: HsiaoChen Online) over the old desktop ones.
const natural = (v) => /natural|online|neural|google/i.test(v.name) * 2 + !v.localService;
function browserSpeak(text) {
  if (!('speechSynthesis' in window)) return Promise.resolve();
  const lang = zh(text) ? 'zh-TW' : 'en-US', all = speechSynthesis.getVoices();
  const pool = zh(text) ? [/zh[-_]TW/i, /^zh/i] : [/^en[-_]US/i, /^en/i];
  const voice = pool.map((re) => all.filter((v) => re.test(v.lang)).sort((a, b) => natural(b) - natural(a))[0]).find(Boolean);
  const u = Object.assign(new SpeechSynthesisUtterance(text), { lang, rate: 1.05 });
  if (voice) u.voice = voice;
  return new Promise((ok) => { u.onend = u.onerror = ok; speechSynthesis.speak(u); });
}
