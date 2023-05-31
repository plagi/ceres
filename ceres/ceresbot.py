import logging

from ceres.balances import Balances
from ceres.exchange import ExchangesHandler
from ceres.remote import Telegram
from ceres.strategy import SpotArbitrage
from ceres.config import Config


logger = logging.getLogger(__name__)


class CeresBot:
    def __init__(self, config) -> None:
        self.config = Config(config)

        if self.config.dry:
            logger.info("Bot is running in dry mode")

        self.exchangeHandler = ExchangesHandler(self.config)
        self.wallets = Balances(self.config, self.exchangeHandler)
        self.strategy = SpotArbitrage(self.config, self.exchangeHandler)
        self.symbol = self.config.symbol
        self.min_profit = self.config.min_profit
        counter, base = self.symbol.split("/")
        self.counter = counter
        self.base = base
        self.balances = None
        self.total_trades = 0
        self.total_profit = 0
        self.total_turnover = 0
        if self.config.telegram_enabled:
            self.telegram = Telegram(self.config)

    def main_loop(self):
        self.balances = self.exchangeHandler.get_balances()
        signal, orders = self.strategy.check_opportunity()
        if not signal:
            return
        if float(orders['profit']['profit']) > 0.005:
            logger.info(f'Creating orders now: {orders}')
            self.create_orders(orders)
        else:
            logger.info(f'Profit too low: {orders["profit"]["profit"]}')

    def check_balance(self, orders):
        for exchange, order in orders["exchange_orders"].items():
            if self.is_balance_insufficient(exchange, order):
                return False
        return True

    def is_balance_insufficient(self, exchange, order):
        if order['side'] == 'sell' and (self.counter in self.balances[exchange]) and  self.balances[exchange][self.counter]['free'] < order['amount']:
            return True
        if order['side'] == 'buy' and (self.base in self.balances[exchange]) and self.balances[exchange][self.base]['free'] < order['amount']*order['price']:
            return True
        return False

    def get_summary_message(self, orders):
        msg = f"Profit: {orders['profit']['profit']} Total: { format(self.total_profit, '.5f') } Trades: {self.total_trades} Turnover: {self.total_turnover}  {self.counter}\n"
        counter_balance = 0
        base_balance = 0
        for exchange, balance in self.balances.items():
            counter_balance += balance[self.counter]['total']
            base_balance += balance[self.base]['total']
        msg += f"Balance: { format(counter_balance, '.2f') } {self.counter} {format(base_balance, '.2f')} {self.base}"
        return msg

    def execute_orders(self, orders):
        msg = ""
        self.total_profit += float(orders['profit']['profit'])
        self.total_trades += 1

        for exchange, order in orders["exchange_orders"].items():
            print(f"Placing {order['type']} {order['side']} order for {order['amount']} {self.symbol} @ {order['price']} on {exchange}")
            msg += f"{order['side']} {order['amount']} {self.symbol} @ {order['price']} on {exchange} \n"
            self.total_turnover += order['amount']
            res = self.exchangeHandler.create_order(exchange, order['type'], order['side'], order['amount'], order['price'])
        msg += self.get_summary_message(orders)
        self.telegram.send_message(msg)

    def create_orders(self, orders):
        balance_enough = self.check_balance(orders)
        if balance_enough:
            self.execute_orders(orders)
        else:
            print("Balance not enough")

