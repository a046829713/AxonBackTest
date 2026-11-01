"""
PortfolioTrader Module for AxonBackTest.

Institutional-grade, multi-asset portfolio management and backtesting engine.
Adopts a Target Position (State-driven) architecture with exact transaction friction modeling,
vectorized multi-asset time alignment, and mark-to-market NAV accounting.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd
from AxonBackTest import config
from AxonBackTest.config import OrderSide
from AxonBackTest.strategy import Strategy


@dataclass
class PositionState:
    """Tracks running execution and position state for a single strategy."""

    strategy_name: str
    symbol: str
    quantity: float = 0.0
    avg_entry_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_fee: float = 0.0
    total_slippage: float = 0.0
    total_tax: float = 0.0
    total_trades: int = 0


class PortfolioManagement:
    """
    Portfolio Management and Backtesting Orchestrator.

    Coordinates multi-asset target position rebalancing, order execution friction modeling,
    mark-to-market equity tracking, and performance reporting.
    """

    def __init__(
        self,
        config: Optional[config.PortfolioConfig] = None,
        formal: bool = False,
    ):
        self.config: config.PortfolioConfig = config if config is not None else config.PortfolioConfig()
        self.strategys: List[Strategy] = []
        self.formal: bool = formal

        self.min_scale: Optional[pd.DatetimeIndex] = None
        self.data: Optional[Dict[Any, Any]] = None
        self.report: Optional[List[Dict[str, Any]]] = None
        self.report_df: Optional[pd.DataFrame] = None
        self.metrics: Dict[str, Any] = {}
        self.trades: List[Dict[str, Any]] = []
        self.position_states: Dict[str, PositionState] = {}

    @property
    def strategies(self) -> List[Strategy]:
        """Convenience accessor for registered strategies."""
        return self.strategys

    @strategies.setter
    def strategies(self, val: List[Strategy]) -> None:
        self.strategys = val

    @property
    def parameter_info(self) -> Dict[str, Any]:
        """Configuration parameters snapshot for auditing and reporting."""
        return {
            "initial_capital": self.config.initial_capital,
            "leverage": self.config.leverage,
            "strategies_count": len(self.strategys),
            "base_currency": self.config.base_currency,
            "formal": self.formal,
        }

    def activate(self) -> None:
        """Activates and validates portfolio settings."""
        self._validate_settings()

    def _validate_settings(self) -> None:
        """Validates portfolio runtime settings."""
        if self.config.initial_capital <= 0:
            raise ValueError(f"Initial capital must be positive: {self.config.initial_capital}")
        if self.config.leverage <= 0:
            raise ValueError(f"Leverage must be positive: {self.config.leverage}")

    def register_strategys(self, strategys: Union[List[Strategy], Strategy]) -> None:
        """Registers one or more Strategy instances into the portfolio."""
        if isinstance(strategys, list):
            self.strategys.extend(strategys)
        elif isinstance(strategys, Strategy):
            self.strategys.append(strategys)

    def register_strategies(self, strategies: Union[List[Strategy], Strategy]) -> None:
        """Standardized English alias for register_strategys."""
        self.register_strategys(strategies)

    def time_min_scale(self) -> pd.DatetimeIndex:
        """
        Extracts, deduplicates, and sorts the unified datetime timeline across all registered strategies.
        """
        all_datetimes = set()
        for strategy in self.strategys:
            if not strategy.df.empty:
                all_datetimes.update(strategy.df.index)

        sorted_times = sorted(all_datetimes)
        self.min_scale = pd.DatetimeIndex(sorted_times)
        return self.min_scale

    def get_data(self) -> Dict[pd.Timestamp, Dict[str, Optional[Dict[str, Any]]]]:
        """
        Aligns market data across all strategies indexed by timestamp.
        Optimized with unified DatetimeIndex reindexing for high performance.
        """
        if self.min_scale is None:
            self.time_min_scale()

        strategy_records = {}
        for s in self.strategys:
            reindexed = s.df.reindex(self.min_scale)
            strategy_records[s.strategyName] = reindexed.to_dict(orient="index")

        data: Dict[pd.Timestamp, Dict[str, Optional[Dict[str, Any]]]] = {}
        for ts in self.min_scale:
            data[ts] = {
                name: strategy_records[name].get(ts)
                for name in strategy_records
            }

        self.data = data
        return data

    def _align_market_arrays(self) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Pre-extracts aligned NumPy arrays for Open, Close, and Position for zero-overhead bar iteration.
        """
        aligned_data: Dict[str, Dict[str, np.ndarray]] = {}
        for s in self.strategys:
            reindexed = s.df.reindex(self.min_scale)
            # Forward-fill position to preserve target exposure across sparse bars, default to 0.0
            pos_series = reindexed["Position"].ffill().fillna(0.0)
            open_series = reindexed["Open"]
            close_series = reindexed["Close"]

            aligned_data[s.strategyName] = {
                "open": open_series.to_numpy(dtype=float),
                "close": close_series.to_numpy(dtype=float),
                "position": pos_series.to_numpy(dtype=float),
            }
        return aligned_data

    def generate_report(self) -> List[Dict[str, Any]]:
        """
        Executes the institutional backtest simulation and generates performance report records.

        Execution Protocol:
        - At bar Open: evaluate target position change (ΔQ) and execute orders at Open price with slippage and fees.
        - At bar Close: mark-to-market valuation at Close price to calculate unrealized PnL and total NAV equity.
        """
        self.activate()
        if not self.strategys:
            raise ValueError("No strategies registered in PortfolioManagement.")

        self.time_min_scale()
        if len(self.min_scale) == 0:
            raise ValueError("No market data found across registered strategies.")

        aligned_arrays = self._align_market_arrays()
        n_strategies = len(self.strategys)
        n_bars = len(self.min_scale)

        # Initialize portfolio state
        cash = float(self.config.initial_capital)
        equity = cash
        self.trades = []
        self.position_states = {
            s.strategyName: PositionState(
                strategy_name=s.strategyName,
                symbol=s.config.instrument.symbol,
            )
            for s in self.strategys
        }

        # Tracking arrays for fast vector recording
        datetimelist: List[str] = []
        timestamps: List[pd.Timestamp] = []
        equity_records = np.zeros(n_bars, dtype=float)
        cash_records = np.zeros(n_bars, dtype=float)
        unrealized_records = np.zeros(n_bars, dtype=float)
        realized_records = np.zeros(n_bars, dtype=float)
        friction_records = np.zeros(n_bars, dtype=float)
        fee_records = np.zeros(n_bars, dtype=float)
        slippage_records = np.zeros(n_bars, dtype=float)
        tax_records = np.zeros(n_bars, dtype=float)
        margin_records = np.zeros(n_bars, dtype=float)

        cum_realized_pnl = 0.0
        cum_fee = 0.0
        cum_slippage = 0.0
        cum_tax = 0.0
        cum_friction = 0.0

        # Bar-by-bar simulation loop
        for k in range(n_bars):
            ts = self.min_scale[k]
            timestamps.append(ts)
            datetimelist.append(str(ts))

            # Available capital for this bar's allocation
            prev_equity = equity
            allocated_capital = (prev_equity * self.config.leverage) / n_strategies

            # -----------------------------------------------------------
            # 1. Open Phase: Order Execution & Target Position Rebalance
            # -----------------------------------------------------------
            for s in self.strategys:
                name = s.strategyName
                state = self.position_states[name]
                inst = s.config.instrument

                curr_pos_ratio = aligned_arrays[name]["position"][k]
                prev_pos_ratio = aligned_arrays[name]["position"][k - 1] if k > 0 else None
                open_price = aligned_arrays[name]["open"][k]

                # Check if market bar exists for this instrument
                if np.isnan(open_price) or open_price <= 0:
                    continue

                # Determine if target exposure changed (or initial bar entry)
                needs_rebalance = (k == 0 and curr_pos_ratio != 0.0) or (
                    k > 0 and curr_pos_ratio != prev_pos_ratio
                )

                if needs_rebalance:
                    # Calculate target notional and contract quantity
                    if abs(curr_pos_ratio) < 1e-6:
                        target_qty = 0.0
                    else:
                        target_notional = allocated_capital * curr_pos_ratio
                        raw_target_qty = target_notional / (open_price * inst.multiplier)
                        target_qty = inst.round_quantity(raw_target_qty)
                        # If below minimum order quantity, cannot hold position
                        if abs(target_qty) < inst.min_order_qty:
                            target_qty = 0.0

                    delta_qty = target_qty - state.quantity

                    # Round delta to lot increments
                    delta_qty = inst.round_quantity(delta_qty)

                    if abs(delta_qty) >= inst.min_order_qty:
                        trade_side = OrderSide.BUY if delta_qty > 0 else OrderSide.SELL
                        trade_qty = abs(delta_qty)

                        is_close = (
                            (state.quantity > 0 and delta_qty < 0)
                            or (state.quantity < 0 and delta_qty > 0)
                        )

                        # Evaluate exact trade friction using strategy configuration
                        exec_result = s.config.evaluate_order(
                            base_price=open_price,
                            quantity=trade_qty,
                            side=trade_side,
                            is_close=is_close,
                        )

                        exec_price = exec_result.execution_price
                        fee = exec_result.fee_cost
                        slip = exec_result.slippage_cost
                        tax = exec_result.tax_cost
                        friction = exec_result.total_friction

                        cum_fee += fee
                        cum_slippage += slip
                        cum_tax += tax
                        cum_friction += friction

                        # Deduct friction immediately from cash
                        cash -= friction
                        state.total_fee += fee
                        state.total_slippage += slip
                        state.total_tax += tax
                        state.total_trades += 1

                        # Position accounting & Realized PnL settlement
                        trade_realized_pnl = 0.0
                        prev_qty = state.quantity
                        prev_avg_price = state.avg_entry_price

                        if is_close:
                            close_qty = min(abs(prev_qty), trade_qty)
                            direction = 1.0 if prev_qty > 0 else -1.0
                            trade_realized_pnl = (
                                direction
                                * (exec_price - prev_avg_price)
                                * close_qty
                                * inst.multiplier
                            )
                            cash += trade_realized_pnl
                            cum_realized_pnl += trade_realized_pnl
                            state.realized_pnl += trade_realized_pnl

                            # Check for complete flip (e.g., long to short or short to long)
                            if trade_qty > abs(prev_qty):
                                state.quantity = target_qty
                                state.avg_entry_price = exec_price
                            elif abs(target_qty) < 1e-8:
                                state.quantity = 0.0
                                state.avg_entry_price = 0.0
                            else:
                                state.quantity = target_qty
                                # Partially closed: entry price basis remains unchanged
                                state.avg_entry_price = prev_avg_price
                        else:
                            # Increasing position in current direction or opening from flat
                            new_qty = prev_qty + delta_qty
                            if abs(prev_qty) < 1e-8:
                                new_avg_price = exec_price
                            else:
                                new_avg_price = (
                                    abs(prev_qty) * prev_avg_price + trade_qty * exec_price
                                ) / abs(new_qty)
                            state.quantity = new_qty
                            state.avg_entry_price = new_avg_price

                        # Record trade execution log
                        self.trades.append(
                            {
                                "datetime": ts,
                                "strategy": name,
                                "symbol": inst.symbol,
                                "side": trade_side.value,
                                "quantity": trade_qty,
                                "base_price": open_price,
                                "exec_price": exec_price,
                                "turnover": exec_result.turnover,
                                "slippage": slip,
                                "fee": fee,
                                "tax": tax,
                                "friction": friction,
                                "realized_pnl": trade_realized_pnl,
                                "position_after": state.quantity,
                            }
                        )

            # -----------------------------------------------------------
            # 2. Close Phase: Mark-to-Market Valuation & NAV Calculation
            # -----------------------------------------------------------
            total_unrealized_pnl = 0.0
            total_margin_used = 0.0

            for s in self.strategys:
                name = s.strategyName
                state = self.position_states[name]
                inst = s.config.instrument
                close_price = aligned_arrays[name]["close"][k]

                if not np.isnan(close_price) and close_price > 0 and abs(state.quantity) > 0:
                    unrealized = (
                        state.quantity
                        * (close_price - state.avg_entry_price)
                        * inst.multiplier
                    )
                    state.unrealized_pnl = unrealized
                    total_unrealized_pnl += unrealized

                    margin = (
                        abs(state.quantity)
                        * close_price
                        * inst.multiplier
                        * inst.initial_margin_rate
                    )
                    total_margin_used += margin
                else:
                    state.unrealized_pnl = 0.0

            equity = cash + total_unrealized_pnl

            # Record bar-level metrics
            equity_records[k] = equity
            cash_records[k] = cash
            unrealized_records[k] = total_unrealized_pnl
            realized_records[k] = cum_realized_pnl
            margin_records[k] = total_margin_used
            friction_records[k] = cum_friction
            fee_records[k] = cum_fee
            slippage_records[k] = cum_slippage
            tax_records[k] = cum_tax

        # -----------------------------------------------------------
        # 3. Assemble Report DataFrame
        # -----------------------------------------------------------
        report_dict: Dict[str, Any] = {
            "datetimelist": datetimelist,
            "Datetime": timestamps,
            "CloseProfit": equity_records,  # Preserved for BackTester.plot_image compatibility
            "Equity": equity_records,
            "Cash": cash_records,
            "UnrealizedPnL": unrealized_records,
            "RealizedPnL": realized_records,
            "MarginUsed": margin_records,
            "TotalFriction": friction_records,
            "TotalFee": fee_records,
            "TotalSlippage": slippage_records,
            "TotalTax": tax_records,
        }

        # Add per-strategy position tracking columns
        for s in self.strategys:
            name = s.strategyName
            report_dict[f"pos_{name}"] = aligned_arrays[name]["position"]

        self.report_df = pd.DataFrame(report_dict)

        # -----------------------------------------------------------
        # 4. Compute Statistical Summary Performance Metrics
        # -----------------------------------------------------------
        initial_cap = float(self.config.initial_capital)
        final_equity = float(equity_records[-1])
        total_return = (final_equity - initial_cap) / initial_cap

        # Annualized CAGR (annualize only if span >= 1 day to avoid exponential explosion)
        time_span = timestamps[-1] - timestamps[0]
        total_days = time_span.total_seconds() / 86400.0
        if total_days >= 1.0 and final_equity > 0:
            cagr = (final_equity / initial_cap) ** (365.25 / total_days) - 1.0
        else:
            cagr = total_return


        # Maximum Drawdown (MDD)
        peak_series = np.maximum.accumulate(equity_records)
        drawdowns = (equity_records - peak_series) / np.maximum(peak_series, 1e-8)
        max_drawdown = float(np.min(drawdowns))
        max_drawdown_amount = float(np.min(equity_records - peak_series))

        # Bar Returns & Annualized Sharpe Ratio
        eq_series = pd.Series(equity_records)
        pct_returns = eq_series.pct_change().dropna()
        if len(pct_returns) > 1 and pct_returns.std() > 0:
            # Estimate bars per year based on average frequency
            avg_bar_seconds = time_span.total_seconds() / max(1, n_bars - 1)
            bars_per_year = (365.25 * 86400.0) / max(1.0, avg_bar_seconds)
            sharpe_ratio = float(
                np.sqrt(bars_per_year) * (pct_returns.mean() / pct_returns.std())
            )
        else:
            sharpe_ratio = 0.0

        # Trade Analytics
        total_trade_count = len(self.trades)
        closed_trades = [t for t in self.trades if t["realized_pnl"] != 0.0]
        win_trades = [t for t in closed_trades if t["realized_pnl"] > 0]
        loss_trades = [t for t in closed_trades if t["realized_pnl"] < 0]

        win_rate = len(win_trades) / len(closed_trades) if closed_trades else 0.0
        gross_profit = sum(t["realized_pnl"] for t in win_trades)
        gross_loss = abs(sum(t["realized_pnl"] for t in loss_trades))
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (float("inf") if gross_profit > 0 else 0.0)
        )

        self.metrics = {
            "initial_capital": initial_cap,
            "final_equity": round(final_equity, 4),
            "total_return": round(total_return, 6),
            "total_return_pct": f"{round(total_return * 100, 2)}%",
            "cagr": round(cagr, 6),
            "cagr_pct": f"{round(cagr * 100, 2)}%",
            "max_drawdown": round(max_drawdown, 6),
            "max_drawdown_pct": f"{round(max_drawdown * 100, 2)}%",
            "max_drawdown_amount": round(max_drawdown_amount, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "total_trades": total_trade_count,
            "closed_trades": len(closed_trades),
            "win_trades": len(win_trades),
            "loss_trades": len(loss_trades),
            "win_rate": round(win_rate, 4),
            "win_rate_pct": f"{round(win_rate * 100, 2)}%",
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else "inf",
            "total_fee": round(cum_fee, 4),
            "total_slippage": round(cum_slippage, 4),
            "total_tax": round(cum_tax, 4),
            "total_friction": round(cum_friction, 4),
        }

        # Format output record list for full backward compatibility
        self.report = self.report_df.to_dict("records")
        return self.report
