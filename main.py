from matplotlib import pyplot as plt

from AxonBackTest.PorfolioTrader import PortfolioManagement
from AxonBackTest.backtester import BackTester
from AxonBackTest.config import PortfolioConfig, PresetFactory
from AxonBackTest.strategy import Strategy
import pandas as pd
from pathlib import Path

import numpy as np
from decimal import Decimal


def get_min_float(number:float):
    # 將數值以字串傳入 Decimal（避免 float 初期的精度誤差）
    num = Decimal(str(number))

    return float(Decimal(10) ** num.as_tuple().exponent)  # Decimal('0.01')




def get_strategys(symbols:list[str]):
    strategys = []
    for symbol_name in symbols:
        # user define
        _df = pd.read_csv(f"result/{symbol_name}_orders.csv")
        _config = PresetFactory.crypto_perpetual(
            symbol=f"{symbol_name}",
            strategy_name=f"{symbol_name}-RL-30M",
            history_data_path=f"result/{symbol_name}_orders.csv",
            min_order_qty=get_min_float(_df['Close'].iloc[0]),
            tick_size = get_min_float(_df['Close'].iloc[0]),
            slippage_pct=0.0001,
            fee_pct=0.0001
        )

        # 2. Initialize Strategy and load data from CSV
        strategy = Strategy(config=_config)
        strategy.load_data_from_csv()
        strategys.append(strategy)

    return strategys


def rand_pick_symbol(symbol_number:int) -> list:
    # 指定目標資料夾路徑
    folder_path = Path("./result")    
    output = np.random.choice([f.name.split("_")[0] for f in folder_path.iterdir() if f.is_file()],symbol_number)
    return output




strategys = get_strategys(rand_pick_symbol(symbol_number=10))

# 3. Setup Portfolio Manager & BackTester
pfm = PortfolioManagement(config=PortfolioConfig(initial_capital=10000.0, leverage=2.0))
pfm.register_strategies(strategys)

bt = BackTester(manager=pfm)
bt.generate_report()
bt.print_metrics()
bt.plot_image()
