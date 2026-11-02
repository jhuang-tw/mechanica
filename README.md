# Mechanica

**An interactive machine classroom where Meta Muse Spark is the teacher.** Open it in a phone browser or in a Meta Quest headset, pick one of eight machines, and learn how it works by repairing it, taking it apart and asking questions. Muse Spark answers by moving the real parts of the 3D model.

- Live demo: https://mechanica.hoson.xyz (phone browser; on Quest tap **VR**)
- Built for the **Meta Global AI Developer Hackathon, Indie track**, by Jim (`jhuang-tw`).
- **Everything in this repository was built during the hackathon** (repository created 2026-10-27, work from 2026-10-26 on). Each feature, its Meta model and its commits are listed in [`docs/BUILT_DURING_HACKATHON.md`](docs/BUILT_DURING_HACKATHON.md). An earlier private prototype was used only as a design reference; none of its code, models or media are here.

## What it does

| Feature | Meta model |
|---|---|
| **Repair challenge** (the home screen): a broken machine runs in front of you. Guess the fault by voice, typing or a tap; Muse Spark checks your guess on the 3D model with its tools (isolate, drive, X-ray) and gives a clue. Repair it, explain why in your own words, and Muse grades the explanation and replays the link you missed. Every tool call is shown on screen as it plays | Muse Spark tool calling, Muse Voice Transcribe |
| **Muse tour** (讓 Muse 帶你看): one tap and Muse Spark directs a 30–60 s narrated teardown, calling a `scene` tool 3–8 times for camera moves, explode, X-ray, isolate and drives | Muse Spark tool calling |
| **X-ray teardown**: taking a machine apart turns its shell to glass so the mechanism stays visible; Muse can call `xray` too | Muse Spark tool calling |
| **Photo to 3D**: photograph a real machine; Muse Spark names it and its parts with boxes, SAM 3.1 traces each part on the photo, and a tapped trace flies into that part of the exploded 3D model | Muse Spark vision, SAM 3.1 |
| **Ask Muse**: ask anything about the machine; the answer is a demonstration that Muse Spark choreographs with the exhibit's own controls | Muse Spark tool calling, Muse Voice Transcribe |
| **Lessons, guess first, Muse tutor, explain it back**: 25 cause-and-effect lessons; predict before each step; a Socratic tutor that grades free answers and remembers weak spots | Muse Spark, Muse Voice Transcribe |
| **Hands-on parts**: drag a pedal or piston and the whole drive follows at real gear ratios; doors and cowls swing on their hinges; first-person ride on the motorbike and car | — |
| **VR mode on Meta Quest**: the same URL in WebXR, wrist menu, real hand meshes, two fists to explode, turn and move, voice questions | Muse Voice Transcribe |

Eight exhibits, all modelled during the hackathon: road bicycle, car, steam locomotive, helicopter, turbofan jet, mechanical dive watch, mixed-reality headset and a 700 cc motorbike (282 parts). The app is in English and Traditional Chinese.

## How Meta's models are used

All model calls go through `server/meta.mjs`; keys stay on the server.

- **Muse Spark** (`muse-spark-1.3`) with **tool calling**: the exhibit's whole action surface (`isolate`, `highlight`, `hide`, `show`, `detach`, `rotate`, `drive`, `xray`; the tour's `scene` tool adds camera framing, orbit and explode) is exposed as tools, with part ids as enums from the exhibit manifest. The server and client check every call against the manifest (known parts only, clamped values) before it plays. Used by Ask Muse, the Muse tour, the tutor, explain-back and the repair challenge (`check` and `grade` tools).
- **Muse Spark vision**: names the machine in a photo and returns each visible part with a box.
- **SAM 3.1** (`sam-3.1`, parsed with the official `@meta-sam/parser`): masks the parts Muse saw; the client keeps the mask instance that best matches Muse's box.
- **Muse Voice Transcribe** (`muse-voice-transcribe-1.0`): push-to-talk WAV from the phone or the headset, followed by one Muse Spark pass that fixes part names.
- Meta's **IWER** WebXR emulator is used in development to test the Quest mode without a headset.

Spoken lines use Inworld TTS-2 Flash (not a Meta model), with Azure or the browser's own voice as fallbacks.

## Run it

```bash
npm install
cp .env.example .env      # set META_API_KEY (INWORLD_API_KEY optional)
npm start                 # build + server → http://localhost:8098
npm run dev               # dev: Vite on 8099 (/api goes to 8098; also run node server/serve.mjs)
npm test                  # offline tests, no model calls
```

Without a headset: `npm run dev`, then open `http://localhost:8099/?xr` to emulate a Quest 3 with IWER.

## VR controls

- **Menu**: open your left hand, palm facing you, and tap the gear on the inside of the wrist with your right index finger (controllers: Y or B). It switches exhibits, lessons, quiz, explode, reset, Muse tour, voice question and exit.
- **Pick a part**: trigger, or pinch along the ray. The part lights up and its explanation is read aloud.
- **Two fists** (controllers: both grips): pull apart to explode, twist to turn, push or lift together to move.
- **Subtitles**: one line below your view that fades after a few seconds; the full answer is spoken.

## Folders

```
src/                  front end (Vite + three.js): landing, exhibit view, part rig, Muse playback, photo, VR
public/exhibits/      exhibits: index.json; <id>/manifest.json, model.glb, thumb.jpg
server/               Node server: static files + /api (Muse Spark, tools, vision, SAM 3.1, Voice Transcribe, TTS)
tools/                model build scripts (build123d CAD, Blender, GLB optimizer, content export/import)
docs/                 interfaces, hackathon ledger, submission text
test/                 node --test
```

To add or change a contract, edit `docs/interfaces.md` first, then make `npm test` pass. No brand logos; only assets we have rights to (see the asset table in the ledger).

---

## 中文簡介

Mechanica 是手機打開就能玩的機械教學，老師是 Meta Muse Spark。首頁是修理挑戰：看一台壞掉的機器，說出你的猜測，Muse Spark 用工具在 3D 模型上檢查給你看；另有 Muse 導覽、X 光拆解、真機照片 → SAM 3.1 → 3D 零件、課程與先猜再看、Muse 家教，同一個網址在 Quest 上可進 VR。所有程式、模型與資料都是活動期間（2026-10-26 起）做的，見 `docs/BUILT_DURING_HACKATHON.md`。
