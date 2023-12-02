import pathlib
from datetime import datetime as DT
from datetime import timedelta as TD
from db.handler.sqlite3_handler import DatabaseHandler


def test_db_handler_add_heating_hours():
    db_handler = DatabaseHandler(
        config={'db_path': r'C:\Users\mikku\Documents\projekty\my-ufh-v2\my-ufh\tmp\sample.db'})
    now = DT.now()
    past_hour = now + TD(hours=5)
    db_handler.add_boiler_heating_time_hours(now, past_hour)


if __name__ == '__main__':
    test_db_handler_add_heating_hours()