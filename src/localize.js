// An exhibit in English: manifest.json stays the source (Chinese, ids, numbers, motion) and en.json beside it holds
// only the words, keyed by part / drive / lesson / fault id, so a part added to the manifest never breaks the overlay.
// Shared by the browser (src/main.js) and the server (server/ai.mjs).
//   en.json: { name, title, intro, suggest[], looksLike, ride: { hint },
//              parts: { id: { name, info, aliases[] } }, drives: { id: name },
//              lessons: { id: { title, steps: [{ say, quiz: { q, options: [[text, why]] } }] } },
//              faults: { id: { title, short, symptom, hint, suspects[], cause, why, answer } } }
// A part with no translation yet falls back to its `en` search name, so no Chinese shows on the English site.
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
export function localize(m, o) {
  if (!o) return m;
  const pick = (base, over, keys) => { const r = { ...base }; for (const k of keys) if (over?.[k] != null) r[k] = over[k]; return r; };
  return {
    ...pick(m, o, ['name', 'title', 'intro', 'suggest', 'looksLike']),
    lang: 'en',
    parts: m.parts.map((p) => {
      const x = o.parts?.[p.id];
      if (x) return { ...p, name: x.name ?? p.name, info: x.info ?? p.info, aliases: x.aliases ?? [] };
      const name = cap(p.en || p.id.replace(/_/g, ' '));
      return { ...p, name, info: name, aliases: [] };
    }),
    drives: (m.drives || []).map((d) => ({ ...d, name: o.drives?.[d.id] ?? d.name })),
    lessons: (m.lessons || []).map((l) => {
      const x = o.lessons?.[l.id];
      return { ...l, title: x?.title ?? l.title, steps: l.steps.map((s, i) => {
        const y = x?.steps?.[i];
        if (!y) return s;
        const quiz = s.quiz && { q: y.quiz?.q ?? s.quiz.q, options: s.quiz.options.map(([text, right, why], k) => [y.quiz?.options?.[k]?.[0] ?? text, right, y.quiz?.options?.[k]?.[1] ?? why]) };
        return { ...s, say: y.say ?? s.say, ...(quiz && { quiz }) };
      }) };
    }),
    ...(m.faults && { faults: m.faults.map((f) => pick(f, o.faults?.[f.id], ['title', 'short', 'symptom', 'hint', 'suspects', 'cause', 'why', 'answer'])) }),
    ...(m.ride && { ride: { ...m.ride, hint: o.ride?.hint ?? m.ride.hint } }),
  };
}
