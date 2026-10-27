# 3-minute demo video: script and shot list

Target 2:50–3:00. English voice-over with burned-in captions (judges watch muted or fast).
Every Meta model on screen gets a small lower-third tag, e.g. `Muse Spark · tool calling`.
Demo (25%) and Meta tooling (25%) are half the score: show real model output, never mock-ups.

Legend for **Source**: `REC` = I record from the running app (phone viewport, Playwright / browser pane),
`JIM` = only Jim can film, `QUEST` = Quest screen capture (Jim, or Meta Quest Developer Hub cast), `GFX` = I make it.

| # | Time | Shot | Source | Voice-over |
|---|---|---|---|---|
| 1 | 0:00–0:08 | Hand holds a phone, points it at a real bicycle / motorbike, taps the shutter | JIM | "You learn how machines work by taking them apart. Most of us never get to." |
| 2 | 0:08–0:18 | Phone screen: photo → "Recognised: road bike" → the 3D bike appears | REC | "Mechanica changes that. Point your phone at a machine, and Muse Spark's vision recognises it…" |
| 3 | 0:18–0:32 | SAM 3.1 masks bloom over the photo one by one, then the same parts light up on the 3D model side by side | REC | "…SAM 3.1 cuts your photo into its real parts, and each one is linked to a part you can pull out." |
| 4 | 0:32–0:40 | Title card: **Mechanica**: point, ask, take it apart | GFX | (music hit) |
| 5 | 0:40–1:05 | Bicycle. Voice: "Why is it harder to pedal in the big chainring?" Show the tool-call trace sliding in (`shift_front big`, `show_ratio`, `slow_time`, `highlight chain`) while the chain jumps and the ratio readout changes | REC | "Ask a question and the model doesn't just answer. Muse Spark calls the exhibit's own controls, so the answer happens in front of you." |
| 6 | 1:05–1:35 | Tap a bicycle part (freehub ratchet or rear derailleur) → "Show me" → AI-choreographed demo: camera moves, part motion, captions. Small overlay of the generated JSON | REC | "For any part, Muse Spark writes the lesson itself: camera, motion and captions, played back as a guided demo of cause and effect." |
| 7 | 1:35–1:50 | Drag-explode the parts SAM 3.1 found in a second photo (e.g. a motorbike), finger gestures | REC | "Everything comes apart, from any photo, in a phone browser." |
| 8 | 1:50–2:15 | Same app on Quest: hand menu, pinch a part out, voice question in VR | QUEST | "And the same web app runs in a Meta Quest headset through Meta's IWSDK. Ask with your voice; Muse Voice Transcribe hears you." |
| 9 | 2:15–2:35 | Architecture card: phone / Quest → server → Muse Spark (tools, vision, structured output), SAM 3.1, Voice Transcribe | GFX | "One web app, five Meta capabilities, no install." |
| 10 | 2:35–2:52 | Montage of different real photos turned into part lessons, 1.5 s each | REC | "For students, new technicians and anyone curious: every machine, open to everyone." |
| 11 | 2:52–3:00 | End card: name, live URL, QR code, "Built with Meta Muse Spark · SAM 3.1" | GFX | "Mechanica. Try it now on your phone." |

## Notes
- **Indie rule: show only what was built from Oct 26 on.** No pre-hackathon exhibit (the nine VR exhibits, their models and animations) may appear. Shots 5, 6 and 8 use the bicycle exhibit (rewritten from scratch in the new repo) or photo-generated parts. Shot 1 should be Jim's real bicycle, so the photo, the SAM masks and the 3D exhibit are the same machine.
- Record at 1080×1920 for phone shots, then place them on a 1920×1080 canvas with the tag and captions beside them (one master in 16:9; a 9:16 cut for social is optional and helps the "most viral" bonus prize).
- Shots 2, 3, 5 and 6 must be real model calls; cache the exact runs we keep so a retake does not spend credits again.
- Fallback if Shot 1 is missing: open on shot 2 using a phone photo Jim sends.
- Music: royalty-free only. No brand logos on the exhibits (they are already generic).
