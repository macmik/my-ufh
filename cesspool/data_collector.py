import time
import logging
from threading import Lock
from dataclasses import dataclass
from datetime import datetime as DT
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
        self._cesspool_client = HttpClient(
            ip=self._config['cesspool']['ip'],
            port=self._config['cesspool']['port']
        )

    def _do(self):
        with self._lock:
            self._collect_data()
        logger.info('Cesspool data updated.')
        time.sleep(self._refresh_interval)

    def _collect_data(self):
        state = self._cesspool_client.get_json('state')
        with self._lock:
            self._last_data = CesspoolData(
                distance_mm=state['distance_mm'],
                level_percent=state['level_percent'],
                last_updated=DT.strptime(state['timestamp'], '%Y%m%d-%H%M%S') if state['timestamp'] is not None else None
            )

    def get_last_data(self):
        with self._lock:
            return self._last_data
