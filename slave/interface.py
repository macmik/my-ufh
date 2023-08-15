from http_client import HttpClient
from relay_handler import RelayHandler


class SlaveInterface:
    def __init__(self, name, config):
        self._name = name
        self._config = config
        self._ip = self._config['slaves'][name]['ip']
        self._relay_handler = RelayHandler(
            self._ip,
            self._config['slaves'][name]['relay_controller_app_port'],
            self._config['slaves'][name]['relay_type'],
            self._config
        )
        self._temperature_http_client = HttpClient(
            self._ip, self._config['slaves'][name]['temperatures_app_port'],
        )

    def get_measurements(self):
        return self._temperature_http_client.get_json('state')

    def enable_loop(self, gpio):
        self._relay_handler.enable(gpio)

    def disable_loop(self, gpio):
        self._relay_handler.disable(gpio)

    def get_loop_state(self, gpio):
        return self._relay_handler.get_gpio_state(gpio)
