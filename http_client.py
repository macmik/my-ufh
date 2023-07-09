import requests


class HttpClient:
    def __init__(self, ip, port):
        self._session = requests.Session()
        self._ip = ip
        self._port = port
        self._address = 'http://' + self._ip + ':' + str(self._port)

    def get_json(self, endpoint, params=None):
        return self._session.get(self._address + '/' + endpoint, params=params, timeout=5.0).json()

    def post(self, endpoint, params=None):
        self._session.post(self._address + '/' + endpoint, params=params, timeout=5.0)
