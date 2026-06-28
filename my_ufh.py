import sys
import json
import logging
from os import environ
from pathlib import Path
from threading import Event

from flask import Flask

from zone.zone import Zone
from zone.controller import ZoneController
from data_agreggator import DataAggregator
from heating.manager import HeatingManager
from settings.worker import SettingsUpdaterWorker
from slave.interface import SlaveInterface
from slave.phoscon_interface import PhosconInterface
from measurement_collector import MeasurementCollector
from heating_supervisor import HeatingSupervisor
from cesspool.data_collector import CesspoolDataCollector
from db.sqlite3_handler import DatabaseHandler
from routes import routes


def setup_logging():
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    log_level = environ.get("LOG_LVL", "dump")
    if log_level == "dump":
        level = logging.DEBUG
    elif log_level == "info":
        level = logging.INFO
    elif log_level == "error":
        level = logging.ERROR
    elif log_level == "warning":
        level = logging.WARNING
    else:
        logging.error('"%s" is not correct log level', log_level)
        sys.exit(1)
    if getattr(setup_logging, "_already_set_up", False):
        logging.warning("Logging already set up")
    else:
        logging.basicConfig(format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", level=level)
        setup_logging._already_set_up = True


def create_app():
    app = Flask(__name__, static_folder='templates')

    setup_logging()
    config = json.loads(Path('config.json').read_text())
    stop_event = Event()

    db_handler = DatabaseHandler(config)
    slave_interfaces = {name: SlaveInterface(name, config) for name in config['slaves'].keys()}
    slave_interfaces.update({
        'phoscon': PhosconInterface('phoscon', config)
    })
    settings_worker = SettingsUpdaterWorker(config, stop_event)
    measurement_collector = MeasurementCollector(config, stop_event, slave_interfaces.values(), db_handler)
    zones = [Zone(**zone_config) for zone_config in config['zones']]
    zone_controllers = [ZoneController(config,
                                       stop_event,
                                       zone,
                                       settings_worker,
                                       measurement_collector,
                                       slave_interfaces[zone.slave]) for zone in zones]
    supervisor = HeatingSupervisor(config, stop_event, zone_controllers, db_handler)
    cesspool_data_collector = CesspoolDataCollector(config, stop_event, db_handler)
    data_aggregator = DataAggregator(config, stop_event, zone_controllers)
    heating_manager = HeatingManager(config, stop_event, data_aggregator, zone_controllers)

    settings_worker.start()
    measurement_collector.start()
    _ = [controller.start() for controller in zone_controllers]
    supervisor.start()
    cesspool_data_collector.start()
    data_aggregator.start()
    heating_manager.start()

    app.my_config = config
    app.zone_controllers = zone_controllers
    app.heating_supervisor = supervisor
    app.settings_worker = settings_worker
    app.measurement_collector = measurement_collector
    app.cesspool_data_collector = cesspool_data_collector
    app.data_aggregator = data_aggregator

    app.register_blueprint(routes)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
