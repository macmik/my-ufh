import time
import logging
from threading import Event
from datetime import datetime as DT

from worker import Worker
from boiler_handler import BoilerHandler
from heating_time_collector import HeatingTimeCollector

logger = logging.getLogger(__name__)


class HeatingSupervisor(Worker):
    def __init__(self, config, stop_event, zones_controllers):
        super().__init__(config, stop_event)
        self._heating_time_collector = HeatingTimeCollector(config)
        self._zones_controllers = zones_controllers
        self._boiler_handler = BoilerHandler(config)
        self._is_boiler_heating = False
        self._sleep_time = self._config['supervisor']['refresh_interval']
        self._start_heating_ts = None
        self._stop_heating()
        self._heating_event = Event()
        self._heating_event.set()

    def _do(self):
        if not self._heating_event.is_set():
            logger.debug('Heating disabled.')
            if self._is_boiler_heating:
                self._stop_heating()
            time.sleep(self._sleep_time)
            return
        heating_required = any(ctrl.is_heating_required() for ctrl in self._zones_controllers)
        if heating_required and not self._is_boiler_heating:
            self._start_heating()
        elif not heating_required and self._is_boiler_heating:
            self._stop_heating()
        logger.debug(f'Heating required = {heating_required}.')
        time.sleep(self._sleep_time)

    def _start_heating(self):
        self._boiler_handler.heat()
        self._is_boiler_heating = True
        self._start_heating_ts = DT.now()
        logger.debug('Heating started.')

    def _stop_heating(self):
        self._boiler_handler.not_heat()
        self._is_boiler_heating = False
        if self._start_heating_ts:
            self._heating_time_collector.add(self._start_heating_ts, DT.now())
        logger.debug('Heating stopped.')

    def user_stop_heating(self):
        logger.debug('User requested disable heating.')
        self._heating_event.clear()

    def user_start_heating(self):
        logger.debug('User requested enable heating.')
        self._heating_event.set()

    def get_heating_time_collector(self):
        return self._heating_time_collector
