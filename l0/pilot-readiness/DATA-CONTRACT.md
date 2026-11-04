# Room → L0 → Outcome → Review／Memory：PROPOSED 資料契約

所有新增外部 sidecar、欄位、狀態與橋接流程均 **PROPOSED**，未實作／未啟用。
不修改既有 `prediction_v1`、L0 envelope、Core 或已採用設計文件。

## 共同完整性與身份

現有 L0 欄位映射保持：`record_id → id`、`record_type → kind`、`actor_role → actor`；
`record_version=1.0`、`protocol_version=L0-v1.0`、`actor_identity`、`created_at_utc`、
`evidence_class`、`payload`、有序 `parents`、`prediction_ref`、`content_sha256`。
所有引用是精確 `{id, hash_kind, sha256}`；不能只有路徑或 prediction ID。
canonical JSON body hash 與 raw bytes hash 分開，不以 Markdown hash 替代 JSON hash。
改任何身份／版本／內容都需新 ID／版本，重試同 ID 同 bytes 才能 idempotent。

PROPOSED Room 身份 sidecar：八個已存在角色的已核准 identity binding、model／prompt
版本、Room ID、message ID、輸出作者、匯出時間、原始訊息時間、已知工具／資料存取、
原始檔案 hash 與匯出者。Codex 是工程核驗者，不是新增研究 Bot。Founder 身份為
外部決策者。不要把目前 `fixture:<role>` 當成真實 Grok／Founder 身份；部署 binding
變更不能直接套在既有 SQLite（其 mapping 已固定），需另行核准的新 Pilot 儲存空間。
原始 Room 時間是來源宣告，不等同外部 custody；匯出不證明模型沒有隱藏資訊。

## 逐階輸入／輸出與責任

| 階段 | 必要輸入 | 輸出／引用 | 失敗處理與現況 |
| --- | --- | --- | --- |
| Research Room | Founder scope；工具／horizon／cutoff；固定 strategy／memory snapshot；四位 specialist 的來源版本 | 原始 Room 匯出、來源 inventory、每項 claim／刊登及修訂 UTC／raw hash，明列已知、推論與未知 | 沒有可驗證的 publication/as-of 證據，不能補寫成已知；Room importer 尚未實作 |
| Skeptic → Chief | 同一 draft revision；至少三項不同實質挑戰 | challenge 的 claim、failure_mechanism、alternative、forecast_impact、resolution_test；Chief 每項 disposition、理由及挑戰 hash | 機器可查欄位／不同內容，人工仍須核驗實質性；Chief 唯一決定預測 |
| Chief final → Registry | 完整既有 prediction_v1；獨立 measurement；final research／challenge／memory／strategy／evaluation 原物 | 唯一 PRED ID/hash；完整版本身份 L0 records；primary_call 由凍結 probs + 既有 FLAT→DOWN→UP tie rule 導出 | 禁止反向用未來結果決定概率、bounds、策略或時間；不補 M1 欄位 |
| Freeze／custody | 完整 bundle、manifest、受核准的外部 receipt | Core freeze 的 strategy_version／strategy_ref／research_ref／memory_snapshot_ref／measurement_ref／evaluation_ref／primary_call／custody_ref；外部驗證 sidecar | 現有 Core 只接受 PENDING／UNVERIFIED；sidecar 不能強行變成 VERIFIED／ELIGIBLE |
| Outcome verification | exact freeze ref；指定 session／target_at；兩個來源的 raw evidence 及使用權 | Core outcome 的 ticker、session、currency、price_basis、close（decimal string）、target_at、verified_at、final、source_verified、session_verified、price_verified、source_refs、status | 日期未到不取結果；來源不一致 DISPUTED、缺證 PENDING；布林值是人工核驗輸入，不是資料商自證 |
| Scorer | exact prediction／freeze／measurement／最新 VERIFIED outcome；核准的 as_of | 既有 score result：actual、primary_call、summed Brier、Log Loss／Infinity status、directional_accuracy；完整父引用 | PROPOSED 尚未授權執行。score 不讀外網；performance_eligible 仍 false；不引用 fill 或 P&L |
| Review | 最新 Outcome 對應的有效 Score；原研究及反證 | findings、contrary_evidence、limitations；score_ref 如提供必須等於唯一直接 Score parent；前版 review 的 supersedes | Outcome 尚未重評分，禁止新 Review；不能選較有利歷史 Score；R2 已實作這些寫入檢查 |
| Memory proposal | 最新且仍綁當前 Score 的 Review；原始 prediction ID/hash | lesson、scope、confidence、falsification_condition、review_trigger、contrary_evidence、status；proposed_at／available_at／approved_at／effective_at；父 refs／supersedes | approved/effective 保持 null；無自動啟用；舊 Review 不得繞過新 Outcome 未評分的限制 |
| 新策略假設 | 同一預測下的記錄、反證與候選差異 | PROPOSED strategy record，parent_version_ref、version、rules、change_reason；外部 Founder decision | 不啟用、不升級、不形成新 cohort；跨樣本策略證據整合須另行契約／工程授權 |

## prediction_v1 與 measurement

保留既有 id、strategy_version、ticker、baseline_price、baseline_source_tier、band、
horizon_end、probs、EVENT_EXPOSED、knowledge_cutoff_utc、frozen_at_utc、content_sha256
及 demo／notes 的原始定義。新 genuine prediction 應與人工 fixture 分開標記，但
`demo:false` 本身不使它成為 verified genuine-forward evidence。

measurement 現有欄位：session、ticker、lower／upper（decimal strings）、currency、
price_basis=`official_regular_close`、market_timezone、target_at、band_unit、rounding_rule、
tie_priority。外部 measurement provenance sidecar 另記上市市場、baseline session／官方欄位、
日曆與公司行動政策 hash。不能把新欄位塞入 prediction_v1；也不重算既有 frozen bounds。

PROPOSED 本小型 Pilot 新 band=0.3 percentage points（±0.3%），以原始官方 baseline
close 計算 Decimal bounds、按核准交易 tick 四捨五入 HALF_UP 並保存精確字串。
這是新 Pilot 參數，不套用到 M1 或其他歷史預測。若工具 tick／價格基礎未核驗，不凍結。
UP if C>U、DOWN if C<L、FLAT 含兩邊界沿用既有規則；分數公式不變。

## 外部來源／核驗 sidecar（PROPOSED）

每個 source evidence 應保存：source_id、publisher／上游／listing market、field_name、
observation_session、observation_time、published_at、revision_at、retrieved_at、raw_artifact_ref、
raw hash、adjustment、currency／precision、entitlement／terms_snapshot_ref、verifier identity、
verification_at、disagreement／missing_reason。研究來源另有 first_available_at 與 cutoff decision。
不能用 retrieved_at 代替 publication；無法查得的欄位明列 UNKNOWN，不自動視為通過。
不同來源若共用上游在 corroboration roster 合併為一來源。

這些是 sidecar 契約，不是現有 Registry 可直接接受的新 record kind。
未來橋接器須對原物、metadata、L0 evidence.payload.artifact_sha256／locator／available_at
建立完整映射，並驗證 trusted receipt 與 observation，不准只把驗證旗標填 true。
Core 既有 evidence 是 hash/locator 記錄，不會自行檢查外站真實性／授權。

## 時序、修訂與避免假造歷史

Room 原始訊息時間、L0 記錄建立時間、SQLite 寫入時間、Chief freeze 宣告、外部
見證時間與 Outcome 發布／核驗時間分開保存。PROPOSED adapter 必須解決現有
Core 需完整 prediction_ref 才能寫 prefreeze evidence 的限制：Room 的可變 draft
先作不可變 raw artifacts 保存，Chief final 後才綁正式 PRED hash。不能為了滿足
`parents.created_at <= freeze` 而把新匯入記錄回填為較早的 Room 時間。
在真實時鐘下重演 finalization／normalization／registration／freeze／外部 receipt
的順序，是未來工程驗收必要案例；目前尚未有合格橋接器，故不得啟動 Pilot。

研究 cutoff ≤ Chief freeze 宣告 ≤ 外部收件及獨立核驗 < 核准 deadline < target observation；
外部證明若延遲，不改寫 frozen_at，記 failed/quarantined attempt。早期資料不能引用後來
結果或 memory。Outcome revision 追加 supersedes／原因；Score revision 追加前版 Score；
Review／Memory 同理引用各自最新 predecessor，保留舊 bytes。Lifecycle 不倒退不代表
最新 revision 已 review 完成；current-score/current-review binding 才是後續記錄的依據。

## 已知整合阻塞：Memory 不能偷偷變成跨樣本學習

R1/R2 會遞迴拒絕 Review／Memory／Strategy 的跨預測祖先。將上一預測 memory
包成同一新預測 evidence 也不能洗掉 lineage。直接把它放進新 freeze 的祖先鏈，
後續 Review 仍可能因跨預測 lineage 被拒絕。**不得繞過此限制或刪掉來源引用。**
PROPOSED 此五樣本只產生各自的 memory proposals，固定原核准 strategy，不把
任何新 memory 用於後續預測，不生成所謂已學習版本。完整跨樣本 Memory → 新策略 →
未來 holdout 需要另一個明確採用的 multi-prediction provenance 契約、工程改動與 QA。

PROPOSED 邊界驗收（未執行）：錯 hash／版本／身份、延遲 receipt、deadline 後編輯、
未知 source publication、錯 session／盤後或 adjusted close、缺少最新 score、混入跨預測
memory、程序中斷／重試／重啟，全部應 fail closed。人工匯入及跨系統驗證器未實作，
不能僅以已接受 Core 的 34/46 項離線測試視作這條端到端流程已通。
