# L0 Forward Pilot Readiness — Founder 審查入口

日期：2026-11-04（Asia/Shanghai）。授權：技術準備、文件研究與方案評估。
基線 main：`2a681e8bd247a68446f09e661bde572752504727`。
獨立分支：`docs/l0-forward-pilot-readiness`。

**建議：準備文件 GO FOR REVIEW；正式 Forward Pilot NO-GO。**
目前沒有經核准且可驗證的外部 custody、現行官方收盤資料／使用權方案，
現有 Core 也刻意不接受 VERIFIED custody 或解除隔離；不能靠文件替代實作閘門。
所有本目錄新增方案、數值、時點與驗收參數均為 **PROPOSED / NOT ADOPTED**。
既有已採用規則與既有 Core 行為以原文件／程式為準。

審查文件：

- [FREEZE-CUSTODY.md](FREEZE-CUSTODY.md)：最低增量成本方案、獨立核驗與信任限制。
- [DATA-COST-ASSESSMENT.md](DATA-COST-ASSESSMENT.md)：來源、延遲、官方 close 語義、授權及成本。
- [DATA-CONTRACT.md](DATA-CONTRACT.md)：Research Room → Registry → Outcome → Scorer → Review → Memory。
- [PILOT-PLAN.md](PILOT-PLAN.md)：小規模觀察設計、全樣本名冊、失敗／停止規則。
- [READINESS-REPORT.md](READINESS-REPORT.md)：實作差距、風險、GO/NO-GO 條件、完整性及 Founder 決策。
- [SOURCES.md](SOURCES.md)：實際閱讀來源、固定版本、短摘錄與無法查證項目。

沒有啟動 Pilot、凍結新預測、產生 Outcome、評分 M1、執行 Core／交易測試、
發送時間戳請求、連接行情／券商／模型 API、啟動 Bot／排程、付費或部署。
只讀公開技術文件；GitHub 用於基線查核與提交本文件 Draft PR。
既有 `L0-R2-QA.zip` 未追蹤檔保留，未收入提交。
