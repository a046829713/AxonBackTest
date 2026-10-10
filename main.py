import numpy as np
import pandas as pd
from AxonBackTest.PorfolioTrader import PortfolioManagement
from AxonBackTest.backtester import BackTester
from AxonBackTest.config import PortfolioConfig, PresetFactory
from AxonBackTest.strategy import Strategy
import time

def generate_fake_signals(df: pd.DataFrame):
    # This part is very important, original is order think,
    # buy We need to change thought.
    # right now is Target signal.
    # traget_signal_arrays = np.random.randint(-1, 2, size=len(self.df))

    choices = [-1, 0, 1]
    probabilities = [0.33, 0.33, 0.34]
    traget_signal_arrays = np.random.choice(choices, size=len(df), p=probabilities)
    return traget_signal_arrays


def generate_fake_postionsize(df: pd.DataFrame):
    PositionSizing_arrays = np.random.rand(len(df))
    return PositionSizing_arrays


# 1.preset all config.
BTCUSDT_strategy = Strategy(
    PresetFactory.crypto_perpetual(strategy_name="BTCUSDT-DQN-30K",
                                   history_data_path="/home/b0457812963/Mamba3RL/SynapseX/Brain/simulation/test_data/BTCUSDT-F-30-Min.csv"),
    generate_signals_fn=generate_fake_signals,
    generate_postion_size_fn=generate_fake_postionsize,
)


# 2. put strategy to PortfolioManagement
pfm = PortfolioManagement(PortfolioConfig(initial_capital=15000, formal=False))
pfm.register_strategys(BTCUSDT_strategy)


# 3.active backtest
BackTester(manager=pfm)
