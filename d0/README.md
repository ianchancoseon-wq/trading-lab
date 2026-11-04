# D0 — 手動研究資料收集 MVP

D0 先讓資料閉環運作：市場／新聞 → 研究 → 預測 → Outcome → Review → Memory →
下一輪研究。所有資料固定 **RESEARCH_ONLY / performance_eligible:false**。
不要求正式 freeze custody 或績效資格，未核驗及缺值資料也能保留供研究。
D0 不會修改 L0 Core 的資格、不評分 M1、不執行模型或正式 Pilot，不產生訂單。

## 可直接查看的完整範例

[八筆學習資料軌跡](examples/LEARNING-TRACE.md) · [完整 JSON](examples/synthetic-loop.json)
· [實際 CLI 結果](evidence/cli-run.json)

這是程式寫定的合成 Agent 輸出，不是真實 AI 調用。數字、新聞、日期全部虛構；
下一輪研究明確引用上一輪 Memory，只證明資料流能跑通，不代表學習能力提升。

## 執行（Python 標準庫，從 repository root）

```sh
# 使用獨立本地 D0 檔案；不要指定既有 L0 DB。
D0_RUN_DIR=$(mktemp -d)
python3 -B -m d0 --db "$D0_RUN_DIR/research.sqlite" import d0/examples/synthetic-loop.json
python3 -B -m d0 --db "$D0_RUN_DIR/research.sqlite" status
python3 -B -m d0 --db "$D0_RUN_DIR/research.sqlite" export > "$D0_RUN_DIR/export.json"
# 再匯入同一份檔案：inserted=0, replayed=8。
python3 -B -m d0 --db "$D0_RUN_DIR/research.sqlite" import d0/examples/synthetic-loop.json
```

`status` 顯示總數、各類數量、缺值筆數與研究分類；`export` 按儲存順序輸出全部記錄。
匯入檔必須是 UTF-8 JSON array，依父記錄順序排列。失敗回傳 exit 2、stderr
`D0 error:`；整批 rollback，不留半組有效記錄。CLI 不啟動背景服務／網路或排程。
不要用相同輸出檔路徑覆蓋未保存的手動來源檔。

## 最小統一格式

可複製範例 JSON 編輯，或使用 `d0.records.build()` 組裝人工輸入。

| 欄位 | 語義 |
| --- | --- |
| schema / kind | `d0_record_v1`；market、news、research、prediction、outcome、review、memory |
| id / series_id / version / supersedes | 不可變記錄 ID；修訂序列與連續版本；前版精確 hash ref，首版為 null |
| symbol / evidence_class / origin | 只收 SPY；固定 RESEARCH_ONLY；MANUAL 或 SYNTHETIC |
| actor_identity | 來源提供的 Agent／人工身份標籤，未經身份認證；範例為 synthetic:scripted-example |
| source | name、uri、content、acquired_at_utc、sha256；uri 只保存，不抓取 |
| created_at_utc / target_at_utc | 記錄建立與目標觀察時間，必須有時區，不推測缺失的時間 |
| payload | 類型對應的原始資料／摘要／機率／理由等 |
| parents | 有序 `{id,hash_kind,sha256}` refs；完整可重建的跨輪來源鏈 |
| prediction_ref | Outcome／Review／Memory 必須指向其原始 D0 prediction 的精確 ref；其餘為 null |
| content_sha256 | 記錄 canonical JSON body 的 SHA-256（排除其自身），與 L0 哈希語義一致 |
| missing_fields / data_status / timing_status | 自動推導的缺值與時間限制標記，不可自行偽造以隱藏問題 |
| performance_eligible | 永遠 false，不能由輸入提升 |

來源 `source.sha256` 是**手動提供的 UTF-8 source.content bytes** 的 SHA-256。
它不宣稱等於未提供的整份網頁／PDF hash，也不保證 source URI 的內容真實或有使用權。
若未提供 source.sha256 或 content_sha256，匯入時計算；若已提供則嚴格核對。
不保留輸入 JSON 的排版／空白作原物；來源原文保留在 source.content，其他值採
canonical JSON 儲存。原始預測的持久化值及來源文字一經保存不得覆寫。

必要語義欄位：market(session, close)、news(summary)、research(question,
knowledge_cutoff_utc)、prediction(probs, rationale, knowledge_cutoff_utc)、
outcome(observation)、review(findings, contrary_evidence)、memory(lesson, scope,
falsification_condition)。缺值用 null／空字串並標記 MISSING。close、probs 和 cutoff 的缺值保留原樣，
不補值。缺 cutoff 的時間狀態為 NOT_ASSESSED；非空而格式錯誤的值會被拒絕。
來源名稱／URI、取得時間、目標時間、ID 等最小可稽核 metadata 缺失則拒絕匯入。
機率若存在須為 UP/FLAT/DOWN、有限且加總為 1；market close 若存在需正有限
十進位字串。不進行官方 close 認定、事件分類、Brier 或收益計算。

cutoff 晚於目標或記錄建立時間時，匯入會以 TIMING_CONFLICT 拒絕。比較採時區
換算後的時間點，等於界線是合法值。建立時間已達目標，或來源在 cutoff 後才取得，
標為 RETROSPECTIVE。其餘有 cutoff 的記錄標為 DECLARED_ONLY，表示自報時序。
原始來源的
publication time、Agent authored time 等可放 payload，不能拿 acquired_at 冒充。
時間／可信度資訊不全的內容仍只作研究資料，不進正式績效分母。

## 修訂、重試與研究反饋

同 ID／相同內容重匯入為 replay；同 ID 改內容（即使重算 hash）拒絕。
修訂需新 ID、同 series_id、version+1、supersedes 指向最新前版且列為 parent。
這保留原預測，不重新解釋它。不同 ID 相同來源不自動去重：同一新聞可能有不同
研究用途；操作者應重用穩定 ID 來做 retry，不用新 ID 冒充新增樣本。

Outcome 必須連到指定 prediction。Review 使用該 prediction 的最新 Outcome，
Memory 使用最新 Review 且其 Outcome 仍當前有效。這三類的修訂保留首版的完整
prediction_ref（ID、hash kind、hash）與 target，匯入與重開均驗證。
新 research 可以引用此前 Memory 的完整 hash parent，不需要宣稱它已經是
正式「approved memory」。D0 沒有策略 activation API，既有 L0 跨預測限制不變。

手動公眾歷史行情／新聞摘要可以按這個格式加入，但使用者仍須遵守資料取得與
保存權利；資料公開不是再散布授權。不要匯入 credentials、私人通訊或付費內容。
本次交付只使用 synthetic source，不查資料、不調用 Grok 或其他 API。

## 測試與邊界

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s d0/tests -v
```

D0 使用獨立 SQLite、完整交易、hash chain 與 immutable triggers。既有非 D0 DB
會在寫入鎖保護下、建表前被拒絕；L0 也使用同一初始化交易檢查 schema／類型、建表及觸發器，避免首次並發初始化混庫。舊資料庫若含
衝突 cutoff 或跨預測修訂，重開會報錯並保留原始記錄與 hash。
新匯入可計算缺少的 hash／衍生欄位；已存資料讀取則要求完整欄位、核對實際 JSON
與原 hash chain，不會自動補回刪掉的 source.sha256、content_sha256 或狀態欄位。
沒有外部時間／簽章、模型推理、資料真偽驗證、CSV/PDF
解析、GUI、自動採集、排程或正式統計。獨立 connection 供每個 worker 使用；
不要在 threads 間共用 Store handle。失敗匯入以 exit/stderr 回報，未建立額外持久
錯誤事件表。完整鏈驗證適合此小型 MVP，非大型資料倉庫。

來源／身份自我宣告與一致 hash 不等同外部認證；高權限者一致重寫整個 DB 或截斷
尾端，沒有外部錨點便不能保證偵測。保留原始人工檔與 SQLite 備份，由操作者管理。

詳細結果：[D0-IMPLEMENTATION-REPORT.md](D0-IMPLEMENTATION-REPORT.md)。
