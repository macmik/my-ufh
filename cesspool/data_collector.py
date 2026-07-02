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


def _linear_regression(xs, ys):
    n = len(xs)
    if n < 2:
        return None

    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return None

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


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
        self._history = []
        self._history_keep_time_days = TD(days=self._config['cesspool']['history_keep_time_days'])
        self._history_save_interval_mins = TD(minutes=self._config['cesspool']['history_save_interval_mins'])
        self._refresh_force_after_mins = TD(minutes=self._config['cesspool']['refresh_force_after_mins'])
        self._drop_measurement_diff_mm = self._config['cesspool']['drop_measurement_diff_mm']
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
                last_updated=DT.strptime(state['timestamp'], '%Y%m%d-%H:%M:%S')
            )
            if not cesspool_data.last_updated:
                return

            self._maintain_history()
            self._append_new_measurement(cesspool_data)

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
        if not cesspool_data.last_updated:
            return

        last_element = self._history[-1]

        if cesspool_data.last_updated - last_element.last_updated > self._refresh_force_after_mins:
            logger.debug('Force update cesspool data.')
            self._history.append(cesspool_data)
            return

        if cesspool_data.last_updated - last_element.last_updated > self._history_save_interval_mins:
            distance_diff = last_element.distance_mm - cesspool_data.distance_mm
            time_diff = cesspool_data.last_updated - last_element.last_updated
            if time_diff.days > 1 or distance_diff > self._drop_measurement_diff_mm:
                logger.debug(f'Found strange measurement for cesspool. Last distance {last_element.distance_mm}, '
                             f'current {cesspool_data.distance_mm}. Difference {distance_diff}. Skipping.')
                return
            logger.debug(f'Appending new cesspool data to history, {str(cesspool_data)}.')
            self._history.append(cesspool_data)

    def get_last_data(self):
        with self._lock:
            return self._history[-1] if self._history else CesspoolData(distance_mm=0, level_percent=0,
                                                                        last_updated=None)

    def get_history(self):
        with self._lock:
            return list(self._history)

    def predict_empty_date(self) -> Optional[DT]:
        with self._lock:
            history = list(self._history)

        min_samples = self._config['cesspool']['prediction_min_samples']
        if len(history) < min_samples:
            return None

        empty_at_free_percent = self._config['cesspool']['empty_at_free_percent']
        target_level_percent = 100 - empty_at_free_percent

        timestamps = []
        levels = []
        for measurement in history:
            if not measurement.last_updated:
                continue
            timestamps.append(measurement.last_updated.timestamp())
            levels.append(measurement.level_percent)

        if len(timestamps) < min_samples:
            return None

        regression = _linear_regression(timestamps, levels)
        if regression is None:
            return None

        slope, intercept = regression
        if slope <= 0:
            return None

        predicted_timestamp = (target_level_percent - intercept) / slope
        return DT.fromtimestamp(predicted_timestamp)
