from . import config
import numpy as np
import os
import pandas as pd


class Strategy:
    def __init__(self, parameter_datas: dict, formal:bool = False, df:pd.DataFrame = None):
        self.formal = formal  # 策略是否正式啟動
        self.checkData(parameter_datas)
        self.config = config.StrategyConfig.from_dict(parameter_datas)
        if self.config.symbolType == "FUTURES":
            fileName = f"{self.config.symbolName}-F-{self.config.freq_time}-{self.config.unit}.csv"
        
        if df is None:
            self.load_data(local_data_path=os.path.join(self.config.historyDataPath, fileName))
        else:
            self.df = df
            
    def checkData(self, parameter_datas: dict):
        return parameter_datas

    def generate_signals(self, Mode: str):
        if Mode == "fake_signal_Mode":
            # This part is very important, original is order think,
            # buy We need to change thought.
            # right now is Target signal.
            # traget_signal_arrays = np.random.randint(-1, 2, size=len(self.df))
            
            choices = [-1, 0, 1]
            probabilities = [0.33, 0.33, 0.34]

            # choices = [ 1]
            # probabilities = [1]
            traget_signal_arrays = np.random.choice(choices, size=len(self.df), p=probabilities)

            PositionSizing_arrays =  np.random.rand(len(self.df))
            # PositionSizing_arrays =  np.ones(len(self.df))
            return traget_signal_arrays, PositionSizing_arrays
        elif Mode =="truely_signal_Mode":
            


            return traget_signal_arrays, PositionSizing_arrays
        else:
            raise ValueError("please chcek strategy generate signals.")
    
    def load_data(self, local_data_path: str):
        """
            如果非正式交易的的時候，可以啟用
        """
        if self.formal:
            raise KeyError("This is formal trade, please Check")

        if not os.path.exists(local_data_path):
            raise FileNotFoundError("Please check your local file path.")
        
        self.df = pd.read_csv(local_data_path)
        self.df.set_index("Datetime", inplace=True)
        # ['Open', 'High', 'Low', 'Close', 'Volume', 'quote_av', 'trades','tb_base_av', 'tb_quote_av']