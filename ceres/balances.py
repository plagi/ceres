import copy
import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class Asset(NamedTuple):
    currency: str
    free: float = 0
    used: float = 0
    total: float = 0


class Balances:
    def __init__(self, config, exchangeshandler) -> None:
        self._config = config
        self._exchangeshandler = exchangeshandler
        self._initial_balance = {}
        self.dry: bool = self._config.get("dry", True)
        self._get_initial_balance()
        # print(self._initial_balance)
        self._balance = copy.deepcopy(self._initial_balance)

    def _get_initial_balance(self):
        if self.dry:
            """
            example of balance of a exchange
            {'BTC': {'free': 1.0, 'used': 0.0, 'total': 1.0}, 'ETH': {'free': 0.0, 'used': 0.0, 'total': 0.0}}
            """
            pass
        else:
            balances = self._exchangeshandler.get_balances()
            for ex, balance in balances.items():
                bal = {}
                # print(ex, balance)
                for coin, info in balance.items():
                    # print(coin,info)
                    if coin not in ["timestamp", "datetime"]:
                        bal[coin] = Asset(
                            currency=coin,
                            free=info.get("free", 0),
                            used=info.get("used", 0),
                            total=info.get("total", 0),
                        )
                self._initial_balance[ex] = bal

    def get_free(self, exchange, currency):
        return self._balance[exchange][currency].free

    def get_total(self, exchange, currency):
        return self._balance[exchange][currency].total

    def get_total_currency(self, currency: str):
        total_balance = 0
        for exchange in self._balance:
            total_balance += self.get_total(exchange, currency)
        return total_balance

    def update_balance(self):
        balances = self._exchangeshandler.get_balances()
        for exchange, balance in balances.items():
            for coin, info in balance.items():
                if coin not in ["timestamp", "datetime"]:
                    self._balance[exchange][coin] = Asset(
                        currency=coin,
                        free=info.get("free", 0),
                        used=info.get("used", 0),
                        total=info.get("total", 0),
                    )

    def check_free_amount(self, exchange, currency, required_amount):
        free_amount = self.get_free(exchange, currency)
        return free_amount >= required_amount
