import logging
from datetime import datetime as DT
from datetime import timedelta as TD
from collections import defaultdict

logger = logging.getLogger(__name__)


def _convert_timedelta_to_hours(td):
    return td.total_seconds() / 3600


class HeatingTimeCollector:
    def __init__(self, config):
        self._config = config
        self._max_days_history = self._config.get('max_days_history_for_heating_time', 30)
        self._heating_minutes_per_day = defaultdict(int)

    def get_heating_minutes_per_day(self):
        return self._heating_minutes_per_day

    def add(self, start_ts, end_ts):
        self._maintain()
        logger.debug(f'Heating time collector: start_ts={start_ts}, end_ts={end_ts}.')
        if start_ts.day == end_ts.day:
            self._heating_minutes_per_day[start_ts.date()] += _convert_timedelta_to_hours(end_ts - start_ts)
            return
        self.add(start_ts,
                 DT(
                     year=end_ts.year,
                     month=end_ts.month,
                     day=end_ts.day,
                 ) - TD(minutes=1))
        self.add(
            DT(
                year=end_ts.year,
                month=end_ts.month,
                day=end_ts.day,
            ), end_ts)

    '''def get_plot(self):
        days = self._heating_minutes_per_day.keys()
        values = self._heating_minutes_per_day.values()
        plt.bar(days, values)
        plt.xlabel('date')
        plt.ylabel('minutes')

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        return buffer'''

    def _maintain(self):
        today = DT.now()
        for date in list(self._heating_minutes_per_day.keys()):
            if (today - DT.combine(date, DT.min.time())).days > self._max_days_history:
                logger.debug(f'Removing date from time collector: {date}.')
                del self._heating_minutes_per_day[date]
