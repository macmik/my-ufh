import time
import logging
from worker import Worker
from heating.methods.enable_when_decreasing import EnableWhenDecreasing


class HeatingManager(Worker):
    def __init__(self, config, stop_event, data_aggregator, zone_controllers):
        super().__init__(config, stop_event)
        self._logger = logging.getLogger(__name__)
        self._data_aggregator = data_aggregator
        self._zone_controllers = zone_controllers
        self._refresh_interval = self._config['heating_manager']['refresh_interval_sec']
        self._methods = [EnableWhenDecreasing(
            config, data_aggregator, zone_controllers,
        )]

    def _do(self):
        zones_to_start_heating = set()
        for method in self._methods:
            zones_to_start_heating.update(method.check())

        self._logger.info(f'Found zones to start heating {str(zones_to_start_heating)}.')

        for zone_name in zones_to_start_heating:
            for zone_ctrl in zone_name:
                if zone_ctrl.get_zone_name() == zone_name:
                    self._logger.info(f'Staring to heat {zone_name}.')
                    zone_ctrl.enable_heat()

        time.sleep(self._refresh_interval)
