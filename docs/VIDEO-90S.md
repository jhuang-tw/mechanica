# 90-second demo video: the repair loop

Target 1:25–1:30. English voice-over with burned-in captions (judges may watch muted).
This cut replaces the feature tour in `VIDEO.md` with one story: **the machine is broken → you guess → Muse checks your guess on the model → you fix it → you explain the principle back → Muse grades it.**
Everything on screen was built during the hackathon (Oct 26 onward). A small corner badge `Built Oct 26 – Nov 4` stays on the whole video, and every Meta model call gets a lower-third tag.

Source column: `REC` = screen recording of the running app (phone viewport 1080×1920 on a 1920×1080 canvas), `VR` = headset footage from the VR-recording thread, `STUDY` = learner test with novices, `GFX` = made in the edit.

<!-- 給 Jim（中文）：
- 主線只用腳踏車「鏈條脫落」這一題，最好懂；其他七台只在 1:12 的蒙太奇閃過。
- 猜測一定要「用講的」或打字：點三個選項是本機判斷，不會呼叫 Muse，影片就不能標 Muse。
- 第一次故意猜錯（煞車卡住），讓評審看到 Muse 真的去模型上檢查、不給答案、只給線索。
- 8–9 號鏡頭（VR、學習者前後測）是預留位，素材到了再換；沒有就照備案。
-->

| # | Time | Shot | Source | Voice-over / caption | Tag |
|---|---|---|---|---|---|
| 1 | 0:00–0:06 | Bicycle on the repair screen. The crank and chainring spin, the rear wheel does not. Caption: **"You pedal, but the rear wheel won't turn. What's wrong?"** | REC | "This bike is broken. Your job: find out why." | `Built during the hackathon` |
| 2 | 0:06–0:09 | Title card: **Mechanica**: fix the machine, then explain it | GFX | (music hit) | |
| 3 | 0:09–0:22 | Learner holds the mic and says a **wrong** guess: "I think the back brake is stuck." Muse isolates the brake and rear wheel, runs the drive in the broken state (brake is free, wheel still stops), and answers with a clue, not the answer. Tool-call trace slides in on the side: `check(not_it)`, `isolate brake_rear`, `drive pedal` | REC | "Say what you think. Muse Spark doesn't just reply: it tests your guess on the real model. The brake is free, so it gives you a clue instead of the answer." | `Muse Spark · tool calling` (+ `Muse Voice Transcribe` only if the live server uses it) |
| 4 | 0:22–0:32 | Second guess, spoken: "Something between the front gear and the back is not moving... the chain?" Muse returns `check(found)`, isolates the chain and praises the find. The app repairs it on its own: the chain drops back on, the rear wheel spins, card reads **Fixed** | REC | "Follow the force, find the break, and fix it." | `Muse Spark · tool calling` |
| 5 | 0:32–0:47 | Explain it back. On screen: **"Why does the chainring keep spinning while the wheel stays still?"** Learner answers out loud, half right: "The chain carries the turning to the wheel." Muse grades it `partial`, says what was right and replays the drive path on the model with the missing link (chain → cassette → rear wheel) isolated | REC | "Then the real test: explain why, in your own words. Muse grades the explanation and shows you the link you missed." | `Muse Spark · grading (structured output)` |
| 6 | 0:47–0:52 | Learner retries, Muse grades `right`, the next fault is picked | REC | "Right. Next machine." | |
| 7 | 0:52–1:02 | **[SLOT: VR footage]** Same app in a Meta Quest: wrist menu, pick the bike, two-fist explode, pinch the chain out and put it back. Placeholder until the VR thread's clips arrive | VR | "The same web app runs in a Meta Quest. No install. Grab the parts with your hands." | `WebXR on Meta Quest` |
| 8 | 1:02–1:12 | **[SLOT: learner evidence]** 3–5 novices, before vs. after one repair loop. Bar chart (before / after score per person) and one 2-second clip of a learner explaining the chain in their own words | STUDY + GFX | "We tested it with `<N>` people who had never fixed a bike. Before: `<X>` of `<N>` could explain why. After one loop: `<Y>` of `<N>`." | |
| 9 | 1:12–1:20 | Montage, 1.5 s each, the other faults: helicopter tail shaft, jet HP shaft, watch minute wheel, steam rods, motorcycle clutch slip | REC | "Eight machines, each with a fault to find and a principle to explain." | |
| 10 | 1:20–1:25 | Architecture card: phone / Quest → server → Muse Spark (tool calling, structured grading), Muse Voice Transcribe, SAM 3.1 | GFX | "One web app, built on Meta's models." | |
| 11 | 1:25–1:30 | End card: Mechanica, live URL, QR code, "Built with Meta Muse Spark" | GFX | "Mechanica. Break it, fix it, understand it." | |

## Recording notes
- **Shots 3–6 must be real model calls**, in one continuous session on the live server, so the trace and the replay are genuine. Keep the server log of the take. Do not stage the trace; record it from the app (or a debug overlay that prints the returned tool calls).
- Guesses must be **spoken or typed**. Tapping one of the three suggested answers is judged locally and never reaches Muse, so it cannot carry a Muse tag.
- Muse output varies. Do 3–4 takes and keep the clearest one; if a take answers `found` on the wrong guess, discard it.
- Only claim `Muse Voice Transcribe` if the live server's speech-to-text is actually the Meta endpoint during the take. If it is not, drop the tag and the word "transcribe" from shot 10.
- English site is the default, so record in English. A 繁中 cut can reuse the same shot list with `?lang=zh`.
- Music: royalty-free only. Voice: Jim's voice, or TTS whose terms allow it (record the service in `BUILT_DURING_HACKATHON.md`).

## Slot 7: VR footage (from the VR-recording thread)
- Needed: 8–10 s total. Best order: wrist menu opens → bike picked → two-fist explode → pinch the chain out.
- The VR menu has no repair challenge yet, so the VR shot shows hands-on disassembly, not the repair loop. The voice-over above is written for that.
- Real headset capture is strongly preferred. If only the IWER emulator (`?xr`) is available, label it on screen as `Emulated Quest view (IWER)`, never as headset footage.
- Fallback if no footage: cut shot 7 and give its 10 s to shots 5 and 8.

## Slot 8: learner before/after test (3–5 novices)
Run it before recording, takes about 10 minutes per person. Only the numbers you actually measured go on screen.

1. **Who:** 3–5 people who have never repaired a bicycle (family, friends, teammates' contacts). Get verbal consent to use their answers; show faces only with permission, otherwise hands or voice only.
2. **Before (2 min, paper or chat):** the same three questions for everyone:
   - Q1: "You pedal and the chainring spins, but the rear wheel doesn't move. What is the most likely cause?"
   - Q2: "Explain in one sentence why that stops the wheel."
   - Q3 (transfer): "A helicopter's engine runs but the small tail rotor stopped. What would you check first, and why?"
3. **Use the app (≈5 min):** one repair loop on the bike: guess by voice, find the fault, fix it, explain it back. No coaching from us.
4. **After (2 min):** the same three questions.
5. **Score:** 0–2 points per question (0 = wrong, 1 = right direction but no cause → effect, 2 = names the break in the force path). Max 6. Record per person: before, after, and their Q2 answer in their own words.
6. **On screen:** a simple before/after bar per person plus one quote. If the gain is small, say so honestly ("most could already guess the cause; explaining why went from X to Y").

| Person | Before (0–6) | After (0–6) | Q2 after, own words | OK to show face? |
|---|---|---|---|---|
| P1 | | | | |
| P2 | | | | |
| P3 | | | | |
| P4 | | | | |
| P5 | | | | |
