import logging
from datetime import datetime as DT
from http_client import HttpClient

logger = logging.getLogger(__name__)

DIVIDERS = {
    'temperature': 100,
    'humidity': 100,
    'pressure': 1,
}


def _strptime(ts):
    print(ts)
    return DT.strptime(ts, '%Y-%m-%dT%H:%M:%S.%f')


class Sensor:
    def __init__(self, name, config):
        self._name = name
        self._config = config
        self._required_measurements = self._config['available_data']

    def collect_data(self, state_json):
        logger.debug(f'Collecting data for sensor {self._name}.')
        measurements = {}
        last_updated = None
        battery = None
        for sensor_id, data in state_json.items():
            if data['name'] != self._name:
                continue
            state = data['state']
            for measurement_name in self._required_measurements:
                if measurement_name in state:
                    measurements[measurement_name] = round(state[measurement_name] / DIVIDERS[measurement_name], 1)
            last_updated = _strptime(state['lastupdated'])
            measurements['battery'] = data['config']['battery']

        logger.debug(f'Data collected for sensor {self._name}.')
        return {
            'last_updated': last_updated.strftime('%Y%m%d-%H%M%S.%f'),
            'measurement': measurements,
        }


class PhosconInterface:
    def __init__(self, name, config):
        self._name = name
        self._config = config
        self._api_key = self._config[self._name]['api_key']
        self._sensors = {}
        self._http_client = HttpClient(
            self._config[self._name]['ip'],
            self._config[self._name]['port'],
        )
        self._init_sensors()

    def _init_sensors(self):
        for sensor_config in self._config[self._name]['sensors']:
            self._sensors[sensor_config['name']] = Sensor(sensor_config['name'], sensor_config)

    def get_measurements(self):
        logger.debug(f'Updating measurements for {self._name}.')
        current_state = self._http_client.get_json('/'.join(['api', self._api_key, 'sensors']))
        return_state = {}
        for sensor_name, sensor in self._sensors.items():
            return_state[sensor_name] = sensor.collect_data(current_state)
        return return_state
