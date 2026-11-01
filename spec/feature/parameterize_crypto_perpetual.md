# 規格文件：PresetFactory.crypto_perpetual 參數化與規格自訂支援

- **分類 (Category)**: `feature`
- **規格路徑 (Spec Path)**: `spec/feature/parameterize_crypto_perpetual.md`
- **狀態 (Status)**: `已核准並實作 Approved & Implemented`

## 📋 目錄 / Index
1. [1. 背景動機與現況分析 (Background)](#1-背景動機與現況分析-background)
2. [2. 改動範圍與設計邊界 (Scope)](#2-改動範圍與設計邊界-scope)
3. [3. 逐步實作查核清單與代碼藍圖 (CheckList)](#3-逐步實作查核清單與代碼藍圖-checklist)
4. [4. 驗證計畫與測試指令 (Valid)](#4-驗證計畫與測試指令-valid)

---

## 1. 背景動機與現況分析 (Background)

### 1.1 問題陳述與設計動機
在現行 [`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py) 中，`PresetFactory.crypto_perpetual` 旨在提供加密貨幣永續合約的開箱即用預設配置。

然而，現行實作中將合約規格（如價格跳動單位 `tick_size`、委託批量 `lot_size`、最小下單量 `min_order_qty` 等）硬編碼（Hardcoded）為 BTCUSDT 的標準值（0.1 USDT, 0.001 BTC）。當使用者回測其他幣種（如 `AAVEUSDT`、`ETHUSDT`、`SOLUSDT`、`DOGEUSDT` 等）時：
1. **價格跳動失真**：低單價或高精度幣種因 `tick_size=0.1`，在 `round_price()` 執行時會發生嚴重的四捨五入誤差。
2. **委託數量精度失真**：不同標的的最小下單精度與步長不一，寫死 `lot_size=0.001` 會導致部位調整與手續費計算失真。
3. **槓桿保證金率無法配置**：`initial_margin_rate` 與 `maintenance_margin_rate` 未開放設定，固定為 1.0 (全額無槓桿) 與 0.05。
4. **成本模型與額外參數無法自訂**：滑價類型、手續費最低收費門檻、交易稅以及 `extra_params` 未開放傳參。

依據使用者指示，採取**方案 A**，並嚴格遵循**單一改動原則（Single Change Principle）**，專注於擴充 `PresetFactory.crypto_perpetual` 的參數可配置性，同時保持 100% 向後相容（維持 BTCUSDT 的預設值）。

### 1.2 現況與預期行為對照 (Current vs. Expected Behavior)
| 維度 | 現況行為 (Current Behavior) | 預期行為 (Expected Behavior) |
| :--- | :--- | :--- |
| **合約規格參數 (Instrument)** | `multiplier=1.0`, `tick_size=0.1`, `lot_size=0.001`, `min_order_qty=0.001`, `currency="USDT"` 全部硬編碼 | 開放為函數參數，可依回測標的自由指定；預設值維持原值以向後相容 |
| **保證金率設定 (Margin)** | 未開放，`InstrumentConfig` 預設為 `initial=1.0`, `maintenance=0.05` | 開放 `initial_margin_rate` 與 `maintenance_margin_rate` 參數 |
| **滑價與手續費模型擴充** | 滑價類型寫死為 `PERCENTAGE`，手續費類型寫死為 `PERCENTAGE`，`min_fee=0.0` | 支援自訂 `slippage_type`, `fee_type`, `min_fee` |
| **交易稅擴充** | 寫死 `tax_type=TaxType.ZERO`, `rate=0.0` | 支援自訂 `tax_rate` 與 `tax_type` |
| **策略額外參數** | `extra_params` 未傳遞，固定為預設空字典 | 支援透過參數注入 `extra_params: Optional[Dict[str, Any]] = None` |
| **向後相容性 (Backward Compatibility)** | 僅少數參數可配置 | 原有呼叫端無需任何修改即可維持原本運行行為 |

### 1.3 根因分析與相關代碼連結
- 受影響位置：[`AxonBackTest/config.py:L409-L450`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py#L409-L450)
- 根因：`PresetFactory.crypto_perpetual` 內部直接以常數數值實體化 `InstrumentConfig`、`SlippageConfig`、`FeeConfig` 與 `TaxConfig`，缺乏可選引數覆蓋機制。

---

## 2. 改動範圍與設計邊界 (Scope)

### 2.1 檔案與模組影響矩陣 (File Scope Matrix)
| 編號 | 目標檔案與路徑 | 範圍類別 | 預計變更內容說明 |
| :---: | :--- | :---: | :--- |
| **Item 1** | [`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py) | **In-Scope (納入)** | 擴充 `PresetFactory.crypto_perpetual` 函數簽名與內部配置物件建構邏輯。 |
| **Item 2** | [`tests/test_config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/tests/test_config.py) | **In-Scope (納入)** | 新增測試套件，涵蓋預設行為向後相容性、自訂標的規格（如 AAVE, DOGE）與價格精度捨入驗證。 |
| **Item 3** | [`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py) | **Out-of-Scope (排除)** | 策略邏輯不需改動，直接消費配置。 |
| **Item 4** | [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) | **Out-of-Scope (排除)** | 回測核心不需改動。 |
| **Item 5** | `PresetFactory.taiwan_index_futures` | **Out-of-Scope (排除)** | 嚴格遵循單一改動原則，維持原狀。 |

### 2.2 設計邊界與非目標 (Boundaries & Non-Goals)
- **納入範圍之邊界 (In-Scope)**：
  - 維持現行前 6 個位置引數順序（`symbol`, `strategy_name`, `slippage_pct`, `fee_pct`, `timeframe`, `history_data_path`），以確保任何位置引數或關鍵字引數的現有呼叫端不會受到破壞。
  - 新增參數包含：`multiplier`, `tick_size`, `lot_size`, `min_order_qty`, `currency`, `initial_margin_rate`, `maintenance_margin_rate`, `slippage_type`, `fee_type`, `min_fee`, `tax_rate`, `tax_type`, `extra_params`。
  - 所有新參數均設有符合原 BTCUSDT 行為之預設值。
- **排除範圍 (Out-of-Scope / Non-Goals)**：
  - 不引入外部幣種規格資料庫或網路 API 抓取規格（保持零外部相依性）。
  - 不更動 `PresetFactory` 以外的任何類別。

---

## 3. 逐步實作查核清單與代碼藍圖 (CheckList)

### 3.1 步驟式實作清單 (Task Checklist)
- [x] **步驟 1: 更新 `crypto_perpetual` 函式簽名與 Docstring**
  - [x] 保留既有 6 個參數位置順序與型別標註。
  - [x] 依序加入規格自訂可選參數，並給定預設值。
  - [x] 更新清晰的英文 Docstring 說明各項參數功能。
- [x] **步驟 2: 傳遞參數至配置模型**
  - [x] 將 `multiplier`, `tick_size`, `lot_size`, `min_order_qty`, `currency`, `initial_margin_rate`, `maintenance_margin_rate` 傳入 `InstrumentConfig`。
  - [x] 將 `slippage_type`, `slippage_pct` 傳入 `SlippageConfig`。
  - [x] 將 `fee_type`, `fee_pct`, `min_fee` 傳入 `FeeConfig`。
  - [x] 將 `tax_type`, `tax_rate` 傳入 `TaxConfig`。
  - [x] 將 `extra_params` 正確傳入 `StrategyConfig`（若為 None 則傳入空字典 `{}`）。
- [x] **步驟 3: 新增單元測試 `tests/test_config.py`**
  - [x] 測試 1：驗證 `crypto_perpetual()` 無傳入任何自訂引數時，規格與原預設值完全一致（向後相容驗證）。
  - [x] 測試 2：驗證自訂參數（例如 `AAVEUSDT`：`tick_size=0.01`, `lot_size=0.01`, `currency="USDT"`）正確反映在 `StrategyConfig.instrument` 中。
  - [x] 測試 3：驗證自訂 `tick_size` 與 `lot_size` 在 `instrument.round_price()` 及 `instrument.round_quantity()` 之計算正確性。
  - [x] 測試 4：驗證自訂保證金率、滑價類型、手續費最低門檻與 `extra_params` 之傳遞正確性。
- [x] **步驟 4: 代碼防禦性與規範查核**
  - [x] 遵循專案規範：代碼內部 docstrings 與註解全英文。
  - [x] 確保無任何 dead code 或未使用的變數。

### 3.2 詳細程式碼變更藍圖 (Code Modification Blueprint)

#### 3.2.1 [`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py)
```python
    @staticmethod
    def crypto_perpetual(
        symbol: str = "BTCUSDT",
        strategy_name: str = "crypto_temp_strategy",
        slippage_pct: float = 0.0005,
        fee_pct: float = 0.0005,
        timeframe: str = "30m",
        history_data_path: str = "simulation/",
        multiplier: float = 1.0,
        tick_size: float = 0.1,
        lot_size: float = 0.001,
        min_order_qty: float = 0.001,
        currency: str = "USDT",
        initial_margin_rate: float = 1.0,
        maintenance_margin_rate: float = 0.05,
        slippage_type: SlippageType = SlippageType.PERCENTAGE,
        fee_type: FeeType = FeeType.PERCENTAGE,
        min_fee: float = 0.0,
        tax_rate: float = 0.0,
        tax_type: TaxType = TaxType.ZERO,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> StrategyConfig:
        """
        Institutional preset factory for Crypto Linear Perpetual Contracts.
        Defaults to Binance BTCUSDT standards while allowing complete customization
        for any arbitrary crypto asset (e.g., AAVE, ETH, SOL, DOGE).

        :param symbol: Ticker symbol (e.g., 'BTCUSDT', 'AAVEUSDT').
        :param strategy_name: Identifier for the strategy instance.
        :param slippage_pct: Slippage rate (default: 0.0005 = 0.05% / 5 bps).
        :param fee_pct: Commission rate (default: 0.0005 = 0.05% / 5 bps).
        :param timeframe: Bar timeframe (e.g., '30m', '1h', '1d').
        :param history_data_path: Path to historical CSV or data store.
        :param multiplier: Contract point multiplier (default: 1.0).
        :param tick_size: Minimum price increment (e.g., 0.1 for BTC, 0.01 for ETH/AAVE).
        :param lot_size: Step size for trade quantity (e.g., 0.001 for BTC, 0.01 for AAVE).
        :param min_order_qty: Minimum allowable order quantity.
        :param currency: Settlement currency (e.g., 'USDT', 'USDC').
        :param initial_margin_rate: Initial margin requirement (1.0 = 1x leverage, 0.1 = 10x leverage).
        :param maintenance_margin_rate: Maintenance margin requirement before liquidation.
        :param slippage_type: Slippage calculation model.
        :param fee_type: Fee calculation model.
        :param min_fee: Minimum commission floor.
        :param tax_rate: Transaction tax rate (default: 0.0).
        :param tax_type: Tax calculation model (default: ZERO).
        :param extra_params: Optional dictionary of supplementary strategy parameters.
        :return: Fully configured StrategyConfig instance.
        """
        instrument = InstrumentConfig(
            symbol=symbol,
            asset_class=AssetClass.CRYPTO_PERPETUAL,
            multiplier=multiplier,
            tick_size=tick_size,
            lot_size=lot_size,
            min_order_qty=min_order_qty,
            currency=currency,
            initial_margin_rate=initial_margin_rate,
            maintenance_margin_rate=maintenance_margin_rate,
        )
        slippage = SlippageConfig(
            slippage_type=slippage_type,
            value=slippage_pct,
        )
        fee = FeeConfig(
            fee_type=fee_type,
            rate=fee_pct,
            min_fee=min_fee,
        )
        tax = TaxConfig(
            tax_type=tax_type,
            rate=tax_rate,
        )
        return StrategyConfig(
            name=strategy_name,
            instrument=instrument,
            slippage=slippage,
            fee=fee,
            tax=tax,
            timeframe=timeframe,
            history_data_path=history_data_path,
            extra_params=extra_params if extra_params is not None else {},
        )
```

---

## 4. 驗證計畫與測試指令 (Valid)

### 4.1 驗證環境與執行指令
> [!IMPORTANT]
> 所有驗證指令必須依據專案規範，嚴格使用虛擬環境之 Python 直譯器：
> 絕對路徑: `/home/b0457812963/AxonBackTest/bin/python`
> 相對路徑: `../bin/python`

```bash
# 1. 執行配置模組專屬單元測試
../bin/python -m unittest tests/test_config.py

# 2. 執行策略回歸測試 (確保無回歸錯誤)
../bin/python -m unittest tests/test_strategy.py

# 3. 執行 main.py 實機驗證
../bin/python main.py
```

### 4.2 驗收查核準則 (Acceptance Criteria)
- [x] **1. 向後相容性**：`PresetFactory.crypto_perpetual()` 在無傳入任何新增引數時，其產出的 `StrategyConfig` 各項欄位與修改前 100% 相同。
- [x] **2. 規格參數自訂有效性**：傳入自訂的 `tick_size=0.01`、`lot_size=0.01`、`min_order_qty=0.01`、`initial_margin_rate=0.1` 時，配置物件完全如實保留並反映於 `instrument`。
- [x] **3. 捨入精度生效性**：在自訂 `tick_size=0.01` 下，`round_price(105.126)` 應正確計算為 `105.13`，而非原寫死 0.1 時的 `105.1`。
- [x] **4. 測試覆蓋全數通過**：所有單元測試與 `main.py` 運行正常無報錯。
