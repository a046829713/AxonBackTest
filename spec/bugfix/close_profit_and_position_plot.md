# 規格文件：已平倉損益欄位修正與多視窗部位視覺化重構 (CloseProfit Mapping Fix & Equity/Position Visualization)

- **分類 (Category)**: `bugfix`
- **規格路徑 (Spec Path)**: `spec/bugfix/close_profit_and_position_plot.md`
- **狀態 (Status)**: `已核准並實作完成 (Approved & Implemented)`

## 📋 目錄 / Index
1. [1. 背景動機與現況分析 (Background)](#1-背景動機與現況分析-background)
2. [2. 改動範圍與設計邊界 (Scope)](#2-改動範圍與設計邊界-scope)
3. [3. 逐步實作查核清單與代碼藍圖 (CheckList)](#3-逐步實作查核清單與代碼藍圖-checklist)
4. [4. 驗證計畫與測試指令 (Valid)](#4-驗證計畫與測試指令-valid)

---

## 1. 背景動機與現況分析 (Background)

### 1.1 問題陳述與設計動機
在執行 [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py) 回測 [FARTCOINUSDT_orders.csv](file:///home/b0457812963/AxonBackTest/AxonBackTest/FARTCOINUSDT_orders.csv) 時，自 `2026-01-18 08:00:00`（第 832 根 K 線）起至回測結束 `2026-09-24 05:00:00`（第 12,778 根 K 線），目標部位比例 (`Position`) 恆定維持於 `0.9960984`（持倉 `32,291.943` 顆），期間無任何調倉或平倉交易，實際累計已實現損益 (`RealizedPnL = 1615.8225`) 與已結算現金餘額 (`Cash = 11574.4155`) 均為完全水平直線。

然而，呼叫 [`BackTester.plot_image`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py#L26-L44) 所繪製之 `Portfolio Close Profit Over Time` 曲線卻在後期劇烈上下抖動（於 `3325.19` 至 `11349.74` 之間波動）。其根本原因為報表組裝時將逐根盯市總淨值 (`equity_records`，含未平倉浮動損益 `UnrealizedPnL`) 誤綁定至 `"CloseProfit"` 欄位，造成「已平倉損益」名實不符。

依據與使用者討論確認之決策：
1. **採用方案 A 還原 `CloseProfit` 語意**：將 `"CloseProfit"` 改為綁定 `cash_records`（含初始本金之已結算現金餘額：$\text{InitialCapital} + \text{RealizedPnL} - \text{TotalFriction}$），使持倉未平倉期間呈現水平階梯線。
2. **第一張圖片（資金與損益對照視窗）**：於同一張 Figure 採用上下雙子圖 (`2x1 Subplots`, 共用時間 X 軸)，上方繪製 `Equity`（逐根盯市總淨值），下方繪製 `CloseProfit`（已平倉結算資金）。
3. **第二張圖片（獨立部位視窗）**：在呼叫 [`BackTester.plot_image`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py#L26-L44) 時額外建立第二張獨立 Figure 視窗，繪製各策略之目標部位比例 (`Position Ratio`, 即 `pos_<strategy>` 欄位)。
4. **代碼整潔清理**：一併移除 [`PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) 內殘留針對 `AAVEUSDT-RL-30M` 的硬編碼除錯 `print`。

### 1.2 現況與預期行為對照 (Current vs. Expected Behavior)
| 維度 | 現況行為 (Current Behavior) | 預期行為 (Expected Behavior) |
| :--- | :--- | :--- |
| **`CloseProfit` 欄位定義** | 誤綁定至 `equity_records`（含未實現損益 `UnrealizedPnL`），抱單期間隨收盤價不斷抖動 | 綁定至 `cash_records`（已實現結算資金 `Cash`），未發生交易與平倉期間嚴格保持水平直線 |
| **資金圖表 (`Figure 1`)** | 單一子圖僅繪製被誤植的 `CloseProfit` | 上下雙子圖 (`sharex=True`)：上圖為 `Equity`（總淨值），下圖為 `CloseProfit`（已平倉資金階梯線） |
| **部位圖表 (`Figure 2`)** | 無部位視覺化圖表，難以直觀比對持倉區間與損益變化 | 額外產生獨立 Figure 視窗，以階梯線 (`steps-post`) 繪製各策略目標部位比例 (`pos_*`) |
| **呼叫介面與相容性** | `bt.plot_image()` 顯示單一視窗 | 維持呼叫一次 `bt.plot_image()` 同時彈出兩張獨立 Figure 視窗，[`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py) 無須更動 |
| **除錯殘留代碼** | 存在 `if name == "AAVEUSDT-RL-30M": print(...)` 硬編碼輸出 | 完全清除殘留除錯輸出，保持核心撮合迴圈乾淨高效 |

### 1.3 根因分析與相關代碼連結
- **`CloseProfit` 欄位錯置**：[`AxonBackTest/PorfolioTrader.py:L366-L374`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L366-L374)
  在 [`PortfolioManagement._build_report_dataframe`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L345-L386) 中，第 369 行寫為 `"CloseProfit": equity_records`，而 `equity_records` 於 [`PorfolioTrader.py:L545`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L545) 計算為 `ctx.cash + total_unrealized_pnl`，導致未平倉浮動損益混入 `CloseProfit`。
- **殘留除錯列印**：[`AxonBackTest/PorfolioTrader.py:L169-L170`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L169-L170) 及 [`AxonBackTest/PorfolioTrader.py:L215-L217`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L215-L217)
  在 [`PortfolioManagement._execute_open_rebalance`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L139-L298) 內部殘留特定標的名稱之 `print` 語句。
- **單一曲線繪圖介面**：[`AxonBackTest/backtester.py:L26-L44`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py#L26-L44)
  [`BackTester.plot_image`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py#L26-L44) 僅繪製單張 `CloseProfit` 折線圖，未分離 `Equity` 與 `CloseProfit`，亦缺乏部位比例圖表。

---

## 2. 改動範圍與設計邊界 (Scope)

### 2.1 檔案與模組影響矩陣 (File Scope Matrix)
| 編號 | 目標檔案與路徑 | 範圍類別 | 預計變更內容說明 |
| :---: | :--- | :---: | :--- |
| **Item 1** | [`AxonBackTest/PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) | **In-Scope (納入)** | 1. 將 `_build_report_dataframe` 中的 `"CloseProfit"` 改為綁定 `cash_records`。<br>2. 移除 `_execute_open_rebalance` 中兩處 `AAVEUSDT-RL-30M` 除錯 `print`。 |
| **Item 2** | [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) | **In-Scope (納入)** | 重構 `BackTester.plot_image()`：<br>1. 建立 Figure 1（上下雙子圖：上 `Equity`、下 `CloseProfit`）。<br>2. 建立 Figure 2（繪製所有 `pos_*` 策略目標部位比例曲線）。<br>3. 統一於結尾呼叫一次 `plt.show()` 同時呈現兩個視窗。 |
| **Item 3** | [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py) | **Out-of-Scope (排除)** | 維持現有呼叫流程 (`bt.plot_image()`) 不變，確保無破壞性相容。 |
| **Item 4** | [`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py) | **Out-of-Scope (排除)** | 策略資料載入與 `Position` 欄位解析邏輯維持不變。 |
| **Item 5** | [`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py) | **Out-of-Scope (排除)** | 合約規格與訂單摩擦計算模型維持不變。 |

### 2.2 設計邊界與非目標 (Boundaries & Non-Goals)
- **納入範圍之邊界 (In-Scope)**：
  - `report_df["CloseProfit"]` 嚴格等於 `report_df["Cash"]`（即初始資金加減累計已實現損益與交易摩擦）。
  - 績效統計指標 [`PortfolioManagement._calculate_performance_metrics`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L388-L473) 維持以 `equity_records`（Mark-to-Market 總淨值）計算總報酬率、CAGR、Max Drawdown 與 Sharpe Ratio，不受 `CloseProfit` 欄位修正影響。
  - Figure 2 自動偵測 `report_df` 中所有以 `"pos_"` 開頭之欄位，同時支援單一策略與多策略組合繪圖。
  - 遵循專案代碼規範，新增與修改之 `.py` 註解與 Docstring 一律使用英文撰寫。
- **排除範圍 (Out-of-Scope / Non-Goals)**：
  - 不變更訂單撮合邏輯、滑價/手續費計算或部位再平衡觸發條件。
  - 不新增額外外部繪圖套件依賴（僅使用專案既有的 `matplotlib` 與 `pandas`）。

---

## 3. 逐步實作查核清單與代碼藍圖 (CheckList)

### 3.1 步驟式實作清單 (Task Checklist)
- [x] **步驟 1: 修正 `PorfolioTrader.py` 報表欄位與清理殘留除錯輸出**
  - [x] 移除 [`PorfolioTrader.py:L169-L170`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L169-L170) 與 [`PorfolioTrader.py:L215-L217`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L215-L217) 的 `AAVEUSDT-RL-30M` 除錯 `print`。
  - [x] 修改 [`PortfolioManagement._build_report_dataframe`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py#L345-L386) 中 `"CloseProfit"` 映射為 `cash_records`。
- [x] **步驟 2: 重構 `BackTester.plot_image` 雙視窗視覺化邏輯**
  - [x] 若 `self.report is None`，自動呼叫 `self.generate_report()`，並檢查空報表防禦處理。
  - [x] 建立 **Figure 1** (`plt.subplots(2, 1, figsize=(15, 10), sharex=True)`)：
    - [x] 上子圖 (`ax_equity`)：繪製 `Equity` 時間序列，標註標題 `Portfolio Equity Over Time (Mark-to-Market)` 與 Y 軸 `Equity (USD)`。
    - [x] 下子圖 (`ax_close_profit`)：以 `drawstyle="steps-post"` 繪製 `CloseProfit` 時間序列，標註標題 `Portfolio Close Profit Over Time (Realized)` 與 Y 軸 `Close Profit (USD)`。
  - [x] 建立 **Figure 2** (`plt.subplots(figsize=(15, 5))`)：
    - [x] 篩選 `pos_cols = [col for col in report_df.columns if col.startswith("pos_")]`。
    - [x] 以 `drawstyle="steps-post"` 繪製各策略目標部位比例曲線，並加入 `y=0.0` 基準虛線輔助判讀多空曝險。
  - [x] 於函式末尾統一呼叫一次 `plt.show()`，確保兩個視窗同時顯示。
- [x] **步驟 3: 代碼防禦性與整潔維護**
  - [x] 確保 `.py` 檔案內所有註解、Docstring 與型別標註 (`Type Hints`) 均為標準英文。
  - [x] 對缺失 `Equity` 或 `pos_*` 欄位的舊式輸入具備安全防護，避免拋出未預期 `KeyError`。

### 3.2 詳細程式碼變更藍圖 (Code Modification Blueprint)

#### 3.2.1 [`AxonBackTest/PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py)
```python
    # In _build_report_dataframe():
        report_dict: Dict[str, Any] = {
            "datetimelist": datetimelist,
            "Datetime": timestamps,
            "CloseProfit": cash_records,  # Realized cash balance (Initial Capital + Realized PnL - Friction)
            "Equity": equity_records,
            "Cash": cash_records,
            "UnrealizedPnL": unrealized_records,
            "RealizedPnL": realized_records,
            "MarginUsed": margin_records,
            "TotalFriction": friction_records,
            "TotalFee": fee_records,
            "TotalSlippage": slippage_records,
            "TotalTax": tax_records,
        }
```

#### 3.2.2 [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py)
```python
    def plot_image(self) -> None:
        """
        Renders two standalone figures:
        1. Figure 1: Stacked subplots with Mark-to-Market Equity (top) and Realized CloseProfit (bottom).
        2. Figure 2: Strategy target position ratios over time.
        """
        if self.report is None:
            self.generate_report()

        if not self.report:
            raise ValueError("Report data is empty; cannot render plots.")

        report_df = pd.DataFrame(self.report)
        report_df["datetimelist"] = pd.to_datetime(report_df["datetimelist"])
        report_df.set_index("datetimelist", inplace=True)
        report_df.index.name = "Datetime"

        plt.style.use("seaborn-v0_8-darkgrid")

        # Figure 1: Top = Equity (MTM), Bottom = CloseProfit (Realized Cash)
        fig1, (ax_equity, ax_close) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
        fig1.canvas.manager.set_window_title("Portfolio Equity & Close Profit")

        if "Equity" in report_df.columns:
            ax_equity.plot(
                report_df.index,
                report_df["Equity"],
                label="Equity (Mark-to-Market)",
                color="#1f77b4",
                linewidth=1.2,
            )
        ax_equity.set_title("Portfolio Equity Over Time (Mark-to-Market)", fontsize=14)
        ax_equity.set_ylabel("Equity (USD)", fontsize=12)
        ax_equity.legend(loc="upper left")
        ax_equity.grid(True)

        ax_close.plot(
            report_df.index,
            report_df["CloseProfit"],
            label="CloseProfit (Realized Cash)",
            color="#2ca02c",
            linewidth=1.2,
            drawstyle="steps-post",
        )
        ax_close.set_title("Portfolio Close Profit Over Time (Realized)", fontsize=14)
        ax_close.set_xlabel("Date", fontsize=12)
        ax_close.set_ylabel("Close Profit (USD)", fontsize=12)
        ax_close.legend(loc="upper left")
        ax_close.grid(True)
        fig1.tight_layout()

        # Figure 2: Target Position Ratio Over Time
        pos_cols = [col for col in report_df.columns if col.startswith("pos_")]
        if pos_cols:
            fig2, ax_pos = plt.subplots(figsize=(15, 5))
            fig2.canvas.manager.set_window_title("Portfolio Target Positions")
            for col in pos_cols:
                strategy_label = col.removeprefix("pos_")
                ax_pos.plot(
                    report_df.index,
                    report_df[col],
                    label=strategy_label,
                    linewidth=1.2,
                    drawstyle="steps-post",
                )
            ax_pos.axhline(0.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
            ax_pos.set_title("Strategy Target Position Ratio Over Time", fontsize=14)
            ax_pos.set_xlabel("Date", fontsize=12)
            ax_pos.set_ylabel("Position Ratio", fontsize=12)
            ax_pos.legend(loc="upper left")
            ax_pos.grid(True)
            fig2.tight_layout()

        plt.show()
```

---

## 4. 驗證計畫與測試指令 (Valid)

### 4.1 驗證環境與執行指令
> [!IMPORTANT]
> 所有驗證指令必須依據專案規範，嚴格使用虛擬環境之 Python 直譯器：
> 絕對路徑: `/home/b0457812963/AxonBackTest/bin/python`
> 相對路徑（自專案根目錄 `/home/b0457812963/AxonBackTest/AxonBackTest`）: `../bin/python`

```bash
# 1. 驗證 FARTCOINUSDT 後期持倉不變時 CloseProfit 完全無抖動，且產生 2 張 Figure 與正確子圖結構
cd /home/b0457812963/AxonBackTest/AxonBackTest && MPLBACKEND=Agg /home/b0457812963/AxonBackTest/bin/python -c "
import matplotlib.pyplot as plt
plt.show = lambda *a, **kw: None
import main
rdf = main.pfm.report_df
after = rdf[rdf['Datetime'] > '2026-01-18 08:00:00']
assert after['CloseProfit'].nunique() == 1, 'CloseProfit must remain flat when holding constant position!'
assert (rdf['CloseProfit'] == rdf['Cash']).all(), 'CloseProfit must equal Cash!'
assert len(plt.get_fignums()) == 2, f'Expected 2 figures, got {len(plt.get_fignums())}'
fig1, fig2 = [plt.figure(n) for n in plt.get_fignums()]
assert len(fig1.axes) == 2, 'Figure 1 must have 2 subplots (Equity & CloseProfit)'
assert len(fig2.axes) == 1, 'Figure 2 must have 1 subplot (Position Ratio)'
print('ALL VERIFICATION CHECKS PASSED!')
"

# 2. 驗證 AAVEUSDT-RL-30M 不再印出殘留除錯訊息，且多策略繪圖正常運作
cd /home/b0457812963/AxonBackTest/AxonBackTest && MPLBACKEND=Agg /home/b0457812963/AxonBackTest/bin/python -c "
import io, contextlib, matplotlib.pyplot as plt
plt.show = lambda *a, **kw: None
from main import get_strategys
from AxonBackTest.PorfolioTrader import PortfolioManagement
from AxonBackTest.backtester import BackTester
from AxonBackTest.config import PortfolioConfig

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    pfm = PortfolioManagement(config=PortfolioConfig(initial_capital=10000.0, leverage=1.0))
    pfm.register_strategies(get_strategys(['FARTCOINUSDT', 'AAVEUSDT']))
    bt = BackTester(manager=pfm)
    bt.generate_report()
    bt.plot_image()
assert buf.getvalue() == '', f'Unexpected stdout output: {buf.getvalue()}'
print('MULTI-STRATEGY & CLEAN STDOUT CHECK PASSED!')
"
```

### 4.2 驗收查核準則 (Acceptance Criteria)
- [x] **1. 數值與財務邏輯正確性**：
  - [x] `report_df["CloseProfit"]` 與 `report_df["Cash"]` 完全一致。
  - [x] 在 `FARTCOINUSDT` 於 `2026-01-18 08:00:00` 後持倉固定為 `0.9960984` 期間（共 11,946 根 Bar），`CloseProfit` 標準差為 `0.0`（唯一值 `11574.415475`），徹底消除假性抖動。
  - [x] `Equity` 仍正確反映逐根盯市總淨值（最終淨值 `5969.8996`），績效統計指標維持不變。
- [x] **2. 圖表結構與視覺化驗收**：
  - [x] 呼叫 `bt.plot_image()` 後產生 **2 張獨立 Figure 視窗**。
  - [x] Figure 1 包含上下 2 個共用 X 軸的子圖：上為 `Equity`，下為 `CloseProfit`（階梯線）。
  - [x] Figure 2 獨立繪製策略目標部位比例 (`pos_*`) 階梯線並支援單一或多策略圖例。
- [x] **3. 實機執行與整潔度驗證**：
  - [x] 執行 `AAVEUSDT` 回測時不再輸出殘留的 `"開盤價:"` 與 `"***"` 除錯訊息。
  - [x] [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py) 無須修改即可直接運行通過。
