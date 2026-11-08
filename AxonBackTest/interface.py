from dataclasses import dataclass, field

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


@dataclass
class PortfolioSimulationContext:
    """Encapsulates running cash and accumulated friction state during simulation."""

    cash: float
    cum_realized_pnl: float = 0.0
    cum_fee: float = 0.0
    cum_slippage: float = 0.0
    cum_tax: float = 0.0
    cum_friction: float = 0.0
