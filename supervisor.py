import logging
import time

from worker import Worker

logger = logging.getLogger(__name__)


class Supervisor(Worker):
    def __init__(self, config, stop_event, zones_controllers):
        super().__init__(config, stop_event)
        self._zones_controllers = zones_controllers

    def _do(self):
        boiler_heating_required = any(ctrl.is_heating_required() for ctrl in self._zones_controllers)
        logger.debug(f'Boiler heating required={boiler_heating_required}.')
        time.sleep(self._config['supervisor']['refresh_interval'])
