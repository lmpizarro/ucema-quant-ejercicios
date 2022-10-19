from collections import namedtuple

import pyRofex

import simple_trading_bot.conf.transaction_costs as tc


class Trader:
    """
    Class to detect IR arbitrage opportunities and place orders in the exchange.
    """
    def __init__(
            self,
            instrument_expert,
            ir_expert,
            rofex_proxy,
            yfinance_md_feed,
            data_update_watchman):
        self._futures_by_ticker = instrument_expert.rofex_instruments_by_ticker()
        self._maturity_tags = instrument_expert.tradeable_maturity_tags()
        self._ir_expert = ir_expert
        self._rofex_proxy = rofex_proxy
        self._yfinance_md_feed = yfinance_md_feed
        self._data_update_watchman = data_update_watchman

    def evaluate_and_trade_each_maturiry(self):
        for maturity_tag in self._maturity_tags:
            if self._ir_expert.maturiry_ready_to_trade(maturity_tag):
                self.evaluate_and_trade_single_maturity(maturity_tag)

    def evaluate_and_trade_single_maturity(self, maturity_tag):
        """Look for implicit rate arbitrage opportunities and place orders if found."""
        #Try to sell the more expensive taker and buy the cheaper offered.
        ticker_to_sell, max_taker_rate = self._ir_expert.max_taker_rate(maturity_tag=maturity_tag)
        ticker_to_buy, min_offered_rate = self._ir_expert.min_offered_rate(maturity_tag=maturity_tag)
        #Strong assumption: transaction cost can be expressed as a constant rate difference.
        if not max_taker_rate - min_offered_rate > tc.TRANSACITON_COST:
            return
        #If arb opportunity found determines the trade size.
        future_to_buy = self._futures_by_ticker[ticker_to_buy]
        future_to_sell = self._futures_by_ticker[ticker_to_sell]
        #Get the spot prices for the underliers.
        underlier_to_buy = future_to_sell.underlier_ticker()
        underlier_buy_price = self._yfinance_md_feed.price(underlier_to_buy)
        underlier_to_sell = future_to_buy.underlier_ticker()
        underlier_sell_price = self._yfinance_md_feed.price(underlier_to_sell)

        future_asks = self._rofex_proxy.asks()
        future_bids = self._rofex_proxy.bids()
        available_buy_size = future_asks[ticker_to_buy].size
        available_sell_size = future_bids[ticker_to_sell].size
        #Minimum available size in cash amount.
        amount_to_trade = min(
            available_buy_size * future_to_buy.contract_size() * underlier_sell_price,
            available_sell_size * future_to_sell.contract_size() * underlier_buy_price)
        #Round up the sizes (in contract units). This has issues when few contracts are available.
        buy_size = int(amount_to_trade / future_to_buy.contract_size() / underlier_sell_price + 0.5)
        sell_size = int(amount_to_trade / future_to_sell.contract_size() / underlier_buy_price + 0.5)
        buy_price = future_asks[ticker_to_buy].price
        sell_price = future_bids[ticker_to_sell].price
        underlier_buy_size = sell_size * future_to_sell.contract_size()
        underlier_sell_size = buy_size * future_to_buy.contract_size()
        #Estimate the profit.
        trade_rate_profit = (max_taker_rate - min_offered_rate - tc.TRANSACITON_COST)
        av_position_to_take = (underlier_buy_size * underlier_buy_price +
                               underlier_sell_size * underlier_sell_price) * 0.5
        #If the data is not ahead and order sizes make sense, place orders and print trade info.
        if not self._data_update_watchman.should_update() and (buy_size * sell_size) > 0:
            #Either pyRofex or remarkets seems not to be allowing Market orders
            #so we need to use Limits with the correct price
            buy_order = self._rofex_proxy.place_order(
                ticker=ticker_to_buy,
                side=pyRofex.Side.BUY,
                size=buy_size,
                price=buy_price,
                time_in_force=pyRofex.TimeInForce.ImmediateOrCancel,
                order_type=pyRofex.OrderType.LIMIT)
            sell_order = self._rofex_proxy.place_order(
                ticker=ticker_to_sell,
                side=pyRofex.Side.SELL,
                size=sell_size,
                price=sell_price,
                time_in_force=pyRofex.TimeInForce.ImmediateOrCancel,
                order_type=pyRofex.OrderType.LIMIT)

            #TODO: improve order tracking.
            #TODO: wrap trade info and use a printer class.
            trade_info = [
                f'--- Trade Info For Tenure {maturity_tag} ---',
                'Rate long side:',
                f'Buy:      {ticker_to_buy:<12} -> {buy_size:>8} @ {buy_price:.2f}',
                f'Sell:     {underlier_to_sell:<12} -> {underlier_sell_size:>8} @ {underlier_sell_price:.2f}',
                f'Imp Rate: {min_offered_rate:.6f}',
                f'Traded amount: {underlier_sell_size * underlier_sell_price:.2f}',
                f'Order reception info:   {buy_order}',
                f'Order execution status: {self._rofex_proxy.order_execution_status(buy_order["order"]["clientId"])}',
                f'---',
                f'Rate short side:',
                f'Sell:     {ticker_to_sell:<12} -> {sell_size:>8} @ {sell_price:.2f}',
                f'Buy:      {underlier_to_buy:<12} -> {underlier_buy_size:>8} @ {underlier_buy_price:.2f}',
                f'Imp Rate: {max_taker_rate:.6f}',
                f'Traded amount: {underlier_buy_size * underlier_buy_price:.2f}',
                f'Order reception info:   {sell_order}',
                f'Order execution status: {self._rofex_proxy.order_execution_status(sell_order["order"]["clientId"])}',
                f'--------------------------------------------',
                f'Trade rate profit:     {trade_rate_profit:.6f}',
                f'Average position size: {av_position_to_take:.2f}',
                f'--------------------------------------------',
                '']

            print('\n'.join(trade_info), flush=True)

