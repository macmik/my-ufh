import logging
import sqlite3
import calendar
from threading import Lock
from datetime import datetime as DT
from datetime import timedelta as TD


logger = logging.getLogger(__name__)

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ00:00'


def convert_timedelta_to_hours(td):
    return td.total_seconds() / 3600


def _get_epoch(ts):
    return calendar.timegm(ts.timetuple())


class DatabaseHandler:
    DB_MEASUREMENTS = 'measurements'
    DB_HEATING = 'boiler_heating_time'
    DB_HEATING_PER_DAY = 'boiler_heating_time_hours_per_day'

    def __init__(self, config):
        self._write_lock = Lock()
        self._config = config
        self._conn = sqlite3.connect(self._config['db_path'], check_same_thread=False)
        self._cur = self._conn.cursor()
        self._initialize_db()

    def _initialize_db(self):
        if self._db_exists():
            logger.info('Database already initialized.')
            return
        logger.info('Initializing database.')
        self._cur.execute(f'CREATE TABLE {self.DB_MEASUREMENTS}(mac, temperature, humidity, battery, timestamp)')
        self._cur.execute(f'CREATE TABLE {self.DB_HEATING}(start_timestamp, end_timestamp)')
        self._cur.execute(f'CREATE TABLE {self.DB_HEATING_PER_DAY}(timestamp, hours)')

    def _db_exists(self):
        result = self._cur.execute('SELECT name FROM sqlite_master')
        return result.fetchone() is not None

    def add_boiler_heating_time_raw(self, start_timestamp, end_timestamp):
        with self._write_lock:
            self._cur.execute(f'INSERT INTO {self.DB_HEATING} VALUES(?, ?)', [
                start_timestamp.strftime(DATETIME_FORMAT),
                end_timestamp.strftime(DATETIME_FORMAT)
            ])
            self._conn.commit()

    def add_boiler_heating_time_hours(self, start_timestamp, end_timestamp):
        if start_timestamp.day == end_timestamp.day:
            timestamp = _get_epoch(start_timestamp.date())
            heating_hours = convert_timedelta_to_hours(end_timestamp - start_timestamp)
            query = f'SELECT timestamp, hours FROM {self.DB_HEATING_PER_DAY} WHERE timestamp={str(timestamp)}'
            self._cur.execute(query)
            result = self._cur.fetchone()
            if not result:
                self._cur.execute(f'INSERT INTO {self.DB_HEATING_PER_DAY} VALUES(?, ?)', [timestamp, heating_hours])
                self._conn.commit()
                logger.debug('Added new heating time hours.')
            else:
                logger.debug('Updating existing time hour row.')
                db_timestamp, db_hours = result
                query = f'UPDATE {self.DB_HEATING_PER_DAY} SET hours = ? WHERE timestamp = ?'
                values = (db_hours + heating_hours, timestamp)
                self._cur.execute(query, values)
                self._conn.commit()
                logger.debug(f'Updated heating time hours for {start_timestamp}.')
        else:
            logger.debug('Splitting date into two.')
            self.add_boiler_heating_time_hours(start_timestamp, DT(
                     year=end_timestamp.year,
                     month=end_timestamp.month,
                     day=end_timestamp.day,
                 ) - TD(minutes=1))

            self.add_boiler_heating_time_hours(
                DT(
                    year=end_timestamp.year,
                    month=end_timestamp.month,
                    day=end_timestamp.day,
                ), end_timestamp)

    def add_measurement(self, measurement):
        with self._write_lock:
            self._cur.execute(f'INSERT INTO {self.DB_MEASUREMENTS} VALUES(?, ?, ?, ?, ?)', [
                measurement.mac,
                measurement.temperature,
                measurement.humidity,
                measurement.battery,
                _get_epoch(measurement.last_updated),
            ])
            self._conn.commit()
