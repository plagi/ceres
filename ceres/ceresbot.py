import logging

from ceres.balances import Balances
from ceres.exchange import ExchangesHandler
from ceres.remote import Telegram
from ceres.strategy import SpotArbitrage


logger = logging.getLogger(__name__)


class CeresBot:
    def __init__(self, config) -> None:
        self._config = config
        if config["dry"]:
            logger.info("Bot is running in dry mode")

        self.exchangeHandler = ExchangesHandler(self._config)
        self.wallets = Balances(self._config, self.exchangeHandler)
        self.strategy = SpotArbitrage(self._config, self.exchangeHandler)
        self.symbol = config['symbol']
        counter, base = self.symbol.split("/")
        self.counter = counter
        self.base = base
        self.balances = None
        if self._config.get("telegram", None).get('enabled', False):
            self.telegram = Telegram(self._config)

    def main_loop(self):
        self.balances = self.exchangeHandler.get_balances()
        signal, orders = self.strategy.check_opportunity()
        if not signal:
            return
        logger.info(f'Creating orders now: {orders}')
        self.create_orders(orders)

    def create_orders(self, orders):
        # {'exchange_orders': {'kucoin': {'symbol': 'EVER/USDT', 'type': 'limit', 'side': 'buy', 'amount': 20,
        # 'price': 0.06682}, 'bybit': {'symbol': 'EVER/USDT', 'type': 'limit', 'side': 'sell', 'amount': 20,
        # 'price': 0.06707}}, 'profit': {'profit': 0.0009858000000000043, 'profit_pct': 9.858000000000044e-06,
        # 'fees': 0.0040142}}
        # binance.create_order('BTC/USDT', 'limit', 'buy', amount, price, params)
        balance_enough = True
        for exchange, order in orders["exchange_orders"].items():
            if order['side'] == 'sell' and (self.counter in self.balances[exchange]) and  self.balances[exchange][self.counter]['free'] < order['amount']:
                balance_enough = False
            if order['side'] == 'buy' and (self.base in self.balances[exchange]) and self.balances[exchange][self.base]['free'] < order['amount']*order['price']:
                balance_enough = False

        if balance_enough:
            self.telegram.send_message(orders)

            for exchange, order in orders["exchange_orders"].items():
                print(f"Placing {order['type']} {order['side']} order for {order['amount']} {self.symbol} @ {order['price']} on {exchange}")
                res = self.exchangeHandler.create_order(exchange, order['type'], order['side'], order['amount'], order['price'])
        else:
            print("Balance not enough")
        pass

