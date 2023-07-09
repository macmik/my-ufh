from http_client import HttpClient
from common import RelayType


class SlaveInterface:
    def __init__(self, name, config):
        self._name = name
        self._config = config
        self._relay_type = RelayType(self._config['slaves'][name]['relay_type'])
        self._relay_enable_value = 1 if self._relay_type is RelayType.HIGH_ENABLED else 0
        self._relay_disable_value = int(not self._relay_enable_value)
        self._ip = self._config['slaves'][name]['ip']
        self._temperature_http_client = HttpClient(
            self._ip, self._config['slaves'][name]['temperatures_app_port'],
        )
        self._relay_controller_client = HttpClient(
            self._ip, self._config['slaves'][name]['relay_controller_app_port'],
        )

    def get_measurements(self):
        return self._temperature_http_client.get_json('state')

    def enable_loop(self, gpio):
        print('enable', self._relay_controller_client._address, gpio, self._relay_enable_value)
        self._relay_controller_client.post('set', params={'gpio': gpio, 'value': self._relay_enable_value})

    def disable_loop(self, gpio):
        print('disable', self._relay_controller_client._address, gpio, self._relay_enable_value)
        self._relay_controller_client.post('set', params={'gpio': gpio, 'value': self._relay_disable_value})

    def get_loop_state(self, gpio):
        return self._relay_controller_client.get_json('get', params={'gpio': gpio})
