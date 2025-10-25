import time
import logging
from datetime import time as dt_time
from datetime import datetime as DT
from threading import Event

from measurement import get_pre_initialized
from worker import Worker


class ZoneController(Worker):
    def __init__(self, config, stop_event, zone, settings_worker, measurement_collector, slave_interface):
        super().__init__(config, stop_event)
        self._zone = zone
        self._settings_worker = settings_worker
        self._measurement_collector = measurement_collector
        self._slave_interface = slave_interface
        self._should_heat = Event()
        self._should_heat.clear()
        self._heating_started_ts = None
        self._latest_measurement = get_pre_initialized()
        self._required_temperature = None
        self._refresh_interval = self._config['zone_controller']['refresh_interval']
        self._logger = logging.getLogger(self._zone.id)
        self._init()

    def _init(self):
        self._logger.debug(f'Initializing {self._zone.id}.')
        self._slave_interface.disable_loop(self._zone.gpio)

    def is_heating_required(self):
        return self._should_heat.is_set()

    def get_last_measurement(self):
        return self._latest_measurement

    def get_required_temperature(self):
        return self._required_temperature

    def get_zone_name(self):
        return self._zone.name

    def get_heating_started_ts(self):
        return self._heating_started_ts

    def _do(self):
        try:
            self._check()
        except KeyError as e:
            self._logger.error(f'Cant find measurements for zone.')
        finally:
            time.sleep(self._refresh_interval)

    def _check(self):
        settings = self._settings_worker.get_settings()
        if not settings:
            self._logger.debug(f'Settings are empty. Skipping')
            return
        setting = settings.get_setting_by_id(self._zone.id)
        measurement = self._measurement_collector.get_measurements_by_mac(self._zone.mac)
        if measurement.mac != self._zone.mac:
            self._logger.debug(f'Not measurement for zone {self._zone.name}. Waiting.')
            return
        self._check_temperature(measurement, setting)
        self._latest_measurement = measurement

    def _check_temperature(self, measurement, setting):
        now = DT.now().time()

        date_time_range = (
            dt_time(hour=setting.day.hour, minute=setting.day.minute),
            dt_time(hour=setting.night.hour, minute=setting.night.minute),
        )
        if date_time_range[0] <= now < date_time_range[1]:
            temperature_required = setting.day.temperature
            self._logger.debug(f'We are inside day range!')
        else:
            temperature_required = setting.night.temperature
            self._logger.debug('We are inside night range!')
        self._logger.debug(
            f'Temperature required={temperature_required}, temperature_measured={measurement.temperature}.'
        )
        self._check_heating(measurement.temperature, temperature_required)
        self._logger.debug(f'Is heating required = {self._should_heat.is_set()}.')
        self._required_temperature = temperature_required

    def _check_heating(self, current_temperature, temperature_required):
        if current_temperature < temperature_required - self._config['hysteresis']:
            self.enable_heat()
        elif current_temperature >= temperature_required + (self._config['hysteresis'] - 1):
            self.disable_heat()

    def enable_heat(self):
        if not self._should_heat.is_set():
            self._logger.debug(f'{self._zone.name} heating started!')
            self._slave_interface.enable_loop(self._zone.gpio)
            self._heating_started_ts = DT.now()
            self._should_heat.set()

    def disable_heat(self):
        if self._should_heat.is_set():
            self._logger.debug(f'{self._zone.name} heating stopped!')
            self._slave_interface.disable_loop(self._zone.gpio)
            self._should_heat.clear()
