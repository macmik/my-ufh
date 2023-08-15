from relay_handler import RelayHandler


class BoilerHandler:
    def __init__(self, config):
        self._config = config
        self._relay_handler = RelayHandler(
            ip=config['boiler']['ip'],
            port=config['boiler']['port'],
            _type=config['boiler']['relay_type'],
            config=self._config,
        )
        self._gpio = self._config['boiler']['gpio']

    def heat(self):
        self._relay_handler.enable(self._gpio)

    def not_heat(self):
        self._relay_handler.disable(self._gpio)