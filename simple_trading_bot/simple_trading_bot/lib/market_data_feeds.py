import copy
import sys
import threading
import time
from collections import defaultdict, namedtuple
from pprint import pprint

import pyRofex
import yfinance

import simple_trading_bot.lib.pyrofex_wrapper as prw


FLOAT_LIMIT = 1e-4


OrderbookLevel = namedtuple('OrderbookLevel', 'price size')


class MarketDataFeed:

    def __init__(self):
        self._last_update_timestamp = 0.
        self._running = False

    def last_update_timestamp(self):
        return self._last_update_timestamp

    def _update_last_timestamp(self):
        self._last_update_timestamp = time.time()

    def start_listening(self):
        raise NotImplementedError

    def stop(self):
        self._running = False

    def running(self):
        return self._running


class YfinanceMDFeed(MarketDataFeed):
    """
    Class to retrieve prices from yahoo finance.
    Data will be refreshed on a configurable regular basis.
    """

    def __init__(self, instrument_expert, update_frequency):
        super().__init__()
        self._tickers = instrument_expert.tradeable_yfinance_tickers()
        self._inverse_ticker_map = instrument_expert.inverse_yfinance_tickers_map()
        self._update_frequency = update_frequency
        self._listening_thread = None
        self._prices = {}

    def start_listening(self):
        """Starts data retrieving"""
        print('YFinaince MD Feed is starting listening...')
        self._listening_thread = threading.Thread(target=self._update_prices)
        self._running = True
        self._listening_thread.start()
        print('Started')

    def last_prices(self):
        return self._prices.copy()

    def price(self, ticker):
        return self._prices.get(ticker, 0.)

    def _update_prices(self):
        """Process retrieved data"""
        while self._running:
            try:
                data = yfinance.download(
                    tickers=self._tickers,
                    period='1d',
                    interval='1d',
                    progress=False)
                start = time.time()
                prices = data['Close'].to_dict(orient='records')[0]
                #Prices will be updated only on change
                if any((price - self._prices.get(self._inverse_ticker_map[ticker], 0.) > FLOAT_LIMIT)
                       for ticker, price in prices.items()):
                    self._prices = {self._inverse_ticker_map[ticker]: price for ticker, price in prices.items()}
                    self._update_last_timestamp()
                    print(f'Updated {self._prices}\n', flush=True)
                time.sleep(self._update_frequency)
            except Exception as e:
                traceback.print_exc()
                print(f'Exception occurred updating yfinance prices. Stopping YFinance...')
                self.stop()


class RofexProxy(MarketDataFeed):
    """
    Class used as a proxy for rofex.
    Main responsabilities are data retrieving and order placing and tracking.
    Stands on pyRofex package (https://github.com/matbarofex/pyRofex) through PyRofexWrapper class.
    """
    DATA_ENTRIES = [
        pyRofex.MarketDataEntry.BIDS,
        pyRofex.MarketDataEntry.OFFERS]

    def __init__(self, instrument_expert, subscribe_to_order_report=False):
        super().__init__()
        self._futures_ticker = instrument_expert.tradeable_rofex_tickers()
        self._pyrofex_wrapper = prw.PyRofexWrapper()
        self._bids = {}
        self._asks = {}
        self._bids_lock = threading.Lock()
        self._asks_lock = threading.Lock()
        self._subscribe_to_order_report = subscribe_to_order_report

    def __str__(self):
        repr_str = ''
        all_tickers = set(self._bids.keys()).union(set(self._asks.keys()))
        for ticker in all_tickers:
            repr_str += (f'{ticker}: '
                         f'{self._bids[ticker].get(pyRofex.MarketDataEntry.BIDS.value, "-")}'
                         f'{self._asks[ticker].get(pyRofex.MarketDataEntry.OFFERS.value, "-")}')
        return repr_str

    def start_listening(self):
        """Starts data retrieving"""
        print('Rofex starting listening')
        self._running = True
        self._pyrofex_wrapper.init_websocket_connection(
            market_data_handler=self._market_data_handler,
            order_report_handler=self._order_report_handler,
            error_handler=self._error_handler,
            exception_handler=self._exception_handler)
        self._pyrofex_wrapper.market_data_subscription(
            tickers=self._futures_ticker,
            entries=self.DATA_ENTRIES)
        #Set this True to recieve order updates through websocket
        if self._subscribe_to_order_report:
            self._pyrofex_wrapper.order_report_subscription()
        print('Started')

    def stop(self):
        super().stop()
        self._pyrofex_wrapper.close_websocket_connection_safely()

    def asks(self):
        with self._asks_lock:
            copied = copy.deepcopy(self._asks)
        return copied

    def bids(self):
        with self._bids_lock:
            copied = copy.deepcopy(self._bids)
        return copied

    def place_order(self, *args, **kwargs):
        return self._pyrofex_wrapper.send_order(*args, **kwargs)

    def get_order_status(self, *args, **kwargs):
        return self._pyrofex_wrapper.get_order_status(*args, **kwargs)

    def order_execution_status(self, order_id):
        return self.get_order_status(order_id)['order']['status']

    def _market_data_handler(self, message):
        """
        Handles market data messages recieved through websocket
        Parses the data and keeps bid/ask information for each ticker
        """
        try:
            print(f'Rofex Market Data Received {message}\n', flush=True)
            ticker = message['instrumentId']['symbol']
            market_data = message['marketData']
            if market_data[pyRofex.MarketDataEntry.OFFERS.value]:
                md_entry = market_data[pyRofex.MarketDataEntry.OFFERS.value][0]
                with self._asks_lock:
                    self._asks[ticker] = OrderbookLevel(md_entry['price'], md_entry['size'])
            if market_data[pyRofex.MarketDataEntry.BIDS.value]:
                md_entry = market_data[pyRofex.MarketDataEntry.BIDS.value][0]
                with self._bids_lock:
                    self._bids[ticker] = OrderbookLevel(md_entry['price'], md_entry['size'])
            self._update_last_timestamp()
        except Exception as e:
            traceback.print_exc()
            print(f'Exception ocurred during market data handling. Stopping Rofex...')
            self.stop()

    def _order_report_handler(self, message):
        print('============ Order Report Message Received ==============')
        pprint(message)
        print('=========================================================')
        sys.stdout.flush()

    def _error_handler(self, message):
        print(f'Rofex Error Message Received: {message}')
        self.stop()

    def _exception_handler(self, e):
        print(f'Rofex Exception Occurred: {message}')
        self.stop()
