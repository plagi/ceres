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
        print(self.wallets)
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
        self.wallets.update_balance()
        signal, orders = self.strategy.check_opportunity()
        if not signal:
            return
        if float(orders['profit']['profit']) > self.min_profit and self.check_balance(orders):
            logger.info(f'Creating orders now: {orders}')
            self.execute_orders(orders)
        else:
            logger.info(f'Profit too low: {orders["profit"]["profit"]} or balance not enough')

    def check_balance(self, orders):
        for exchange, order in orders["exchange_orders"].items():
            if self.is_balance_insufficient(exchange, order):
                return False
        return True

    def is_balance_insufficient(self, exchange, order):
        if order['side'] == 'sell':
            return not self.wallets.check_free_amount(exchange, self.counter, order['amount'])
        if order['side'] == 'buy':
            return not self.wallets.check_free_amount(exchange, self.base, order['amount']*order['price'])
        return False

    def get_summary_message(self, orders):
        msg = f"Profit: {orders['profit']['profit']} Total: {format(self.total_profit, '.5f')} Trades: {self.total_trades} Turnover: {self.total_turnover}  {self.counter}\n"
        counter_balance = self.wallets.get_total_currency(self.counter)
        counter_balance_base = list(orders['exchange_orders'].items())[0][1]['price'] * counter_balance
        base_balance = self.wallets.get_total_currency(self.base)
        msg += f"Balance: {format(counter_balance, '.2f')} {self.counter} ({format(counter_balance_base, '.2f')} {self.base}) {format(base_balance, '.2f')} {self.base} ({format(base_balance + counter_balance_base, '.2f')} {self.base})"
        return msg

    def execute_orders(self, orders):
        msg = ""
        self.total_profit += float(orders['profit']['profit'])
        self.total_trades += 1
        for exchange, order in orders["exchange_orders"].items():
            logger.info(f"Placing {order['type']} {order['side']} order for {order['amount']} {self.symbol} @ {order['price']} on {exchange}")
            msg += f"{order['side']} {order['amount']} {self.symbol} @ {order['price']} on {exchange} \n"
            self.total_turnover += order['amount']
            res = self.exchangeHandler.create_order(exchange, order['type'], order['side'], order['amount'], order['price'])
        msg += self.get_summary_message(orders)
        self.telegram.send_message(msg)
