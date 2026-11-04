# 研究來源、版本與限制

查核日期：2026-11-04，Asia/Shanghai。未抓取任何真實價格；所有請求是公開文件
或本專案 GitHub metadata。來源原文未整份再散布；以下保留短摘錄及定位。
官方 GitHub 來源 bytes 已以固定 commit 重新取得並確認與閱讀內容一致，原文
SHA-256 在 [research-sources.json](research-sources.json)。文件 SHA 證明讀了哪份
內容，不證明產品權利、未來可用性或官方市場結果。

## 實際閱讀、固定版本

**S1 — OpenTimestamps 官方 client README**

https://github.com/opentimestamps/opentimestamps-client/blob/f3a9e92e4dcb89ed93396d71ec808b3290a438c4/README.md

短摘錄： “to *verify* timestamps you need a local Bitcoin Core node”。
Requirements / Usage 章也說明：可在沒有 local node 下建立；calendar 回應先是
pending；鏈上確認約數小時；upgrade 將完成的路徑加入 proof。這裡的時間描述是
專案文件解釋，不是本 Pilot SLA。未呼叫其中 calendar URL、未運行範例或安裝 client。

**S2 — Alpaca 官方歷史 market-data 文件（repository 已 archived）**

https://github.com/alpacahq/alpaca-docs/blob/2080c5e0efbbd812c48eef9209a7a9962de67d2a/content/market-data/_index.md

短摘錄： “The Free plan consists of data from IEX”。
Subscription Plans / Exchanges / Conditions 章區分 IEX、CTA／UTP、Market Center
Official Close、Closing Print 及 corrected consolidated close。供應商維護的
協議解說不是現行 CTA／UTP 規格全文；正式欄位與更正行為仍須直接核驗上游規格。
其中舊價格表與 entitlement **不得引用為現行商業條款**。

另閱讀同 repo 的 historical stock pricing 文件確認 raw／adjustment／feed 欄位
可能分開；不以它作新主張的現行授權證據，亦未取其實際 API 範例的市場資料。

**S3 — Alpaca 官方 SDK DataFeed／Adjustment 定義（repository 未 archived）**

https://github.com/alpacahq/alpaca-py/blob/87cf99cfd86c844eeb8d83e0b735183ccdb6c3d0/alpaca/data/enums.py

短摘錄： “DELAYED_SIP (str): SIP data with a 15 minute delay”。
DataFeed / Adjustment 類型也列 IEX、SIP、RAW、SPLIT、DIVIDEND、ALL。
這證實程式接口的資料類別，**不證明免費 entitlement、SLA 或任何 close 為官方價**。
只讀 code 文件，沒有 import／初始化 SDK、認證或 market/broker API 呼叫。

**S4 — 專案 main 與 GitHub PR #4 metadata**

https://github.com/ianchancoseon-wq/trading-lab/pull/4

GitHub 查得 state=MERGED，merge commit
`634fa1dd9ec3bf8e1787421724f029a5f9953b44`。
工作基線為後續 reconciliation main `2a681e8bd247a68446f09e661bde572752504727`。
`phase0c/LAB-STATE.md` 記錄 34 bundled + 12 independently authored QA，合計
46/46 PASS；本次沒有重跑、沒有將未入庫的 QA 檔當成已入庫，也沒有擴大其接受範圍。
現有 `records.py`、`registry.py`、`scoring.py` 的只讀檢查確認 fixture身份、custody、
跨預測限制、quarantine/current-score guards 仍在。舊設計文案的歷史 draft 標籤
不取代最新 LAB-STATE；本分支不修改其內容。

## 直接公開網站存取結果／尚未驗證來源

以下都是公開文件 URL，透過既有網路政策請求時回傳 HTTP 403。沒有變更 allowlist、
繞過 proxy、關閉 TLS，或把其他鏡像冒充原站。403 表示此環境未能閱讀，不等於
網站對所有人都不可用。

| 欲查核來源 | 原始 URL | 本次結果與缺口 |
| --- | --- | --- |
| OTS 官網 | https://www.opentimestamps.org/ | 403；改讀官方 GitHub S1，未核實現行 calendar 運維承諾 |
| NYSE hours/calendars | https://www.nyse.com/markets/hours-calendars | 403；實際 Pilot 日期／半日規則需另取得官方快照 |
| Nasdaq Closing Cross | https://www.nasdaqtrader.com/Trader.aspx?id=ClosingCross | 403；NOCP／拍賣與例外處理的現行規則未核驗 |
| Alpaca 最新公開產品文件 | https://docs.alpaca.markets/docs/about-market-data-api | 403；當期定價／權限／保存和再散布條款未核驗 |

下列是**待讀的 primary references，不宣稱已查證**：

- CTA CTS 官方規格（由 S2 引用）：https://www.ctaplan.com/publicdocs/ctaplan/CTS_Pillar_Output_Specification.pdf
- UTP 官方規格（由 S2 引用）：https://www.utpplan.com/DOC/UtpBinaryOutputSpec.pdf
- RFC 3161 標準背景：https://www.rfc-editor.org/rfc/rfc3161
- GitHub REST issue comments metadata 說明：https://docs.github.com/en/rest/issues/comments
- 選定 exchange/data vendor 的正式 market-data agreements、non-display／internal-use／retention／redistribution 條款，以及候選免費方案當期價目。

因此本研究可確定來源類型與工程風險，但尚不能簽認任何零成本官方 close 路徑
或外部證明服務符合正式 Pilot 要求。Founder 可在後續授權中允許存取官方文件，
或提供來源可核對的原文／合約快照，讓獨立 Reviewer 補齊；本任務不代購、不開戶。
