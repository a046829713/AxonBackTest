# 規格文件：Strategy 類別重構與真實訂單資料整合 (Target Position Integration)

- **分類 (Category)**: `feature`
- **規格路徑 (Spec Path)**: `spec/feature/strategy_orders_integration.md`
- **狀態 (Status)**: `已核准並實作完成 (Approved & Implemented)`

## 📋 目錄 / Index
1. [1. 背景動機與現況分析 (Background)](#1-背景動機與現況分析-background)
2. [2. 改動範圍與設計邊界 (Scope)](#2-改動範圍與設計邊界-scope)
3. [3. 逐步實作查核清單與代碼藍圖 (CheckList)](#3-逐步實作查核清單與代碼藍圖-checklist)
4. [4. 驗證計畫與測試指令 (Valid)](#4-驗證計畫與測試指令-valid)

---

## 1. 背景動機與現況分析 (Background)

### 1.1 問題陳述與設計動機
在先前早期開發階段，由於尚未產出正式的強化學習（RL）或策略模型訂單歷史檔案，在 [`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py) 與 [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py) 中暫時使用了虛擬訊號生成函數（`generate_fake_signals`, `generate_fake_postionsize`）。

現在系統已經具備正式產出的訂單資料檔案（例如 [`AAVEUSDT_orders.csv`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AAVEUSDT_orders.csv)），其結構已完整包含：
- `Datetime`: 時間戳記
- `Symbol`: 交易標的代碼
- `Open`: 開盤價
- `Close`: 收盤價
- `Action`: 模型原始動作值
- `Position`: 目標持倉部位數值（0.0 ~ 1.0）

為了遵循**「單次改動不要太大、漸進式迭代」**與**「目標部位導向（Target Position / State-driven）」**的現代量化套件設計理念，本次重構將清理所有遺留的虛擬訊號生成程式碼，將 `Strategy` 轉型為高內聚、輕量化的單資產時序資料與目標部位代理人。

### 1.2 現況與預期行為對照 (Current vs. Expected Behavior)
| 維度 | 現況行為 (Current Behavior) | 預期行為 (Expected Behavior) |
| :--- | :--- | :--- |
| **訊號/部位來源** | 依賴外部隨機產生函式 (`_generate_signals_fn`, `_generate_postion_size_fn`) | 直接接收真實訂單/部位歷史資料 (`CSV` 檔案或 `pd.DataFrame`) |
| **Strategy 職責** | 包含 `generate_signals()`、`register_signals()` 等臃腫邏輯 | 轉為「瘦核心」容器，僅負責持有資產價格與目標部位，並自動計算部位變更量 ($\Delta Position$) |
| **資料合約驗證** | 無欄位校驗，若缺少資料僅在執行期拋出泛化例外 | 明確檢查必要欄位 (`Open`, `Close`, `Position`) 與 `DatetimeIndex`，提供清晰的錯誤訊息 |
| **進入點 (main.py)** | 充斥隨機產生訊號邏輯與路徑寫死的模擬檔案 | 簡潔乾淨的端到端入口，直接讀取 `AAVEUSDT_orders.csv` 並注入 Strategy |

### 1.3 根因分析與相關代碼連結
- [`AxonBackTest/strategy.py:L10-L51`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py#L10-L51)：存在已無用處的 `_generate_signals_fn`, `_generate_postion_size_fn`, `register_signals()`, `generate_signals()`, `generate_postion_sizes()`。
- [`main.py:L9-L24`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py#L9-L24)：定義了已不再需要的 `generate_fake_signals` 與 `generate_fake_postionsize`，且資料讀取未正確串連至 Strategy。

---

## 2. 改動範圍與設計邊界 (Scope)

### 2.1 檔案與模組影響矩陣 (File Scope Matrix)
| 編號 | 目標檔案與路徑 | 範圍類別 | 預計變更內容說明 |
| :---: | :--- | :---: | :--- |
| **Item 1** | [`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py) | **In-Scope (納入)** | 移除虛擬訊號生成相關欄位與方法；重構 `__init__`、`set_data`、`load_data_from_csv`；增加欄位檢查與 `PositionChange` 自動計算。 |
| **Item 2** | [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py) | **In-Scope (納入)** | 移除隨機訊號生成邏輯；調整為讀取 `AAVEUSDT_orders.csv` 並傳入 `Strategy` 的乾淨範例。 |
| **Item 3** | `tests/test_strategy.py` | **In-Scope (納入 - 新建)** | 新增單元測試套件，涵蓋 CSV 載入、DataFrame 載入、必要欄位檢查、部位變動差分計算。 |
| **Item 4** | [`AxonBackTest/PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) | **Out-of-Scope (排除)** | 保持現況，後續階段再針對投資組合與撮合邏輯進行重構，避免本次更動範圍過大。 |
| **Item 5** | [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) | **Out-of-Scope (排除)** | 保持現況，留待後續報表與視覺化階段再整合。 |

### 2.2 設計邊界與非目標 (Boundaries & Non-Goals)
- **納入範圍之邊界 (In-Scope)**：
  - `Strategy` 類別純淨化，完全基於目標部位（Target Position）架構。
  - 支援從 `history_data_path` 讀取 CSV，或透過 `data: pd.DataFrame` 直接注入。
  - 嚴格的資料合約驗證（包含 `Open`, `Close`, `Position` 檢查）。
  - 自動生成 `PositionChange` 序列（即 $Position_t - Position_{t-1}$）。
- **排除範圍 (Out-of-Scope / Non-Goals)**：
  - 本次**不修改**投資組合等級的保證金計算、資金分配與滑價手續費撮合（`PorfolioTrader.py`）。
  - 本次**不涉及**多商品時間軸對齊與合併報表產出。

---

## 3. 逐步實作查核清單與代碼藍圖 (CheckList)

### 3.1 步驟式實作清單 (Task Checklist)
- [x] **步驟 1: 重塑 `Strategy` 類別架構 (`AxonBackTest/strategy.py`)**
  - [x] 移除 `generate_signals_fn`, `generate_postion_size_fn`, `self.signals`, `self.postion_sizes`。
  - [x] 移除 `register_signals()`, `generate_signals()`, `generate_postion_sizes()`。
  - [x] 更新 `__init__`：支援可選傳入 `data: pd.DataFrame | None = None`。
  - [x] 實作 `set_data(df: pd.DataFrame)`：
    - 檢查必要欄位（`Open`, `Close`, `Position`）。
    - 處理 `Datetime` 索引轉換（若非 DatetimeIndex 則以 Datetime 欄位轉為索引）。
    - 自動計算 `PositionChange`：`df["Position"].diff().fillna(df["Position"])`。
  - [x] 完善 `load_data_from_csv(file_path: str | None = None)`：預設讀取 `self.config.history_data_path` 或指定路徑，並調用 `set_data`。
  - [x] 提供便利屬性存取器：`positions`, `position_changes`, `open_prices`, `close_prices`。
- [x] **步驟 2: 精簡入口程式碼 (`main.py`)**
  - [x] 刪除 `generate_fake_signals` 與 `generate_fake_postionsize`。
  - [x] 使用 `PresetFactory.crypto_perpetual` 建立 AAVE 策略設定（或指定 `history_data_path="AAVEUSDT_orders.csv"`）。
  - [x] 建立 `Strategy` 實例並載入資料，輸出資料預覽驗證成功載入。
- [x] **步驟 3: 新增單元測試 (`tests/test_strategy.py`)**
  - [x] 測試從 DataFrame 成功載入與資料合約驗證。
  - [x] 測試缺少必要欄位（如缺 `Position` 或 `Close`）時引發明確之 `ValueError`。
  - [x] 測試 `PositionChange` 數值計算之正確性。
  - [x] 測試從實際 `AAVEUSDT_orders.csv` 載入之相容性。
- [x] **步驟 4: 代碼整潔與防禦性維護**
  - [x] 清理未使用的模組引入（如無用的 `Enum` 等）。
  - [x] 確保型別標註 (Type Hints) 完整且嚴謹。

### 3.2 詳細程式碼變更藍圖 (Code Modification Blueprint)

#### 3.2.1 [`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py)
```python
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import pandas as pd
from . import config

class Strategy:
    """
    單一標的之交易策略資料與目標部位代理容器。
    以目標部位 (Target Position / State-driven) 為核心，管理價格歷史與模型期望暴露部位。
    """
    def __init__(
        self,
        config: config.StrategyConfig,
        formal: bool = False,
        data: Optional[pd.DataFrame] = None,
    ):
        self.formal: bool = formal
        self.config: config.StrategyConfig = config
        self.df: pd.DataFrame = pd.DataFrame()

        if data is not None:
            self.set_data(data)

    def set_data(self, df: pd.DataFrame) -> None:
        """
        注入並校驗策略資料。
        必要欄位包含: Open, Close, Position (時間戳可為 Datetime 欄位或 DatetimeIndex)。
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty.")

        working_df = df.copy()

        # 處理 Datetime 索引
        if "Datetime" in working_df.columns:
            working_df["Datetime"] = pd.to_datetime(working_df["Datetime"])
            working_df.set_index("Datetime", inplace=True)
        elif not isinstance(working_df.index, pd.DatetimeIndex):
            try:
                working_df.index = pd.to_datetime(working_df.index)
            except Exception as e:
                raise ValueError("DataFrame index must be a valid DatetimeIndex or contain a 'Datetime' column.") from e

        # 校驗必要核心欄位
        required_cols = {"Open", "Close", "Position"}
        missing_cols = required_cols - set(working_df.columns)
        if missing_cols:
            raise ValueError(f"Strategy data missing required columns: {missing_cols}")

        # 自動計算部位變更量 (PositionChange)
        working_df["PositionChange"] = working_df["Position"].diff().fillna(working_df["Position"])
        self.df = working_df

    def load_data_from_csv(self, file_path: Optional[str] = None) -> None:
        """
        從指定或預設配置之 CSV 檔案載入資料。
        """
        target_path = file_path or self.config.history_data_path
        if not target_path or not os.path.exists(target_path):
            raise FileNotFoundError(f"Strategy data file not found: {target_path}")

        raw_df = pd.read_csv(target_path)
        self.set_data(raw_df)

    def load_data_from_pd(self, df: pd.DataFrame) -> None:
        """向下相容之 DataFrame 載入介面"""
        self.set_data(df)

    @property
    def positions(self) -> pd.Series:
        return self.df["Position"] if not self.df.empty else pd.Series(dtype=float)

    @property
    def position_changes(self) -> pd.Series:
        return self.df["PositionChange"] if not self.df.empty else pd.Series(dtype=float)

    @property
    def open_prices(self) -> pd.Series:
        return self.df["Open"] if not self.df.empty else pd.Series(dtype=float)

    @property
    def close_prices(self) -> pd.Series:
        return self.df["Close"] if not self.df.empty else pd.Series(dtype=float)
```

#### 3.2.2 [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py)
```python
import pandas as pd
from AxonBackTest.config import PresetFactory
from AxonBackTest.strategy import Strategy

# 1. 配置 AAVEUSDT 永續合約策略
aave_config = PresetFactory.crypto_perpetual(
    strategy_name="AAVEUSDT-RL-30M",
    history_data_path="AAVEUSDT_orders.csv"
)

# 2. 建立 Strategy 實例並載入資料
strategy = Strategy(config=aave_config)
strategy.load_data_from_csv()

# 3. 預覽載入後資料與部位變更量
print("載入成功！資料概覽：")
print(strategy.df[["Open", "Close", "Position", "PositionChange"]].head(10))
```

---

## 4. 驗證計畫與測試指令 (Valid)

### 4.1 驗證環境與執行指令
> [!IMPORTANT]
> 依據專案規格，所有測試必須在虛擬環境的 Python 直譯器下執行：
> 絕對路徑: `/home/b0457812963/AxonBackTest/bin/python`

```bash
# 1. 執行 Strategy 單元測試
/home/b0457812963/AxonBackTest/bin/python -m unittest tests/test_strategy.py

# 2. 執行 main.py 端到端入口驗證
cd /home/b0457812963/AxonBackTest/AxonBackTest && /home/b0457812963/AxonBackTest/bin/python main.py
```

### 4.2 驗收查核準則 (Acceptance Criteria)
- [ ] **1. 資料合約正確性**：
  - [ ] 傳入正確之 `AAVEUSDT_orders.csv` 時能順利載入並解析為 `DatetimeIndex`。
  - [ ] 缺少 `Open`、`Close` 或 `Position` 時引發清晰的 `ValueError`。
- [ ] **2. 數值邏輯正確性**：
  - [ ] 第一筆 `PositionChange` 等於首筆 `Position`。
  - [ ] 後續每筆 `PositionChange` 精確等於當前筆部位減去前一筆部位 ($Position_t - Position_{t-1}$)。
- [ ] **3. 實機執行無報錯**：
  - [ ] `tests/test_strategy.py` 全部測試通過（綠燈）。
  - [ ] `main.py` 能順暢運行並印出前 10 筆資料預覽。
