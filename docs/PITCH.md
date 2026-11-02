# Mechanica: an interactive machine classroom

> Submission text draft (English). Track: Indie. Theme: Push the Frontier.
> Fill in the video link before submitting.

## One-liner
Mechanica is an interactive machine classroom on your phone or in a Quest headset. Pick a machine, take it apart, guess what happens next, and watch Meta's Muse Spark move the real parts to show you why.

## The problem
People learn how machines work with their hands: you open the engine and watch the gears turn. Most learners never get that chance. Textbooks show static cutaways and videos can't answer "why". Real machines are expensive, dangerous or sealed. Vocational students, junior technicians and curious kids all hit the same wall.

## What it does
1. **Fix a broken machine.** The app opens on a machine with a fault. You watch the symptom and say what you think is wrong; **Muse Spark** checks your guess on the 3D model by calling the exhibit's tools (each call is listed on screen as it plays). Then you repair it, explain why in your own words, and Muse grades the explanation.
2. **Pick a machine and a lesson.** Eight exhibits: road bicycle, motorbike, car, steam locomotive, helicopter, turbofan jet, mechanical watch and a mixed-reality headset. Each one has cause-and-effect lessons, for example "what happens when you shift to the big chainring?"
3. **Guess, then see.** Every lesson step asks you to predict the result before it plays. Then the real parts move at their real ratios.
4. **Take it apart.** Tap a part to learn what it is, drag it and the whole drive follows, pull it off. Exploding a machine turns its shell to X-ray glass so the insides keep running in view.
5. **Ask anything, and the model acts.** "Why is it harder to pedal in the big chainring?" **Muse Spark tool calling** answers by driving the exhibit itself: it shifts the gear, slows time, highlights the chain and shows the ratio. Every step is checked against the exhibit before it plays.
6. **Muse tour.** One tap and Muse Spark directs a 30–60 s narrated teardown: camera framing, explode, X-ray, isolate, real drives, one spoken line per shot.
7. **Muse tutor and explain-it-back.** Socratic questions graded right / partial / misconception, a demo aimed at the gap, and a learner record so a return visit starts from your weak spots.
8. **Talk instead of type.** **Muse Voice Transcribe** handles spoken questions, hands-free in VR.
9. **Photograph a real machine.** **Muse Spark vision** names the machine and its parts, **SAM 3.1** traces each part on your photo, and a tapped trace flies into that part of the 3D model.
10. **Phone first, headset ready.** One web app in English or 繁體中文 runs in a phone browser and in Meta Quest (WebXR, hand tracking). No install.

## How we used Meta AI
| Model | Where | Beyond a basic call |
|---|---|---|
| Muse Spark (`muse-spark-1.3`) tool calling | Repair challenge, Q&A, tutor | The exhibit's whole action surface is exposed as tools, so the model *drives the simulation* to answer; calls are shown on screen |
| Muse Spark tool calling (`scene` tool) | Muse tour | The model directs camera, explode, X-ray and drives shot by shot; every shot is validated against the manifest |
| Muse Spark (structured output) | Choreographed demos, guess feedback, explain-it-back grading | Timed part motions the server validates (known parts only, clamped values); cause → effect links marked covered or missed |
| Muse Voice Transcribe | Voice questions | 16 kHz WAV from the browser, then one Muse Spark pass fixes part names; works inside VR |
| Muse Spark vision | Photo → exhibit and parts | Picks the exhibit and names the visible parts, and says "not a machine" for a cat or a mug |
| SAM 3.1 | Photo → part outlines | Masks are linked to the matching 3D parts |

## Built during the hackathon
Everything in this repository was written between Oct 26 and Nov 4, 2026, and the git history is the record. See `BUILT_DURING_HACKATHON.md` for each feature with its commits and date.
Third-party open source (unmodified dependencies): three.js, Vite, @meta-sam/parser, build123d, glTF Transform, meshoptimizer, iwer. Spoken lines use Inworld TTS; vehicle shells started as Tripo3D meshes. Details and licenses are in the ledger.

## Try it
- Live demo: https://mechanica.hoson.xyz (works in any phone browser; tap **VR** on Quest)
- Video: `<link>`
- Code: https://github.com/jhuang-tw/mechanica

## What's next
A teacher mode where one Quest leads a class of phones through the same lesson. More machines, written as data: every exhibit is a manifest of parts, motions and lessons, so a new machine needs no new code.
