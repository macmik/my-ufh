import logging
from datetime import datetime as DT
from datetime import timedelta as TD


class EnableWhenDecreasing:
    """
    When boiler is heating (at least one of the zones need heating), check whether some other zone is in between
    expected temperature +- hysteresis and temperature is decreasing.
    It means that probably it will need heating in some near future so we can enable it right now.
    """

    def __init__(self, config, data_aggregator, zone_controllers):
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._data_aggregator = data_aggregator
        self._zone_controllers = zone_controllers
        self._check_prev_temp_time_minutes = self._config['enable_when_decreasing']['check_prev_temp_time_minutes']

    def check(self):
        self._logger.info('Starting to check EnableWhenDecreasing.')
        is_any_zone_heating = any(zone_ctrl.is_heating_required() for zone_ctrl in self._zone_controllers)

        if not is_any_zone_heating:
            self._logger.info('No heating needed. Returning.')
            return []

        not_heating_zones_names = [zone_ctrl.get_zone_name() for zone_ctrl in self._zone_controllers if not
        zone_ctrl.is_heating_required()]

        zone_measurements = self._data_aggregator.get_zone_measurements()

        zones_names_to_start_heating = [self._check_zone(name, measurement_container) for name, measurement_container
                                        in zone_measurements.items() if name in not_heating_zones_names]

        return [zone_name for zone_name in zones_names_to_start_heating if zone_name is not None]

    def _check_zone(self, name, measurements_container):
        measurements_history = measurements_container.get_measurements()
        if not measurements_history:
            return None

        now = DT.now()
        min_delta = TD(minutes=self._check_prev_temp_time_minutes)
        max_delta = TD(minutes=self._check_prev_temp_time_minutes + 10)

        last_measurement = measurements_history[-1]
        historic_measurement = None
        for measurement in reversed(measurements_history):
            diff = now - measurement.last_updated
            if min_delta <= diff <= max_delta:
                historic_measurement = measurement
                self._logger.debug(f'Found historic measurement for {name}, last={str(last_measurement)},'
                                   f'historic={str(historic_measurement)}.')
                break

        if not historic_measurement:
            self._logger.debug(f'Not found historic measurement for {name}.')
            return None

        if last_measurement.temperature - historic_measurement.temperature < 0:
            # Check whether temperature is decreasing still.
            self._logger.warning(f'EnableWhenDecreasing for {name} found!')
            return name

        return None
