import time
import logging
from worker import Worker
from datetime import timedelta as TD
from datetime import datetime as DT


class ZoneMeasurementsContainer:
    def __init__(self, zone_name, config):
        self._logger = logging.getLogger(__name__)
        self._logger.info(f'Initializing zone measurement container for {zone_name}.')
        self._zone_name = zone_name
        self._config = config
        self._measurements = []
        self._max_time_delta_days = TD(days=self._config['data_aggregator']['keep_data_time_days'])

    def add(self, measurement):
        self._measurements.append(measurement)
        self._maintain_queue()

    def get_measurements(self):
        return self._measurements

    def get_zone_name(self):
        return self._zone_name

    def _maintain_queue(self):
        filtered_measurements = []
        current_timestamp = DT.utcnow()
        for measurement in self._measurements:
            if current_timestamp - measurement.last_updated > self._max_time_delta_days:
                continue
            filtered_measurements.append(measurement)
        self._measurements = filtered_measurements


class DataAggregator(Worker):
    def __init__(self, config, stop_event, zone_controllers):
        super().__init__(config, stop_event)
        self._logger = logging.getLogger(__name__)
        self._logger.info('Initializing DataAggregator.')
        self._zone_controllers = zone_controllers
        self._refresh_interval = self._config['data_aggregator']['refresh_interval_sec']
        self._zone_measurements = {
            zone_controller.get_zone_name(): ZoneMeasurementsContainer(zone_controller.get_zone_name(), config) for
            zone_controller in
            self._zone_controllers}

    def _do(self):
        self._logger.info('Updating data in DataAggregator.')
        self._update_zone_measurements()
        time.sleep(self._refresh_interval)

    def _update_zone_measurements(self):
        for zone_controller in self._zone_controllers:
            measurement = zone_controller.get_last_measurement()
            if measurement.temperature is None:
                continue
            self._zone_measurements[zone_controller.get_zone_name()].add(zone_controller.get_last_measurement())

    def get_zone_measurements(self):
        return self._zone_measurements