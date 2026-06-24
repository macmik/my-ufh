import json
import time
import logging
from pathlib import Path
from threading import Event
from datetime import datetime as DT
from datetime import timedelta as TD


from worker import Worker
from boiler_handler import BoilerHandler
from heating_time_collector import HeatingTimeCollector

logger = logging.getLogger(__name__)

USER_HEATING_STATE_PATH = Path('data/user_heating_state.json')


class HeatingSupervisor(Worker):
    def __init__(self, config, stop_event, zones_controllers, db_handler):
        super().__init__(config, stop_event)
        self._heating_time_collector = HeatingTimeCollector(config)
        self._zones_controllers = zones_controllers
        self._boiler_handler = BoilerHandler(config)
        self._db_handler = db_handler
        self._is_boiler_heating = False
        self._sleep_time = self._config['supervisor']['refresh_interval']
        self._start_heating_ts = None
        self._stop_heating()
        self._heating_event = Event()
        if self._load_user_heating_state():
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
            end_ts = DT.now()
            self._heating_time_collector.add(self._start_heating_ts, end_ts)
            self._db_handler.add_boiler_heating_time_raw(self._start_heating_ts, end_ts)
            self._db_handler.add_boiler_heating_time_hours(self._start_heating_ts, end_ts)
        logger.debug('Heating stopped.')

    def user_stop_heating(self):
        logger.debug('User requested disable heating.')
        self._heating_event.clear()
        self._save_user_heating_state(False)

    def user_start_heating(self):
        logger.debug('User requested enable heating.')
        self._heating_event.set()
        self._save_user_heating_state(True)

    @staticmethod
    def _load_user_heating_state():
        if not USER_HEATING_STATE_PATH.exists():
            return True
        try:
            data = json.loads(USER_HEATING_STATE_PATH.read_text())
            return bool(data.get('heating_enabled', True))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning('Could not load user heating state, defaulting to enabled: %s', e)
            return True

    @staticmethod
    def _save_user_heating_state(enabled):
        try:
            USER_HEATING_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            USER_HEATING_STATE_PATH.write_text(
                json.dumps({'heating_enabled': enabled}, indent=4)
            )
        except OSError as e:
            logger.error('Could not save user heating state: %s', e)

    def get_user_heating_enabled(self):
        return self._heating_event.is_set()

    def get_heating_time_collector(self):
        return self._heating_time_collector
