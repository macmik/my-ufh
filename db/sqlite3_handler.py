import logging
import sqlite3

logger = logging.getLogger(__name__)


class DatabaseHandler:
    def __init__(self, config):
        self._config = config
        self._conn = sqlite3.connect(self._config['db_path'])
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
        return result is not None

    def add_boiler_heating_time(self, start_timestamp, end_timestamp):
        self._cur.execute('INSERT INTO boiler_heating_time VALUES(?, ?)', [
            start_timestamp.strftime('%Y%m%d-%H:%M:%S'),
            end_timestamp.strftime('%Y%m%d-%H:%M:%S')
        ])

    def add_measurement(self, measurement):
        self._cur.execute('INSERT INTO measurements VALUES(?, ?, ?, ?, ?)', [
            measurement.mac,
            measurement.temperature,
            measurement.humidity,
            measurement.battery,
            measurement.last_updated.strftime('%Y%m%d-%H:%M:%S')
        ])
