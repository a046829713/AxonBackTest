# Specification: Universal Granular Configuration Architecture (Clean-Slate)

- **Category**: `feature`
- **Spec Path**: `spec/feature/universal_config_system.md`
- **Status**: `Approved & Implemented`

## 📋 Index / Contents
1. [1. Background & Architectural Goals](#1-background--architectural-goals)
2. [2. Target Scope & Architecture Boundaries](#2-target-scope--architecture-boundaries)
3. [3. Implementation Checklist & Detailed Blueprint](#3-implementation-checklist--detailed-blueprint)
4. [4. Validation & Verification Plan](#4-validation--verification-plan)

---

## 1. Background & Architectural Goals

### 1.1 Problem Statement & Redesign Objective
The previous configuration system in [`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py) suffered from significant structural limitations:
- Ad-hoc, unstructured parameter dictionaries.
- CamelCase naming inconsistencies (`symbolName`, `symbolCategory`, `freq_time`).
- Single, scalar fee and slippage percentages unable to handle institutional financial instruments.

Per user requirements, we discard legacy baggage to build a clean-slate, modern, strictly-typed configuration framework optimized for:
1. **Multi-Asset Class Support**: Full support for traditional futures (e.g., Taiwan Index Futures - TXF) and cryptocurrencies (e.g., BTC/USDT Perpetual/Spot).
2. **First-Class Instrument Specifications**: Native modeling of point value / contract multiplier (`multiplier`), minimum price tick (`tick_size`), lot sizing (`lot_size`), and margin requirements.
3. **Three Core Friction Costs (Separated & Flexible)**:
   - **Slippage**: Price execution deviation (Fixed Percentage, Fixed Points, Fixed Ticks, Zero).
   - **Fee / Commission**: Brokerage transaction cost (Percentage of turnover, Fixed amount per lot/contract, Zero).
   - **Tax**: Government transaction tax (Turnover percentage, Fixed per lot, Zero) with flexible side application (Both sides, Sell/Close only).
4. **Institutional Execution Decomposition**: Encapsulated evaluation producing a detailed cost breakdown (`TradeExecutionResult`).
5. **Turnkey Presets**: Pre-configured factories for Taiwan Index Futures (`TXF`) and Bitcoin Perpetual (`BTCUSDT`).

### 1.2 Current vs. Expected Architecture
| Dimension | Legacy Architecture | New Clean-Slate Architecture |
| :--- | :--- | :--- |
| **Naming Convention** | Mixed camelCase and snake_case | 100% PEP 8 compliant `snake_case` dataclasses |
| **Asset Class Model** | Primitive string (`"FUTURES"`) | Strongly typed `AssetClass` Enum (`FUTURES`, `CRYPTO_PERPETUAL`, `CRYPTO_SPOT`, `EQUITY`, `FOREX`) |
| **Slippage Modeling** | Single float `slippage_percent` | `SlippageConfig` supporting `PERCENTAGE`, `FIXED_POINTS`, `FIXED_TICKS`, and `ZERO` |
| **Fee Modeling** | Flat float `fee_percent` | `FeeConfig` supporting `PERCENTAGE` (turnover bps), `FIXED_PER_UNIT` (per lot), minimum floor |
| **Tax Modeling** | Not supported (0%) | `TaxConfig` supporting `PERCENTAGE` (turnover tax rate), side rules (`BOTH`, `SELL_ONLY`, `CLOSE_ONLY`) |
| **Contract Multiplier** | Absent (implicitly assumed 1.0) | `multiplier` in `InstrumentConfig` (e.g., TXF = 200 TWD/point, BTC = 1.0) |
| **Cost Computation** | Scattered arithmetic in backtester | Unified method `calculate_execution(...)` producing `TradeExecutionResult` |
| **Presets** | None | `PresetFactory` providing one-line constructors for TXF and BTC |

---

## 2. Target Scope & Architecture Boundaries

### 2.1 File & Module Scope Matrix
| Index | Target File & Line | Scope | Planned Action |
| :---: | :--- | :---: | :--- |
| **Item 1** | [`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py) | **In-Scope** | Complete clean-slate rewrite with typed dataclasses, enums, calculation engine, presets, and serialization. |
| **Item 2** | [`tests/test_config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/tests/test_config.py) | **In-Scope (NEW)** | Comprehensive verification test suite using project virtual environment interpreter. |
| **Item 3** | [`AxonBackTest/strategy.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/strategy.py) | **Out-of-Scope** | Will be adapted in a subsequent engine integration spec. |
| **Item 4** | [`AxonBackTest/backtester.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/backtester.py) | **Out-of-Scope** | Will be adapted in a subsequent engine integration spec. |

### 2.2 Architectural Boundaries & Non-Goals
- **In-Scope Boundaries**:
  - Pure Python standard library implementation (`dataclasses`, `enum`, `typing`, `math`). Zero third-party dependency additions.
  - Independent cost modules: `SlippageConfig`, `FeeConfig`, `TaxConfig`.
  - Aggregated cost evaluator returning `TradeExecutionResult`.
  - Instrument contract specification: `InstrumentConfig`.
  - Strategy & Portfolio management configurations: `StrategyConfig`, `PortfolioConfig`.
  - Presets: `PresetFactory.taiwan_index_futures()` and `PresetFactory.crypto_perpetual()`.
  - Full dictionary serialization (`to_dict()`) and deserialization (`from_dict()`).
- **Out-of-Scope (Non-Goals)**:
  - Modifying the backtester execution loop (matching engine will consume this new config in a dedicated engine spec).
  - L2 order-book queue simulation.

---

## 3. Implementation Checklist & Detailed Blueprint

### 3.1 Step-by-Step Task Checklist
- [x] **Step 1: Enums & Core Types**
  - [x] `AssetClass`: `FUTURES`, `CRYPTO_PERPETUAL`, `CRYPTO_SPOT`, `EQUITY`, `FOREX`
  - [x] `OrderSide`: `BUY`, `SELL`
  - [x] `SlippageType`: `PERCENTAGE`, `FIXED_POINTS`, `FIXED_TICKS`, `ZERO`
  - [x] `FeeType`: `PERCENTAGE`, `FIXED_PER_UNIT`, `ZERO`
  - [x] `TaxType`: `PERCENTAGE`, `FIXED_PER_UNIT`, `ZERO`
  - [x] `TaxSide`: `BOTH`, `SELL_ONLY`, `CLOSE_ONLY`
- [x] **Step 2: Slippage Module (`SlippageConfig`)**
  - [x] Execution price calculation:
    - `PERCENTAGE`: $P \times (1 + \text{sign} \times \text{value})$
    - `FIXED_POINTS`: $P + \text{sign} \times \text{value}$
    - `FIXED_TICKS`: $P + \text{sign} \times (\text{value} \times \text{tick\_size})$
    - `ZERO`: $P$
  - [x] Calculation of absolute slippage loss.
- [x] **Step 3: Fee Module (`FeeConfig`)**
  - [x] Commission calculation:
    - `PERCENTAGE`: $\max(\text{min\_fee}, \text{turnover} \times \text{rate})$
    - `FIXED_PER_UNIT`: $\max(\text{min\_fee}, \text{quantity} \times \text{rate})$
    - `ZERO`: $0.0$
- [x] **Step 4: Tax Module (`TaxConfig`)**
  - [x] Government transaction tax calculation:
    - Side filter (`BOTH`, `SELL_ONLY`, `CLOSE_ONLY`).
    - `PERCENTAGE`: $\text{turnover} \times \text{rate}$ (e.g. Taiwan futures $0.00002$).
    - `FIXED_PER_UNIT`: $\text{quantity} \times \text{rate}$.
    - `ZERO`: $0.0$.
- [x] **Step 5: Composite Execution Result (`TradeExecutionResult`)**
  - [x] Holds `base_price`, `execution_price`, `quantity`, `turnover`, `slippage_cost`, `fee_cost`, `tax_cost`, `total_friction`, `net_cash_impact`.
- [x] **Step 6: Instrument Specification (`InstrumentConfig`)**
  - [x] `symbol`, `asset_class`, `multiplier`, `tick_size`, `lot_size`, `min_order_qty`, `currency`, `initial_margin_rate`, `maintenance_margin_rate`.
  - [x] `round_price(price)` and `round_quantity(qty)`.
- [x] **Step 7: Strategy & Portfolio Configurations**
  - [x] `StrategyConfig`: integrates `name`, `instrument`, `slippage`, `fee`, `tax`, `timeframe`, `data_path`, `extra_params`.
  - [x] Evaluator method: `evaluate_order(base_price, quantity, side, is_close)` -> `TradeExecutionResult`.
  - [x] `PortfolioConfig`: `initial_capital`, `leverage`, `start_date`, `end_date`, `risk_free_rate`, `base_currency`.
- [x] **Step 8: Factory Presets (`PresetFactory`)**
  - [x] `PresetFactory.taiwan_index_futures()` (TXF: multiplier 200, tick 1.0, slippage 1.0 pt, fee 50 TWD, tax 0.00002).
  - [x] `PresetFactory.crypto_perpetual()` (BTCUSDT: multiplier 1.0, tick 0.1, slippage 0.05%, fee 0.05%, tax 0.0).
- [x] **Step 9: Serialization**
  - [x] `to_dict()` and `from_dict()` on all dataclasses.

### 3.2 Detailed Code Modifications Blueprint

#### 3.2.1 Architecture Blueprint for [`AxonBackTest/config.py`](file:///home/b0457812963/AxonBackTest/AxonBackTest/AxonBackTest/config.py)

```python
"""
AxonBackTest Configuration Module
A modular, strictly-typed configuration system for quantitative backtesting.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import math
from typing import Optional, Dict, Any, Union


class AssetClass(str, Enum):
    FUTURES = "FUTURES"
    CRYPTO_PERPETUAL = "CRYPTO_PERPETUAL"
    CRYPTO_SPOT = "CRYPTO_SPOT"
    EQUITY = "EQUITY"
    FOREX = "FOREX"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SlippageType(str, Enum):
    PERCENTAGE = "PERCENTAGE"       # Relative % of price (e.g., 0.0005 for 0.05%)
    FIXED_POINTS = "FIXED_POINTS"   # Absolute price points (e.g., 1.0 pt for TXF)
    FIXED_TICKS = "FIXED_TICKS"     # Number of minimum ticks (ticks * tick_size)
    ZERO = "ZERO"                   # No slippage


class FeeType(str, Enum):
    PERCENTAGE = "PERCENTAGE"       # Turnover * rate (e.g., 0.0005)
    FIXED_PER_UNIT = "FIXED_PER_UNIT" # Fixed commission per unit/lot (e.g., 50 TWD)
    ZERO = "ZERO"                   # No commission


class TaxType(str, Enum):
    PERCENTAGE = "PERCENTAGE"       # Turnover * rate (e.g., 0.00002 for Taiwan futures)
    FIXED_PER_UNIT = "FIXED_PER_UNIT" # Fixed tax per unit/lot
    ZERO = "ZERO"                   # Tax-exempt (e.g., Crypto)


class TaxSide(str, Enum):
    BOTH = "BOTH"                   # Charged on both Buy and Sell
    SELL_ONLY = "SELL_ONLY"         # Charged only on Sell (e.g., Stock transactions)
    CLOSE_ONLY = "CLOSE_ONLY"       # Charged only when closing a position


@dataclass
class SlippageConfig:
    slippage_type: SlippageType = SlippageType.PERCENTAGE
    value: float = 0.0005

    def calculate_execution_price(self, base_price: float, side: Union[OrderSide, str], tick_size: float = 1.0) -> float:
        """
        Calculates execution price after applying directional slippage.
        Buy orders slip upwards; Sell orders slip downwards.
        """
        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()
        sign = 1.0 if side_str in ["BUY", "BUY_TO_COVER", "LONG"] else -1.0

        if self.slippage_type == SlippageType.PERCENTAGE:
            exec_price = base_price * (1.0 + sign * self.value)
        elif self.slippage_type == SlippageType.FIXED_POINTS:
            exec_price = base_price + (sign * self.value)
        elif self.slippage_type == SlippageType.FIXED_TICKS:
            exec_price = base_price + (sign * self.value * tick_size)
        elif self.slippage_type == SlippageType.ZERO:
            exec_price = base_price
        else:
            raise ValueError(f"Unknown slippage type: {self.slippage_type}")

        return max(0.0, exec_price)


@dataclass
class FeeConfig:
    fee_type: FeeType = FeeType.PERCENTAGE
    rate: float = 0.0005
    min_fee: float = 0.0

    def calculate_fee(self, turnover: float, quantity: float) -> float:
        """
        Calculates brokerage commission.
        """
        if self.fee_type == FeeType.PERCENTAGE:
            fee = turnover * self.rate
        elif self.fee_type == FeeType.FIXED_PER_UNIT:
            fee = quantity * self.rate
        elif self.fee_type == FeeType.ZERO:
            fee = 0.0
        else:
            raise ValueError(f"Unknown fee type: {self.fee_type}")

        return max(self.min_fee, fee)


@dataclass
class TaxConfig:
    tax_type: TaxType = TaxType.ZERO
    rate: float = 0.0
    tax_side: TaxSide = TaxSide.BOTH

    def calculate_tax(self, turnover: float, quantity: float, side: Union[OrderSide, str], is_close: bool = False) -> float:
        """
        Calculates government transaction tax.
        """
        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()
        is_sell = side_str in ["SELL", "SHORT"]

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
            raise ValueError(f"Unknown tax type: {self.tax_type}")


@dataclass
class TradeExecutionResult:
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
        """Alias for total friction cost (slippage + fee + tax)."""
        return self.total_friction


@dataclass
class InstrumentConfig:
    symbol: str
    asset_class: AssetClass = AssetClass.FUTURES
    multiplier: float = 1.0           # Contract multiplier / point value (e.g., 200 for TXF)
    tick_size: float = 0.1            # Minimum price increment
    lot_size: float = 1.0             # Minimum order step size
    min_order_qty: float = 1.0        # Minimum allowed order quantity
    currency: str = "USD"
    initial_margin_rate: float = 1.0  # 1.0 for unleveraged, 0.1 for 10x leverage
    maintenance_margin_rate: float = 0.05

    def round_price(self, price: float) -> float:
        """Rounds price to nearest tick_size."""
        if self.tick_size <= 0:
            return price
        return round(round(price / self.tick_size) * self.tick_size, 8)

    def round_quantity(self, qty: float) -> float:
        """Rounds quantity to lot_size increments."""
        if self.lot_size <= 0:
            return qty
        return round(math.floor(qty / self.lot_size) * self.lot_size, 8)


@dataclass
class StrategyConfig:
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
        is_close: bool = False
    ) -> TradeExecutionResult:
        """
        Evaluates complete execution for an order:
        calculates execution price with slippage, contract turnover, fee, and tax.
        """
        valid_qty = self.instrument.round_quantity(quantity)
        exec_price = self.slippage.calculate_execution_price(base_price, side, self.instrument.tick_size)
        exec_price = self.instrument.round_price(exec_price)

        turnover = exec_price * valid_qty * self.instrument.multiplier
        slippage_cost = abs(exec_price - base_price) * valid_qty * self.instrument.multiplier
        fee_cost = self.fee.calculate_fee(turnover, valid_qty)
        tax_cost = self.tax.calculate_tax(turnover, valid_qty, side, is_close=is_close)
        total_friction = slippage_cost + fee_cost + tax_cost

        return TradeExecutionResult(
            base_price=base_price,
            execution_price=exec_price,
            quantity=valid_qty,
            turnover=turnover,
            slippage_cost=slippage_cost,
            fee_cost=fee_cost,
            tax_cost=tax_cost,
            total_friction=total_friction
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StrategyConfig:
        data = data.copy()
        if "instrument" in data and isinstance(data["instrument"], dict):
            data["instrument"] = InstrumentConfig(**data["instrument"])
        if "slippage" in data and isinstance(data["slippage"], dict):
            data["slippage"] = SlippageConfig(**data["slippage"])
        if "fee" in data and isinstance(data["fee"], dict):
            data["fee"] = FeeConfig(**data["fee"])
        if "tax" in data and isinstance(data["tax"], dict):
            data["tax"] = TaxConfig(**data["tax"])
        return cls(**data)


@dataclass
class PortfolioConfig:
    initial_capital: float = 100000.0
    leverage: float = 1.0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    risk_free_rate: float = 0.02
    base_currency: str = "USD"
    max_active_positions: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PortfolioConfig:
        return cls(**data)


class PresetFactory:
    """
    Convenience factory generating pre-configured strategies for standard assets.
    """

    @staticmethod
    def taiwan_index_futures(
        symbol: str = "TXF",
        name: str = "TXF_Strategy",
        slippage_points: float = 1.0,
        fee_per_lot: float = 50.0,
        tax_rate: float = 0.00002,
        timeframe: str = "30m",
        history_data_path: str = "simulation/"
    ) -> StrategyConfig:
        """
        Preset for Taiwan Index Futures (TXF / 大台指).
        - Multiplier: 200 TWD per point
        - Tick Size: 1.0 point
        - Slippage: Fixed Points (default 1.0 point)
        - Fee: Fixed per contract (default 50 TWD)
        - Tax: Percentage (0.00002 = 1/50000 of contract value, both buy/sell)
        """
        instrument = InstrumentConfig(
            symbol=symbol,
            asset_class=AssetClass.FUTURES,
            multiplier=200.0,
            tick_size=1.0,
            lot_size=1.0,
            min_order_qty=1.0,
            currency="TWD"
        )
        slippage = SlippageConfig(
            slippage_type=SlippageType.FIXED_POINTS,
            value=slippage_points
        )
        fee = FeeConfig(
            fee_type=FeeType.FIXED_PER_UNIT,
            rate=fee_per_lot
        )
        tax = TaxConfig(
            tax_type=TaxType.PERCENTAGE,
            rate=tax_rate,
            tax_side=TaxSide.BOTH
        )
        return StrategyConfig(
            name=name,
            instrument=instrument,
            slippage=slippage,
            fee=fee,
            tax=tax,
            timeframe=timeframe,
            history_data_path=history_data_path
        )

    @staticmethod
    def crypto_perpetual(
        symbol: str = "BTCUSDT",
        name: str = "BTCUSDT_Perp_Strategy",
        slippage_pct: float = 0.0005,
        fee_pct: float = 0.0005,
        timeframe: str = "30m",
        history_data_path: str = "simulation/"
    ) -> StrategyConfig:
        """
        Preset for Crypto Perpetual Contracts (BTCUSDT Linear Perp).
        - Multiplier: 1.0 (USDT-margined)
        - Tick Size: 0.1 USDT
        - Lot Size: 0.001 BTC
        - Slippage: Percentage (default 0.05% / 5 bps)
        - Fee: Percentage (default 0.05% / 5 bps taker fee)
        - Tax: Zero (tax-exempt)
        """
        instrument = InstrumentConfig(
            symbol=symbol,
            asset_class=AssetClass.CRYPTO_PERPETUAL,
            multiplier=1.0,
            tick_size=0.1,
            lot_size=0.001,
            min_order_qty=0.001,
            currency="USDT"
        )
        slippage = SlippageConfig(
            slippage_type=SlippageType.PERCENTAGE,
            value=slippage_pct
        )
        fee = FeeConfig(
            fee_type=FeeType.PERCENTAGE,
            rate=fee_pct
        )
        tax = TaxConfig(
            tax_type=TaxType.ZERO,
            rate=0.0
        )
        return StrategyConfig(
            name=name,
            instrument=instrument,
            slippage=slippage,
            fee=fee,
            tax=tax,
            timeframe=timeframe,
            history_data_path=history_data_path
        )
```

---

## 4. Validation & Verification Plan

### 4.1 Verification Environment & Commands
> [!IMPORTANT]
> All executions MUST adhere to repository environment standards using the virtual environment interpreter:
> Absolute path: `/home/b0457812963/AxonBackTest/bin/python`
> Relative path: `../bin/python`

```bash
# Verification command:
../bin/python -m unittest tests/test_config.py
```

### 4.2 Acceptance Verification Checklist
- [x] **1. Slippage Accuracy**:
  - [x] `PERCENTAGE`: Base price $10,000, 0.05% slippage -> Buy = $10,005.0, Sell = $9,995.0.
  - [x] `FIXED_POINTS`: Base price 20,000 pts, 1.0 pt slippage -> Buy = 20,001.0, Sell = 19,999.0.
  - [x] `FIXED_TICKS`: Base price 20,000 pts, tick_size 1.0, 2 ticks -> Buy = 20,002.0, Sell = 19,998.0.
  - [x] `ZERO`: Execution price equals base price.
- [x] **2. Fee Calculation**:
  - [x] `PERCENTAGE`: Turnover 100,000 * 0.0005 = 50.0. Min fee check if turnover is small.
  - [x] `FIXED_PER_UNIT`: 2 contracts * 50 TWD = 100.0 TWD.
  - [x] `ZERO`: Fee = 0.0.
- [x] **3. Tax Calculation**:
  - [x] `PERCENTAGE`: Turnover 4,000,000 * 0.00002 = 80.0 TWD.
  - [x] Side sensitivity: `SELL_ONLY` exempts Buy orders from tax.
  - [x] `ZERO`: Tax = 0.0.
- [x] **4. Comprehensive Execution Decomposition (`evaluate_order`)**:
  - [x] **Taiwan Index Futures (TXF)**:
    - Base price: 20,000 pts, Quantity: 1 lot, Buy order.
    - Multiplier: 200 TWD/pt.
    - Slippage: 1.0 point -> Executed price: 20,001.0.
    - Turnover: 20,001.0 * 1 * 200 = 4,000,200 TWD.
    - Slippage cost: 1.0 * 1 * 200 = 200 TWD.
    - Fee cost: 50 TWD.
    - Tax cost: 4,000,200 * 0.00002 = 80.004 TWD.
    - Total friction: 330.004 TWD.
  - [x] **Crypto Perpetual (BTCUSDT)**:
    - Base price: 60,000 USDT, Quantity: 1.5 BTC, Buy order.
    - Multiplier: 1.0.
    - Slippage: 0.05% -> Executed price: 60,030.0 USDT.
    - Turnover: 60,030.0 * 1.5 = 90,045.0 USDT.
    - Slippage cost: 30.0 * 1.5 = 45.0 USDT.
    - Fee cost: 90,045.0 * 0.0005 = 45.0225 USDT.
    - Tax cost: 0.0 USDT.
    - Total friction: 90.0225 USDT.
- [x] **5. Factory Presets**:
  - [x] `PresetFactory.taiwan_index_futures()` generates valid TXF config with multiplier 200, tick 1.0.
  - [x] `PresetFactory.crypto_perpetual()` generates valid BTCUSDT config with multiplier 1.0, tick 0.1.
- [x] **6. Serialization**:
  - [x] `StrategyConfig.to_dict()` and `from_dict()` round-trip preserves all nested configurations without data loss.
