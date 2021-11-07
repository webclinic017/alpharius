import alpharius
import collections
import datetime
import pandas as pd
import unittest.mock as mock

Clock = collections.namedtuple('Clock', ['next_open', 'next_close'])
Asset = collections.namedtuple('Asset', ['symbol', 'tradable', 'marginable',
                                         'shortable', 'easy_to_borrow'])
Account = collections.namedtuple('Account', ['equity', 'cash'])
Position = collections.namedtuple('Position', ['symbol', 'qty', 'current_price',
                                               'market_value', 'cost_basis',
                                               'avg_entry_price', 'change_today',
                                               'unrealized_plpc'])
Order = collections.namedtuple('Order', ['id', 'symbol', 'side', 'qty', 'notional',
                                         'filled_qty', 'filled_at', 'filled_avg_price'])
History = collections.namedtuple('History', ['equity'])
PolygonResponse = collections.namedtuple('PolygonResponse', ['status', 'results'])


class FakeAlpaca:

    def __init__(self):
        self.get_account_call_count = 0
        self.list_assets_call_count = 0
        self.get_clock_call_count = 0
        self.list_orders_call_count = 0
        self.list_positions_call_count = 0
        self.submit_order_call_count = 0
        self.cancel_order_call_count = 0
        self.get_portfolio_history_call_count = 0

    def get_account(self):
        self.get_account_call_count += 1
        return Account('2000', '2000')

    def list_assets(self):
        self.list_assets_call_count += 1
        return [Asset(symbol, True, True, True, True)
                for symbol in ['QQQ', 'SPY', 'DIA', 'TQQQ']]

    def list_positions(self):
        self.list_positions_call_count += 1
        return [Position('QQQ', '10', '10.0', '100.0', '99.0', '9.9', '0.01', '0')]

    def get_clock(self):
        self.get_clock_call_count += 1
        next_open = mock.Mock()
        next_open.timestamp.return_value = 1615987800
        next_close = mock.Mock()
        next_close.timestamp.return_value = 1616007600
        return Clock(next_open, next_close)

    def list_orders(self, *args, **kwargs):
        self.list_orders_call_count += 1
        return [Order('ORDER123', 'DIA', 'short', '14', None, '0', '2021-03-17T10:15:00.0Z', '12'),
                Order('ORDER123', 'SPY', 'long', '12', None, '1', '2021-03-17T10:20:00.0Z', '13')]

    def submit_order(self, *args, **kwargs):
        self.submit_order_call_count += 1

    def cancel_order(self, *args, **kwargs):
        self.cancel_order_call_count += 1

    def get_portfolio_history(self, *args, **kwargs):
        self.get_portfolio_history_call_count += 1
        return History([i + 100 for i in range(10)])


class FakePolygon:

    def __init__(self):
        self.stocks_equities_aggregates_call_count = 0

    def stocks_equities_aggregates(self, ticker, multiplier, timespan, *args, **kwargs):
        self.stocks_equities_aggregates_call_count += 1
        results = []
        if multiplier == 1 and timespan == 'day':
            results = [{'t': str(t * 1000), 'o': 40, 'h': 41, 'l': 39, 'c': 40.5, 'vw': 40.123, 'v': 10}
                       for t in range(int(pd.to_datetime('2021-02-17').timestamp()),
                                      int(pd.to_datetime('2021-03-19').timestamp()),
                                      86400)]
        elif multiplier == 5 and timespan == 'minute':
            results = [{'t': str(t * 1000), 'o': 40, 'h': 41, 'l': 39, 'c': 40.5, 'vw': 40.123, 'v': 10}
                       for t in range(int(pd.to_datetime('2021-03-17 09:30:00-04:00').timestamp()),
                                      int(pd.to_datetime('2021-03-17 16:05:00-04:00').timestamp()),
                                      300)]

        return PolygonResponse('OK', results)


class FakeProcess(alpharius.Processor):
    def __init__(self, trading_frequency):
        super().__init__()
        self.get_stock_universe_call_count = 0
        self.process_data_call_count = 0
        self.trading_frequency = trading_frequency

    def get_trading_frequency(self):
        return self.trading_frequency

    def get_stock_universe(self, view_time):
        self.get_stock_universe_call_count += 1
        return ['QQQ', 'SPY', 'DIA']

    def process_data(self, context):
        self.process_data_call_count += 1
        if context.current_time.time() == datetime.time(10, 0) and context.symbol == 'QQQ':
            return alpharius.Action('QQQ', alpharius.ActionType.BUY_TO_OPEN, 1, 51)
        if context.current_time.time() == datetime.time(10, 0) and context.symbol == 'DIA':
            return alpharius.Action('DIA', alpharius.ActionType.BUY_TO_OPEN, 1, 51)
        if context.current_time.time() == datetime.time(11, 30) and context.symbol == 'QQQ':
            return alpharius.Action('QQQ', alpharius.ActionType.SELL_TO_CLOSE, 1, 52)
        if context.current_time.time() == datetime.time(12, 0) and context.symbol == 'DIA':
            return alpharius.Action('DIA', alpharius.ActionType.SELL_TO_CLOSE, 1, 52)
        if context.current_time.time() == datetime.time(13, 0) and context.symbol == 'DIA':
            return alpharius.Action('DIA', alpharius.ActionType.SELL_TO_OPEN, 1, 52)
        if context.current_time.time() == datetime.time(13, 10) and context.symbol == 'DIA':
            return alpharius.Action('DIA', alpharius.ActionType.BUY_TO_CLOSE, 1, 50)
        if context.current_time.time() == datetime.time(16, 0) and context.symbol == 'SPY':
            return alpharius.Action('SPY', alpharius.ActionType.BUY_TO_OPEN, 1, 50)


class FakeProcessorFactory(alpharius.ProcessorFactory):

    def __init__(self, trading_frequency: alpharius.TradingFrequency):
        super().__init__()
        self.create_call_count = 0
        self.processor = FakeProcess(trading_frequency)

    def create(self, *args, **kwargs):
        self.create_call_count += 1
        return self.processor
