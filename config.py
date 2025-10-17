class StrategyConfig:
    def __init__(self, strategy_name: str, symbol_name: str, symbol_type: str, fee_percent: float, slippage_percent: float, freq_time: int, history_data_path: str, strategy_type: str, unit: str):
        """
            strategy_type (str) :"BOTH"  "ONLYBUY "ONLYSELLSHORT"
            freq_time (int) : "30"

        """
        self.strategyName = strategy_name
        self.symbolName = symbol_name
        self.symbolType = symbol_type
        self.feePercent = fee_percent
        self.slippagePercent = slippage_percent
        self.freq_time = freq_time  # use how much sequence
        self.historyDataPath = history_data_path
        self.strategyType = strategy_type
        self.unit = unit

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class PortfolioManagementConfig:
    def __init__(self, capital: float = 15000.0, leverage: float = 4.0, startDate:str = None, endDate:str = None):
        self.capital = capital
        self.leverage = leverage
        self.startDate = startDate
        self.endDate = endDate
