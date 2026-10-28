// Browser media helpers: hold-to-talk recording as 16 kHz mono WAV (what Meta speech-to-text takes),
// a phone photo shrunk to a small JPEG, and spoken answers.
import { isEn } from './i18n.js';

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

// the page's language picks the voice: Taiwan Mandarin, or English (the natural-sounding system voices first)
let voice;
const pickVoice = (want, any) => {
  const vs = speechSynthesis.getVoices(), good = (v) => /natural|neural|premium|enhanced|google/i.test(v.name);
  return vs.find((v) => want.test(v.lang) && good(v)) || vs.find((v) => want.test(v.lang)) || vs.find((v) => any.test(v.lang));
};
export function speak(text) {
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  if (!text) return;
  voice ||= isEn ? pickVoice(/en[-_]US/i, /^en/i) : pickVoice(/zh[-_]TW/i, /^zh/i);
  const u = Object.assign(new SpeechSynthesisUtterance(text), { lang: isEn ? 'en-US' : 'zh-TW', rate: isEn ? 1 : 1.05 });
  if (voice) u.voice = voice;
  speechSynthesis.speak(u);
}
