"""
AxonBackTest Configuration Module
Institutional-grade, strictly typed configuration architecture for quantitative backtesting.
Supports multiple asset classes, granular slippage models, multi-dimensional transaction costs,
and pre-configured turnkey templates.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import math
from typing import Optional, Dict, Any, Union


class AssetClass(str, Enum):
    """Financial asset class enumeration."""

    FUTURES = "FUTURES"
    CRYPTO_PERPETUAL = "CRYPTO_PERPETUAL"
    CRYPTO_SPOT = "CRYPTO_SPOT"
    EQUITY = "EQUITY"
    FOREX = "FOREX"


class OrderSide(str, Enum):
    """Order direction enumeration."""

    BUY = "BUY"
    SELL = "SELL"


class SlippageType(str, Enum):
    """Slippage calculation model enumeration."""

    PERCENTAGE = (
        "PERCENTAGE"  # Price drift proportional to base price (e.g., 0.0005 = 0.05%)
    )
    FIXED_POINTS = "FIXED_POINTS"  # Absolute index points (e.g., 1.0 point for Taiwan Index Futures)
    FIXED_TICKS = (
        "FIXED_TICKS"  # Number of minimum price increments (ticks * tick_size)
    )
    ZERO = "ZERO"  # Idealized zero slippage


class FeeType(str, Enum):
    """Brokerage fee / commission model enumeration."""

    PERCENTAGE = "PERCENTAGE"  # Turnover * rate (e.g., 0.0005 = 5 bps taker fee)
    FIXED_PER_UNIT = "FIXED_PER_UNIT"  # Fixed commission per contract / lot (e.g., 50 TWD per contract)
    ZERO = "ZERO"  # Zero commission


class TaxType(str, Enum):
    """Government transaction tax model enumeration."""

    PERCENTAGE = "PERCENTAGE"  # Turnover * rate (e.g., 0.00002 for Taiwan futures tax)
    FIXED_PER_UNIT = "FIXED_PER_UNIT"  # Fixed tax per contract / lot
    ZERO = "ZERO"  # Tax-exempt (e.g., Cryptocurrencies)


class TaxSide(str, Enum):
    """Transaction tax application rule."""

    BOTH = "BOTH"  # Levied on both opening and closing (Buy and Sell)
    SELL_ONLY = "SELL_ONLY"  # Levied strictly on Sell orders (e.g., Stock transactions)
    CLOSE_ONLY = "CLOSE_ONLY"  # Levied strictly when closing positions


@dataclass
class SlippageConfig:
    """Configuration and calculation model for price execution slippage."""

    slippage_type: SlippageType = SlippageType.PERCENTAGE
    value: float = 0.0005

    def __post_init__(self):
        if isinstance(self.slippage_type, str):
            self.slippage_type = SlippageType(self.slippage_type)
        if self.value < 0:
            raise ValueError(f"Slippage value cannot be negative: {self.value}")

    def calculate_execution_price(
        self, base_price: float, side: Union[OrderSide, str], tick_size: float = 1.0
    ) -> float:
        """
        Calculates executed price after applying directional slippage.
        Buy orders execute higher (base_price + slippage).
        Sell orders execute lower (base_price - slippage).
        """
        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()
        if side_str in ["BUY", "BUY_TO_COVER", "LONG"]:
            sign = 1.0
        elif side_str in ["SELL", "SHORT", "SELL_SHORT"]:
            sign = -1.0
        else:
            raise ValueError(f"Unrecognized order side: {side}")

        if self.slippage_type == SlippageType.PERCENTAGE:
            exec_price = base_price * (1.0 + sign * self.value)
        elif self.slippage_type == SlippageType.FIXED_POINTS:
            exec_price = base_price + (sign * self.value)
        elif self.slippage_type == SlippageType.FIXED_TICKS:
            exec_price = base_price + (sign * self.value * tick_size)
        elif self.slippage_type == SlippageType.ZERO:
            exec_price = base_price
        else:
            raise ValueError(f"Unsupported slippage type: {self.slippage_type}")

        return max(0.0, exec_price)


@dataclass
class FeeConfig:
    """Configuration and calculation model for brokerage commission fees."""

    fee_type: FeeType = FeeType.PERCENTAGE
    rate: float = 0.0005
    min_fee: float = 0.0

    def __post_init__(self):
        if isinstance(self.fee_type, str):
            self.fee_type = FeeType(self.fee_type)
        if self.rate < 0:
            raise ValueError(f"Fee rate cannot be negative: {self.rate}")
        if self.min_fee < 0:
            raise ValueError(f"Minimum fee cannot be negative: {self.min_fee}")

    def calculate_fee(self, turnover: float, quantity: float) -> float:
        """Calculates commission fee amount given turnover and trade quantity."""
        if self.fee_type == FeeType.PERCENTAGE:
            fee = turnover * self.rate
        elif self.fee_type == FeeType.FIXED_PER_UNIT:
            fee = quantity * self.rate
        elif self.fee_type == FeeType.ZERO:
            fee = 0.0
        else:
            raise ValueError(f"Unsupported fee type: {self.fee_type}")

        return max(self.min_fee, fee)


@dataclass
class TaxConfig:
    """Configuration and calculation model for government transaction taxes."""

    tax_type: TaxType = TaxType.ZERO
    rate: float = 0.0
    tax_side: TaxSide = TaxSide.BOTH

    def __post_init__(self):
        if isinstance(self.tax_type, str):
            self.tax_type = TaxType(self.tax_type)
        if isinstance(self.tax_side, str):
            self.tax_side = TaxSide(self.tax_side)
        if self.rate < 0:
            raise ValueError(f"Tax rate cannot be negative: {self.rate}")

    def calculate_tax(
        self,
        turnover: float,
        quantity: float,
        side: Union[OrderSide, str],
        is_close: bool = False,
    ) -> float:
        """Calculates government transaction tax considering trade side rules."""
        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()
        is_sell = side_str in ["SELL", "SHORT", "SELL_SHORT"]

        if self.tax_side == TaxSide.SELL_ONLY and not is_sell:
            return 0.0
        if self.tax_side == TaxSide.CLOSE_ONLY and not is_close:
            return 0.0

        if self.tax_type == TaxType.PERCENTAGE:
            return turnover * self.rate
        elif self.tax_type == TaxType.FIXED_PER_UNIT:
            return quantity * self.rate
        elif self.tax_type == TaxType.ZERO:
            return 0.0
        else:
            raise ValueError(f"Unsupported tax type: {self.tax_type}")


@dataclass
class TradeExecutionResult:
    """Detailed decomposition of simulated trade execution friction."""

    base_price: float
    execution_price: float
    quantity: float
    turnover: float
    slippage_cost: float
    fee_cost: float
    tax_cost: float
    total_friction: float

    @property
    def total_cost(self) -> float:
        """Total transaction friction cost (slippage + fee + tax)."""
        return self.total_friction


@dataclass
class InstrumentConfig:
    """Instrument contract specification model."""

    symbol: str
    asset_class: AssetClass = AssetClass.FUTURES
    multiplier: float = 1.0  # Contract multiplier / point value (e.g., 200 for TXF)
    tick_size: float = 0.1  # Minimum price increment
    lot_size: float = 1.0  # Step size / lot size
    min_order_qty: float = 1.0  # Minimum allowed order quantity
    currency: str = "USD"
    initial_margin_rate: float = 1.0  # 1.0 for full cash, 0.1 for 10x leverage
    maintenance_margin_rate: float = 0.05

    def __post_init__(self):
        if isinstance(self.asset_class, str):
            self.asset_class = AssetClass(self.asset_class)
        if self.multiplier <= 0:
            raise ValueError(f"Contract multiplier must be positive: {self.multiplier}")
        if self.tick_size <= 0:
            raise ValueError(f"Tick size must be positive: {self.tick_size}")
        if self.lot_size <= 0:
            raise ValueError(f"Lot size must be positive: {self.lot_size}")
        if self.min_order_qty <= 0:
            raise ValueError(
                f"Min order quantity must be positive: {self.min_order_qty}"
            )

    def round_price(self, price: float) -> float:
        """Rounds price to the nearest tick_size increment."""
        if self.tick_size <= 0:
            return price
        steps = round(price / self.tick_size)
        return round(steps * self.tick_size, 8)

    def round_quantity(self, qty: float) -> float:
        """Rounds quantity to lot_size increments (flooring to valid lots)."""
        if self.lot_size <= 0:
            return qty
        lots = math.floor(round(qty / self.lot_size, 8))
        return round(lots * self.lot_size, 8)


@dataclass
class StrategyConfig:
    """Complete strategy execution and market configuration."""

    name: str
    instrument: InstrumentConfig
    slippage: SlippageConfig = field(default_factory=SlippageConfig)
    fee: FeeConfig = field(default_factory=FeeConfig)
    tax: TaxConfig = field(default_factory=TaxConfig)
    timeframe: str = "30m"
    history_data_path: str = "simulation/"
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def evaluate_order(
        self,
        base_price: float,
        quantity: float,
        side: Union[OrderSide, str],
        is_close: bool = False,
    ) -> TradeExecutionResult:
        """
        Evaluates full trade execution for an order:
        Applies directional slippage, calculates contract turnover, commission fee,
        government transaction tax, and total friction cost.
        """
        if quantity <= 0:
            raise ValueError(f"Order quantity must be positive: {quantity}")

        valid_qty = self.instrument.round_quantity(quantity)
        if valid_qty < self.instrument.min_order_qty:
            raise ValueError(
                f"Valid quantity {valid_qty} is below min order quantity {self.instrument.min_order_qty}"
            )

        raw_exec_price = self.slippage.calculate_execution_price(
            base_price=base_price, side=side, tick_size=self.instrument.tick_size
        )
        exec_price = self.instrument.round_price(raw_exec_price)

        turnover = exec_price * valid_qty * self.instrument.multiplier
        slippage_cost = (
            abs(exec_price - base_price) * valid_qty * self.instrument.multiplier
        )
        fee_cost = self.fee.calculate_fee(turnover=turnover, quantity=valid_qty)
        tax_cost = self.tax.calculate_tax(
            turnover=turnover, quantity=valid_qty, side=side, is_close=is_close
        )
        total_friction = slippage_cost + fee_cost + tax_cost

        return TradeExecutionResult(
            base_price=base_price,
            execution_price=exec_price,
            quantity=valid_qty,
            turnover=turnover,
            slippage_cost=slippage_cost,
            fee_cost=fee_cost,
            tax_cost=tax_cost,
            total_friction=total_friction,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes StrategyConfig to a clean dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StrategyConfig:
        """Reconstructs StrategyConfig from a dictionary."""
        data_copy = data.copy()
        if "instrument" in data_copy and isinstance(data_copy["instrument"], dict):
            data_copy["instrument"] = InstrumentConfig(**data_copy["instrument"])
        if "slippage" in data_copy and isinstance(data_copy["slippage"], dict):
            data_copy["slippage"] = SlippageConfig(**data_copy["slippage"])
        if "fee" in data_copy and isinstance(data_copy["fee"], dict):
            data_copy["fee"] = FeeConfig(**data_copy["fee"])
        if "tax" in data_copy and isinstance(data_copy["tax"], dict):
            data_copy["tax"] = TaxConfig(**data_copy["tax"])
        return cls(**data_copy)


@dataclass
class PortfolioConfig:
    """Portfolio-level capital, risk, and runtime management configuration."""

    initial_capital: float = 100000.0
    leverage: float = 1.0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    base_currency: str = "USDT"
    formal: bool = False

    def __post_init__(self):
        if self.initial_capital <= 0:
            raise ValueError(
                f"Initial capital must be positive: {self.initial_capital}"
            )
        if self.leverage <= 0:
            raise ValueError(f"Leverage must be positive: {self.leverage}")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes PortfolioConfig to a clean dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PortfolioConfig:
        """Reconstructs PortfolioConfig from a dictionary."""
        return cls(**data)


class PresetFactory:
    """

    Turnkey factory for creating institutional preset strategies.

    """

    @staticmethod
    def taiwan_index_futures(
        symbol: str = "TXF",
        name: str = "TXF_Strategy",
        slippage_points: float = 1.0,
        fee_per_lot: float = 50.0,
        tax_rate: float = 0.00002,
        timeframe: str = "30m",
        history_data_path: str = "simulation/",
    ) -> StrategyConfig:
        """
        Institutional preset for Taiwan Index Futures (TXF / 大台指).
        - Multiplier: 200 TWD per point
        - Tick Size: 1.0 point
        - Slippage: Fixed Points (default 1.0 pt)
        - Fee: Fixed per contract (default 50 TWD)
        - Tax: Percentage (0.00002 = 1/50000 on contract turnover, both sides)
        - Currency: TWD
        """
        instrument = InstrumentConfig(
            symbol=symbol,
            asset_class=AssetClass.FUTURES,
            multiplier=200.0,
            tick_size=1.0,
            lot_size=1.0,
            min_order_qty=1.0,
            currency="TWD",
        )
        slippage = SlippageConfig(
            slippage_type=SlippageType.FIXED_POINTS, value=slippage_points
        )
        fee = FeeConfig(fee_type=FeeType.FIXED_PER_UNIT, rate=fee_per_lot)
        tax = TaxConfig(
            tax_type=TaxType.PERCENTAGE, rate=tax_rate, tax_side=TaxSide.BOTH
        )
        return StrategyConfig(
            name=name,
            instrument=instrument,
            slippage=slippage,
            fee=fee,
            tax=tax,
            timeframe=timeframe,
            history_data_path=history_data_path,
        )

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
