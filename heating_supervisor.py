import time
import logging

from worker import Worker
from boiler_handler import BoilerHandler

logger = logging.getLogger(__name__)


class HeatingSupervisor(Worker):
    def __init__(self, config, stop_event, zones_controllers):
        super().__init__(config, stop_event)
        self._zones_controllers = zones_controllers
        self._boiler_handler = BoilerHandler(config)
        self._is_boiler_heating = False
        self._sleep_time = self._config['supervisor']['refresh_interval']

    def _do(self):
        heating_required = any(ctrl.is_heating_required() for ctrl in self._zones_controllers)
        if heating_required and not self._is_boiler_heating:
            self._start_heating()
        elif not heating_required and self._is_boiler_heating:
            self._stop_heating()

        time.sleep(self._sleep_time)

    def _start_heating(self):
        self._boiler_handler.heat()
        self._is_boiler_heating = True
        logger.debug('Heating started.')

    def _stop_heating(self):
        self._boiler_handler.not_heat()
        self._is_boiler_heating = False
        logger.debug('Heating stopped.')
