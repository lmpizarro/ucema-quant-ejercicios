import datetime as dt
import unittest
from unittest.mock import MagicMock, Mock, patch

import pyRofex
from freezegun import freeze_time

import simple_trading_bot.lib.ir_expert as ire
import simple_trading_bot.lib.market_data_feeds as mdf
import simple_trading_bot.lib.trader as trd
from simple_trading_bot.lib.instrument_expert import Future


class TestTrader(unittest.TestCase):
    TODAY = "2021-01-01"

    def setUp(self):
        self._current_underlier_price = 100.
        self._yfinance_md_feed_mock = MagicMock()
        last_prices = {'GGAL': self._current_underlier_price, 'DO': self._current_underlier_price}
        self._yfinance_md_feed_mock.last_prices.return_value = last_prices
        self._yfinance_md_feed_mock.price.side_effect = lambda ticker: last_prices[ticker]

        self._rofex_proxy_mock = MagicMock()
        self._rofex_proxy_mock.bids.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(115, 10), 'DOFeb21': mdf.OrderbookLevel(125, 10)}
        self._rofex_proxy_mock.asks.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(120, 10), 'DOFeb21': mdf.OrderbookLevel(130, 10)}
        self._rofex_proxy_mock.place_order.return_value = {'order': {'clientId': 'test_order_id'}}
        self._rofex_proxy_mock.order_execution_status.return_value = 'THIS IS A TEST'
        self._instrument_expert_mock = MagicMock()
        self._maturity_date = dt.datetime(2021, 6, 30, 0, 0, 0, 0)
        ggal_future = Future('GGALFeb21', self._maturity_date, 'GGAL', 100.)
        do_future = Future('DOFeb21', self._maturity_date, 'DO', 1000.)
        self._instrument_expert_mock.tradeable_rofex_instruments_by_underlier_ticker.return_value = {
            'GGAL': [ggal_future],
            'DO': [do_future]}
        self._instrument_expert_mock.rofex_instruments_by_ticker.return_value = {
            'GGALFeb21': ggal_future,
            'DOFeb21': do_future}
        self._instrument_expert_mock.maturities_of_tradeable_tickers.return_value = {
            'GGALFeb21': 'Feb21',
            'DOFeb21': 'Feb21'}
        self._instrument_expert_mock.tradeable_maturity_tags.return_value = ['Feb21']
        self._ir_expert = ire.IRExpert(
            self._instrument_expert_mock,
            self._rofex_proxy_mock,
            self._yfinance_md_feed_mock)

        self._data_update_watchman_mock = MagicMock()
        self._data_update_watchman_mock.should_update.return_value = False

        self._trader = trd.Trader(
            self._instrument_expert_mock,
            self._ir_expert,
            self._rofex_proxy_mock,
            self._yfinance_md_feed_mock,
            self._data_update_watchman_mock)

    @freeze_time(TODAY)
    def test_trader_when_there_is_arb_opportunity(self):
        self._ir_expert.update_rates()
        self._trader.evaluate_and_trade_each_maturiry()
        self.assertEqual(self._rofex_proxy_mock.place_order.call_count, 2)
        buy_order_args, sell_order_args = self._rofex_proxy_mock.place_order.call_args_list

        self.assertEqual(buy_order_args.kwargs['ticker'], 'GGALFeb21')
        self.assertEqual(buy_order_args.kwargs['side'], pyRofex.Side.BUY)
        self.assertEqual(buy_order_args.kwargs['size'], 10)
        self.assertEqual(buy_order_args.kwargs['price'], 120)
        self.assertEqual(buy_order_args.kwargs['time_in_force'], pyRofex.TimeInForce.ImmediateOrCancel)
        self.assertEqual(buy_order_args.kwargs['order_type'], pyRofex.OrderType.LIMIT)

        self.assertEqual(sell_order_args.kwargs['ticker'], 'DOFeb21')
        self.assertEqual(sell_order_args.kwargs['side'], pyRofex.Side.SELL)
        self.assertEqual(sell_order_args.kwargs['size'], 1)
        self.assertEqual(sell_order_args.kwargs['price'], 125)
        self.assertEqual(sell_order_args.kwargs['time_in_force'], pyRofex.TimeInForce.ImmediateOrCancel)
        self.assertEqual(sell_order_args.kwargs['order_type'], pyRofex.OrderType.LIMIT)

    @freeze_time(TODAY)
    def test_trader_when_there_is_no_arb_opportunity(self):
        self._rofex_proxy_mock.bids.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(115, 10), 'DOFeb21': mdf.OrderbookLevel(120, 10)}
        self._rofex_proxy_mock.asks.return_value = {
            'GGALFeb21': mdf.OrderbookLevel(125, 10), 'DOFeb21': mdf.OrderbookLevel(130, 10)}
        self._ir_expert.update_rates()
        self._trader.evaluate_and_trade_each_maturiry()
        self.assertEqual(self._rofex_proxy_mock.place_order.call_count, 0)
