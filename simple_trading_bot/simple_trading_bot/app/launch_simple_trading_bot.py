import simple_trading_bot.lib.trading_bot as tb


def main():
    tickers = ['GGAL', 'YPFD', 'PAMP', 'DLR']
    spot_update_frequency = 1.
    tb.IRArbitrageTradingBot(tickers, spot_update_frequency).launch()


if __name__ == '__main__':
    main()
