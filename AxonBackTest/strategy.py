from enum import Enum
from typing import Any, Callable
from . import config
import numpy as np
import os
import pandas as pd
from pathlib import Path


class Strategy:
    def __init__(
        self,
        config: config.StrategyConfig,
        formal: bool = False,
        generate_signals_fn: Callable[..., Any] | None = None,
        generate_postion_size_fn: Callable[..., Any] | None = None,
    ):
        self.formal = formal  # the strategy for real trader.
        self.config = config
        self.df = pd.DataFrame()
        self.signals = []
        self.postion_sizes = []
        # We can provider the signal from two ways. one is caculate from function, the other one is register_signals.
        self._generate_signals_fn = generate_signals_fn
        self._generate_postion_size_fn = generate_postion_size_fn

    def load_data_from_csv(self):
        if not os.path.exists(self.config.history_data_path):
            raise FileNotFoundError("Please check your local file path.")

        self.df = pd.read_csv(self.config.history_data_path)
        self.df.set_index("Datetime", inplace=True)

    def load_data_from_pd(self, df: pd.DataFrame):
        self.df = df

    def register_signals(self, signals: list):
        self.signals.extend(signals)

    def generate_signals(self):
        if self.df.empty:
            raise ValueError("Strategy doesn't have any data,please check.")
        self.signals.extend(self._generate_signals_fn(self.df))

        self.df["Signals"] = self.signals

    def generate_postion_sizes(self):
        if self.df.empty:
            raise ValueError("Strategy doesn't have any data,please check.")
        self.postion_sizes.extend(self._generate_postion_size_fn(self.df))
        self.df["PostionSizes"] = self.postion_sizes
