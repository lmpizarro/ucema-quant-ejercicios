import datetime as dt
import unittest
from unittest.mock import MagicMock, Mock, patch

from freezegun import freeze_time

import simple_trading_bot.lib.ir_expert as ire
import simple_trading_bot.lib.market_data_feeds as mdf
from simple_trading_bot.lib.instrument_expert import Future


class TestIRExpert(unittest.TestCase):
    TODAY = "2021-01-01"

    def setUp(self):
        self._current_underlier_price = 100.
        self._yfinance_md_feed_mock = MagicMock()
        self._yfinance_md_feed_mock.last_prices.return_value = {
            'GGAL': self._current_underlier_price,
            'DO': self._current_underlier_price}

        self._rofex_proxy_mock = MagicMock()
        self._rofex_proxy_mock.bids.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(115, 10), 'DOFeb21': mdf.OrderbookLevel(125, 10)}
        self._rofex_proxy_mock.asks.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(120, 10), 'DOFeb21': mdf.OrderbookLevel(130, 10)}
        self._instrument_expert_mock = MagicMock()
        self._maturity_date = dt.datetime(2021, 6, 30, 0, 0, 0, 0)
        self._instrument_expert_mock.tradeable_rofex_instruments_by_underlier_ticker.return_value = {
            'GGAL': [Future('GGALFeb21', self._maturity_date, 'GGAL', 100.)],
            'DO': [Future('DOFeb21', self._maturity_date, 'DO', 1000.)]}
        self._instrument_expert_mock.maturities_of_tradeable_tickers.return_value = {
            'GGALFeb21': 'Feb21', 'DOFeb21': 'Feb21'}
        self._ir_expert = ire.IRExpert(
            self._instrument_expert_mock,
            self._rofex_proxy_mock,
            self._yfinance_md_feed_mock)

    @freeze_time(TODAY)
    def test_update_rates_when_there_is_arb_opportunity(self):
        self._ir_expert.update_rates()
        _, max_taker_rate = self._ir_expert.max_taker_rate('Feb21')
        _, min_offered_rate = self._ir_expert.min_offered_rate('Feb21')
        self.assertTrue(max_taker_rate > min_offered_rate)


    @freeze_time(TODAY)
    def test_update_rates_when_there_is_no_arb_opportunity(self):
        self._rofex_proxy_mock.bids.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(115, 10), 'DOFeb21': mdf.OrderbookLevel(120, 10)}
        self._rofex_proxy_mock.asks.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(125, 10), 'DOFeb21': mdf.OrderbookLevel(130, 10)}
        self._ir_expert.update_rates()
        _, max_taker_rate = self._ir_expert.max_taker_rate('Feb21')
        _, min_offered_rate = self._ir_expert.min_offered_rate('Feb21')
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
            'GGALFeb21': mdf.OrderbookLevel(100, 10), 'DOFeb21': mdf.OrderbookLevel(max_taker_price, 10)}
        self._rofex_proxy_mock.asks.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(min_offered_price, 10), 'DOFeb21': mdf.OrderbookLevel(500, 10)}
        self._ir_expert.update_rates()
        _, max_taker_rate = self._ir_expert.max_taker_rate('Feb21')
        _, min_offered_rate = self._ir_expert.min_offered_rate('Feb21')
        self.assertAlmostEqual(fxd_max_taker_rate, max_taker_rate, 10)
        self.assertAlmostEqual(fxd_min_offered_rate, min_offered_rate, 10)
