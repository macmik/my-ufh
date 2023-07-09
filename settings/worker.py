import time
import logging
from threading import Lock
from datetime import datetime as DT
from http_client import HttpClient
from worker import Worker
from settings.settings import Settings


logger = logging.getLogger(__name__)


class SettingsUpdaterWorker(Worker):
    def __init__(self, config, stop_event):
        super().__init__(config, stop_event)
        self._lock = Lock()
        self._refresh_interval = self._config['settings']['refresh_interval']
        self._http_client = HttpClient(self._config['settings']['ip'], self._config['settings']['port'])
        self._current_settings = None
        self._last_update_time = None
        self._settings_valid = False

    def _do(self):
        logging.info('Updating settings.')
        t0 = time.time()
        try:
            with self._lock:
                self._current_settings = Settings(self._http_client.get_json('settings.json'))
                self._last_update_time = DT.now()
                self._settings_valid = True
                logger.info('Settings updated correctly.')
        except Exception as e:
            self._settings_valid = False
            logger.debug('Settings update failed!')
            logger.error(str(e))
        finally:
            time.sleep(self._refresh_interval - (time.time() - t0))

    def get_settings(self):
        with self._lock:
            if self._settings_valid:
                return self._current_settings
            return None
