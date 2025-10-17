# SynapseXBT 量化回測框架

這是一個專為加密貨幣期貨設計的量化交易回測框架。

根據專案內的備註，此工具主要設計用於處理 **預先產生的訂單列表 (order list)**，並對其進行績效回測與分析。

目前的 `backtester.py` 腳本展示了如何在模擬模式下 (`fakeMode=True`) 運行策略，以進行開發和測試。

## ✨ 功能特色

- **多策略管理**: 可同時管理和回測多個交易對 (Symbol) 的策略。
- **可配置的投資組合**: 支援設定總資金、槓桿等投資組合參數。
- **清晰的模組化設計**: 將回測器 (`BackTester`)、投資組合管理 (`PortfolioManagement`) 和策略 (`Strategy`) 分離，易於擴展。

## ⚙️ 如何使用

您可以透過修改並執行 `backtester.py` 來啟動回測。

### 1. 設定回測參數

打開 `backtester.py` 檔案，找到檔案最下方的 `if __name__ == "__main__":` 區塊。

您可以修改 `PortfolioManagement` 的初始化參數來設定您想回測的交易對。

```python
if __name__ == "__main__":
    # 在此處修改您想回測的交易對，例如 ["BNBUSDT", "BTCUSDT"]
    manager = PortfolioManagement(symbols=["BNBUSDT"], formal=False)
    
    # 初始化並執行回測
    bt = BackTester(manager=manager)
    bt.run()
```

### 2. 執行回測

儲存您的修改後，在終端機 (Terminal) 中執行以下指令：

```bash
python backtester.py
```

程式將會根據您設定的交易對，初始化對應的策略並在模擬模式下運行。

## 🔧 程式碼結構

- `backtester.py`:
    - **`BackTester`**: 回測器的主類別，是執行回測的進入點。
    - **`PortfolioManagement`**: 投資組合管理類別。負責管理總資金、槓桿，並根據傳入的 `symbols` 列表來生成和管理多個策略實例。
- `strategy.py` (推斷):
    - **`Strategy`**: 代表單一交易策略的類別，處理特定交易對的歷史數據、交易邏輯和訂單產生。
- `config.py` (推斷):
    - **`PortfolioManagementConfig`**: 存放投資組合相關的設定，例如起始資金和槓桿。


