class Config:
    def __init__(self, config):
        self._config = config
        self.telegram = config.get('telegram', {})

    def get(self, name, default=None):
        return self._config.get(name, default)

    @property
    def dry(self):
        return self._config.get('dry', False)

    @property
    def symbol(self):
        return self._config.get('symbol')

    @property
    def min_profit(self):
        return self._config.get('min_profit', 0.005)

    @property
    def telegram_enabled(self):
        telegram_config = self._config.get('telegram', {})
        return telegram_config.get('enabled', False)

    @property
    def telegram_enabled(self):
        return self.telegram.get('enabled', False)

    @property
    def telegram_token(self):
        return self.telegram.get('token')

    @property
    def telegram_chat_id(self):
        return self.telegram.get('chat_id')