import time
import logging
from threading import Lock
from datetime import datetime as DT

from worker import Worker
from measurement import Measurement, get_pre_initialized

logger = logging.getLogger(__name__)


class MeasurementCollector(Worker):
    def __init__(self, config, stop_event, slave_interfaces, db_handler):
        super().__init__(config, stop_event)
        self._lock = Lock()
        self._config = config
        self._refresh_interval = self._config['measurement_collector']['refresh_interval']
        self._slave_interfaces = slave_interfaces
        self._current_measurements_per_mac = {}
        self._db_handler = db_handler

    def _do(self):
        with self._lock:
            self._current_measurements_per_mac = self._collect_measurements()
        logger.info('Measurements updated.')
        time.sleep(self._refresh_interval)

    def _collect_measurements(self):
        measurements_per_mac = {}
        for interface in self._slave_interfaces:
            try:
                for mac, data in interface.get_measurements().items():
                    last_updated = DT.strptime(data['last_updated'], '%Y%m%d-%H%M%S.%f')
                    if mac in measurements_per_mac:
                        if last_updated < measurements_per_mac[mac].last_updated:
                            logger.debug(f'{mac} newer ts already in measurements. Skipping')
                            continue
                    measurement = Measurement(
                        mac=mac,
                        last_updated=last_updated,
                        **data['measurement']
                    )
                    measurements_per_mac[mac] = measurement
                    self._db_handler.add_measurement(measurement)
            except Exception as e:
                logger.error(str(e))
        return measurements_per_mac

    def get_measurements(self):
        with self._lock:
            return self._current_measurements_per_mac

    def get_measurements_by_mac(self, mac):
        if mac not in self._current_measurements_per_mac:
            logger.error(f'{mac} not found in measurements. Return preinitialized.')
            return get_pre_initialized()
        return self._current_measurements_per_mac[mac]
