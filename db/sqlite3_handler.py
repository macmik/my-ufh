import logging
import sqlite3
import calendar
from threading import Lock

logger = logging.getLogger(__name__)

#DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ00:00'


class DatabaseHandler:
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
        self._cur.execute('CREATE TABLE measurements(mac, temperature, humidity, battery, timestamp)')
        self._cur.execute('CREATE TABLE boiler_heating_time(start_timestamp, end_timestamp)')

    def _db_exists(self):
        result = self._cur.execute('SELECT name FROM sqlite_master')
        return result.fetchone() is not None

    def add_boiler_heating_time(self, start_timestamp, end_timestamp):
        with self._write_lock:
            self._cur.execute('INSERT INTO boiler_heating_time VALUES(?, ?)', [
                start_timestamp.strftime(DATETIME_FORMAT),
                end_timestamp.strftime(DATETIME_FORMAT)
            ])
            self._conn.commit()

    def add_measurement(self, measurement):
        with self._write_lock:
            self._cur.execute('INSERT INTO measurements VALUES(?, ?, ?, ?, ?)', [
                measurement.mac,
                measurement.temperature,
                measurement.humidity,
                measurement.battery,
                calendar.timegm(measurement.last_updated.timetuple()),
            ])
            self._conn.commit()
