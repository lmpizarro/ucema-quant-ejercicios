import datetime as dt
import unittest
from unittest.mock import MagicMock, Mock, patch

from freezegun import freeze_time

import simple_trading_bot.lib.ir_expert as ire
import simple_trading_bot.lib.market_data_feeds as mdf
from simple_trading_bot.lib.instrument_expert import Future


class TestIRExpert(unittest.TestCase):
    TODAY = "2023-04-01"

    def setUp(self):
        self.ggal = 'GGAL'
        self.dlr = 'DLR'
        self.maturity = 'MAY23'
        self.ggal_ticker = f'{self.ggal}/{self.maturity}'
        self.dlr_ticker = f'{self.dlr}/{self.maturity}'
        self._current_underlier_price = 100.
        self._yfinance_md_feed_mock = MagicMock()
        self._yfinance_md_feed_mock.last_prices.return_value = {
            self.ggal: self._current_underlier_price,
            self.dlr: self._current_underlier_price}

        self._rofex_proxy_mock = MagicMock()
        self._rofex_proxy_mock.bids.return_value = {
            self.ggal_ticker: mdf.OrderbookLevel(115, 10), self.dlr_ticker: mdf.OrderbookLevel(125, 10)}
        self._rofex_proxy_mock.asks.return_value = {
            self.ggal_ticker: mdf.OrderbookLevel(120, 10), self.dlr_ticker: mdf.OrderbookLevel(130, 10)}
        self._instrument_expert_mock = MagicMock()
        self._maturity_date = dt.datetime(2023, 5, 30, 0, 0, 0, 0)
        self._instrument_expert_mock.tradeable_rofex_instruments_by_underlier_ticker.return_value = {
            self.ggal: [Future(self.ggal_ticker, self._maturity_date, self.ggal, 100.)],
            self.dlr: [Future(self.dlr_ticker, self._maturity_date, self.dlr, 1000.)]}
        self._instrument_expert_mock.maturities_of_tradeable_tickers.return_value = {
            self.ggal_ticker: self.maturity, self.dlr_ticker: self.maturity}
        self._ir_expert = ire.IRExpert(
            self._instrument_expert_mock,
            self._rofex_proxy_mock,
            self._yfinance_md_feed_mock)

    @freeze_time(TODAY)
    def test_update_rates_when_there_is_arb_opportunity(self):
        self._ir_expert.update_rates()
        _, max_taker_rate = self._ir_expert.max_taker_rate(self.maturity)
        _, min_offered_rate = self._ir_expert.min_offered_rate(self.maturity)
        self.assertTrue(max_taker_rate > min_offered_rate)


    @freeze_time(TODAY)
    def test_update_rates_when_there_is_no_arb_opportunity(self):
        self._rofex_proxy_mock.bids.return_value = {
            self.ggal_ticker: mdf.OrderbookLevel(115, 10), self.dlr_ticker: mdf.OrderbookLevel(120, 10)}
        self._rofex_proxy_mock.asks.return_value = {
            self.ggal_ticker: mdf.OrderbookLevel(125, 10), self.dlr_ticker: mdf.OrderbookLevel(130, 10)}
        self._ir_expert.update_rates()
        _, max_taker_rate = self._ir_expert.max_taker_rate(self.maturity)
        _, min_offered_rate = self._ir_expert.min_offered_rate(self.maturity)
        self.assertTrue(max_taker_rate < min_offered_rate)

    @freeze_time(TODAY)
    def test_update_rates_using_implicit_rate_to_set_prices(self):
        fxd_max_taker_rate = 0.45
        fxd_min_offered_rate = 0.40
        days_to_maturity = (self._maturity_date - dt.datetime.now()).days
        max_taker_price = ((1 + fxd_max_taker_rate / self._ir_expert.DAYS_IN_A_YEAR) ** days_to_maturity
                           * self._current_underlier_price)
        min_offered_price = ((1 + fxd_min_offered_rate / self._ir_expert.DAYS_IN_A_YEAR) ** days_to_maturity
                           * self._current_underlier_price)

        self._rofex_proxy_mock.bids.return_value = {
            self.ggal_ticker: mdf.OrderbookLevel(100, 10), self.dlr_ticker: mdf.OrderbookLevel(max_taker_price, 10)}
        self._rofex_proxy_mock.asks.return_value = {
            self.ggal_ticker: mdf.OrderbookLevel(min_offered_price, 10), self.dlr_ticker: mdf.OrderbookLevel(500, 10)}
        self._ir_expert.update_rates()
        _, max_taker_rate = self._ir_expert.max_taker_rate(self.maturity)
        _, min_offered_rate = self._ir_expert.min_offered_rate(self.maturity)
        self.assertAlmostEqual(fxd_max_taker_rate, max_taker_rate, 10)
        self.assertAlmostEqual(fxd_min_offered_rate, min_offered_rate, 10)
