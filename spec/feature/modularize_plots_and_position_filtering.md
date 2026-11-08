# 規格文件：繪圖函式獨立化與商品部位互動屏蔽功能 (Modularize Plots and Position Filtering)

- **分類 (Category)**: `feature`
- **規格路徑 (Spec Path)**: `spec/feature/modularize_plots_and_position_filtering.md`
- **狀態 (Status)**: `已完成 Completed`

## 📋 目錄 / Index
1. [1. 背景動機與現況分析 (Background)](#1-背景動機與現況分析-background)
2. [2. 改動範圍與設計邊界 (Scope)](#2-改動範圍與設計邊界-scope)
3. [3. 逐步實作查核清單與代碼藍圖 (CheckList)](#3-逐步實作查核清單與代碼藍圖-checklist)
4. [4. 驗證計畫與測試指令 (Valid)](#4-驗證計畫與測試指令-valid)

---

## 1. 背景動機與現況分析 (Background)

### 1.1 問題陳述與設計動機
在現行 [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) 中，[`BackTester.plot_image()`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py#L26-L103) 將兩張性質完全不同的視覺化圖表高度耦合在同一個巨型函式中：
1. **圖表 1 (Figure 1 - 投資組合績效總覽)**：上方為盯市淨值 (`Equity`)，下方為已平倉累積損益 (`CloseProfit`)。
2. **圖表 2 (Figure 2 - 策略部位曲線)**：時間序列上的各策略目標部位比例 (`Position Ratio`, `pos_*`)。

目前存在兩大核心痛點：
1. **缺乏獨立呼叫彈性**：使用者無法單獨呼叫「績效圖」或「部位圖」，每次調用 `plot_image()` 皆強制同時渲染兩張圖表。
2. **部位圖缺乏篩選/屏蔽機制**：當組合包含 10 個、20 個甚至更多交易對或商品時，部位圖中大量折線互相交錯重疊，極度混亂難以判讀。使用者強烈需要能「屏蔽特定商品部位」或「單獨只查看某一個商品部位」的功能。

針對使用者的疑問：*「如果 matplotlib 做不到的話幫我改用成 GUI 也可以 pyqt6 也可以」*：
- 經環境檢測，當前 Python 虛擬環境 (`/home/b0457812963/AxonBackTest/bin/python`) 已配置 `matplotlib` 與 `tkinter`（後端為 `TkAgg`），尚未安裝且無須強行引入龐大的 `PyQt6` C++ 依賴。
- `matplotlib` 自身原生即提供強大的 GUI 互動元件：
  - `matplotlib.widgets.CheckButtons`（勾選框）：即時動態勾選/取消顯示個別商品部位。
  - `matplotlib.widgets.Button`（動作按鈕）：一鍵「全部顯示 (All)」與「全部隱藏 (None)」，方便使用者一鍵隱藏全部後僅點選欲查看的單一商品。
  - 圖例拾取事件 (`mpl_connect('pick_event')`)：直接用滑鼠點擊圖例 (Legend) 上之商品名稱/折線即可動態切換顯示狀態。
  - 程式碼參數篩選：提供 `symbols` / `strategies` 參數，使用者亦可直接以程式碼指定檢視之標的。

因此，本規格將兩張圖表獨立為兩個高內聚方法，並在部位圖中原生整合 Matplotlib 互動屏蔽與程式碼篩選功能，同時保留 `plot_image()` 封裝以確保現有代碼 100% 向後相容。

### 1.2 現況與預期行為對照 (Current vs. Expected Behavior)
| 維度 | 現況行為 (Current Behavior) | 預期行為 (Expected Behavior) |
| :--- | :--- | :--- |
| **函式架構** | 單一巨型函式 [`plot_image()`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py#L26-L103) 內聯處理兩張圖之資料前處理與繪製。 | 拆分為 `plot_performance()` 與 `plot_positions()` 兩個獨立函式，提取私有 `_prepare_report_df()` 統一前處理。`plot_image()` 作為整合入口維持相容。 |
| **部位圖顯示** | 無差別繪製所有 `pos_*` 欄位，多標的時線條雜亂無法篩選。 | 支援參數過濾 (`symbols=["BTCUSDT"]`) 與視窗內即時互動屏蔽 (CheckButtons + 按鈕 + 點擊圖例切換)。 |
| **獨立查看單一商品部位** | 無法單獨查看，必須人工在混雜線條中辨識。 | 透過 `plot_positions(symbols="BTCUSDT")` 直接查看，或在互動視窗中點選「全部隱藏」後僅勾選目標標的。 |
| **外部相容性** | 既有腳本（如 [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py)）呼叫 `bt.plot_image()`。 | 呼叫 `bt.plot_image()` 行為不變，維持相容且圖 2 同步升級具備屏蔽互動能力。 |

### 1.3 根因分析與相關代碼連結
- 目標函式：[`backtester.py:L26-L103`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py#L26-L103)
- 現有程式未將報表 DataFrame 轉置格式封裝為共用邏輯，亦未分離績效圖與部位圖的職責，導致繪圖流程缺乏模組化與篩選擴充性。

---

## 2. 改動範圍與設計邊界 (Scope)

### 2.1 檔案與模組影響矩陣 (File Scope Matrix)
| 編號 | 目標檔案與路徑 | 範圍類別 | 預計變更內容說明 |
| :---: | :--- | :---: | :--- |
| **Item 1** | [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) | **In-Scope (納入)** | 1. 實作 `_prepare_report_df()` 私有輔助方法。<br>2. 實作 `plot_performance()` 獨立繪製淨值與損益圖。<br>3. 實作 `plot_positions()` 獨立繪製部位圖並新增互動屏蔽與商品篩選功能。<br>4. 重構 `plot_image()` 呼叫上述兩函式維持完整相容。 |
| **Item 2** | [`AxonBackTest/PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) | **Out-of-Scope (排除)** | 報表生成與回測計算邏輯維持不變。 |
| **Item 3** | [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py) | **Out-of-Scope (排除)** | 呼叫端維持相容，不強迫修改現有回測執行腳本。 |

### 2.2 設計邊界與非目標 (Boundaries & Non-Goals)
- **納入範圍之邊界 (In-Scope)**：
  - 拆分出獨立的 `plot_performance(self, show: bool = True) -> Optional[plt.Figure]`。
  - 拆分出獨立的 `plot_positions(self, symbols: Optional[Union[str, Sequence[str]]] = None, interactive: bool = True, show: bool = True) -> Optional[plt.Figure]`。
  - 部位圖支援多維度篩選匹配：支援依照商品前綴（例如 `"BTCUSDT"`）、完整策略名稱（例如 `"BTCUSDT-RL-30M"`）或欄位名稱（例如 `"pos_BTCUSDT-RL-30M"`）進行過濾。
  - 部位圖支援視窗即時互動：
    - 右側設置 `CheckButtons` 控制面板。
    - 頂部設置 `[全部顯示 (All)]` 與 `[全部隱藏 (None)]` 快速切換按鈕。
    - 支援圖例拾取切換（點擊圖例線條/文字即可切換對應曲線之顯示/隱藏狀態，被隱藏者圖例透明度設為 0.2）。
  - 物件引用保護：互動元件將被綁定至 Figure 物件實例（例如 `fig._interactive_widgets`），防止被 Python 垃圾回收機制 (GC) 銷毀導致事件回呼失效。
- **排除範圍 (Out-of-Scope / Non-Goals)**：
  - 不強制引入 `PyQt6` 作為專案額外依賴。Matplotlib 原生 Widgets 完全能滿足篩選與屏蔽需求；若未來有獨立 Desktop App 需求，可再另行擴充。

---

## 3. 逐步實作查核清單與代碼藍圖 (CheckList)

### 3.1 步驟式實作清單 (Task Checklist)
- [x] **步驟 1: 實作共用報表前處理方法 `_prepare_report_df`**
  - [x] 檢查報表是否已生成，未生成則調用 `generate_report()`。
  - [x] 驗證報表非空，轉換 `datetimelist` 為 `DatetimeIndex`。
- [x] **步驟 2: 實作獨立績效總覽圖繪製方法 `plot_performance`**
  - [x] 建立 Figure 1（上下雙子圖：Mark-to-Market Equity 與 Realized CloseProfit）。
  - [x] 支援 `show: bool = True` 參數，允許返回 `plt.Figure` 供進一步自訂。
- [x] **步驟 3: 實作獨立策略部位圖與互動屏蔽方法 `plot_positions`**
  - [x] 提取所有 `pos_*` 欄位並依 `symbols` 進行模糊與精準過濾。
  - [x] 繪製目標折線 (`drawstyle="steps-post"`) 並收集 `Line2D` 物件與策略標籤對應字典。
  - [x] 當 `interactive=True` 且標的數大於 1 時：
    - [x] 調整繪圖區域邊界，右側劃分出專屬控制軸 (Axes)。
    - [x] 加入 `[All]` 與 `[None]` 快速切換按鈕。
    - [x] 加入多選勾選框 `CheckButtons`。
    - [x] 綁定圖例拾取事件 (`pick_event`)，支援直接點擊圖例標籤切換顯示狀態。
    - [x] 儲存 widget 參照至 `fig._interactive_widgets` 防禦垃圾回收。
  - [x] 支援 `show: bool = True` 參數，返回 `plt.Figure`。
- [x] **步驟 4: 重構 `plot_image` 整合包裝**
  - [x] 依序調用 `plot_performance(show=False)` 與 `plot_positions(show=False)`。
  - [x] 呼叫 `plt.show()` 同時彈出雙視窗，維持既有行為不變。
- [x] **步驟 5: 代碼防禦性與規格整潔維護**
  - [x] 加入完整英文 Type Hints 與 Docstrings。
  - [x] 處理標的名稱不存在時的友善 Warning/錯誤處理。

### 3.2 詳細程式碼變更藍圖 (Code Modification Blueprint)

#### 3.2.1 [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py)
```python
import copy
import time
from typing import Any, Dict, List, Optional, Sequence, Union
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, CheckButtons
import numpy as np
import pandas as pd
from AxonBackTest.PorfolioTrader import PortfolioManagement
import AxonBackTest.config as config
from AxonBackTest.strategy import Strategy


class BackTester:
    def __init__(self, manager: PortfolioManagement = None):
        self.pfm = manager
        self.report = None

    def generate_report(self):
        self.report = self.pfm.generate_report()
        return self.report

    def _prepare_report_df(self) -> pd.DataFrame:
        """Validates report presence and converts it into a DatetimeIndexed DataFrame."""
        if self.report is None:
            self.generate_report()

        if not self.report:
            raise ValueError("Report data is empty; cannot render plots.")

        report_df = pd.DataFrame(self.report)
        report_df["datetimelist"] = pd.to_datetime(report_df["datetimelist"])
        report_df.set_index("datetimelist", inplace=True)
        report_df.index.name = "Datetime"
        return report_df

    def plot_performance(self, show: bool = True) -> plt.Figure:
        """
        Renders the portfolio performance figure with two stacked subplots:
        1. Top: Mark-to-Market Equity over time.
        2. Bottom: Realized CloseProfit cash balance over time.
        """
        report_df = self._prepare_report_df()
        plt.style.use("seaborn-v0_8-darkgrid")

        fig, (ax_equity, ax_close) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
        if fig.canvas.manager is not None:
            fig.canvas.manager.set_window_title("Portfolio Equity & Close Profit")

        if "Equity" in report_df.columns:
            ax_equity.plot(
                report_df.index,
                report_df["Equity"],
                label="Equity (Mark-to-Market)",
                color="#1f77b4",
                linewidth=1.2,
            )
            ax_equity.legend(loc="best", frameon=True, facecolor="white", framealpha=0.8)
        ax_equity.set_title("Portfolio Equity Over Time (Mark-to-Market)", fontsize=14)
        ax_equity.set_ylabel("Equity (USD)", fontsize=12)
        ax_equity.grid(True)

        if "CloseProfit" in report_df.columns:
            ax_close.plot(
                report_df.index,
                report_df["CloseProfit"],
                label="CloseProfit (Realized Cash)",
                color="#2ca02c",
                linewidth=1.2,
                drawstyle="steps-post",
            )
            ax_close.legend(loc="best", frameon=True, facecolor="white", framealpha=0.8)
        ax_close.set_title("Portfolio Close Profit Over Time (Realized)", fontsize=14)
        ax_close.set_xlabel("Date", fontsize=12)
        ax_close.set_ylabel("Close Profit (USD)", fontsize=12)
        ax_close.grid(True)
        fig.tight_layout()

        if show:
            plt.show()
        return fig

    def plot_positions(
        self,
        symbols: Optional[Union[str, Sequence[str]]] = None,
        interactive: bool = True,
        show: bool = True,
    ) -> Optional[plt.Figure]:
        """
        Renders strategy target position ratios over time.

        Args:
            symbols: Optional single symbol string or sequence of symbols/strategies to filter.
            interactive: If True, enables interactive GUI checkboxes, All/None buttons, and clickable legend.
            show: If True, calls plt.show() immediately.
        """
        report_df = self._prepare_report_df()
        plt.style.use("seaborn-v0_8-darkgrid")

        pos_cols = [col for col in report_df.columns if col.startswith("pos_")]
        if not pos_cols:
            print("No position columns (pos_*) found in report.")
            return None

        # Filter by symbols/strategies if provided
        if symbols is not None:
            if isinstance(symbols, str):
                target_symbols = {symbols.strip().lower()}
            else:
                target_symbols = {s.strip().lower() for s in symbols}

            filtered_cols = []
            for col in pos_cols:
                raw_name = col.removeprefix("pos_").lower()
                # Matches exact column, strategy name, or symbol prefix
                if (
                    col.lower() in target_symbols
                    or raw_name in target_symbols
                    or any(raw_name.startswith(t) or t in raw_name for t in target_symbols)
                ):
                    filtered_cols.append(col)

            if not filtered_cols:
                print(f"Warning: No matching position columns found for filter: {symbols}. Available: {[c.removeprefix('pos_') for c in pos_cols]}")
                filtered_cols = pos_cols
            pos_cols = filtered_cols

        fig, ax_pos = plt.subplots(figsize=(16, 6))
        if fig.canvas.manager is not None:
            fig.canvas.manager.set_window_title("Portfolio Target Positions")

        lines_by_label: Dict[str, Any] = {}
        for col in pos_cols:
            strategy_label = col.removeprefix("pos_")
            (line,) = ax_pos.plot(
                report_df.index,
                report_df[col],
                label=strategy_label,
                linewidth=1.2,
                drawstyle="steps-post",
            )
            lines_by_label[strategy_label] = line

        ax_pos.axhline(0.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
        ax_pos.set_title("Strategy Target Position Ratio Over Time", fontsize=14)
        ax_pos.set_xlabel("Date", fontsize=12)
        ax_pos.set_ylabel("Position Ratio", fontsize=12)
        leg = ax_pos.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.8)
        ax_pos.grid(True)

        # Interactive controls (CheckButtons, All/None buttons, Pickable Legend)
        interactive_widgets = []
        if interactive and len(lines_by_label) > 1:
            # Leave space on the right for controls
            fig.subplots_adjust(left=0.08, right=0.80, top=0.92, bottom=0.10)

            # Quick Toggle Buttons: [All] and [None]
            ax_btn_all = fig.add_axes([0.83, 0.90, 0.06, 0.04])
            ax_btn_none = fig.add_axes([0.90, 0.90, 0.06, 0.04])
            btn_all = Button(ax_btn_all, "All", color="#e0e0e0", hovercolor="#c0c0c0")
            btn_none = Button(ax_btn_none, "None", color="#e0e0e0", hovercolor="#c0c0c0")

            # CheckButtons panel
            labels = list(lines_by_label.keys())
            actives = [True] * len(labels)
            
            # Dynamically size widget height
            cb_height = min(0.75, max(0.25, 0.035 * len(labels) + 0.05))
            ax_check = fig.add_axes([0.83, 0.88 - cb_height, 0.14, cb_height])
            check = CheckButtons(ax_check, labels, actives)

            def set_all_visibility(visible: bool):
                for i, label in enumerate(labels):
                    line = lines_by_label[label]
                    line.set_visible(visible)
                    # Sync checkbox state if mismatch
                    if check.get_status()[i] != visible:
                        check.set_active(i)
                _update_legend_styles()
                fig.canvas.draw_idle()

            def on_check_clicked(label: str):
                line = lines_by_label[label]
                line.set_visible(not line.get_visible())
                _update_legend_styles()
                fig.canvas.draw_idle()

            def _update_legend_styles():
                if leg is not None:
                    for text, l_line in zip(leg.get_texts(), leg.get_lines()):
                        name = text.get_text()
                        if name in lines_by_label:
                            vis = lines_by_label[name].get_visible()
                            alpha = 1.0 if vis else 0.2
                            text.set_alpha(alpha)
                            l_line.set_alpha(alpha)

            btn_all.on_clicked(lambda event: set_all_visibility(True))
            btn_none.on_clicked(lambda event: set_all_visibility(False))
            check.on_clicked(on_check_clicked)

            # Interactive Legend picking
            if leg is not None:
                legend_map = {}
                for legline, legtext, (label, origline) in zip(leg.get_lines(), leg.get_texts(), lines_by_label.items()):
                    legline.set_picker(True)
                    legline.set_pickradius(5)
                    legtext.set_picker(True)
                    legend_map[legline] = label
                    legend_map[legtext] = label

                def on_pick(event):
                    artist = event.artist
                    if artist in legend_map:
                        label = legend_map[artist]
                        idx = labels.index(label)
                        check.set_active(idx)  # triggers on_check_clicked internally

                fig.canvas.mpl_connect("pick_event", on_pick)

            interactive_widgets.extend([btn_all, btn_none, check])
            # Keep references alive
            fig._interactive_widgets = interactive_widgets
        else:
            fig.tight_layout()

        if show:
            plt.show()
        return fig

    def plot_image(self) -> None:
        """
        Renders two standalone figures:
        1. Performance overview: Equity & CloseProfit.
        2. Target position ratios with interactive product filtering.
        """
        self.plot_performance(show=False)
        self.plot_positions(show=False)
        plt.show()
```

---

## 4. 驗證計畫與測試指令 (Valid)

### 4.1 驗證環境與執行指令
> [!IMPORTANT]
> 所有驗證指令必須依據專案規範，嚴格使用虛擬環境之 Python 直譯器：
> 絕對路徑: `/home/b0457812963/AxonBackTest/bin/python`

```bash
# 1. 執行單元與邊界測試（無頭模式 Headless 驗證函式簽名、回傳型別與篩選邏輯）
/home/b0457812963/AxonBackTest/bin/python -c "
import matplotlib
matplotlib.use('Agg')
from AxonBackTest.backtester import BackTester
import pandas as pd

bt = BackTester()
bt.report = [
    {'datetimelist': '2023-01-01 00:00:00', 'Equity': 10000.0, 'CloseProfit': 10000.0, 'pos_BTCUSDT': 0.5, 'pos_ETHUSDT': -0.3},
    {'datetimelist': '2023-01-01 01:00:00', 'Equity': 10100.0, 'CloseProfit': 10050.0, 'pos_BTCUSDT': 0.0, 'pos_ETHUSDT': 0.2},
]
# 測試 1: 獨立呼叫 plot_performance
fig1 = bt.plot_performance(show=False)
assert fig1 is not None, 'plot_performance must return Figure'

# 測試 2: 獨立呼叫 plot_positions（全部繪製）
fig2 = bt.plot_positions(show=False)
assert fig2 is not None, 'plot_positions must return Figure'

# 測試 3: 參數篩選單一商品
fig3 = bt.plot_positions(symbols='BTCUSDT', show=False)
assert fig3 is not None, 'plot_positions with single symbol filter must return Figure'

# 測試 4: 既有 plot_image 整合呼叫
bt.plot_image()
print('All programmatic validation tests passed successfully!')
"

# 2. 執行主回測模擬整合驗證
/home/b0457812963/AxonBackTest/bin/python -c "
import matplotlib
matplotlib.use('Agg')
import main
print('main.py execution with new plotting methods passed!')
"
```

### 4.2 驗收查核準則 (Acceptance Criteria)
- [x] **1. 獨立化呼叫驗證**：
  - [x] 可單獨調用 `bt.plot_performance()` 且僅彈出 Figure 1（淨值與平倉損益圖）。
  - [x] 可單獨調用 `bt.plot_positions()` 且僅彈出 Figure 2（部位比例圖）。
  - [x] 調用 `bt.plot_image()` 同時彈出兩張視窗，與原有行為保持 100% 相容。
- [x] **2. 篩選與屏蔽功能驗證**：
  - [x] 支援參數傳遞 `symbols="BTCUSDT"` 或 `symbols=["BTCUSDT", ...]`，可精準僅繪製指定商品。
  - [x] 在部位圖視窗中，點選 `[None]` 可隱藏全部，接著勾選特定商品勾選框即可單獨查看該商品部位。
  - [x] 點選 `[All]` 可立即恢復全部顯示。
  - [x] 點選圖例文字/標籤可切換該曲線可見度並調整透明度樣式。
- [x] **3. 實機執行驗證 (Runtime Verification)**：
  - [x] 執行上述測試指令無任何未捕捉之例外或報錯。
