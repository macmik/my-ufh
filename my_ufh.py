import sys
import json
import logging
from os import environ
from pathlib import Path
from threading import Event

from flask import Flask, render_template

from zone.zone import Zone
from zone.controller import ZoneController
from settings.worker import SettingsUpdaterWorker
from slave.interface import SlaveInterface
from measurement_collector import MeasurementCollector
from heating_supervisor import HeatingSupervisor


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

    slave_interfaces = {name: SlaveInterface(name, config) for name in config['slaves'].keys()}
    settings_worker = SettingsUpdaterWorker(config, stop_event)
    measurement_collector = MeasurementCollector(config, stop_event, slave_interfaces.values())
    zones = [Zone(**zone_config) for zone_config in config['zones']]
    zone_controllers = [ZoneController(config,
                                       stop_event,
                                       zone,
                                       settings_worker,
                                       measurement_collector,
                                       slave_interfaces[zone.slave]) for zone in zones]
    supervisor = HeatingSupervisor(config, stop_event, zone_controllers)

    settings_worker.start()
    measurement_collector.start()
    _ = [controller.start() for controller in zone_controllers]
    supervisor.start()

    app.zone_controllers = zone_controllers
    app.heating_supervisor = supervisor
    return app


app = create_app()


@app.route('/table')
def table():
    state = []
    for zone_ctrl in app.zone_controllers:
        try:
            last_measurement = zone_ctrl.get_last_measurement()
            heating_started_ts = zone_ctrl.get_heating_started_ts()
            state.append({
                'name': zone_ctrl.get_zone_name(),
                'temperature': last_measurement.temperature,
                'last_update': last_measurement.last_updated.strftime('%Y%m%d-%H:%M:%S'),
                'required_temperature': zone_ctrl.get_required_temperature(),
                'heating': zone_ctrl.is_heating_required(),
                'heating_started': heating_started_ts.strftime('%Y%m%d-%H:%M:%S') if heating_started_ts else None,
            })
        except Exception as e:
            logging.error(e)

    return render_template('table.html', title='status', locations=state)

@app.route('/enable')
def enable_heating():
    app.heating_supervisor.user_start_heating()
    return 'ok'


@app.route('/disable')
def disable_heating():
    app.heating_supervisor.user_stop_heating()
    return 'ok'


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
