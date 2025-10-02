import time
import logging
from threading import Lock
from dataclasses import dataclass
from datetime import datetime as DT
from datetime import timedelta as TD
from typing import Optional


from worker import Worker
from http_client import HttpClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CesspoolData:
    distance_mm: int
    level_percent: int
    last_updated: Optional[DT]


class CesspoolDataCollector(Worker):
    def __init__(self, config, stop_event, db_handler):
        super().__init__(config, stop_event)
        self._db_handler = db_handler
        self._lock = Lock()
        self._refresh_interval = self._config['cesspool']['refresh_interval']
        self._last_data = CesspoolData(distance_mm=0, level_percent=0, last_updated=None)
        self._history = []
        self._history_keep_time_days = TD(days=self._config['cesspool']['history_keep_time_days'])
        self._history_save_interval_mins = TD(minutes=self._config['cesspool']['history_save_interval_mins'])
        self._cesspool_client = HttpClient(
            ip=self._config['cesspool']['ip'],
            port=self._config['cesspool']['port']
        )

    def _do(self):
        self._collect_data()
        logger.info('Cesspool data updated.')
        time.sleep(self._refresh_interval)

    def _collect_data(self):
        state = self._cesspool_client.get_json('state')
        with self._lock:
            cesspool_data = CesspoolData(
                distance_mm=state['distance_mm'],
                level_percent=state['level_percent'],
                last_updated=DT.strptime(state['timestamp'], '%Y%m%d-%H:%M:%S') if state['timestamp'] is not None else None
            )

            self._maintain_history()
            self._append_new_measurement(cesspool_data)
            self._last_data = cesspool_data

    def _maintain_history(self):
        filtered = []

        for cesspool_data in self._history:
            if cesspool_data.last_updated and cesspool_data.last_updated - DT.now() > self._history_keep_time_days:
                continue
            filtered.append(cesspool_data)
        self._history = filtered

    def _append_new_measurement(self, cesspool_data):
        if not self._history:
            self._history.append(cesspool_data)
            return
        if not cesspool_data.last_updated or not cesspool_data.last_updated:
            return

        last_element = self._history[-1]

        if cesspool_data.last_updated - last_element.last_updated > self._history_save_interval_mins:
            self._history.append(cesspool_data)

    def get_last_data(self):
        with self._lock:
            return self._last_data

    def get_history(self):
        return self._history