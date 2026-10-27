# Mechanica: an interactive machine classroom

> Submission text draft (English). Track: Indie. Theme: Push the Frontier.
> Fill in the `<…>` placeholders before submitting.

## One-liner
Mechanica is an interactive machine classroom on your phone or in a Quest headset. Pick a machine, take it apart, guess what happens next, and watch Meta's Muse Spark move the real parts to show you why.

## The problem
People learn how machines work with their hands: you open the engine and watch the gears turn. Most learners never get that chance. Textbooks show static cutaways and videos can't answer "why". Real machines are expensive, dangerous or sealed. Vocational students, junior technicians and curious kids all hit the same wall.

## What it does
1. **Pick a machine and a lesson.** Eight exhibits: road bicycle, motorbike, car, steam locomotive, helicopter, turbofan jet, mechanical watch and a mixed-reality headset. Each one has cause-and-effect lessons, for example "what happens when you shift to the big chainring?"
2. **Guess, then see.** Every lesson step asks you to predict the result before it plays. Then the parts move, and Muse Spark explains why your guess was right or wrong.
3. **Take it apart.** Tap a part to learn what it is, pull it off, and look inside: shells open, internals run.
4. **Ask anything, and the model acts.** "Why is it harder to pedal in the big chainring?" **Muse Spark tool calling** answers by driving the exhibit itself: it shifts the gear, slows time, highlights the chain path and shows the ratio.
5. **AI-choreographed demos.** For any question, Muse Spark writes a short sequence of part motions and captions, which the app checks and plays back as a guided demonstration.
6. **Talk instead of type.** **Muse Voice Transcribe** handles spoken questions, hands-free in VR.
7. **Bonus: photograph a real machine.** **Muse Spark vision** recognises it and opens the matching exhibit, and **SAM 3.1** outlines its real parts on your photo.
8. **Phone first, headset ready.** One web app runs in a phone browser and in Meta Quest (WebXR). No install.

## How we used Meta AI
| Model | Where | Beyond a basic call |
|---|---|---|
| Muse Spark (`muse-spark-1.3`) tool calling | Q&A tutor | The exhibit's whole action surface is exposed as tools, so the model *drives the simulation* to answer |
| Muse Spark (structured output) | Choreographed demos, guess feedback | Generates timed part motions that the client validates (known parts only, clamped values) and plays |
| Muse Voice Transcribe | Voice questions | 16 kHz WAV from the browser, works inside VR |
| Muse Spark vision | Photo → exhibit (bonus) | Picks the exhibit, and says "not a machine" for a cat or a mug |
| SAM 3.1 | Photo → part outlines (bonus) | Masks are linked to the matching 3D parts |

## Built during the hackathon
Everything in this repository was written between Oct 26 and Nov 4, 2026, and the git history is the record. See `BUILT_DURING_HACKATHON.md` for each feature with its commits and date.
Third-party open source: three.js, Vite, `<others>` (unmodified dependencies).

## Try it
- Live demo: `<public URL>` (works in any phone browser; tap "Enter VR" on Quest)
- Video: `<link>`
- Code: `<repo link>`

## What's next
A teacher mode where one Quest leads a class of phones through the same lesson. More machines, written as data: every exhibit is a manifest of parts, motions and lessons, so a new machine needs no new code.
