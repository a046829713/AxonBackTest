import AxonBackTest.config as config
from AxonBackTest.strategy import Strategy
from AxonBackTest.PorfolioTrader import PortfolioManagement
import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import copy




class BackTester():
    def __init__(self, manager: PortfolioManagement = None):
        """

            operater all process.
        Args:
            manager (PortfolioManagement, optional): _description_. Defaults to None.
        """
        self.pfm = manager
        self.report = None
        self.pfm.activate()

    def generate_report(self):
        self.report = self.pfm.generate_report()
        return self.report

    def plot_image(self):
        if self.report is None:
            self.generate_report()

        report_df = pd.DataFrame(self.report)

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

    def print_paramter_info(self):
        for key, value in self.pfm.parameter_info.items():
            print("參數名稱:", key, "目前設定值:", value)

    def print_metrics(self):
        """Prints formatted statistical summary metrics."""
        print("=" * 50)
        print("          Portfolio Performance Metrics           ")
        print("=" * 50)
        for key, value in self.pfm.metrics.items():
            print(f"{key:25s}: {value}")
        print("=" * 50)

