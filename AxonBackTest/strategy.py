"""
Strategy Module for AxonBackTest.

Represents an asset's market data combined with its target exposure over time.
Adopts a Target Position (State-driven) architecture.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Union, List, Any
import pandas as pd
from . import config


class Strategy:
    """
    Strategy container representing an instrument's market data and target positions over time.
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
        Validates and ingests strategy data.
        Required columns: Open, Close, Position.
        Index or column must provide valid timestamp information.
        Automatically calculates bar-by-bar PositionChange.
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty.")

        working_df = df.copy()

        # Handle Datetime index
        if "Datetime" in working_df.columns:
            working_df["Datetime"] = pd.to_datetime(working_df["Datetime"])
            working_df.set_index("Datetime", inplace=True)
        elif not isinstance(working_df.index, pd.DatetimeIndex):
            try:
                working_df.index = pd.to_datetime(working_df.index)
            except Exception as e:
                raise ValueError(
                    "DataFrame index must be a valid DatetimeIndex or contain a 'Datetime' column."
                ) from e

        # Ensure index name is standardized
        working_df.index.name = "Datetime"

        # Validate required columns
        required_cols = {"Open", "Close", "Position"}
        missing_cols = required_cols - set(working_df.columns)
        if missing_cols:
            raise ValueError(f"Strategy data missing required columns: {missing_cols}")

        # Ensure numeric types
        working_df["Open"] = working_df["Open"].astype(float)
        working_df["Close"] = working_df["Close"].astype(float)
        working_df["Position"] = working_df["Position"].astype(float)

        # Calculate position change: first bar is the initial position itself
        working_df["PositionChange"] = (
            working_df["Position"].diff().fillna(working_df["Position"])
        )

        self.df = working_df

    def load_data_from_csv(self, file_path: Optional[str] = None) -> None:
        """
        Loads market and order data from a CSV file.
        Uses file_path if provided, otherwise defaults to config.history_data_path.
        """
        target_path = file_path or self.config.history_data_path
        if not target_path or not os.path.exists(target_path):
            raise FileNotFoundError(f"Strategy data file not found: {target_path}")

        raw_df = pd.read_csv(target_path)
        self.set_data(raw_df)

    def load_data_from_pd(self, df: pd.DataFrame) -> None:
        """
        Backward-compatible helper to inject a DataFrame.
        """
        self.set_data(df)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def positions(self) -> pd.Series:
        """Returns the target position time series."""
        return self.df["Position"] if not self.df.empty else pd.Series(dtype=float)

    @property
    def position_changes(self) -> pd.Series:
        """Returns the position change (trade delta) time series."""
        return self.df["PositionChange"] if not self.df.empty else pd.Series(dtype=float)

    @property
    def open_prices(self) -> pd.Series:
        """Returns the bar open prices time series."""
        return self.df["Open"] if not self.df.empty else pd.Series(dtype=float)

    @property
    def close_prices(self) -> pd.Series:
        """Returns the bar close prices time series."""
        return self.df["Close"] if not self.df.empty else pd.Series(dtype=float)

    @property
    def signals(self) -> List[Any]:
        """Backward-compatibility: returns signals or positions list."""
        if not self.df.empty and "Action" in self.df.columns:
            return self.df["Action"].tolist()
        elif not self.df.empty and "Position" in self.df.columns:
            return self.df["Position"].tolist()
        return []
