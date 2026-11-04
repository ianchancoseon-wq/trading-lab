# D0 Data Collection MVP — 實作交付報告

狀態：**D0 MVP SUBMITTED FOR REVIEW / NOT ACCEPTED**。
日期：2026-11-04（Asia/Shanghai）。
基線：`2a681e8bd247a68446f09e661bde572752504727`。
獨立分支：`feat/d0-research-data`。最終 head SHA 隨提交回覆／PR 提供，避免自參照 hash。

Founder D0 決議授權本次離線工程、人工資料輸入能力及 synthetic tests，並將研究
資料收集與正式績效資格分離。本 MVP 不受限於 PR #5 尚未採用的正式 Pilot
準備條件，也沒有採用／修改那份方案或現有 L0/G1/G2a 規則。

## 已實作

- `d0/records.py`：七種統一記錄格式，SPY 限制、RESEARCH_ONLY 固定分類、來源
  原文與 SHA-256、取得／建立／目標時間、版本／父記錄 refs、缺值標記、機率／
  價格／JSON 錯誤檢查。重用既有 L0 canonical hash 語義，不改其函式。
- `d0/store.py`：獨立 local SQLite，原始預測不可變、同 ID/hash 重試、連續修訂、
  必要父記錄／subject／target／current-review 檢查，跨輪 Memory 可作明確研究輸入。
  BEGIN IMMEDIATE + synchronous FULL + ordered hash chain + immutable triggers。
  非 D0 DB 在建表前被拒絕，不會在 L0 DB 新增 D0 資料表。
- `d0/__main__.py`：人工檔案 import/status/export，stdout JSON，錯誤 exit 2；
  不初始化外部服務、不含模型／行情／券商 client。
- `d0/examples/`：八筆可查看原物與完整讀取 trace，包含下一輪 research 的 Memory parent。
- `d0/tests/`、`d0/evidence/`：離線 adversarial tests、CLI 實際執行、完整性證據。

原始資料不因「缺值／未認證」被偽造補齊；payload 缺值明確標記 MISSING，
最小來源／時間 metadata 缺失則拒絕並報錯。正式 eligibility 不在 D0 中判定。
所有記錄 performance_eligible:false；沒有 outcome quality promotion、formal
score、績效彙總、策略 activation 或真實模型學習過程。

## 實際測試結果

命令（repository root）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s d0/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s l0/tests -v
```

- **D0：18 tests passed**，0 failures/errors/skips。
- **L0 回歸：34 tests passed**，0 failures/errors/skips。
- 合計 **52 developer tests passed**，不是獨立 QA 或 Founder acceptance。
- G1/G2a 的 Risk Gate／交易 fixtures／模擬器均未執行；M1 未評分。

D0 測試包括完整研究循環、重試無重複、stale/rehashed ID conflict、原預測保留與
新版本連續鏈、缺值不補值、錯來源 hash／時間 metadata、壞父 refs／target、
NaN/Infinity／壞 close／重複 JSON key、偽造績效分類、歷史回顧標記、舊 Review
不能在更新 Outcome 後驅動新 Memory、不得使用 L0 DB、CLI JSON／錯誤回傳。

持久化驗證：注入 batch write failure 後整批 rollback；三個獨立 connections
並發匯入只新增八筆；子程序在批次中途退出後 DB 無部分資料、commit 後退出
保留八筆；重開後精確重建相同記錄；儲存鏈損壞 fail closed。
既有 L0 的身份／版本、quarantine、Score／Review／Memory 與持久化回歸全部通過。

實際 CLI 已以獨立 temporary DB 完整執行：

| 操作 | 真實輸出 |
| --- | --- |
| 匯入 synthetic-loop.json | inserted=8, replayed=0 |
| 原檔再次匯入 | inserted=0, replayed=8 |
| status | 8 records，7 類，missing=0，RESEARCH_ONLY，performance_eligible=false |
| export | 逐記錄與原始合成 JSON 完全相等 |

可查看：[學習資料軌跡](examples/LEARNING-TRACE.md)、[完整 JSON](examples/synthetic-loop.json)、
[CLI 輸出](evidence/cli-run.json)、[D0 測試](evidence/d0-tests.txt)、[L0 回歸](evidence/l0-regression-tests.txt)。
資料與 Agent 敘述均為 scripted synthetic fixtures，無實際 Grok／AI API 呼叫。
Memory 改變下一輪研究輸入，並不證明預測改善，更不證明 AI 已具備學習能力。

## 完整性與範圍

本次只新增 `d0/`；所有既有 **138 個 main 基線檔案**逐 byte 與指定 base 比對，
保持不變。涵蓋全部 L0、G1/G2a、M1、歷史 manifests、adopted L0 文件和 LAB-STATE。
M1 原 SHA-256：`2317319d9ec2b33d9ccd2b8316c6c39b2f78d2d25e7fa7ad45aeb0e9274f224e`。
檔案清單／原物 hash 見 `evidence/baseline-integrity.json`、新增交付 SHA 見
`evidence/FILES.sha256`（不含自身 hash）。原有兩個未追蹤 ZIP 保留、不收入提交。
未新增 credentials、token、真實券商識別碼；來源採 `fixture:`，沒有 live network dependency。

## 限制／待驗收事項

本 MVP 只接 UTF-8 JSON array，沒有自動網頁／CSV／PDF 抽取。source.content
代表操作者提供的原文或摘要，不等同完整網站／PDF；真實資料來源／授權／身份未經認證。
來源相同但不同 ID 的記錄不自動合併；使用穩定 ID 作重試。缺失與回顧標記是研究
限制提示，不是正式品質或前瞻證明。人類仍須審閱亂填時序和輸入內容。

SQLite 需要可靠 local filesystem／fsync；未測實際斷電／磁碟控制器故障。
hash chain 不是簽章，高權限整庫重寫或尾部截斷無外部錨點不能證明沒有發生。
全量重建／驗證優先可稽核，批量操作可能 O(n²)，未做大量資料效能設計。

無策略升級、無 formal metrics，亦無宣稱學習改善。既有 L0 custody 和資格判斷
完全未修改；D0 的研究 Memory 流轉不代表正式 memory activation。
本次未執行真實資料匯入、券商／行情／模型 API、訂單、正式 Pilot、定時服務、
部署、G2b 或任何付費服務。下一步是 Founder 審查本 MVP 與合成 trace，並另行
決定是否／如何手動提供真實研究資料。只交付 Draft PR，不合併。

建議：**D0 MVP READY FOR REVIEW**，等待驗收。
