from typing import List, Union
import numpy as np
import pandas as pd
from AxonBackTest import config
from AxonBackTest.strategy import Strategy


class PortfolioManagement:
    def __init__(
        self,
        config: config.PortfolioConfig,
        formal: bool = False,
    ):
        self.config = config
        self.strategys: List[Strategy] = []
        self.formal = formal

    def activate(self):
        self.reload_strategrys_datas()
        self.get_strategys_signals()
        self.get_strategys_postion_sizes()
        self._validate_settings()

    def reload_strategrys_datas(self):
        if self.formal == False:
            for strategy in self.strategys:
                if strategy.df.empty:
                    strategy.load_data_from_csv()

    def get_strategys_signals(self):
        if self.formal == False:
            for strategy in self.strategys:
                if not strategy.signals:
                    strategy.generate_signals()

    def get_strategys_postion_sizes(self):
        if self.formal == False:
            for strategy in self.strategys:
                if not strategy.signals:
                    strategy.generate_postion_sizes()

    def register_strategys(self, strategys: Union[list, Strategy]):
        if isinstance(strategys, list):
            self.strategys.extend(strategys)

        if isinstance(strategys, Strategy):
            self.strategys.append(strategys)

    def _validate_settings(self) -> None:
        # 1. first check the signal len equal the dataframe len.
        pass

    def generate_report(self, TargetPrcie: str = "Open"):
        """
        Step 1 : 由於每個商品的時間長段不一樣，要先處理。

        Step 2 : 要特別計算摩擦成本.

        TargetPrcie : i think should use Open price.
        """
        self.parameter_info["report_target_price"] = TargetPrcie
        # 紀錄模板初始化
        self.update_each_backTestInfoMap()
        self.update_global_backTestInfoMap()
        self.time_min_scale()
        self.data = self.get_data()

        self.report_info["datetimelist"] = []
        self.report_info["CloseProfit"] = []

        for each_timestamp, each_row in self.data.items():
            for each_strategy_name, each_strategy_info in each_row.items():
                # 如果那個時間有資料的話 且有訂單的話
                if each_strategy_info:
                    signal = each_strategy_info["signal"]
                    postionSizing = each_strategy_info["postionSizing"]

                    self._updateinfo(
                        signal,
                        postionSizing,
                        each_strategy_info[TargetPrcie],
                        self._backTestInfoMap[each_strategy_name],
                        self.global_Info,
                    )

            self.report_info["datetimelist"].append(each_timestamp)
            self.report_info["CloseProfit"].append(self.global_Info["CloseProfit"])

        report_df = pd.DataFrame(self.report_info)
        report_df["datetimelist"] = report_df["datetimelist"].astype(
            str
        )  # 轉為字串以利JSON序列化
        return report_df.to_dict("records")


#     def generate_strategys(self):
#         strategy_names = []
#         for symbol in self.symbols:
#             strategy_name = self._strategy_name("DQN", symbol, "30m")
#             parameter_datas = {
#                 "strategy_name": strategy_name,
#                 "symbol_name": symbol,
#                 "symbol_type": "FUTURES",
#                 "fee_percent": 0.0005,
#                 "slippage_percent": 0.0025,
#                 "freq_time": "30",
#                 "unit": "Min",
#                 "history_data_path": "simulation/",
#                 "strategy_type": "DQN",
#             }
#             self.parameter_info["strategies"].append(parameter_datas)

#             if strategy_name not in strategy_names:
#                 strategy_names.append(strategy_name)
#             else:
#                 raise ValueError("Strategy Name Can't be the same.")

#             self.strategys.append(
#                 Strategy(parameter_datas=parameter_datas, formal=self.formal)
#             )


#     def _strategy_name(self, strategytype: str, symbol_name: str, freq_time: str):
#         return f"{strategytype}-{symbol_name}-{freq_time}"

#     def time_min_scale(self):
#         all_datetimes = []
#         for strategy in self.strategys:
#             all_datetimes.extend(strategy.df.index)

#         self.min_scale = list(set(all_datetimes))
#         self.min_scale.sort()

#     def get_data(self):
#         """
#         將所有策略的資料合併成一個以時間為主鍵的字典。
#         此版本優先遍歷時間戳，可讀性更高且寫法更簡潔。
#         """
#         # 為了快速查找，預先建立一個從策略名稱到其 DataFrame 的映射字典
#         strategy_dfs = {s.config.strategyName: s.df for s in self.strategys}

#         # 遍歷所有獨一的時間戳
#         data = {
#             timestamp: {
#                 name: df.loc[timestamp].to_dict() if timestamp in df.index else None
#                 for name, df in strategy_dfs.items()
#             }
#             for timestamp in self.min_scale
#         }

#         return data

#     def update_each_backTestInfoMap(self):
#         template_data = {
#             "MarketPostion": 0,
#             "PostionSize": 0.0,
#             "action": "",
#             "AvgEntryPrice": 0.0,
#             "ClosePostion_price": 0.0,
#             "fee_percent": 0.0,
#             "slippage_percent": 0.0,
#             "long_open_fee": 0.0,
#             "long_close_fee": 0.0,
#             "short_open_fee": 0.0,
#             "short_close_fee": 0.0,
#             "single_profit": 0.0,
#         }
#         self._backTestInfoMap = {}
#         for s in self.strategys:
#             local_data = copy.deepcopy(template_data)
#             local_data["fee_percent"] = s.config.feePercent
#             local_data["slippage_percent"] = s.config.slippagePercent
#             self._backTestInfoMap.update({s.config.strategyName: local_data})

#     def update_global_backTestInfoMap(self):
#         self.global_Info = {
#             "init_cash": self.config.capital,
#             "leverage": self.config.leverage,
#             "CloseProfit": self.config.capital,
#             "strategys_count": len(self.strategys),
#         }

#     def leverage_model(
#         self,
#         money: float,
#         levelage: float,
#         TargetPrice: float,
#         strategys_count: int,
#         PostionSizing: float,
#     ):
#         """
#         use closeprofit to caculate.
#         """

#         if money < 5:
#             return 0
#         return (money * levelage * PostionSizing) / TargetPrice / strategys_count

#     def _updateinfo(
#         self,
#         signal: float,
#         postionSizing: float,
#         target_price: float,
#         info: dict,
#         global_Info: dict,
#     ):
#         """
#         {
#             'MarketPostion': 0, 'PostionSize': 0.0, 'action': '', 'AvgEntryPrice': 0.0, 'ClosePostion_price': 0.0,
#             ''

#         }

#         {'init_cash': 15000.0, 'leverage': 4.0, 'CloseProfit': 15000.0, 'strategys_count': 1}


#         倉位價值 = 成交數量 × 成交價格

#         目前的設計為 如果小於5元將不在進行任何交易

#         i use cloes_prcie because which can repersant the close postion price,
#         can use in long postion to close,and short postion to close.
#         """

#         marketpostion = info["MarketPostion"]
#         slippage_percent = info["slippage_percent"]
#         fee_percent = info["fee_percent"]
#         CloseProfit = global_Info["CloseProfit"]
#         action = "Hold"

#         # 初始化手續費和單次損益
#         (
#             long_open_fee,
#             long_close_fee,
#             short_open_fee,
#             short_close_fee,
#             single_profit,
#         ) = (0.0, 0.0, 0.0, 0.0, 0.0)

#         if signal == 1:
#             if marketpostion == 0:
#                 action = "BUY"
#                 info["AvgEntryPrice"] = target_price * (1 + slippage_percent)
#                 info["PostionSize"] = self.leverage_model(
#                     CloseProfit,
#                     global_Info["leverage"],
#                     target_price * (1 + slippage_percent + fee_percent),
#                     global_Info["strategys_count"],
#                     PostionSizing=postionSizing,
#                 )
#                 long_open_fee = (
#                     info["PostionSize"] * info["AvgEntryPrice"] * fee_percent
#                 )
#                 CloseProfit = CloseProfit - long_open_fee
#                 info["ClosePostion_price"] = 0.0
#                 marketpostion = 1
#             elif marketpostion == -1:
#                 action = "BUY_TO_COVER_AND_BUY"
#                 # 步驟 1: 平倉空單 (BUY_TO_COVER)
#                 close_price = target_price * (1 + slippage_percent)
#                 single_profit = (info["AvgEntryPrice"] - close_price) * info[
#                     "PostionSize"
#                 ]
#                 short_close_fee = info["PostionSize"] * close_price * fee_percent
#                 CloseProfit = CloseProfit + single_profit - short_close_fee
#                 info["ClosePostion_price"] = close_price

#                 # 步驟 2: 建立新的多單 (BUY)
#                 info["AvgEntryPrice"] = target_price * (1 + slippage_percent)
#                 info["PostionSize"] = self.leverage_model(
#                     CloseProfit,
#                     global_Info["leverage"],
#                     target_price * (1 + slippage_percent + fee_percent),
#                     global_Info["strategys_count"],
#                     PostionSizing=postionSizing,
#                 )
#                 long_open_fee = (
#                     info["PostionSize"] * info["AvgEntryPrice"] * fee_percent
#                 )
#                 CloseProfit = CloseProfit - long_open_fee
#                 marketpostion = 1
#             elif marketpostion == 1:
#                 # 1. 取得目前現有部位
#                 previous_postion = info["PostionSize"]

#                 # 2. 先判斷是要買進還是賣出
#                 new_Postion = self.leverage_model(
#                     CloseProfit,
#                     global_Info["leverage"],
#                     target_price * (1 + slippage_percent + fee_percent),
#                     global_Info["strategys_count"],
#                     PostionSizing=postionSizing,
#                 )

#                 if new_Postion > previous_postion:
#                     action = "Adjustment Long Postion increase"
#                     # 1. 總共增加多少部位
#                     additional_size = new_Postion - previous_postion

#                     # 2. 計算新買入的手續費費用
#                     buy_price = target_price * (1 + slippage_percent)
#                     long_open_fee = additional_size * buy_price * fee_percent

#                     # 3. 重新計算入場價格 及總部位
#                     info["AvgEntryPrice"] = (
#                         previous_postion * info["AvgEntryPrice"]
#                         + additional_size * buy_price
#                     ) / new_Postion
#                     info["PostionSize"] = new_Postion

#                     # 4.更新整體資金
#                     CloseProfit = CloseProfit - long_open_fee

#                 elif new_Postion < previous_postion and new_Postion > 0:
#                     action = "Adjustment Long Postion cut down"
#                     sell_size = previous_postion - new_Postion
#                     close_price = target_price * (1 - slippage_percent)
#                     # 計算手續費
#                     long_close_fee = sell_size * close_price * fee_percent
#                     # 計算"已實現"損益
#                     single_profit = (close_price - info["AvgEntryPrice"]) * sell_size
#                     CloseProfit = CloseProfit + single_profit - long_close_fee
#                     # 更新倉位 (AvgEntryPrice 保持不變)
#                     info["PostionSize"] = new_Postion
#                     info["ClosePostion_price"] = close_price

#                 elif new_Postion < previous_postion and new_Postion == 0:
#                     action = "SELL"  # 動作改成 SELL 更精確
#                     close_price = target_price * (1 - slippage_percent)

#                     # 損益是基於 "全部的舊倉位"
#                     single_profit = (
#                         close_price - info["AvgEntryPrice"]
#                     ) * previous_postion
#                     long_close_fee = previous_postion * close_price * fee_percent

#                     # 更新總資金
#                     CloseProfit = CloseProfit + single_profit - long_close_fee

#                     # 重置倉位資訊
#                     info["AvgEntryPrice"] = 0.0
#                     info["PostionSize"] = 0.0
#                     info["ClosePostion_price"] = close_price
#                     marketpostion = 0

#         elif signal == -1:
#             if marketpostion == 0:
#                 action = "SELL_SHORT"
#                 info["AvgEntryPrice"] = target_price * (1 - slippage_percent)
#                 info["PostionSize"] = self.leverage_model(
#                     CloseProfit,
#                     global_Info["leverage"],
#                     target_price * (1 - slippage_percent + fee_percent),
#                     global_Info["strategys_count"],
#                     PostionSizing=postionSizing,
#                 )
#                 short_open_fee = (
#                     info["PostionSize"] * info["AvgEntryPrice"] * fee_percent
#                 )
#                 CloseProfit = CloseProfit - short_open_fee
#                 info["ClosePostion_price"] = 0.0
#                 marketpostion = -1
#             elif marketpostion == 1:
#                 action = "SELL_AND_SELL_SHORT"
#                 # 步驟 1: 平倉多單 (SELL)
#                 close_price = target_price * (1 - slippage_percent)
#                 single_profit = (close_price - info["AvgEntryPrice"]) * info[
#                     "PostionSize"
#                 ]
#                 long_close_fee = info["PostionSize"] * close_price * fee_percent
#                 CloseProfit = CloseProfit + single_profit - long_close_fee
#                 info["ClosePostion_price"] = close_price

#                 # 步驟 2: 建立新的空單 (SELL_SHORT)
#                 info["AvgEntryPrice"] = target_price * (1 - slippage_percent)
#                 info["PostionSize"] = self.leverage_model(
#                     CloseProfit,
#                     global_Info["leverage"],
#                     target_price * (1 - slippage_percent + fee_percent),
#                     global_Info["strategys_count"],
#                     PostionSizing=postionSizing,
#                 )
#                 short_open_fee = (
#                     info["PostionSize"] * info["AvgEntryPrice"] * fee_percent
#                 )
#                 CloseProfit = CloseProfit - short_open_fee
#                 marketpostion = -1

#             elif marketpostion == -1:
#                 # 1. 取得目前現有部位
#                 previous_postion = info["PostionSize"]

#                 # 2. 先判斷是要買進還是賣出
#                 new_Postion = self.leverage_model(
#                     CloseProfit,
#                     global_Info["leverage"],
#                     target_price * (1 - slippage_percent + fee_percent),
#                     global_Info["strategys_count"],
#                     PostionSizing=postionSizing,
#                 )

#                 if new_Postion > previous_postion:
#                     action = "Adjustment Short Postion increase"
#                     # 1. 總共增加多少部位
#                     additional_size = new_Postion - previous_postion

#                     # 2. 計算新買入的手續費費用
#                     sell_price = target_price * (1 - slippage_percent)
#                     short_open_fee = additional_size * sell_price * fee_percent

#                     # 3. 重新計算入場價格 及總部位
#                     info["AvgEntryPrice"] = (
#                         previous_postion * info["AvgEntryPrice"]
#                         + additional_size * sell_price
#                     ) / new_Postion
#                     info["PostionSize"] = new_Postion

#                     # 4.更新整體資金
#                     CloseProfit = CloseProfit - short_open_fee

#                 elif new_Postion < previous_postion and new_Postion > 0:
#                     action = "Adjustment Short Postion cut down"
#                     buy_size = previous_postion - new_Postion
#                     close_price = target_price * (1 + slippage_percent)
#                     # 計算手續費
#                     short_close_fee = buy_size * close_price * fee_percent

#                     # 計算"已實現"損益
#                     single_profit = (info["AvgEntryPrice"] - close_price) * buy_size

#                     CloseProfit = CloseProfit + single_profit - short_close_fee
#                     # 更新倉位 (AvgEntryPrice 保持不變)
#                     info["PostionSize"] = new_Postion
#                     info["ClosePostion_price"] = close_price

#                 elif new_Postion < previous_postion and new_Postion == 0:
#                     action = "BUY_TO_COVER"
#                     previous_postion = info["PostionSize"]  # 取得舊倉位
#                     close_price = target_price * (1 + slippage_percent)  # 計算平倉價

#                     single_profit = (
#                         info["AvgEntryPrice"] - close_price
#                     ) * previous_postion
#                     short_close_fee = previous_postion * close_price * fee_percent

#                     # 更新總資金
#                     CloseProfit = CloseProfit + single_profit - short_close_fee

#                     # 重置倉位資訊
#                     info["AvgEntryPrice"] = 0.0
#                     info["PostionSize"] = 0.0
#                     info["ClosePostion_price"] = close_price  # 紀錄平倉價
#                     marketpostion = 0

#         elif signal == 0:
#             if marketpostion == 1:
#                 action = "SELL"
#                 close_price = target_price * (1 - slippage_percent)
#                 single_profit = (close_price - info["AvgEntryPrice"]) * info[
#                     "PostionSize"
#                 ]
#                 long_close_fee = info["PostionSize"] * close_price * fee_percent
#                 CloseProfit = CloseProfit + single_profit - long_close_fee

#                 info["AvgEntryPrice"] = 0.0
#                 info["PostionSize"] = 0.0
#                 info["ClosePostion_price"] = close_price
#                 marketpostion = 0
#             elif marketpostion == -1:
#                 action = "BUY_TO_COVER"
#                 close_price = target_price * (1 + slippage_percent)
#                 single_profit = (info["AvgEntryPrice"] - close_price) * info[
#                     "PostionSize"
#                 ]
#                 short_close_fee = info["PostionSize"] * close_price * fee_percent
#                 CloseProfit = CloseProfit + single_profit - short_close_fee

#                 info["AvgEntryPrice"] = 0.0
#                 info["PostionSize"] = 0.0
#                 info["ClosePostion_price"] = close_price
#                 marketpostion = 0

#         info["MarketPostion"] = marketpostion
#         info["action"] = action
#         global_Info["CloseProfit"] = CloseProfit
#         info["long_open_fee"] = long_open_fee
#         info["long_close_fee"] = long_close_fee
#         info["short_open_fee"] = short_open_fee
#         info["short_close_fee"] = short_close_fee
#         info["single_profit"] = single_profit

#         # print("目前訊號:",signal)
#         # print("目前購入比例:",postionSizing)
#         # print("目前動作:",action)
#         # print("目標價格:",target_price)
#         # print("info:",info)
#         # print("總資金損益:",global_Info['CloseProfit'])
#         # print('*'*120)
#         # time.sleep(0.1)
#         return

