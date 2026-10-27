# Mechanica: point your phone at any machine and take it apart

> Submission text draft (English). Track: Indie. Theme: Push the Frontier.
> Fill `<…>` once the app threads land. Keep the section that says what existed before the hackathon.

## One-liner
Mechanica turns a photo of a real machine into a 3D exhibit you can take apart, ask questions about and watch run, on your phone or in a Quest headset, with Meta's models doing the seeing, the segmenting and the teaching.

## The problem
Mechanical understanding is learned with your hands: you open the engine, you watch the gears turn. Most learners never get that chance. Textbooks show static cutaways, videos can't answer "why", and real machines are expensive, dangerous or sealed. Vocational students, junior technicians and curious kids all hit the same wall.

## What it does
1. **Snap a machine.** Take a photo of a bicycle, a motorbike, a watch, a helicopter. **Muse Spark vision** recognises the machine and opens the matching interactive exhibit.
2. **Photo → parts.** **SAM 3.1** segments the photo into its real parts, and each mask is linked to the matching part in the 3D model, so you learn on *your* machine, not a stock picture.
3. **Ask anything, and the model acts.** "Why is it harder to pedal in the big chainring?" **Muse Spark tool calling** doesn't just answer: it calls the exhibit's actions (shift to the big ring, show the gear ratio, slow time, highlight the chain path) so the answer happens in front of you.
4. **AI-choreographed demos.** For any part, Muse Spark writes a short sequence of camera moves, part motions and captions, and the app plays it as a guided demo of cause and effect.
5. **Talk instead of type.** **Muse Voice Transcribe** handles voice questions, hands-free in VR.
6. **Phone first, headset ready.** The same web app runs on a phone browser and in Meta Quest (WebXR through Meta's IWSDK). No install.

The first hand-built exhibit is a **road bicycle**, written from scratch during the hackathon: pedal → chainring → chain → cassette → rear wheel with live gear ratio and speed, front/rear derailleurs, rim brakes, freehub ratchet when coasting, and parts you can pull off. `<more exhibits if added>`

## How we used Meta AI
| Model | Where | Beyond a basic call |
|---|---|---|
| Muse Spark (`muse-spark-1.3`) tool calling | Q&A agent | The exhibit's whole action surface is exposed as tools, so the model *drives the simulation* to answer |
| Muse Spark vision | Photo → exhibit | Picks the exhibit and the parts it can see |
| SAM 3.1 | Photo → part masks | Masks are matched to 3D parts and highlighted on both |
| Muse Spark (structured output) | Part demos | Generates a timed choreography that the engine validates and plays |
| Muse Voice Transcribe | Voice input | 16 kHz WAV from the browser, works inside VR |
| Meta IWSDK | Rendering / XR | One codebase for phone and Quest |

## Built during the hackathon
Everything in this repository was written between Oct 26 and Nov 4, 2026; the git history is the record. See `BUILT_DURING_HACKATHON.md` for feature → commits → date.
Third-party open source: Meta IWSDK, three.js, `<others>` (unmodified dependencies).

## Try it
- Live demo: `<public URL>` (works on any phone browser; tap "Enter VR" on Quest)
- Video: `<link>`
- Code: `<repo link>`

## What's next
Any machine, not only the nine exhibits: generate the 3D parts from the photo itself, then let Muse Spark choreograph the lesson. Classroom mode where a teacher's Quest leads students' phones.
