from AxonBackTest.PorfolioTrader import PortfolioManagement
from AxonBackTest.backtester import BackTester
from AxonBackTest.config import PortfolioConfig, PresetFactory
from AxonBackTest.strategy import Strategy

# 1. Preset configuration for AAVEUSDT Perpetual Strategy
aave_config = PresetFactory.crypto_perpetual(
    symbol="AAVEUSDT",
    strategy_name="AAVEUSDT-RL-30M",
    history_data_path="AAVEUSDT_orders.csv",
)

# 2. Initialize Strategy and load data from CSV
aave_strategy = Strategy(config=aave_config)
aave_strategy.load_data_from_csv()


ace_config = PresetFactory.crypto_perpetual(
    symbol="ACEUSDT",
    strategy_name="ACEUSDT-RL-30M",
    history_data_path="ACEUSDT_orders.csv",
)


ace_strategy = Strategy(config=ace_config)
ace_strategy.load_data_from_csv()


# 3. Setup Portfolio Manager & BackTester
pfm = PortfolioManagement(config=PortfolioConfig(initial_capital=10000.0, leverage=1.0))
pfm.register_strategys([aave_strategy, ace_strategy])

bt = BackTester(manager=pfm)
bt.generate_report()
bt.print_metrics()
bt.plot_image()
