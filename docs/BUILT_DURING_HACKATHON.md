# Built during the hackathon (Oct 26 – Nov 4, 2026)

Every line of code and every asset in this repository was created during the Meta Global AI Developer Hackathon (Indie track).
The repository was created on `<date>`; its first commit is `<hash>`. The git history is the record.

An earlier personal prototype (a private VR mechanics explorer, started 2026-10-20) was used only as a design reference.
None of its code, models or media are in this repository; everything here was rewritten from scratch.

<!-- Team notes (中文，提交前刪掉)：
- 新 repo 是從零重寫，舊專案只當參考。現在 C:\AI\mechanica 的「舊快照」基底（舊 c87ab01）不能進新 repo。
- 每做完一個功能就在下表加一列：功能 → commit 範圍 → 日期。
- 舊專案 10-26 之後的 commit（CAD 傳動、Meta providers、SAM 遮罩、AI 編排）雖然在活動期間，但在舊 repo 裡，為了乾淨一律在新 repo 重寫，不搬。
-->

## Features → commits
| Feature | Meta model / tool | Commits | Date |
|---|---|---|---|
| Mobile-first app: landing, exhibit view, tap a part, explode, reset, optional WebXR VR (three.js) | — | `7dcf6c0`, `44fe640` | 2026-10-27 |
| Manifest-driven part rig: isolate, detach, rotate, real drives (gear ratios), explode | — | `7dcf6c0` | 2026-10-27 |
| Car exhibit app side: manifest (62 parts, 4 lessons with quiz), slider-crank engine, steering, camera glides to the parts in a lesson | — | `1121b07` | 2026-10-27 |
| ⛓ Cause-and-effect lessons and ❓ guess-first quiz (from the manifest) | — | `44fe640` | 2026-10-27 |
| Voice and text questions in the app, spoken answers, AI demo playback | Muse Spark, Muse Voice Transcribe (via server) | `44fe640` | 2026-10-27 |
| Bicycle exhibit: manifest (18 parts, 2 drives, 2 lessons with quiz), placeholder model script | — | `7dcf6c0` | 2026-10-27 |
| Photo → machine recognition | Muse Spark vision | `468ce33` (server) | 2026-10-27 |
| Photo → part masks linked to 3D parts | SAM 3.1 | `468ce33` (server); 3D link `<range>` | 2026-10-27 |
| Q&A agent that drives the exhibit | Muse Spark tool calling | `468ce33` (server) | 2026-10-27 |
| AI-choreographed part demos (server checks every step against the manifest) | Muse Spark tool calling | `468ce33` (server) | 2026-10-27 |
| Voice questions (+ one Muse Spark pass: simplified → traditional, part-name fixes) | Muse Voice Transcribe, Muse Spark | `468ce33` (server) | 2026-10-27 |
| Daily spend caps for the public demo | — | `468ce33` (server) | 2026-10-27 |
| Bicycle model from scratch: CAD drivetrain (build123d), Blender build with one node per manifest part, phone GLB optimizer | — | `1b8f2dd` | 2026-10-27 |
| Car exhibit mechanisms from scratch: CAD inline-four engine, 5-speed gearbox, differential, wheels and brakes; Blender chassis, steering, suspension | — | `ba0aa36` | 2026-10-27 |

## Third-party (unmodified dependencies, used under their licenses)
| Package | License |
|---|---|
| three | MIT |
| Vite | MIT |
| @meta-sam/parser (official SAM 3.1 mask parser) | SAM License (see its LICENSE) |
| build123d (CAD for the drivetrain parts, build tool only) | Apache-2.0 |
| glTF Transform, meshoptimizer (GLB optimization, dev only) | MIT |
| `<others>` | |

## Assets
| Asset | Made with | Rights |
|---|---|---|
| Bicycle model | `tools/exhibits/bike/cad.py` (build123d) + `build.py` (Blender) + `tools/optimize-glb.mjs` | Ours |
| Voice-over | `<Jim / TTS service>` | `<terms>` |
| Music | `<source>` | Royalty-free |
