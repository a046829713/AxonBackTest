from . import config
import numpy as np
import os
import pandas as pd


class Strategy:
    def __init__(self, data: dict, formal:bool = False):
        self.formal = formal  # 策略是否正式啟動
        self.checkData(data)
        self.config = config.StrategyConfig.from_dict(data)
        if self.config.symbolType == "FUTURES":
            fileName = f"{self.config.symbolName}-F-{self.config.freq_time}-{self.config.unit}.csv"
        
        self.load_data(local_data_path=os.path.join(self.config.historyDataPath, fileName))

    def checkData(self, data: dict):
        return data

    def run(self, fakeMode: bool):
        if fakeMode:
            # This part is very important, original is order think,
            # buy We need to change thought.
            # right now is Target signal.
            # traget_signal_arrays = np.random.randint(-1, 2, size=len(self.df))
            
            choices = [-1, 0, 1]
            probabilities = [0.33, 0.33, 0.34]
            traget_signal_arrays = np.random.choice(choices, size=len(self.df), p=probabilities)

            
        return traget_signal_arrays
    
    def load_data(self, local_data_path: str):
        """
            如果非正式交易的的時候，可以啟用
        """
        if self.formal:
            raise KeyError("This is formal trade,please Check")

        self.df = pd.read_csv(local_data_path)
        self.df.set_index("Datetime", inplace=True)
        # ['Open', 'High', 'Low', 'Close', 'Volume', 'quote_av', 'trades','tb_base_av', 'tb_quote_av']