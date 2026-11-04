# 預測凍結與外部時間證明評估

新增方案全部 **PROPOSED**；不實際執行。基線與來源見 [入口](README.md)／[來源](SOURCES.md)。

## 要證明的命題

核驗者必須能確認「這組確切預測及其研究／挑戰／規則／版本內容，最晚在
核准 deadline 前已存在且無替換」。內容存在的最晚時間，不是研究發生的精確時間，
也不證明資料來源沒有洩漏、作者是真正 Chief、或預測正確。
本地 SQLite created_at、檔案 mtime、Git author/committer date、自己簽名的日期都
不是外部時間證明。Git commit hash 可以綁內容，不能單獨證明到達第三方的時間。

## PROPOSED 凍結物與不可變邊界

Chief 完成至少三項實質 Skeptic 挑戰的處置後，輸出候選 bundle：原始 Room
輸出／訊息 ID、正式 prediction_v1、measurement、evaluation 規則、strategy
完整內容與版本、memory snapshot、來源 inventory、challenge/disposition。
保存每個檔案精確 bytes 與 SHA-256；JSON 另保存既有 G1 canonical body hash。
清單按路徑排序，含編碼、hash_kind、長度與所有外部引用，排除自我雜湊。
清單之外另存 receipt，避免 receipt 反過來修改其證明的 bundle。

PROPOSED commitment：對固定 bytes 的 manifest 加入新隨機 salt，明確記錄
域分隔字串、串接格式和算法後做 SHA-256。只對外揭露 commitment，不揭露
預測機率、研究私密內容或原始授權資料；核驗時提供 salt、manifest 和原物。
Salt 不替代加密，也無法隱藏提交帳號／時間／大小等外部 metadata。
外部 receipt 必須綁原始預測 ID/hash、bundle commitment、外部物件 ID、外部
時間、驗證政策版本與核驗者身份。重新算 hash 或換 bundle 均需新預測／新 attempt，
原失敗 attempt 留在名冊；deadline 後不能補寫成原已凍結。

`frozen_at_utc` 是候選文件中 Chief 宣告的時點，外部 receipt 是其後取得的
獨立見證時點；兩者不可混同或為了湊相等而回填。receipt 延誤時保留本地
FROZEN／quarantine 的原始事實，但不得將其當作完成可驗證前瞻樣本。

## 方案比較

| PROPOSED 方案 | 最低增量費用 | 可獨立核驗內容 | 信任／限制與裁決 |
| --- | --- | --- | --- |
| 既有 GitHub 帳號的遠端收件記錄 + 獨立人工見證 | 外部服務費可為 0；人工與既有帳號成本非零 | Reviewer 在自身已授權帳號查到同一 commitment、server-created_at、物件 ID／URL／帳號，另存原始 response 和見證 receipt | 依賴 GitHub 時鐘與未編輯 metadata、見證者誠信；不是可信 TSA 簽章。不把本地 Git 日期當證據。最低成本候選，但需 Founder 接受中心化信任模型 |
| OpenTimestamps 完成證明 + 獨立 Bitcoin Core 核驗 | 提交通常不需用戶另付逐筆鏈上交易費；服務存續與免費政策無保證；驗證節點有儲存／網路／運算成本 | 原物到區塊承諾的密碼學路徑與區塊鏈包含關係 | Pending calendar 回應不是完成證明。官方 client 文件說確認需數小時、核驗需本地 Bitcoin Core（可 pruned）。此任務未安裝、未 stamp、未 upgrade、未驗證樣本 |
| RFC 3161 TSA signed token | 是否有合適免費 TSA 未驗證；不能把試用當永久免費 | messageImprint、genTime、序號／policy、TSA certificate chain 與核准信任根；離線保存 token 和簽章驗證材料 | 依賴 TSA 時鐘／政策／證書撤銷與長期驗證。免費、精度、保存權、SLA 均須另查。不可發起付費請求 |
| email／人工簽收 | 可能無新增費，需既有郵件與獨立 Reviewer | 原始訊息和 Received headers、對方簽收的 digest 與時間 | 單一自寄郵件或可編輯文字不足；郵件 header 可被偽造，對方自填 UTC 也不是強 TSA。僅輔助見證 |
| 本地 Git／SQLite／GPG 簽名 | 幾乎無增量服務費 | 內容完整性、簽署金鑰控制（若金鑰可信） | **不能作獨立外部時間證明**；不接受為主方案 |

### PROPOSED 最低成本候選：人工見證的遠端收件證明

使用獨立 Reviewer 可存取的既有私有 GitHub evidence 位置，由 Founder 核准
寫入者／Reviewer 權限；不得為此開通付費組織功能。遠端記錄包含 commitment
和 schema，不必公開預測內容。Reviewer 以自己的會話取得服務端時間／ID，
核對內容與未編輯狀態，保存回應、遠端 URL、存取身份及當時觀察到的外部 UTC。
以服務端最新內容時間（含 updated_at）判定 deadline；不能將保留的早期 created_at
套到 deadline 後被編輯的新 hash。編輯、刪除、無法重新取回、時間不確定均停止資格。
同一 bundle 可另附 OTS 完成證明增加長期內容存在性佐證，不替換主 deadline 判定。

不保證 GitHub 記錄永久不可刪；人工匯出的 bytes/hash 與獨立簽收只補強保存鏈，
不等同主機簽署的可信時間戳。核驗者至少能用新取得的原物重算 hash，並獨立讀取
主機 metadata，不只閱讀發起者的 screenshot。若 Founder 要求可離線長期驗證、
無需信任主機時鐘的嚴格 TSA 等級，本方案 **NO-GO**，須另選核准 TSA／政策。

### OTS 的 UTC 陷阱

區塊 header timestamp 並非精確可靠 UTC；不能僅看 OTS 顯示日期就斷言在某分鐘
deadline 前完成。若用它證明硬性 UTC deadline，需額外核准「該區塊已在 deadline
前被獨立觀察」的外部證據與誤差／確認政策。更多 confirmations 改善鏈穩定性，
不會把礦工時間變成可信 UTC。calendar 回應也不能冒充鏈上確認。
使用已有獨立節點者可降低新增支出；若沒有，不能宣稱零成本獨立驗證成立。

## Core 的現況與後續工程閘門

現有 Core 刻意只接受 PENDING／UNVERIFIED custody，拒絕升級 ELIGIBLE，且
所有 score 的 performance_eligible 固定 false。**此方案不會更改這些行為。**
未來要由驗證器讀取上述 receipt、綁 actor keys／身份與外部證據、驗證時間順序、
保持 quarantine latch、以另行 Founder decision 進行受限資格決策，必須先有獨立
工程授權與 QA；不可直接修改 DB 或將 custody_status 改成 VERIFIED 來繞過。

PROPOSED 驗收：錯 hash、錯 salt、不同 metadata 時點、deadline 後編輯、缺少
原物、失效證明、Reviewer 非獨立、時間政策未定，任一項即 quarantine／no-go。
不因結果好看而回溯補認證。M1 不適用本流程，不追溯補凍結。
