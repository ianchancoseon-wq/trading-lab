# 官方收盤價、資料來源與成本評估

日期 2026-11-04。所有新增選擇／時限／預算均為 **PROPOSED**。
本次只讀文件，未呼叫行情 API、下載真實行情或驗證任何市場 close。
證據等級與精確 URL 見 [SOURCES](SOURCES.md)。

## 定義先於供應商

目標是指定工具、指定交易日、指定上市市場的 **官方常規交易時段收盤價**，
不是任何畫面上的最後價。正常美股 RTH 通常為 America/New_York 09:30–16:00；
半日市、臨時休市、停牌或拍賣延後必須以交易所日曆與規則核驗。不能永遠寫死
UTC 或上海時間；也不能把盤後價、ETF NAV、bid/ask midpoint、日線 adjusted close
或其他交易場所最後一筆成交當成上市市場官方 close。

PROPOSED 若選 SPY，上市市場預期是 NYSE Arca；若選 Nasdaq 上市工具，須核對
該市場官方 close／closing cross 與無成交時的規則。此任務未重新驗證任一工具的
上市地或最新交易所規則，啟動前必須補證，不能照本段預期直接執行。
兩個網站顯示相同數字，若共用上游，不代表兩個獨立來源。

## IEX、SIP、日線 close 的區別

官方 SDK 明列 IEX（Investors Exchange）與 SIP feed，另有 DELAYED_SIP
「15 minute delay」定義。這只是 feed 定義，不保證任一免費帳號有權限。

- **IEX exchange feed**：單一場所成交／報價。SPY 等其他市場上市工具的
  IEX 最後成交，不能作其上市市場官方 close；有些日子數字接近也不改變語義。
  IEX exchange feed 與舊 IEX Cloud 品牌／歷史產品不能混作同一現行免費服務。
- **SIP**：CTA／UTP 等整合處理器彙集多場所資料，覆蓋與 IEX 不同。整合資料
  中的最後成交或供應商 bar close，不自動等於官方上市市場 closing auction 價。
- **official close**：須知道工具的上市市場、具體資料欄位／交易條件碼及更正規則。
  存檔官方供應商文件區分 Market Center Official Close、Closing Trade／Print、
  Corrected Consolidated Close；條件碼也依 CTS／UTP 協議與版本而異。
  不能僅憑某筆成交的 `M` 就認定是「該工具上市市場」的官方 close。
- **raw daily bar close**：SDK 的 RAW 只表示未按公司行動調整；raw ≠ official。
  需要供應商欄位定義與上市市場身份，而非只選 `adjustment=raw`。

本任務不接入 Alpaca；其官方開源文件只作 IEX／SIP 語義研究來源。

## 候選來源與延遲／授權矩陣

| 來源候選（全部未啟用） | 官方性／核驗用途 | 延遲與修訂 | 零成本／授權判斷 |
| --- | --- | --- | --- |
| 上市交易所官方歷史／auction／official-close 發布 | 主來源最佳候選；須能明確指出工具、交易日、官方欄位與版本 | 盤中 close 時點不等於可取回 final 的時間；更正發布可能更晚。現行 SLA 未查得 | 網站免費瀏覽不等於免費保存、機器處理、非展示或再散布權；現行條款與可得性未核驗。**不能宣稱已具零成本資料路徑** |
| 經授權的 listing-market 官方 EOD/auction 檔 | 可較直接保留來源／版本／更正資訊 | EOD 或次日可接受，取決於產品 | 可能需授權／訂閱；未取得報價，不購買；本次預算下 NO-GO |
| SIP／授權供應商延遲或歷史資料 | 可作主來源或核對，但僅當欄位真的是所需官方 close | SDK 有 delayed_sip 15 分鐘定義；最終狀態、更正／feed 選擇仍另查 | 不從「delay」推導免費。需要帳號、用途、區域、歷史保留與再散布權證據；本次不開戶、不用 API |
| IEX-only 免費資料 | 可作市場微結構研究背景，**不能替代官方 close** | 可能即時；即時性不補足場所覆蓋 | 不適合作本 Pilot primary outcome；不能為了免費改變 outcome 定義 |
| Yahoo／Google／其他公開價頁 | 僅作可能的二級 corroboration，須有欄位定義、上游與可保存證據 | 延遲依工具／來源；close、adjusted close、盤後價可能並列 | 公開可見不等於允許自動抓取、內部保存或對外展示；現行條款未查證。M1 的歷史 Yahoo 說明不是新 Pilot 授權 |
| ETF 發行人網站 | 可核對工具／上市地；價格欄位仍需說明 | NAV、market price、premium/discount 可能不同時點 | 不用 NAV 替代官方 close；現行條款未查證 |

**已閱讀的資料商主文件已 archived**，其中舊 Free／Unlimited 表及舊 $99/mo
不能作 2026-11-04 現價或可購買／可用權限承諾。歷史文件的 15 分鐘敘述也
不能作目前免費 plan 的 SLA。現行 SDK 證實 feed 與 adjustment 類型，不證實價格。

## PROPOSED 最低成本資料路徑（未驗證，不能啟動）

只在 Founder 另行核准後，採人工操作、延後核驗、無 API：從可合法保存的
官方發布頁或檔案取精確 close，獨立 Reviewer 核對來源語義和版本，再用不同上游
的來源 corroborate。保存 raw response／檔案、擷取時間、發布時間、條款版本／URL、
close 欄位名、上市市場、幣別、session、調整標記、correction ID 和 hash。
若對方不允許保存原始資料，先釐清能否存必要 excerpt/hash 與受限附件；核驗者
無法重建事實時即 NO-GO，不為公開 PR 貼上整包受限制行情。

PROPOSED 不要求即時資料；目標 close 後次一美股交易日再人工核驗，可避開
為即時 feed 付費的需求。但等待不能保證免費、授權或 final；市場更正仍保留。
超過預先核准的缺資料時限則記 PENDING／DISPUTED，不猜價、不改 target session。

PROPOSED 兩來源價格必須在相同幣別、精度與 price basis 下精確一致；不使用
隱藏 epsilon 或選最有利價格。若因顯示精度無法精確核對，先取得原欄位精度規則，
不能在看過結果後放寬 tolerance。相同上游算一來源，原始 source lineage 不明則 pending。

## 成本（非採購承諾）

| 項目 | PROPOSED 新增現金上限／估計 | 未包含成本與風險 |
| --- | --- | --- |
| 資料、時間戳服務、模型 API、券商 | 每項新增支出上限 USD 0；無自動試用升級 | 沒有證據證明現成免費官方資料＋獨立 proof 完整可行 |
| GitHub evidence／人工匯出 | 只用既有免費額度；超額或需付費即停 | 既有帳號／組織訂閱不是零成本新承諾 |
| OTS 驗證 | 僅當已有獨立 Bitcoin Core 核驗者且不需新部署 | 節點磁碟、頻寬、電力及人力；沒有節點不算零成本成立 |
| Research Room | 未授權任何新模型運行／部署；本任務模型 API 次數 0 | 未來手動使用既有 Room 也可能消耗現有訂閱／額度，須 Founder 確認涵蓋範圍 |
| 人工準備／核對 | PROPOSED 每樣本 30–60 分鐘工程核對，不含市場研究；5 樣本約 2.5–5 小時 | 只是工作量估算，未測量、未承諾；獨立 reviewer 檔期另計 |

**零新增付費服務是限制，不是已證明可滿足的結論。** 在主來源官方語義、兩份
合法可保存且可重查的資料、使用權與外部核驗成本全部得到證據之前，建議 NO-GO。
