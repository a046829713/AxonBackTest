import pandas as pd
from AxonBackTest.config import PresetFactory
from AxonBackTest.strategy import Strategy

# 1. Preset configuration for AAVEUSDT Perpetual Strategy
aave_config = PresetFactory.crypto_perpetual(
    symbol="AAVEUSDT",
    strategy_name="AAVEUSDT-RL-30M",
    history_data_path="AAVEUSDT_orders.csv",
)

# 2. Initialize Strategy and load data from CSV
strategy = Strategy(config=aave_config)
strategy.load_data_from_csv()

# 3. Preview loaded data and target position changes
print("=== Strategy Data Successfully Loaded ===")
print("Strategy Name:", strategy.config.name)
print("Instrument Symbol:", strategy.config.instrument.symbol)
print("Data Shape:", strategy.df.shape)
print("\nFirst 10 Bars Overview:")
print(strategy.df.head(10))
