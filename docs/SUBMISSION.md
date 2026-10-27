# Meta Global AI Developer Hackathon：規則重點與提交清單

來源（2026-10-27 讀取）：活動頁 https://dev.meta.ai/events/global-hackathon ，
Official Rules／Waiver https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver

## 時程
- 截止：**2026-11-04 21:00 ET**（台灣 11-05 週四 10:00）。評審 11/4–11/8，11/9 決賽與頒獎，加碼獎約 11/10 公布。
- 提交入口：https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit （需登入，表單欄位要 Jim 登入後才看得到）。
- $150 Meta Model API 額度，**只有 10 天開發窗口**，領取前要看 Credit Terms。

## 評分（Official Rules，兩組通用）
| 項目 | 比重 | 我們的對應 |
|---|---|---|
| Impact | 30% | 互動機械教室：八台機器的因果課程、先猜再看、拆零件；對象是學生、技職、維修新手、好奇的人 |
| Use of Meta AI Tooling | 25% | muse-spark 工具呼叫驅動展品、AI 編排示範、猜測回饋、Muse Voice Transcribe；加分項：vision 認機器、SAM 3.1 標出零件 |
| Technical Depth & Execution | 20% | 手機＋Quest 同一份程式、manifest 驅動展品、真實機構、因果示範、測試 |
| Demo | 25% | 能現場跑的網址 + 3 分鐘影片 |

活動頁對 Indie 組的說法是「創意、技術野心、能不能動」，與上表一致。題目可選「Build for Your World」或「Push the Frontier」；我們建議填 **Push the Frontier**（製造／工程教育）。

## 資格問題的答案
1. **既有程式碼可以用嗎？Indie 組不行。**（更正：waiver 沒寫，但 Jim 貼的「4. Hackathon Rules」寫了）
   - Repo 必須公開。
   - Demo 只能展示活動期間（10/26 起）做的功能，評審要能清楚分辨哪些是新的，否則可直接取消資格。
   - Indie 組「New work only」；只有 Startup 組可以建立在既有產品上（但要標清楚新做的部分）。
   - 舊的 VR Mechanics Explorer 第一個 commit 是 2026-10-20，早於活動，`mechanica/` 目前的內容幾乎都是從它複製來的，**不能原樣交 Indie**。

   **已決定**：Indie 組，全新公開 repo `mechanica-meta`，從零重寫，舊專案只當參考，不搬程式、模型或媒體。
   主打教學平台（互動機械教室：課程、先猜再看、拆零件、AI 動零件），拍照辨識是附帶功能。
   `BUILT_DURING_HACKATHON.md` 帳本記錄每個功能 → commit → 日期。
2. **一定要用 Meta 模型嗎？** 規則沒有強制，但「Use of Meta AI Tooling」占 25%，等於必須。**展示版要全部跑在 Meta 上**：LLM、工具呼叫、視覺、SAM 3.1、語音轉文字（`STT_PROVIDER=meta`）。Gemini 只當隱藏的備援，影片和說明都不要出現。
3. **其他資格**：18 歲以上；台灣不在排除名單；Meta／Cerebral Valley 員工及其家人不行。Indie 組可 1–4 人，代表人提交並列出隊員。
4. **授權**：作品所有權歸 Jim，但主辦方取得永久、免費、非獨家的使用授權（可用於行銷）。活動中分享的東西不算機密。

## 開源前檢查
- `.env`、`*.pem`、`*.key` 已在 `.gitignore`；公開前再跑一次 secret 掃描（`npx gitleaks detect` 或 grep `API_KEY=` 有值的行），並看過整個 git 歷史，歷史裡出現過金鑰就要換鑰匙。
- `.env.example` 有提到 archbro 路徑與 sub2api，公開前刪掉。
- 資產權利：Blender 腳本產生的模型是自己的；外殼底模來自 **Tripo**，要確認 Jim 用的方案授權（免費方案通常是 CC BY 4.0、需標註來源）；旁白若用 TTS，要符合該服務條款；音樂只用免版稅。
- 加上 LICENSE（建議 MIT）。

## 只有 Jim 能做的事
- [ ] 在 GitHub 建公開 repo（或同意用 `gh` 建）並推上去。
- [ ] 確認 Tripo 方案與授權。
- [ ] 登入提交入口，確認表單欄位（影片長度上限、是否要 repo 連結、是否要公開網址），把欄位截圖或貼給我。
- [ ] 確認已接受 Official Rules／waiver，並已領取 $150 額度（注意 10 天期限從何時算）。
- [ ] 提供可公開的 demo 網址（Cloudflare tunnel 或部署），影片裡要能說「現在就能打開」。
- [ ] 錄一段真人畫面：用手機拍自己的腳踏車（約 10 秒）。這是影片後段「附帶功能：拍真機器」的鏡頭，不是開場，我無法代拍。
- [ ] 旁白：用自己的聲音錄，或同意我用 TTS。
- [ ] 若要上傳 YouTube／Vimeo，用自己的帳號上傳（不公開連結即可）。
- [ ] 最後按下提交。
