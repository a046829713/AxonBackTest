from . import config
from .strategy import Strategy
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import copy


class PortfolioManagement():
    def __init__(self, symbols: list, capital:float,leverage:float, formal: bool = False):
        self.symbols = symbols
        self.config = config.PortfolioManagementConfig(
            capital = capital,
            leverage = leverage
        )
        self.strategys = []
        self.formal = formal  # 策略是否正式啟動
        self._backTestInfoMap = {}
        self.report_info = {}

    def generate_strategys(self):
        strategy_names = []
        for symbol in self.symbols:
            strategy_name = self._strategy_name("DQN", symbol, "30m")
            data = {
                "strategy_name": strategy_name,
                "symbol_name": symbol,
                "symbol_type": "FUTURES",
                "fee_percent": 0.0005,
                "slippage_percent": 0.0025,
                "freq_time": "30",
                "unit": "Min",
                "history_data_path": "simulation/",
                "strategy_type": "DQN"
            }
            if strategy_name not in strategy_names:
                strategy_names.append(strategy_name)
            else:
                raise ValueError("Strategy Name Can't be the same.")

            self.strategys.append(Strategy(data=data, formal=self.formal))

    def run(self, rolling=True):
        """
            1. read from order file
            2. 
        """
        self.generate_strategys()

        for strategy in self.strategys:
            signals = strategy.run(fakeMode=True)
            if rolling == True:
                signals = np.roll(signals, 1)
                signals[0] = 0
            strategy.df['signal'] = signals

    def _strategy_name(self, strategytype: str, symbol_name: str, freq_time: str):
        return f"{strategytype}-{symbol_name}-{freq_time}"

    def time_min_scale(self):
        all_datetimes = []
        for strategy in self.strategys:
            all_datetimes.extend(strategy.df.index)

        self.min_scale = list(set(all_datetimes))
        self.min_scale.sort()

    def get_data(self):
        """
        將所有策略的資料合併成一個以時間為主鍵的字典。
        此版本優先遍歷時間戳，可讀性更高且寫法更簡潔。
        """
        # 為了快速查找，預先建立一個從策略名稱到其 DataFrame 的映射字典
        strategy_dfs = {s.config.strategyName: s.df for s in self.strategys}

        # 遍歷所有獨一的時間戳
        data = {
            timestamp: {
                name: df.loc[timestamp].to_dict(
                ) if timestamp in df.index else None
                for name, df in strategy_dfs.items()
            }
            for timestamp in self.min_scale
        }

        return data

    def update_each_backTestInfoMap(self):
        template_data = {
            "MarketPostion": 0,
            "PostionSize": 0.0,
            "action": "",
            "OpenPostion_price": 0.0,
            "ClosePostion_prcie": 0.0,
            "fee_percent": 0.0,
            "slippage_percent": 0.0,
            "long_open_fee": 0.0,
            "long_close_fee": 0.0,
            "short_open_fee": 0.0,
            "short_close_fee": 0.0,
            "single_profit": 0.0
        }
        self._backTestInfoMap = {}
        for s in self.strategys:
            local_data = copy.deepcopy(template_data)
            local_data['fee_percent'] = s.config.feePercent
            local_data['slippage_percent'] = s.config.slippagePercent
            self._backTestInfoMap.update({s.config.strategyName: local_data})

    def update_global_backTestInfoMap(self):
        self.global_Info = {
            "init_cash": self.config.capital,
            "leverage": self.config.leverage,
            "CloseProfit": self.config.capital,
            "strategys_count": len(self.strategys)
        }

    def leverage_model(self, money: float, levelage: float, TargetPrice: float, strategys_count: int):
        """ 
            use closeprofit to caculate.       
        """

        if money <5:
            return 0
        return money * levelage / TargetPrice / strategys_count

    def _updateinfo(self, signal: float, target_price: float, info: dict, global_Info: dict):
        """
            {
                'MarketPostion': 0, 'PostionSize': 0.0, 'action': '', 'OpenPostion_price': 0.0, 'ClosePostion_prcie': 0.0,
                ''

            }

            {'init_cash': 15000.0, 'leverage': 4.0, 'CloseProfit': 15000.0, 'strategys_count': 1}


            倉位價值 = 成交數量 × 成交價格

            目前的設計為 如果小於5元將不在進行任何交易
        """

        marketpostion = info['MarketPostion']
        slippage_percent = info['slippage_percent']
        fee_percent = info['fee_percent']
        CloseProfit = global_Info['CloseProfit']
        action = "Hold"

        # 初始化手續費和單次損益
        long_open_fee, long_close_fee, short_open_fee, short_close_fee, single_profit = 0.0, 0.0, 0.0, 0.0, 0.0

        if signal == 1:
            if marketpostion == 0:
                action = "BUY"
                info['OpenPostion_price'] = target_price * \
                    (1 + slippage_percent)
                info['PostionSize'] = self.leverage_model(CloseProfit, global_Info['leverage'], target_price*(
                    1 + slippage_percent + fee_percent), global_Info['strategys_count'])
                long_open_fee = info['PostionSize'] * \
                    info['OpenPostion_price'] * fee_percent
                CloseProfit = CloseProfit - long_open_fee
                info['ClosePostion_prcie'] = 0.0
                marketpostion = 1
            elif marketpostion == -1:
                action = "BUY_TO_COVER_AND_BUY"
                # 步驟 1: 平倉空單 (BUY_TO_COVER)
                close_price = target_price * (1 + slippage_percent)
                single_profit = (info['OpenPostion_price'] -
                                 close_price) * info['PostionSize']
                short_close_fee = info['PostionSize'] * \
                    close_price * fee_percent
                CloseProfit = CloseProfit + single_profit - short_close_fee
                info['ClosePostion_prcie'] = close_price

                # 步驟 2: 建立新的多單 (BUY)
                info['OpenPostion_price'] = target_price * \
                    (1 + slippage_percent)
                info['PostionSize'] = self.leverage_model(
                    CloseProfit, global_Info['leverage'], target_price*(1 + slippage_percent + fee_percent), global_Info['strategys_count'])
                long_open_fee = info['PostionSize'] * \
                    info['OpenPostion_price'] * fee_percent
                CloseProfit = CloseProfit - long_open_fee
                marketpostion = 1

        elif signal == -1:
            if marketpostion == 0:
                action = "SELL_SHORT"
                info['OpenPostion_price'] = target_price * \
                    (1 - slippage_percent)
                info['PostionSize'] = self.leverage_model(
                    CloseProfit, global_Info['leverage'], target_price * (1 - slippage_percent + fee_percent), global_Info['strategys_count'])
                short_open_fee = info['PostionSize'] * \
                    info['OpenPostion_price'] * fee_percent
                CloseProfit = CloseProfit - short_open_fee
                marketpostion = -1
            elif marketpostion == 1:
                action = "SELL_AND_SELL_SHORT"
                # 步驟 1: 平倉多單 (SELL)
                close_price = target_price * (1 - slippage_percent)
                single_profit = (
                    close_price - info['OpenPostion_price']) * info['PostionSize']
                long_close_fee = info['PostionSize'] * \
                    close_price * fee_percent
                CloseProfit = CloseProfit + single_profit - long_close_fee
                info['ClosePostion_prcie'] = close_price

                # 步驟 2: 建立新的空單 (SELL_SHORT)
                info['OpenPostion_price'] = target_price * \
                    (1 - slippage_percent)
                info['PostionSize'] = self.leverage_model(
                    CloseProfit, global_Info['leverage'], target_price * (1 - slippage_percent + fee_percent), global_Info['strategys_count'])
                short_open_fee = info['PostionSize'] * \
                    info['OpenPostion_price'] * fee_percent
                CloseProfit = CloseProfit - short_open_fee
                marketpostion = -1

        elif signal == 0:
            if marketpostion == 1:
                action = "SELL"
                close_price = target_price * (1 - slippage_percent)
                single_profit = (
                    close_price - info['OpenPostion_price']) * info['PostionSize']
                long_close_fee = info['PostionSize'] * \
                    close_price * fee_percent
                CloseProfit = CloseProfit + single_profit - long_close_fee

                info['OpenPostion_price'] = 0.0
                info['PostionSize'] = 0.0
                marketpostion = 0
            elif marketpostion == -1:
                action = "BUY_TO_COVER"
                close_price = target_price * (1 + slippage_percent)
                single_profit = (info['OpenPostion_price'] -
                                 close_price) * info['PostionSize']
                short_close_fee = info['PostionSize'] * \
                    close_price * fee_percent
                CloseProfit = CloseProfit + single_profit - short_close_fee

                info['OpenPostion_price'] = 0.0
                info['PostionSize'] = 0.0
                marketpostion = 0

        info["MarketPostion"] = marketpostion
        info["action"] = action
        global_Info['CloseProfit'] = CloseProfit
        info['long_open_fee'] = long_open_fee
        info['long_close_fee'] = long_close_fee
        info['short_open_fee'] = short_open_fee
        info['short_close_fee'] = short_close_fee
        info['single_profit'] = single_profit
        return

    def generate_report(self, TargetPrcie: str = "Open"):
        """
            Step 1 : 由於每個商品的時間長段不一樣，要先處理。

            Step 2 : 要特別計算摩擦成本.

            TargetPrcie : i think should use Open price.
        """
        # 紀錄模板初始化
        self.update_each_backTestInfoMap()
        self.update_global_backTestInfoMap()
        self.time_min_scale()
        self.data = self.get_data()

        self.report_info['datetimelist'] = []
        self.report_info['CloseProfit']= []
        
        for each_timestamp, each_row in self.data.items():
            for each_strategy_name, each_strategy_info in each_row.items():
                # 如果那個時間有資料的話 且有訂單的話
                if each_strategy_info:
                    signal = each_strategy_info['signal']

                    self._updateinfo(
                        signal, each_strategy_info[TargetPrcie], self._backTestInfoMap[each_strategy_name], self.global_Info)

                    

            self.report_info['datetimelist'].append(each_timestamp)
            self.report_info['CloseProfit'].append(self.global_Info['CloseProfit'])

        report_df = pd.DataFrame(self.report_info)
        report_df['datetimelist'] = report_df['datetimelist'].astype(str) # 轉為字串以利JSON序列化
        return report_df.to_dict('records')
        
    def plot_image(self,data:dict):
        report_df = pd.DataFrame(data)

        # 將 datetimelist 設置為索引並轉換為日期時間格式
        report_df['datetimelist'] = pd.to_datetime(report_df['datetimelist'])
        report_df.set_index('datetimelist', inplace=True)
        report_df.index.name = 'Datetime'

        # 繪製資金曲線圖
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.figure(figsize=(15, 7))
        report_df['CloseProfit'].plot(legend=True)
        plt.title('Portfolio Close Profit Over Time', fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Close Profit (USD)', fontsize=12)
        plt.grid(True)
        plt.show()

class BackTester():
    def __init__(self, manager: PortfolioManagement = None):
        self.pfm = manager

    def generate_report(self):
        self.pfm.run(rolling=False)
        return self.pfm.generate_report()
