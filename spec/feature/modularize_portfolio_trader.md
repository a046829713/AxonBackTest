# 規格文件：PortfolioTrader.py 模組化與函式拆分 (Modularize PortfolioTrader)

- **分類 (Category)**: `feature`
- **規格路徑 (Spec Path)**: `spec/feature/modularize_portfolio_trader.md`
- **狀態 (Status)**: `已完成 Completed`

## 📋 目錄 / Index
1. [1. 背景動機與現況分析 (Background)](#1-背景動機與現況分析-background)
2. [2. 改動範圍與設計邊界 (Scope)](#2-改動範圍與設計邊界-scope)
3. [3. 逐步實作查核清單與代碼藍圖 (CheckList)](#3-逐步實作查核清單與代碼藍圖-checklist)
4. [4. 驗證計畫與測試指令 (Valid)](#4-驗證計畫與測試指令-valid)

---

## 1. 背景動機與現況分析 (Background)

### 1.1 問題陳述與設計動機
在現行 [`PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) 中，核心回測排程函式 [`PortfolioManagement.generate_report()`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L157-L502) 長達 345 行（佔全模組近 70% 代碼行數）。
該函式同時承擔了以下多項高度異質的邏輯：
1. 資料對齊與回測變數初始化。
2. 開盤階段（Open Phase）：目標持倉權重換算、最小下單量取整、手續費/滑價/交易稅摩擦成本扣除、多空平倉/反手/加倉之平均持倉成本與已實現損益結算、交易明細記錄。
3. 收盤階段（Close Phase）：各策略部位盯市評價（MTM）、未實現損益與保證金佔用計算。
4. 回測報表資料表（DataFrame）組裝與個別策略部位欄位對齊。
5. 績效與統計指標運算（Total Return, CAGR, MDD, Sharpe Ratio, 勝率, 獲利因子等）。

此巨型函式導致代碼難以維護、排查問題成本高昂，且各子邏輯無法被單獨隔離測試。

### 1.2 現況與預期行為對照 (Current vs. Expected Behavior)
| 維度 | 現況行為 (Current Behavior) | 預期行為 (Expected Behavior) |
| :--- | :--- | :--- |
| **函式結構** | 單一函式超過 340 行，所有業務邏輯高度內聯耦合。 | 拆分為 4 個高內聚、低耦合的專責私有方法，主函式縮減至 ~45 行。 |
| **狀態流轉** | 多個分散的浮點數累積變數（`cum_fee`, `cum_tax`, `cash` 等）在迴圈內直接變更。 | 引入輕量級模擬狀態資料類別 `PortfolioSimulationContext` 統一管理摩擦成本與現金流。 |
| **除錯與維護** | 調倉問題、盯市計算問題與報表計算問題難以單獨定位。 | 職責分離：開盤撮合、收盤盯市、報表組裝、績效統計各司其職，清晰可追蹤。 |
| **數值與行為相容性** | 產出標準回測報表與績效指標。 | **100% 嚴格數值相容**，不改變任何回測計算結果、指標鍵值與輸出結構。 |

### 1.3 根因分析與相關代碼連結
- 目標函式：[`PorfolioTrader.py:L157-L502`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L157-L502)
- 現有程式未進行次級抽象，使得回測流程控制（Flow Control）與具體金融計算（Financial Computation）緊密交織。

---

## 2. 改動範圍與設計邊界 (Scope)

### 2.1 檔案與模組影響矩陣 (File Scope Matrix)
| 編號 | 目標檔案與路徑 | 範圍類別 | 預計變更內容說明 |
| :---: | :--- | :---: | :--- |
| **Item 1** | [`PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) | **In-Scope (納入)** | 新增 `PortfolioSimulationContext` 資料結構；拆分出 4 個私有輔助方法；簡化 `generate_report()` 主流程。 |
| **Item 2** | [`backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) | **Out-of-Scope (排除)** | 呼叫端介面完全不變，維持相容性。 |
| **Item 3** | [`config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py) | **Out-of-Scope (排除)** | 委託摩擦計算與設定規格維持原樣。 |
| **Item 4** | [`strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py) | **Out-of-Scope (排除)** | 策略資料結構與介面維持原樣。 |

### 2.2 設計邊界與非目標 (Boundaries & Non-Goals)
- **納入範圍之邊界 (In-Scope)**：
  - 定義 `PortfolioSimulationContext` 類別，用以乾淨傳遞 simulation 執行期現金與累積摩擦成本狀態。
  - 實作 `_execute_open_rebalance()`：封裝開盤階段的訂單換算、摩擦扣抵、持倉結算與成交記錄。
  - 實作 `_evaluate_close_mtm()`：封裝收盤階段的 Mark-to-Market 市價評價與保證金計算。
  - 實作 `_build_report_dataframe()`：封裝時間序列陣列轉換為 `report_df` 之邏輯。
  - 實作 `_calculate_performance_metrics()`：封裝統計摘要指標（CAGR, MDD, Sharpe, Win Rate 等）之運算。
  - 重構 `generate_report()`，使其僅作為協調這 4 個方向的調度器。
- **排除範圍 (Out-of-Scope / Non-Goals)**：
  - 本次改動不調整數學計算法則（如手續費公式、Sharpe Ratio 計算邏輯等）。
  - 不更動公開方法與屬性簽名（如 `self.report`, `self.report_df`, `self.metrics`, `self.trades`）。

---

## 3. 逐步實作查核清單與代碼藍圖 (CheckList)

### 3.1 步驟式實作清單 (Task Checklist)
- [x] **步驟 1: 新增模擬執行狀態結構 `PortfolioSimulationContext`**
  - [x] 於 [`PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) 定義 `@dataclass class PortfolioSimulationContext`。
  - [x] 包含欄位：`cash: float`、`cum_realized_pnl: float = 0.0`、`cum_fee: float = 0.0`、`cum_slippage: float = 0.0`、`cum_tax: float = 0.0`、`cum_friction: float = 0.0`。
- [x] **步驟 2: 抽取方向 1 —— 開盤調倉撮合方法 `_execute_open_rebalance()`**
  - [x] 接收當前 K 線索引 `k`、時間戳 `ts`、分配資金 `allocated_capital`、市場資料 `aligned_arrays` 與 `ctx` 狀態。
  - [x] 迭代各策略，計算目標數量（`target_qty`）與淨變更（`delta_qty`）。
  - [x] 呼叫 `evaluate_order()`，結算手續費/滑價/稅費並扣除現金。
  - [x] 處理部位翻轉、平倉（結算已實現損益）或同向加倉（更新加權平均成本）。
  - [x] 寫入成交明細至 `self.trades`。
- [x] **步驟 3: 抽取方向 2 —— 收盤盯市評價方法 `_evaluate_close_mtm()`**
  - [x] 接收當前 K 線索引 `k` 與市場資料 `aligned_arrays`。
  - [x] 迭代各策略，依據 `close_price` 更新 `state.unrealized_pnl`。
  - [x] 計算總未實現損益 `total_unrealized_pnl` 與總佔用保證金 `total_margin_used` 並返回 tuple。
- [x] **步驟 4: 抽取方向 3 —— 報表資料表組裝方法 `_build_report_dataframe()`**
  - [x] 接收各維度記錄陣列（`timestamps`, `datetimelist`, `equity_records`, `cash_records`, 等）與 `aligned_arrays`。
  - [x] 組裝各指標欄位與各策略之部位欄位（`pos_<strategyName>`）。
  - [x] 建立並返回 `pd.DataFrame`。
- [x] **步驟 5: 抽取方向 4 —— 績效指標計算方法 `_calculate_performance_metrics()`**
  - [x] 接收 `timestamps`、`equity_records`、`n_bars`、及累積摩擦成本。
  - [x] 計算總收益率、CAGR、MDD、MDD金額、Sharpe Ratio。
  - [x] 分析成交明細（勝率、盈虧比、盈虧次數分佈）。
  - [x] 組裝並返回標準 `metrics` 字典。
- [x] **步驟 6: 精簡 `generate_report()` 主流程**
  - [x] 將 `generate_report()` 改為呼叫前述 4 個方向的方法。
  - [x] 驗證流程簡潔、易讀、無冗餘代碼。
- [x] **步驟 7: 代碼防禦性與相容性維護**
  - [x] 確保型別標註（Type Hints）與 Docstrings 完整清晰。
  - [x] 保持變數與屬性命名嚴格遵循專案規範。

### 3.2 詳細程式碼變更藍圖 (Code Modification Blueprint)

#### 3.2.1 模擬狀態定義與方法簽名架構
```python
@dataclass
class PortfolioSimulationContext:
    """Encapsulates running cash and accumulated friction state during simulation."""
    cash: float
    cum_realized_pnl: float = 0.0
    cum_fee: float = 0.0
    cum_slippage: float = 0.0
    cum_tax: float = 0.0
    cum_friction: float = 0.0


class PortfolioManagement:
    ...
    def _execute_open_rebalance(
        self,
        k: int,
        ts: pd.Timestamp,
        allocated_capital: float,
        aligned_arrays: Dict[str, Dict[str, np.ndarray]],
        ctx: PortfolioSimulationContext,
    ) -> None:
        """Executes target position rebalancing and trade friction deduction at bar Open."""
        ...

    def _evaluate_close_mtm(
        self,
        k: int,
        aligned_arrays: Dict[str, Dict[str, np.ndarray]],
    ) -> tuple[float, float]:
        """Calculates unrealized PnL and margin used at bar Close."""
        ...

    def _build_report_dataframe(
        self,
        datetimelist: List[str],
        timestamps: List[pd.Timestamp],
        equity_records: np.ndarray,
        cash_records: np.ndarray,
        unrealized_records: np.ndarray,
        realized_records: np.ndarray,
        margin_records: np.ndarray,
        friction_records: np.ndarray,
        fee_records: np.ndarray,
        slippage_records: np.ndarray,
        tax_records: np.ndarray,
        aligned_arrays: Dict[str, Dict[str, np.ndarray]],
    ) -> pd.DataFrame:
        """Assembles simulated time-series arrays into a unified pandas DataFrame."""
        ...

    def _calculate_performance_metrics(
        self,
        timestamps: List[pd.Timestamp],
        equity_records: np.ndarray,
        n_bars: int,
        ctx: PortfolioSimulationContext,
    ) -> Dict[str, Any]:
        """Computes institutional risk, return, drawdown, and trade analytics metrics."""
        ...

    def generate_report(self) -> List[Dict[str, Any]]:
        """Coordinates the 4 phases to run simulation and produce the report."""
        ...
```

---

## 4. 驗證計畫與測試指令 (Valid)

### 4.1 驗證環境與執行指令
依據專案規範，驗證必須嚴格使用虛擬環境之 Python 直譯器：
- 絕對路徑: `/home/b0457812963/AxonBackTest/bin/python`

```bash
# 驗證執行指令:
cd /home/b0457812963/AxonBackTest/AxonBackTest && /home/b0457812963/AxonBackTest/bin/python main.py
```

### 4.2 驗收查核準則 (Acceptance Criteria)
- [x] **1. 數值完全一致性 (Zero Numerical Deviation)**：
  - 重構前後執行 `main.py`，輸出的各項指標數值完全一致：
    - `final_equity`: `-542.2726`
    - `total_return`: `-1.054227`
    - `cagr`: `-1.054227`
    - `max_drawdown`: `-1.097456`
    - `sharpe_ratio`: `0.212`
    - `total_trades`: `1036`
    - `win_trades`: `126`
    - `loss_trades`: `149`
    - `win_rate`: `0.2475`
    - `profit_factor`: `0.2569`
    - `total_friction`: `9610.8741`
- [x] **2. 介面向後相容 (Backward Compatibility)**：
  - `self.report`、`self.report_df`、`self.metrics`、`self.trades` 欄位與格式無任何異動。
  - [`BackTester`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) 呼叫 `generate_report()`、`print_metrics()` 與 `plot_image()` 均無錯誤。
- [x] **3. 可讀性與模組化 (Maintainability)**：
  - 單一函式行數顯著縮減（`generate_report` 控制在 50 行以內），各輔助方法職責明確。


