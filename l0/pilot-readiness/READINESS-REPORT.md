# L0 Forward Pilot 技術準備報告與風險清單

日期：2026-11-04（Asia/Shanghai）。基線：
`2a681e8bd247a68446f09e661bde572752504727`。
授權只涵蓋規劃／研究／技術準備及提交 Draft PR。本目錄所有新增方案、參數、
流程和驗收點均 **PROPOSED / NOT ADOPTED**，不構成 Pilot 或工程修改的執行授權。

## 建議

**準備文件：GO FOR FOUNDER REVIEW。正式 Forward Pilot：NO-GO。**

最低現金增量候選是「既有主機遠端收件證明＋獨立人工核驗」，可加 OTS 長期
內容承諾補強。它仍需核准的信任／時間／保留政策，不能稱為現成可信 TSA。
資料端可考慮「人工取得官方 EOD close、允許延遲核驗、獨立上游 corroboration」，
但尚未確認現行免費來源、官方欄位、使用權和可保存原物，因此不是已可運行方案。

正式 Pilot 不能以 fixture 身份、布林 verified 旗標、local Git 日期或手改 SQLite
取代外部核驗。Core 現有 custody／quarantine／performance 限制仍有效；
獨立離線 QA 通過不等於真實市場、外部時間或端到端 Room 流程已驗證。

## 任務成果與現況

| 範圍 | 已有／本次交付 | 未完成且不宣稱完成 |
| --- | --- | --- |
| 基線 | PR #4 已合併；main 記錄 L0 Core R2 已接受，獨立離線 QA 46/46 | 未把 offline acceptance 推廣為 Pilot 授權 |
| 凍結／時間 | 內容清單、外部 receipt、GitHub 主機／OTS／TSA 比較與低成本候選設計 | 未發送任何 commitment；未開通、核驗或採用外部時間服務 |
| 收盤資料 | 官方／SIP／IEX／bar／adjusted close 差異；延遲和授權核對清單；成本上限方案 | 沒有取得真實 close，未核實現行 exchange/vendor 價格與權限；沒有零成本可用性的保證 |
| 資料契約 | Room 原物、身份／版本、PRED hash、measurement、custody、Outcome、Score、Review、Memory 全流程與缺口 | 未實作 importer、驗證器、資格升級或跨樣本 memory；未改任何 Core |
| 小型觀察計畫 | PROPOSED 五個預先登記未來 SPY session、固定 strategy、手動核驗、保留全部失敗 attempt | 無真實日期名冊、無研究訊息、無模型任務、無預測或結果 |
| 成本 | 新增服務費上限 0 的可行性條件；人工／節點／既有訂閱另列 | 免費來源／獨立節點／Reviewer 可用性未證實，不能承諾總成本為零 |

詳細設計見 [FREEZE-CUSTODY](FREEZE-CUSTODY.md)、[DATA-COST-ASSESSMENT](DATA-COST-ASSESSMENT.md)、
[DATA-CONTRACT](DATA-CONTRACT.md)、[PILOT-PLAN](PILOT-PLAN.md)。
研究來源及無法存取項目見 [SOURCES](SOURCES.md)。

## 正式執行前的獨立工程閘門（本任務未授權實作）

1. **外部 custody 驗證**：採用明確 trust model、核驗者、actor identity、deadline、
   刪改／時鐘／憑證規則；驗證 exact commitment 與外部 receipt。不能把 GitHub
   created_at 附在後來編輯的新內容上，不能把 OTS 區塊 timestamp 當精確 UTC。
2. **官方資料與使用權**：取得官方 close 欄位、上市市場、session/calendar、延遲／
   final/correction 規則和可合法保存／核驗的條款；第二來源不能僅是同上游鏡像。
3. **Room→Registry 真實時序橋接**：最終 PRED hash 前後的 draft／envelope／freeze
   建立時間須可重建，不回填時間、不換 hash、不丟失原始模型輸入與身份。
   引入的任何 adapter 須獨立授權、以純工程資料測試、再 QA。
4. **資格與儲存**：保留 accepted Core。若未來要接受 VERIFIED custody 或正式
   genuine-forward eligibility，需獨立可審查設計、工程、QA 和 Founder decision；
   不得關閉 latch、直接改 DB 或硬填 performance_eligible。新 actor mapping 與
   Pilot store 初始化必須受核准，舊 test store 不是 operational system。
5. **Memory 邊界**：本小型計畫只產生 per-prediction proposals，不啟用。跨樣本
   Memory→新策略的完整引用集合與 QA 是另一閘門，不能洗掉 lineage 來避過 R1。

這些是日後可能需要的最小工作清單，未包含任何交易基礎建設、服務部署或自動化。

## 風險與失敗裁決

| ID／嚴重度 | 風險 | PROPOSED 控制／驗收證據 | 未解決時 |
| --- | --- | --- | --- |
| R01／blocking | 本地可控時間被誤當外部證明 | 原物、hash、獨立遠端收件／核驗與被核准時間政策 | NO-GO |
| R02／blocking | proof 只 pending、block time 不精確、遠端編輯／刪除 | 完整證明、外部觀察時點、最新 metadata、獨立保存原物；不可回溯補認 | sample quarantine；無替代核准路徑則停 |
| R03／blocking | IEX／NAV／adjusted close／盤後價冒充官方 close | 上市市場、具體欄位／條件、原始 precision／session、文件版本 | 不評分 |
| R04／blocking | 免費可看但無權保存／核驗／再散布 | 資料使用範圍及條款快照、可重現的受限保存位置 | NO-GO；不付費繞過 |
| R05／blocking | 來源同上游或價格不一致 | 上游 lineage、兩份原始證據、final/correction/revision 管理 | PENDING／DISPUTED；不選有利價 |
| R06／blocking | 宣告 cutoff 後資訊、歷史網頁新版本或模型隱藏輸入 | as-of source inventory、原始 Room輸出／工具紀錄、獨立核驗、未知項揭露 | quarantine/invalid；污染則停止 cohort |
| R07／blocking | Current Core 不支援外部 custody／真實 finalization | 另行授權的 adapter／verifier／狀態契約測試及 QA | NO-GO；不得手改已接受 Core |
| R08／blocking | 跨預測 memory 失去來源或自動啟用 | 保持 per-sample proposal；固定 strategy，無後續 influence | 阻止新鏈／停止未授權活動 |
| R09／high | 發布延遲、半日／休市、公司行動、停牌、更正 | 預先固定日曆／價基礎／missing deadline／revision policy | 保留 attempt 與 unresolved，不能換日 |
| R10／high | 五樣本被誤稱學習改善，結果好才擴樣 | 固定名冊／endpoint、全部 attempts、只描述流程 | 禁止改善／收益或策略提升主張 |
| R11／high | 真實 Bot 身份不明、模型共享造成假獨立 | 已核准身份／prompt版本、原始輸入、獨立人工 Reviewer | 不使用 fixture identity 簽真實樣本 |
| R12／blocking | 額度升級、付費、訂單、部署、排程、憑證外洩 | 人工預算審核、無執行／API／自動化路徑、受限文件存取 | 立即停止並通知 Founder |
| R13／high | 本地整個 DB 被一致重寫、來源受限無法公開 | 外部內容錨點、獨立原物保存、合法 reviewer 存取；hash 不是簽章 | 不聲稱可證明任意篡改；缺證不納入 |

## GO/NO-GO 決策包（PROPOSED）

Founder 需要逐項審查而非單一 blanket GO：

- 採用本方案或明確修改，核准 custody trust model、證據位置與獨立 Reviewer。
- 核准可核驗的官方資料方案、使用權／保留／公開範圍與成本，維持未授權支出為 0。
- 若需要，另行授權最小 importer／verifier／資格政策的工程改動與獨立 QA。
- 在工程及證據守衛通過後，再給**新的 Pilot execution 授權**：具體未來日期名冊、
  八個既有角色的人工運行範圍／額度、單一 strategy/memory、每個 PROPOSED 時點與
  缺資料規則、停止條件及結案報告限制。不能用本 Draft PR 合併當執行許可。
- 任何候選版本／前瞻 comparison／memory activation 必須再獨立決策；30 blocks、
  0.02 Brier、95% CI 原建議保持未採用，五樣本計畫不取代正式策略晉級要求。

只有每項證據及權限皆滿足，Founder 才能決定下一步；本報告不自行發出 execution GO。
無法合法且零新增支出地取得官方 close 時，維持 NO-GO，而非降級為 IEX 或 synthetic close。

## 本次驗證、交付與限制

本分支只新增 `l0/pilot-readiness/` 的規劃文件與研究／完整性清單。
所有 **138 個 main 基線檔案**逐一與固定基線 Git blob 比較，保持 byte-identical；
因此現有 L0 Core、四份 adopted 設計、G1/G2a、M1、歷史 manifests 與 LAB-STATE 全未改。
M1 SHA-256 仍為 `2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e`。
原未追蹤 L0-R2-QA.zip 留在原處，未收入此分支提交。

驗證只含文件內連結、來源固定版本／hash、基線 bytes、PROPOSED 標記與變更範圍；
沒有跑 Core、Scorer、交易 fixtures 或模型。既有獨立 QA 46/46 是基線接受證據，
不是本次新增或重跑的結果，也不能作端到端 Pilot readiness PASS。
三份官方 GitHub 文件精確來源／SHA 在 research-sources.json；四個直接文件站
403 與尚未核驗條款在 SOURCES 明列。本次沒有擴大網路權限、繞過存取限制、
安裝 timestamp/market SDK 或調用其服務。不是法律意見；資料權利需實際權利方條款。

交付 Draft PR 供 Founder 審查，保持 Draft，不合併；本次未實際凍結任何新預測、
取得真實 Outcome、評分 M1、建立時間戳承諾、產生任何訂單、連接券商、支付 API、
啟動新 Bot、定時器、模型部署、正式 Pilot 或 G2b。交付後停止等待 Founder 決策。

**結論：L0-FORWARD-PILOT-READINESS — READY FOR PLANNING REVIEW；PILOT NO-GO。**
