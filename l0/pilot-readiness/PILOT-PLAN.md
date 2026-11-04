# 小型只觀察預測 Pilot 計畫 — PROPOSED / NOT AUTHORIZED

本文件每個新增選擇、時間、數量、截止與成功／停止標準都為 **PROPOSED**。
不建立真實預測、不排程、不發送任何研究任務、不執行下列流程。
啟動前必須逐項通過 [Readiness 閘門](READINESS-REPORT.md)。

## 目標與樣本

PROPOSED 目標只測量：能否完成可稽核的 prospective freeze → 對應官方 Outcome →
一致 Scorer → 不可變 Review／Memory proposals 的流程。不是證明學習、收益、
交易能力或策略優越性。沒有訂單，也不呼叫 NO_TRADE 的 execution/gate 路徑。

PROPOSED instrument 僅 SPY；horizon 為下一個預先登記完整美股常規 session 的
官方 close，相對前一交易日已核驗官方 close。五個未來、完整 session／五個唯一
prediction ID；不重複計數、不含 M1、任何既有歷史預測或 synthetic fixtures。
實際五個 session 日期由 Founder 在新授權時一次核准，必須都在授權及準備完成之後；
本文件不預先填實際交易日，也不推算 2026-11-10 結果。相鄰日 horizon 共享基準點，
樣本不視為統計獨立；五樣本不足以做學習效能推論。

PROPOSED 固定一個 Chief strategy version/hash、核准 memory snapshot（可為明確空
snapshot），不在 cohort 中更新。八個既有角色依其契約工作，Codex只核驗工程；
本次不調用／部署模型，不更改 prompt/runtime，不新增 Bot。未來手動使用既有
Room 的範圍／額度也須另經授權，不能假設已有訂閱就代表可啟動。

## PROPOSED 時間與資料規則

每個 target D：baseline session 為核准日曆中的前一交易日 D−1。
PROPOSED cutoff D−1 17:30、Chief freeze 最晚 D−1 18:00、外部 receipt 與人工
核驗 deadline 最晚 D 09:00，均為 America/New_York，UTC／上海顯示另行轉換。
採較長空檔讓低成本外部收件／補強 proof 有時間完成；不是服務 SLA。
外部 deadline 之後才取得證據的樣本不算合格。OTS 尚 pending 不能視作完成。

若 D−1 17:30 前尚無合格 baseline official close 或其使用權／證據，該預登記
attempt 失敗／quarantine，不能延後 cutoff 或換 baseline。研究需使用事件發布
當時的版本；已知未來事件可列情境，但不能填入事後實際值。
PROPOSED band 與 rounding 見 DATA-CONTRACT；精確 bounds 在 freeze 前固定。

只選完整常規 session；半日、臨時 closure、停牌導致 official outcome 定義不明時
保留例外與 pending，不改用下一日／盤後收盤。日曆、公司行動規則必須預先核准；
不要用此設計對實際交易日作未查證斷言。

PROPOSED D+1（下一美股交易日）進行一次人工 official-close 核驗；若仍未具
可信 final 狀態，維持 pending。PROPOSED D+2 18:00 ET 為此預登記 cohort 的
缺資料結案點：標記 unresolved，不作 imputation。後續官方更正仍追加留痕，不
覆蓋過去報告；若需要重新開 cohort，須另行 Founder 決策。這不是自動排程。

## PROPOSED 全量名冊與分母

Founder 先簽五個 target 的名冊：target、baseline、deadline、strategy/memory、
custody/data/evaluation policy refs、actor bindings、預算與停止規則；此時不含
未產生的正式 prediction hash。每次嘗試其後補 immutable refs 並保留失敗歷史。
報告必須逐項列 registered attempts、not frozen、freeze pending／quarantined、
await outcome、pending/disputed/invalid、scored、reviewed、memory proposed。
所有 status 與 reason 留痕；有利／不利結果同樣保留。

PROPOSED 處理成功標準：五個預登記 attempt 全部有可重建的結案路徑；不一定
全可評分。若有任何失敗，不得稱「五個有效樣本完成」。每個 scored 樣本須通過
全部證據守衛，由獨立 reviewer 從保存的原物重建同一分類與算術；實際報告分開
呈現每個分母。這是流程完成度，不是統計驗收或學習改善。

公式沿用既有 summed multiclass Brier 與 Log Loss、derived primary accuracy。
PROPOSED 只作有限、描述性報告，依然保留 Core performance_eligible:false；
無收益、交易 P&L、Sharpe、正式 strategy comparison、30-block/0.02/95%CI 閘門。
五個新 memory 只作 proposed，不進下一個預測，不升級策略。

## PROPOSED 失敗／停止規則

- **樣本失敗／隔離**：任何 freeze 漏時、hash/identity/版本錯、來源未知、
  實質挑戰缺失、錯 session/price basis、無法核驗外部 receipt 或 close，不進有效分母。
- **爭議**：兩來源不一致／共享不明上游、官方更正或價格精度衝突，OUTCOME_DISPUTED；
  不投票取價、不挑對預測有利者、不先評分再等確認。
- **立即停止整個 cohort 並通知 Founder**：偽造或刪改證據、未授權解除 quarantine、
  後見資料污染、任何訂單／券商連接／模型新部署／付費升級／自動排程行為、
  預算超額、身份憑證外洩、無法恢復資料或無獨立核驗者。
- **資料權限／可得性停止**：主來源授權到期、禁止必要保存／核驗，或外部證明路徑
  不再可用，暫停未開始的 target，保留原名冊；不私自換供應商／日期／proof政策。
- **固定結束**：五個 attempt 結案或觸發提前停止即結束；不追加樣本直到分數好看。
  逾缺資料 deadline 亦留為 unresolved，不自動延長或補足到五個有效分數。

停止後只交付人工整理的 cohort evidence/report，等待 Founder 審查。解除停止、
新 cohort、正式學習比較、memory/strategy activation、交易或 G2b 都需新授權。
