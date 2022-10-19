import time
import traceback

from simple_trading_bot.lib.ir_expert import IRExpert
from simple_trading_bot.lib.market_data_feeds import RofexProxy, YfinanceMDFeed
from simple_trading_bot.lib.instrument_expert import InstrumentExpert
from simple_trading_bot.lib.data_update_watchman import DataUpdateWatchman
from simple_trading_bot.lib.ir_printer import IRPrinter
from simple_trading_bot.lib.trader import Trader


class IRArbitrageTradingBot:

    def __init__(self, tickers, spot_update_frequency):
        self._instrument_expert = InstrumentExpert(tickers)
        self._rofex_proxy = RofexProxy(self._instrument_expert)
        self._yfinance_md_feed = YfinanceMDFeed(self._instrument_expert, spot_update_frequency)
        self._data_update_watchman = DataUpdateWatchman(self._rofex_proxy, self._yfinance_md_feed)
        self._ir_expert = IRExpert(self._instrument_expert, self._rofex_proxy, self._yfinance_md_feed)
        self._ir_printer = IRPrinter(self._ir_expert)
        self._trader = Trader(
            self._instrument_expert,
            self._ir_expert,
            self._rofex_proxy,
            self._yfinance_md_feed,
            self._data_update_watchman)

    def launch(self):
        self._start()
        self._run()
        self._finish()

    def _start(self):
        self._yfinance_md_feed.start_listening()
        self._rofex_proxy.start_listening()

    def _run(self):
        while True:
            try:
                if self._data_update_watchman.should_update():
                    self._data_update_watchman.set_last_processed_timestamp()
                    self._ir_expert.update_rates()
                    if self._ir_expert.ready():
                        try:
                            self._ir_printer.print_rates()
                        except Exception:
                            print(f'Exception ocurred printing rates. Continuing...')
                        self._trader.evaluate_and_trade_each_maturiry()
            except Exception as e:
                traceback.print_exc()
                print(f'Exception occurred during trading. Stopping...')
                break
            if not self._yfinance_md_feed.running():
                self._yfinance_md_feed.start_listening()
            if not self._rofex_proxy.running():
                self._rofex_proxy.start_listening()

    def _finish(self):
        print('Finishing...')
        self._yfinance_md_feed.stop()
        self._rofex_proxy.stop()
        print('Done!')
