from AxonBackTest.backtester import PortfolioManagement, BackTester

if __name__ == "__main__":
    # 在此處修改您想回測的交易對，例如 ["BNBUSDT", "BTCUSDT"]
    manager = PortfolioManagement(
        symbols=["BTCUSDT"], capital=15000, leverage=4, order_map={}, formal=False)

    
    # 初始化並執行回測
    bt = BackTester(manager=manager)
    bt.generate_report()
    bt.print_paramter_info()
    bt.plot_image()