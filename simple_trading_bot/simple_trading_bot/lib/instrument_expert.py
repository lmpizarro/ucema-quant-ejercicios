import re
import datetime as dt
from dateutil.parser import parse
from collections import defaultdict

import simple_trading_bot.lib.exceptions as exc
import simple_trading_bot.lib.pyrofex_wrapper as prw


class Future:
    """
    Class to represent future contracts
    """

    def __init__(self, ticker, maturity_date, underlier_ticker, contract_size):
        self._ticker = ticker
        self._maturity_date = maturity_date
        self._underlier_ticker = underlier_ticker
        self._contract_size = contract_size

    def __repr__(self):
        return f'{self._ticker}: [{self._underlier_ticker} - {self._maturity_date} - {self._contract_size}]'

    def ticker(self):
        return self._ticker

    def maturity_date(self):
        return self._maturity_date

    def underlier_ticker(self):
        return self._underlier_ticker

    def contract_size(self):
        return self._contract_size

    def days_to_maturity(self, start_date=None):
        """
        Computes the days remaining to maturity.
        Approximation: each day counts as a whole day
        """
        start_date = start_date or dt.datetime.now()
        delta = self._maturity_date.date() - start_date.date()
        if delta.days + 1 <= 0:
            raise exc.ExpiredInstrument(self)
        return delta.days


class InstrumentExpert:
    """
    Class to handle any technicality related to instruments.
    """
    # TODO: Logic to determine whether an instrument is tradeable or not should not be here.

    def __init__(self, tickers):
        self._tickers = tickers
        self._rofex_instruments_by_underlier = defaultdict(list)
        self._rofex_instruments_by_maturity = defaultdict(list)
        self._yfinance_tickers_map = {ticker: self._yfinance_ticker(ticker) for ticker in tickers}
        self._inverse_yfinance_tickers_map = {v: k for k, v in self._yfinance_tickers_map.items()}
        self._rofex_instruments_by_ticker = {}
        self._load_rofex_instruments()

    def futures_ticker(self):
        return list(self._rofex_instruments_by_ticker.keys())

    def yfinance_tickers(self):
        return list(self._yfinance_tickers_map.values())

    def inverse_yfinance_tickers_map(self):
        return self._inverse_yfinance_tickers_map.copy()

    def rofex_instruments_by_underlier(self):
        return copy.deepcopy(self._rofex_instruments_by_underlier)

    def rofex_instruments_by_maturity(self):
        return copy.deepcopy(self._rofex_instruments_by_maturity)

    def rofex_instruments_by_ticker(self):
        return self._rofex_instruments_by_ticker.copy()

    def tradeable_maturity_tags(self):
        return list(self.tradeable_rofex_intruments_by_maturity().keys())

    def tradeable_rofex_intruments_by_maturity(self):
        return {maturity: instruments for maturity, instruments in self._rofex_instruments_by_maturity.items()
                if len(instruments) > 1}

    def maturities_of_tradeable_tickers(self):
        return {instrument.ticker(): maturity
                for maturity, instruments in self.tradeable_rofex_intruments_by_maturity().items()
                for instrument in instruments}

    def tradeable_rofex_instruments(self):
        return sum(self.tradeable_rofex_intruments_by_maturity().values(), [])

    def tradeable_rofex_tickers(self):
        return [future._ticker for future in self.tradeable_rofex_instruments()]

    def tradeable_rofex_instruments_by_underlier_ticker(self):
        tradeable_ticekrs = self.tradeable_rofex_tickers()
        return {underlier: [instrument for instrument in instruments if instrument.ticker() in tradeable_ticekrs]
                for underlier, instruments in self._rofex_instruments_by_underlier.items()}

    def tradeable_yfinance_tickers(self):
        return list(set(self._yfinance_tickers_map[future._underlier_ticker]
                        for future in self.tradeable_rofex_instruments()))

    def _load_rofex_instruments(self):
        """
        Logic to parse rofex instruments
        """
        futures_regexps = {ticker: re.compile(f'^{ticker}[A-Z][a-z][a-z]2.$') for ticker in self._tickers}
        rest_instruments = prw.PyRofexWrapper().get_detailed_instruments()
        for instrument in rest_instruments['instruments']:
            for ticker, regexp in futures_regexps.items():
                if regexp.match(instrument['instrumentId']['symbol']):
                    rofex_ticker = instrument['instrumentId']['symbol']
                    maturity_date = parse(instrument['maturityDate'])
                    contract_size = instrument['contractMultiplier']
                    future = Future(rofex_ticker, maturity_date, ticker, contract_size)
                    self._rofex_instruments_by_underlier[ticker].append(future)
                    self._rofex_instruments_by_maturity[rofex_ticker.replace(ticker, '')].append(future)
                    self._rofex_instruments_by_ticker[rofex_ticker] = future

    @staticmethod
    def _yfinance_ticker(ticker):
        if ticker == 'DO':
            return 'ARS=X'
        return ticker + '.BA'
