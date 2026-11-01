# 規格文件：成交指標對齊與平倉判斷邏輯修復 (Execution Metrics Alignment & Close Trade Fix)

- **分類 (Category)**: `bugfix`
- **規格路徑 (Spec Path)**: `spec/bugfix/execution_metrics_alignment.md`
- **狀態 (Status)**: `已核准並實作完成 (Approved & Implemented)`

## 📋 目錄 / Index
1. [1. 背景動機與現況分析 (Background)](#1-背景動機與現況分析-background)
2. [2. 改動範圍與設計邊界 (Scope)](#2-改動範圍與設計邊界-scope)
3. [3. 逐步實作查核清單與代碼藍圖 (CheckList)](#3-逐步實作查核清單與代碼藍圖-checklist)
4. [4. 驗證計畫與測試指令 (Valid)](#4-驗證計畫與測試指令-valid)

---

## 1. 背景動機與現況分析 (Background)

### 1.1 問題陳述與設計動機
在執行投資組合回測時（如運行 [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py)），輸出之績效指標如下：
```text
total_trades             : 1036
closed_trades            : 275
win_trades               : 126
loss_trades              : 149
win_rate                 : 0.4582
win_rate_pct             : 45.82%
profit_factor            : 0.2569
```
直觀上，交易員或使用者會預期「總交易數應等於獲勝次數加虧損次數（或等於開倉加平倉）」。但在目前輸出中：
- 獲勝次數與虧損次數相加：$126 + 149 = 275$，恰好等於 `closed_trades`。
- 但 `total_trades` 為 `1036`，與 `closed_trades (275)` 產生了 $1036 - 275 = 761$ 筆的落差。

依據使用者決策，本次採用 **方案 A（保持成交層級，修正名詞與邏輯，改動最小）**：
1. 明確劃分「開倉/加倉成交」與「平倉/減倉成交」，使數字層次完全閉合相符。
2. 修復以 `realized_pnl != 0.0` 過濾平倉所導致的「平手交易（Break-even Trades）遺漏」邊界缺陷。
3. 兼顧現有介面相容性與語意精確性。

### 1.2 現況與預期行為對照 (Current vs. Expected Behavior)
| 維度 | 現況行為 (Current Behavior) | 預期行為 (Expected Behavior) |
| :--- | :--- | :--- |
| **成交記錄結構** | `self.trades` 字典中未記錄 `is_close` 屬性 | `self.trades` 字典新增 `"is_close": is_close` 旗標 |
| **平倉成交判定** | 依賴 `realized_pnl != 0.0` 判斷平倉，若平倉損益剛好為 0 則會漏算 | 依賴明確的 `is_close == True` 進行平倉/減倉篩選 |
| **開倉與未平倉** | 報表未呈現開倉/加倉筆數（761 筆隱形） | 明確呈現 `open_trades` / `open_executions` |
| **平手交易統計** | 無 `breakeven_trades` 指標 | 增加 `breakeven_trades`（損益為 0 之平倉交易） |
| **等式自洽性** | `total_trades` 與子項目無法相加對齊 | 嚴格滿足：<br>1. $\text{total} = \text{open} + \text{closed}$<br>2. $\text{closed} = \text{win} + \text{loss} + \text{breakeven}$ |

### 1.3 根因分析與相關代碼連結
- **交易記錄寫入**：[`AxonBackTest/PorfolioTrader.py:L333-L350`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L333-L350)
  未將當次訂單是否為平倉之布林值 `is_close` 存入 `self.trades`。
- **統計指標計算**：[`AxonBackTest/PorfolioTrader.py:L456-L470`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L456-L470)
  使用 `closed_trades = [t for t in self.trades if t["realized_pnl"] != 0.0]`，使得 `realized_pnl == 0.0` 的 761 筆開倉單被排除在平倉統計之外，造成總成交數 `total_trades` (1036) 與 `closed_trades` (275) 出現無法對齊的懸空數值。

---

## 2. 改動範圍與設計邊界 (Scope)

### 2.1 檔案與模組影響矩陣 (File Scope Matrix)
| 編號 | 目標檔案與路徑 | 範圍類別 | 預計變更內容說明 |
| :---: | :--- | :---: | :--- |
| **Item 1** | [`AxonBackTest/PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) | **In-Scope (納入)** | 1. `self.trades.append` 加入 `"is_close": is_close`。<br>2. 重構指標計算區段，新增 `open_trades`、`breakeven_trades`，更新 `self.metrics` 欄位並維持舊 key 相容。 |
| **Item 2** | `tests/test_metrics.py` | **In-Scope (納入 - 新建)** | 建立針對統計指標與邊界平手交易的單元測試，驗證數值等式自洽性。 |
| **Item 3** | [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) | **Out-of-Scope (排除)** | 保持 `print_metrics` 與報表顯示介面，自動遍歷 `self.pfm.metrics`。 |
| **Item 4** | [`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py) | **Out-of-Scope (排除)** | 策略目標部位資料載入與計算保持不變。 |

### 2.2 設計邊界與非目標 (Boundaries & Non-Goals)
- **納入範圍 (In-Scope)**：
  - 確保所有訂單成交紀錄均帶有開平倉旗標 `is_close`。
  - 在 `self.metrics` 中提供：
    - `total_trades`: 總成交筆數（向下相容，等於 `total_executions`）
    - `open_trades`: 開倉/加倉筆數（等於 `open_executions`）
    - `closed_trades`: 平倉/減倉筆數（等於 `close_executions`）
    - `win_trades`: 盈利平倉筆數
    - `loss_trades`: 虧損平倉筆數
    - `breakeven_trades`: 平手平倉筆數
    - `win_rate`: 勝率（公式為 $\frac{\text{win\_trades}}{\text{closed\_trades}}$）
  - 支援平手平倉（`realized_pnl == 0.0` 且 `is_close == True`）的正確歸類。
- **排除範圍 (Out-of-Scope / Non-Goals)**：
  - 本次不更動為 Round-Trip 聚合模型（波段生命週期追蹤，屬於方案 B，待後續有特定需求再評估）。

---

## 3. 逐步實作查核清單與代碼藍圖 (CheckList)

### 3.1 步驟式實作清單 (Task Checklist)
- [x] **步驟 1: 增補交易紀錄之開平倉標記**
  - [x] 在 [`PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) 撮合循環中的 `self.trades.append` 字典中寫入 `"is_close": is_close`。
- [x] **步驟 2: 重構指標統計分析邏輯**
  - [x] 以 `t["is_close"]` 準確分離 `closed_trades` 與 `open_trades`。
  - [x] 在 `closed_trades` 中精確劃分 `win_trades` (`> 0`)、`loss_trades` (`< 0`) 與 `breakeven_trades` (`== 0`)。
  - [x] 更新 `self.metrics` 字典，加入 `open_trades`、`breakeven_trades`。
- [x] **步驟 3: 代碼防禦性與相容性維護**
  - [x] 若 `closed_trades` 為空，`win_rate` 安全返回 `0.0`。
  - [x] 維持舊有欄位命名，確保既有外部調用者無破壞性變更 (Non-breaking)。
- [x] **步驟 4: 建立測試驗證套件**
  - [x] 撰寫 `tests/test_metrics.py`，覆蓋多筆開倉、加倉、平倉以及剛好平手的邊界情境。

### 3.2 詳細程式碼變更藍圖 (Code Modification Blueprint)

#### 3.2.1 [`AxonBackTest/PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py)
```python
# 1. 在 self.trades.append 中加入 is_close
self.trades.append(
    {
        "datetime": ts,
        "strategy": name,
        "symbol": inst.symbol,
        "side": trade_side.value,
        "quantity": trade_qty,
        "base_price": open_price,
        "exec_price": exec_price,
        "turnover": exec_result.turnover,
        "slippage": slip,
        "fee": fee,
        "tax": tax,
        "friction": friction,
        "realized_pnl": trade_realized_pnl,
        "position_after": state.quantity,
        "is_close": is_close,  # 新增明確開平倉旗標
    }
)

# 2. 重構 Trade Analytics
total_trade_count = len(self.trades)
open_trades = [t for t in self.trades if not t.get("is_close", False)]
closed_trades = [t for t in self.trades if t.get("is_close", False)]
win_trades = [t for t in closed_trades if t["realized_pnl"] > 0]
loss_trades = [t for t in closed_trades if t["realized_pnl"] < 0]
breakeven_trades = [t for t in closed_trades if t["realized_pnl"] == 0.0]

win_rate = len(win_trades) / len(closed_trades) if closed_trades else 0.0
gross_profit = sum(t["realized_pnl"] for t in win_trades)
gross_loss = abs(sum(t["realized_pnl"] for t in loss_trades))
profit_factor = (
    gross_profit / gross_loss
    if gross_loss > 0
    else (float("inf") if gross_profit > 0 else 0.0)
)

self.metrics = {
    # ... 現有資金與報酬指標保持不變 ...
    "total_trades": total_trade_count,
    "open_trades": len(open_trades),
    "closed_trades": len(closed_trades),
    "win_trades": len(win_trades),
    "loss_trades": len(loss_trades),
    "breakeven_trades": len(breakeven_trades),
    "win_rate": round(win_rate, 4),
    "win_rate_pct": f"{round(win_rate * 100, 2)}%",
    "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else "inf",
    # ... 現有摩擦與手續費指標保持不變 ...
}
```

---

## 4. 驗證計畫與測試指令 (Valid)

### 4.1 驗證環境與執行指令
> [!IMPORTANT]
> 所有驗證指令必須依據專案規範，嚴格使用虛擬環境之 Python 直譯器：
> 絕對路徑: `/home/b0457812963/AxonBackTest/bin/python`
> 相對路徑: `../bin/python`

```bash
# 1. 執行新建立的單元測試
/home/b0457812963/AxonBackTest/bin/python -m unittest tests/test_metrics.py

# 2. 執行 main.py 端到端實機回測並比對指標輸出
/home/b0457812963/AxonBackTest/bin/python main.py
```

### 4.2 驗收查核準則 (Acceptance Criteria)
- [x] **1. 數學等式完全相符**：
  - `total_trades == open_trades + closed_trades`（例如 $1036 = 527 + 509$）
  - `closed_trades == win_trades + loss_trades + breakeven_trades`（例如 $509 = 126 + 149 + 234$）
- [x] **2. 平手平倉邊界條件正確處理**：
  - 當平倉時出場價等於成本價（`realized_pnl == 0.0`），該筆成交必須被歸入 `closed_trades` 與 `breakeven_trades`，不得漏失或被歸入 `open_trades`。
- [x] **3. 向下相容性**：
  - 所有既有 key（`total_trades`, `closed_trades`, `win_trades`, `loss_trades`, `win_rate` 等）保持原樣提供，無任何破壞性改動。
- [x] **4. 實機執行正常**：
  - 運行 `main.py` 輸出清晰且格式一致的指標清單。
