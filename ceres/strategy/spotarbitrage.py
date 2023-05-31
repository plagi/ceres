import logging

from ceres.strategy.strategybase import StrategyBase

logger = logging.getLogger(__name__)


class Fees:
    def __init__(self):
        self.fees = {}

    def update(self, ex, m):
        self.fees[ex] = {
            "taker": m.get("taker", 0.001),
            "maker": m.get("maker", 0.001),
        }


class OrderBook:
    def __init__(self):
        self.bids = {}
        self.asks = {}

    def update(self, ex, obs):
        self.bids[ex] = obs[ex]["bids"][0][0]
        self.asks[ex] = obs[ex]["asks"][0][0]


class SpotArbitrage(StrategyBase):
    def __init__(self, config, exchangeshandler) -> None:
        super().__init__(config, exchangeshandler)
        self.symbol = self._config.get("symbol")
        self.order_size = self._config.get("order_size", 0)
        self.order_book = OrderBook()
        self.fees = Fees()
        self._get_fees()

    def _get_fees(self):
        """
        if not dry check for potential other fees if high vip ot other
        """
        markets = self.exchangeshandler.get_markets()
        for ex, market in markets.items():
            m = market.get(self.symbol, None)
            if m:
                self.fees.update(ex, m)
        logger.info(f"Fees per exchange: {self.fees.fees}")

    def check_opportunity(self):
        self._get_orderbook_data()
        return self._check_profit()

    def _get_orderbook_data(self):
        obs = self.exchangeshandler.watch_order_books(self.symbol)
        for ex in self.exchangeshandler.current_exchanges:
            self.order_book.update(ex, obs)

    def _check_profit(self):
        min_ask_ex = min(self.order_book.asks, key=self.order_book.asks.get)
        max_bid_ex = max(self.order_book.bids, key=self.order_book.bids.get)
        min_ask_price = self.order_book.asks[min_ask_ex]
        max_bid_price = self.order_book.bids[max_bid_ex]

        min_fee = self.order_size * min_ask_price * self.fees.fees[min_ask_ex]["taker"]
        max_fee = self.order_size * max_bid_price * self.fees.fees[max_bid_ex]["taker"]

        price_profit = max_bid_price - min_ask_price
        profit = (price_profit * self.order_size) - (min_fee + max_fee)
        profit_pct = profit / 100

        logger.debug(
            f"{self.symbol}: Profit after fees: {profit}, buy exchange {min_ask_ex} at: {min_ask_price}, sell exchange {max_bid_ex} at: {max_bid_price}"
        )

        if profit > 0:
            orders = self._create_orders(min_ask_ex, min_ask_price, max_bid_ex, max_bid_price, profit, profit_pct,
                                     min_fee, max_fee)
            logger.info(f'Found arbitrage opportunity for {self.symbol} between {min_ask_ex} and {max_bid_ex}')
            return True, orders

        return False, {}

    def _create_orders(self, min_ask_ex, min_ask_price, max_bid_ex, max_bid_price, profit, profit_pct, min_fee,
                       max_fee):
        return {
            'exchange_orders': {
                min_ask_ex: {
                    'symbol': self.symbol,
                    'type': 'limit',
                    'side': 'buy',
                    'amount': self.order_size,
                    'price': min_ask_price
                },
                max_bid_ex: {
                    'symbol': self.symbol,
                    'type': 'limit',
                    'side': 'sell',
                    'amount': self.order_size,
                    'price': max_bid_price
                }
            },
            'profit': {
                'profit': "%.5f" % profit,
                'profit_pct': "%.6f" % profit_pct,
                'fees': min_fee + max_fee
            }
        }
