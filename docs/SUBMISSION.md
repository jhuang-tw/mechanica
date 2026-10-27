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
| Impact | 30% | 「拍下任何機器 → 手機上變成能拆、能問、會動的 3D 教學」：學生、技職、維修新手、好奇的人 |
| Use of Meta AI Tooling | 25% | muse-spark 工具呼叫驅動展品、vision 認機器、SAM 3.1 照片→零件、AI 編排零件示範、Muse Voice Transcribe |
| Technical Depth & Execution | 20% | WebXR(IWSDK) + 手機同一份程式、真實機構幾何、因果示範、測試 |
| Demo | 25% | 能現場跑的網址 + 3 分鐘影片 |

活動頁對 Indie 組的說法是「創意、技術野心、能不能動」，與上表一致。題目可選「Build for Your World」或「Push the Frontier」；我們建議填 **Push the Frontier**（製造／工程教育）。

## 資格問題的答案
1. **既有程式碼可以用嗎？Indie 組不行。**（更正：waiver 沒寫，但 Jim 貼的「4. Hackathon Rules」寫了）
   - Repo 必須公開。
   - Demo 只能展示活動期間（10/26 起）做的功能，評審要能清楚分辨哪些是新的，否則可直接取消資格。
   - Indie 組「New work only」；只有 Startup 組可以建立在既有產品上（但要標清楚新做的部分）。
   - 舊的 VR Mechanics Explorer 第一個 commit 是 2026-10-20，早於活動，`mechanica/` 目前的內容幾乎都是從它複製來的，**不能原樣交 Indie**。

   **建議方案（Indie）**：開一個全新的公開 repo（不要用 branch），第一個 commit 在活動期間，裡面只放 10/26 之後寫的程式與資產；
   主打全新的部分：拍照 → Muse Spark 視覺辨識 → SAM 3.1 切出零件 → 零件變成可拆的 3D 圖層 → Muse Spark 工具呼叫與 AI 編排示範。
   舊的九個展品不放進 repo、不出現在 demo。若要展品，就在活動期間用新腳本重做 1–2 個，git 時間戳就是證據。
   另附 `BUILT_DURING_HACKATHON.md` 帳本：每個功能 → commit 範圍 → 日期；開源套件（IWSDK、three.js、@meta-sam/parser）列為第三方。

   **替代方案（Startup）**：可沿用舊程式，但要確認 Jim 報名的組別；規則寫「一人只能報一組」，換組要先問主辦方（Discord），而且 Startup 組評「能不能撐住正式上線」，代表人要是新創的在職員工。
2. **一定要用 Meta 模型嗎？** 規則沒有強制，但「Use of Meta AI Tooling」占 25%，等於必須。**展示版要全部跑在 Meta 上**：LLM、工具呼叫、視覺、SAM 3.1、語音轉文字（`STT_PROVIDER=meta`）。Gemini 只當隱藏的備援，影片和說明都不要出現。
3. **其他資格**：18 歲以上；台灣不在排除名單；Meta／Cerebral Valley 員工及其家人不行。Indie 組可 1–4 人，代表人提交並列出隊員。
4. **授權**：作品所有權歸 Jim，但主辦方取得永久、免費、非獨家的使用授權（可用於行銷）。活動中分享的東西不算機密。

## 開源前檢查
- `.env`、`*.pem`、`*.key` 已在 `.gitignore`；公開前再跑一次 secret 掃描（`npx gitleaks detect` 或 grep `API_KEY=` 有值的行），並看過整個 git 歷史，歷史裡出現過金鑰就要換鑰匙。
- `.env.example` 有提到 archbro 路徑與 sub2api，公開前刪掉。
- 資產權利：Blender 腳本產生的模型是 Jim 自己的（但屬活動前作品）；阿帕契直升機的底模來自 **Tripo**，要確認 Jim 用的方案授權（免費方案通常是 CC BY 4.0、需標註來源，商用要付費方案）；旁白若用 TTS，要符合該服務條款；音樂只用免版稅。
- 加上 LICENSE（建議 MIT）。

## 只有 Jim 能做的事
- [ ] **確認報名的是 Indie 還是 Startup 組，以及參賽專案是 Mechanica 還是 Archbro。**
- [ ] 建立新的公開 GitHub repo（或同意我用 `gh` 建）。
- [ ] 確認 Tripo 方案與授權。
- [ ] 登入提交入口，確認表單欄位（影片長度上限、是否要 repo 連結、是否要公開網址），把欄位截圖或貼給我。
- [ ] 確認已接受 Official Rules／waiver，並已領取 $150 額度（注意 10 天期限從何時算）。
- [ ] 提供可公開的 demo 網址（Cloudflare tunnel 或部署），影片裡要能說「現在就能打開」。
- [ ] 錄一段真人畫面：手拿手機拍一台真實機器（腳踏車、機車或手錶），這是影片開場最有力的鏡頭，我無法代拍。
- [ ] 旁白：用自己的聲音錄，或同意我用 TTS。
- [ ] 若要上傳 YouTube／Vimeo，用自己的帳號上傳（不公開連結即可）。
- [ ] 最後按下提交。
