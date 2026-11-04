# D0 完整合成記錄樣例

**SYNTHETIC / RESEARCH_ONLY：以下是程式寫定的教學資料，不是實際 Agent 運行或學習成果。**

實際以 CLI 匯入以下八筆記錄，重複匯入沒有新增；SQLite 匯出的內容與原 JSON 一致。

| ID | 類型 | 關鍵內容 | 精確父記錄 |
| --- | --- | --- | --- |
| D0-MARKET-1 | market | 虛構基準 100.00 | 無 |
| D0-NEWS-1 | news | 虛構混合訊號摘要 | 無 |
| D0-RESEARCH-1 | research | 第一輪研究問題 | D0-MARKET-1, D0-NEWS-1 |
| D0-PREDICTION-1 | prediction | UP .6 / FLAT .3 / DOWN .1；寫定的假設 | D0-RESEARCH-1 |
| D0-OUTCOME-1 | outcome | 虛構目標值 98.00；尚未核驗 | D0-PREDICTION-1 |
| D0-REVIEW-1 | review | 原假設與反證，保留失誤 | D0-OUTCOME-1 |
| D0-MEMORY-1 | memory | 下一輪可考慮的待驗證研究筆記 | D0-REVIEW-1 |
| D0-RESEARCH-2 | research | 明確讀取 Memory 的下一輪研究問題 | D0-MEMORY-1 |

這一輪沒有正式 Brier／績效計分，沒有把該筆記啟用為策略，也沒有宣稱模型能力改善。

每筆來源文字、取得與目標時間、來源 SHA-256、完整記錄 SHA-256、父記錄 hash 均見 [完整 JSON](synthetic-loop.json)。
實際匯入與重試計數見 [CLI 執行輸出](../evidence/cli-run.json)。

資料含研究反饋，但「下一輪問題有引用舊筆記」只證明管線可運行；不能證明 AI 會因此作出較好預測。
