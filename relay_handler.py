from http_client import HttpClient
from common import RelayType


class RelayHandler:
    def __init__(self, ip, port, _type, config):
        self._type = _type
        self._relay_type = RelayType(_type)
        self._config = config
        self._relay_controller_client = HttpClient(ip, port)

    def enable(self, gpio):
        self._relay_controller_client.post('set', params={'gpio': gpio, 'value': self._relay_type.enable})

    def disable(self, gpio):
        self._relay_controller_client.post('set', params={'gpio': gpio, 'value': self._relay_type.disable})

    def get_gpio_state(self, gpio):
        return self._relay_controller_client.get_json('get', params={'gpio': gpio})
