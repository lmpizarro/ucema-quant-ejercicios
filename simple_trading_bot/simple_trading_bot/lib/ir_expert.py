import copy
from collections import defaultdict


class IRExpert:
    """
    Class to compute implicit rates
    """
    DAYS_IN_A_YEAR = 365

    def __init__(self, instrument_expert, rofex_proxy, yfinance_md_feed):
        self._futures_by_underlier_ticker = instrument_expert.tradeable_rofex_instruments_by_underlier_ticker()
        self._maturiries_by_ticker = instrument_expert.maturities_of_tradeable_tickers()
        self._rofex_proxy = rofex_proxy
        self._yfinance_md_feed = yfinance_md_feed
        self._taker_rates = defaultdict(dict)
        self._offered_rates = defaultdict(dict)

    def update_rates(self):
        """
        Updates the implicit rates and organize them by maturity date and ticker
        """
        underlier_prices = self._yfinance_md_feed.last_prices()
        future_bids = self._rofex_proxy.bids()
        future_asks = self._rofex_proxy.asks()
        self._taker_rates = defaultdict(dict)
        self._offered_rates = defaultdict(dict)
        for ticker, underlier_price in underlier_prices.items():
            for future in self._futures_by_underlier_ticker[ticker]:
                future_ticker = future.ticker()
                days_to_maturity = future.days_to_maturity()
                maturity_tag = self._maturiries_by_ticker[future_ticker]
                if future_ticker in future_bids:
                    self._taker_rates[maturity_tag][future_ticker] = self._implicit_rate(
                        future_bids[future_ticker].price,
                        underlier_price,
                        days_to_maturity)
                if future_ticker in future_asks:
                    self._offered_rates[maturity_tag][future_ticker] = self._implicit_rate(
                        future_asks[future_ticker].price,
                        underlier_price,
                        days_to_maturity)

    def taker_rates(self):
        return copy.deepcopy(self._taker_rates)

    def offered_rates(self):
        return copy.deepcopy(self._offered_rates)

    def max_taker_rate(self, maturity_tag):
        return max(self._taker_rates[maturity_tag].items(), key=lambda each: each[1])

    def min_offered_rate(self, maturity_tag):
        return min(self._offered_rates[maturity_tag].items(), key=lambda each: each[1])

    def ready(self):
        return self._taker_rates and self._offered_rates

    def maturiry_ready_to_trade(self, maturity_tag):
        return self._taker_rates[maturity_tag] and self._offered_rates[maturity_tag]

    def _implicit_rate(self, maturity_price, current_price, days_to_maturity):
        """
        Anualized implicit rate computed using Actual/DAYS_IN_A_YEAR
        day count convention and daily compounding.
        """
        return ((maturity_price / current_price) ** (1 / days_to_maturity) - 1) * self.DAYS_IN_A_YEAR



