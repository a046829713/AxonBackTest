# 規格文件：投資組合回測核心引擎重構 (Portfolio Backtest Engine Refactor)

- **分類 (Category)**: `feature`
- **規格路徑 (Spec Path)**: `spec/feature/portfolio_backtest_engine.md`
- **狀態 (Status)**: `已核准並實作完成 (Approved & Implemented)`

## 📋 目錄 / Index
1. [1. 背景動機與現況分析 (Background)](#1-背景動機與現況分析-background)
2. [2. 改動範圍與設計邊界 (Scope)](#2-改動範圍與設計邊界-scope)
3. [3. 逐步實作查核清單與代碼藍圖 (CheckList)](#3-逐步實作查核清單與代碼藍圖-checklist)
4. [4. 驗證計畫與測試指令 (Valid)](#4-驗證計畫與測試指令-valid)

---

## 1. 背景動機與現況分析 (Background)

### 1.1 問題陳述與設計動機
在先前的架構演進中，我們已經成功建構了：
1. **統一配置模組** ([`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py))：提供強型別的合約規格 (`InstrumentConfig`)、滑價模型 (`SlippageConfig`)、手續費 (`FeeConfig`)、稅金 (`TaxConfig`)、回測摩擦評估器 (`evaluate_order`) 以及工廠預設 (`PresetFactory`)。
2. **目標部位策略容器** ([`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py))：標準化為「目標部位 (Target Position / State-driven)」架構，能直接從訂單 CSV (如 `AAVEUSDT_orders.csv`) 解析時間序列與目標曝險比例。

然而，投資組合撮合核心模組 [`AxonBackTest/PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) 仍存在大量未重構與註解掉的歷史代碼：
- **大量過時的硬編碼分支**：舊版 `_updateinfo` 包含 300 多行對 `signal == 1, -1, 0` 的繁瑣 `if/elif` 分支，且手動計算滑價與費率，與現代化的 `StrategyConfig.evaluate_order` 嚴重脫節。
- **過時的工廠函式**：舊版 `generate_strategys` 寫死 DQN 與無效字典結構，目前已被 `PresetFactory` 取代。
- **效能瓶頸**：舊版 `get_data` 透過多層推導式在每一時間戳對每個策略呼叫 `df.loc[timestamp]`，當 K 線長達上萬筆時會產生龐大的 Pandas 索引查找開銷。

依據使用者的需求與定義：**「當神經網絡輸出 action，成交基準為當根 K 線的 Open 價格」**。在每根 K 線開盤時依目標部位執行調倉（成交在 `Open` 加上滑價與摩擦），收盤時進行逐根盯市（Mark-to-Market, 成交在 `Close`）以計算未實現損益與帳戶淨值 (NAV)，進而產出完整的績效報表。

### 1.2 現況與預期行為對照 (Current vs. Expected Behavior)
| 維度 | 現況行為 (Current Behavior) | 預期行為 (Expected Behavior) |
| :--- | :--- | :--- |
| **撮合模式** | 依賴舊版 `signal` (-1, 0, 1) 與手動數百行 `if/elif` 計算 | 基於目標部位差額 ($\Delta Q$) 自動產生訂單，全面整合 `evaluate_order()` |
| **成交基準價** | 寫死或未定，舊註解中存在多種混亂定義 | 依神經網絡設計，明確以當根 **`Open`** 價格作為成交基準價（含滑價計算） |
| **盯市機制 (MTM)** | 混雜於開平倉邏輯，缺乏嚴謹未實現損益計算 | 每根 Bar 收盤時以 **`Close`** 進行 Mark-to-Market，精確計算 NAV 淨值 |
| **多資產對齊效能** | 雙重推導式逐筆呼叫 `df.loc[timestamp]`，耗時數秒至數十秒 | 預先建立統一 `DatetimeIndex` 進行矩陣式對齊，毫秒級完成對齊與線性掃描 |
| **報表輸出** | 僅印出巨大原始字典，無有效指標統計 | 輸出結構化資料（含 `CloseProfit`, `Cash`, `Margin`, `Drawdown`）與績效指標摘要 |
| **BackTester 相容性**| 報表格式不相容導致無法繪圖 | 100% 相容 [`BackTester.plot_image()`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py#L29-L46) |

---

## 2. 改動範圍與設計邊界 (Scope)

### 2.1 檔案與模組影響矩陣 (File Scope Matrix)
| 編號 | 目標檔案與路徑 | 範圍類別 | 預計變更內容說明 |
| :---: | :--- | :---: | :--- |
| **Item 1** | [`AxonBackTest/PorfolioTrader.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/PorfolioTrader.py) | **In-Scope (納入)** | 徹底清理 300+ 行舊註解代碼；重構 `PortfolioManagement`，實作矩陣對齊、Target Position 撮合引擎、逐根盯市、與豐富績效報表生成。 |
| **Item 2** | [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) | **In-Scope (納入)** | 修復/校準 `generate_report` 回傳對接，確保 `plot_image` 可直接讀取新報表繪圖。 |
| **Item 3** | `tests/test_portfolio.py` | **In-Scope (納入 - 新建)** | 建立回測引擎專屬測試套件：驗證多策略對齊、開倉/平倉/反手交易摩擦扣抵、淨值盯市計算與邊界條件。 |
| **Item 4** | [`main.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/main.py) | **In-Scope (納入)** | 串接真實 `AAVEUSDT_orders.csv` 執行端到端完整回測並展示績效指標。 |
| **Item 5** | [`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py) | **Out-of-Scope (排除)** | 現有配置架構完整穩定，不作大幅變更（若有需要僅增補必要輔助屬性）。 |
| **Item 6** | [`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py) | **Out-of-Scope (排除)** | 保持現有 Target Position 資料容器規格。 |

### 2.2 設計邊界與非目標 (Boundaries & Non-Goals)
- **納入範圍 (In-Scope)**：
  - 支援單策略與多策略註冊。
  - 資金分配採用等權重（Equal Capital Allocation，每策略分配 $\frac{\text{Total Equity}}{N} \times \text{Leverage}$）並結合合約乘數換算張數。
  - 成交價嚴格採用當根 `Open` 價格，並套用 `StrategyConfig.evaluate_order` 取得真實成交價（含滑價）、手續費與稅金。
  - 逐根以 `Close` 進行 Mark-to-Market 盯市，計算真實總權益（Equity = Cash + Unrealized PnL）。
  - 提供完整績效統計：Total Return, CAGR, Max Drawdown (MDD), Sharpe Ratio, Total Trades, Win Rate, Total Fee/Slippage。
- **排除範圍 (Out-of-Scope)**：
  - 本次不改動訂單 CSV 檔案結構。
  - 不引入實盤即時撮合 WebSocket 連線（保持純量化回測）。

---

## 3. 逐步實作查核清單與代碼藍圖 (CheckList)

### 3.1 步驟式實作清單 (Task Checklist)
- [x] **步驟 1: 清理舊代碼與無效註解 (`AxonBackTest/PorfolioTrader.py`)**
  - [x] 移除 `_updateinfo`、`generate_strategys`、`_strategy_name` 等 300+ 行廢棄註解。
  - [x] 清理未使用的模組引入，加入完整型別標註 (`from typing import List, Dict, Any, Optional`)。
- [x] **步驟 2: 重構資料對齊引擎 (`time_min_scale` & `align_market_data`)**
  - [x] 取得所有註冊策略的聯集時間戳，建立排序之 `pd.DatetimeIndex`。
  - [x] 以向量化方式提取各策略之 `Open`, `Close`, `Position`，避免逐根 `df.loc` 造成的效能低下。
- [x] **步驟 3: 實作 Target Position 調倉與訂單撮合核心 (`execute_rebalance`)**
  - [x] 追蹤每檔策略的持倉狀態 (`PositionState: qty, avg_price, realized_pnl, unrealized_pnl`)。
  - [x] 每根 Bar 開盤時：
    - 若目標部位比例變更（或首根）：計算目標張數 $TargetQty = \text{round\_quantity}\left(\frac{\text{Equity} \times \text{Leverage} \times P_t}{N \times \text{Open} \times \text{Multiplier}}\right)$。
    - 取得交易差額 $\Delta Q = TargetQty - CurrentQty$。
    - 若 $\Delta Q \neq 0$：調用 `strategy.config.evaluate_order(base_price=Open, quantity=abs(\Delta Q), side=side)`。
    - 依加倉、減倉或反手規則更新持倉均價 (`avg_price`)，並結算已實現損益 (`realized_pnl`) 與扣抵摩擦費用。
- [x] **步驟 4: 實作逐根盯市與淨值記錄 (Mark-to-Market & Portfolio State)**
  - [x] 每根 Bar 收盤時：以 `Close` 計算各策略之未實現損益：
    $$UnrealizedPnL_i = CurrentQty_i \times (Close_i - AvgPrice_i) \times Multiplier_i$$
  - [x] 計算總帳戶淨值：$Equity = Cash + \sum UnrealizedPnL_i$。
  - [x] 逐根記錄時間戳、`CloseProfit` (即 Equity)、`Cash`、各標的持倉與累計手續費/滑價。
- [x] **步驟 5: 實作統計指標計算與報表產生 (`generate_report`)**
  - [x] 計算總回報率 (Total Return %)、年化回報率 (CAGR)、最大回撤 (Max Drawdown)、夏普比率 (Sharpe Ratio)。
  - [x] 回傳包含歷史紀錄 DataFrame / 列表與指標摘要之 `PortfolioReport` 物件，並相容既有字典格式。
- [x] **步驟 6: 相容性與端到端測試 (`tests/test_portfolio.py` & `main.py`)**
  - [x] 撰寫單元測試覆蓋多策略對齊、手續費扣除、盯市損益與平倉邏輯。
  - [x] 執行 `main.py` 完整回測 `AAVEUSDT_orders.csv`。


---

## 4. 驗證計畫與測試指令 (Valid)

### 4.1 虛擬環境執行指令 (強制性規範)
所有驗證與測試均需使用指定之虛擬環境 Python 直譯器：
- `/home/b0457812963/AxonBackTest/bin/python`

### 4.2 驗證項目與標準
1. **單元測試 (`tests/test_portfolio.py`)**：
   - 執行指令：
     ```bash
     cd /home/b0457812963/AxonBackTest/AxonBackTest && /home/b0457812963/AxonBackTest/bin/python -m unittest tests/test_portfolio.py
     ```
   - 驗證重點：
     - 開倉後現金減少相應手續費與滑價。
     - 價格上漲時多頭未實現損益符合預期數學公式。
     - 平倉後未實現損益轉為已實現損益，倉位歸零。
     - 總淨值曲線隨行情與損益連續變動。
2. **整合回測 (`main.py`)**：
   - 執行指令：
     ```bash
     cd /home/b0457812963/AxonBackTest/AxonBackTest && /home/b0457812963/AxonBackTest/bin/python main.py
     ```
   - 驗證重點：
     - 在 12,000+ 筆真實 `AAVEUSDT_orders.csv` 歷史數據下，回測能於 1 秒內極速執行完成。
     - 印出總報酬率、夏普比率、最大回撤等關鍵指標。
     - 調用 `BackTester.plot_image()` 能正常處理 `CloseProfit` 與 `datetimelist`。
