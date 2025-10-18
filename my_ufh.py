import measurement
import sys
import json
import logging
from os import environ
from pathlib import Path
from threading import Event

from flask import Flask, render_template, jsonify, redirect, request

from zone.zone import Zone
from zone.controller import ZoneController
from data_agreggator import DataAggregator
from settings.worker import SettingsUpdaterWorker
from slave.interface import SlaveInterface
from slave.phoscon_interface import PhosconInterface
from measurement_collector import MeasurementCollector
from heating_supervisor import HeatingSupervisor
from cesspool.data_collector import CesspoolDataCollector
from db.sqlite3_handler import DatabaseHandler


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

    settings_worker.start()
    measurement_collector.start()
    _ = [controller.start() for controller in zone_controllers]
    supervisor.start()
    cesspool_data_collector.start()
    data_aggregator.start()

    app.my_config = config
    app.zone_controllers = zone_controllers
    app.heating_supervisor = supervisor
    app.settings_worker = settings_worker
    app.measurement_collector = measurement_collector
    app.cesspool_data_collector = cesspool_data_collector
    app.data_aggregator = data_aggregator
    return app


app = create_app()


@app.route('/')
def index():
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
    settings = {
        'heating_enabled': app.heating_supervisor.get_user_heating_enabled(),
        'vacation_enabled': app.settings_worker.get_vacation_enabled(),
    }
    outdoor_data_measurement = app.measurement_collector.get_measurements_by_mac(app.my_config['outdoor_measurement'])
    outdoor_data = {
        'temperature': outdoor_data_measurement.temperature,
        'humidity': outdoor_data_measurement.humidity,
        'pressure': outdoor_data_measurement.pressure,
        'battery': outdoor_data_measurement.battery,
        'last_updated': outdoor_data_measurement.last_updated.strftime('%Y%m%d-%H:%M:%S'),
    }
    cesspool_data_measurement = app.cesspool_data_collector.get_last_data()
    cesspool_data = {
        'distance_mm': cesspool_data_measurement.distance_mm,
        'level_percent': cesspool_data_measurement.level_percent,
        'last_updated': (
            cesspool_data_measurement.last_updated.strftime('%Y%m%d-%H:%M:%S')
            if cesspool_data_measurement.last_updated
            else None
        )
    }

    return render_template('index.html',
                           locations=state,
                           settings=settings,
                           outdoor_data=outdoor_data,
                           cesspool_data=cesspool_data)


@app.route('/heating_data')
def heating_data():
    heating_time_collector = app.heating_supervisor.get_heating_time_collector()
    heating_time_data = heating_time_collector.get_heating_minutes_per_day()
    labels = [day.strftime('%Y-%m-%d') for day in heating_time_data]

    return render_template('heating.html',
                           labels=labels,
                           values=list(heating_time_data.values()))


@app.route('/temp_settings')
def temp_settings():
    return render_template('temp_settings.html')


@app.route("/tank_chart")
def tank_chart():
    tank_data_history = app.cesspool_data_collector.get_history()
    tank_data = [
        (cesspool_data.last_updated.strftime('%Y%m%d-%H:%M:%S'), cesspool_data.distance_mm)
        for cesspool_data in tank_data_history
    ]
    return render_template("tank_chart.html", tank_data=tank_data)


@app.route("/temp_rooms")
def temp_rooms():
    # Przykładowe dane (normalnie wczytywane np. z bazy danych lub pliku)
    # data = {
    #     "Salon": [
    #         ("2025-10-17 10:00", 22.3),
    #         ("2025-10-17 11:00", 22.5),
    #         ("2025-10-17 12:00", 22.8),
    #     ],
    #     "Sypialnia": [
    #         ("2025-10-17 10:00", 21.1),
    #         ("2025-10-17 11:00", 21.3),
    #         ("2025-10-17 12:00", 21.0),
    #     ],
    #     "Kuchnia": [
    #         ("2025-10-17 10:00", 23.0),
    #         ("2025-10-17 11:00", 23.4),
    #         ("2025-10-17 12:00", 23.1),
    #     ],
    # }

    zone_measurements = app.data_aggregator.get_zone_measurements()

    data = {}
    for zone_name, container in zone_measurements.items():
        data[zone_name] = [(measurement.last_updated.strftime('%Y%m%d %H:%M:%S'), measurement.temperature) for measurement in
                           container.get_measurements()]

    return render_template("temp_rooms.html", title="Temperatury pomieszczeń", data=data)


@app.route('/settings.json', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        return Path('data/settings.json').read_text()
    if request.method == 'POST':
        Path('data/settings.json').write_text(json.dumps(request.get_json(), indent=4))
        return 'ok'
    return 404, 'not ok'


@app.route('/enable_heating')
def enable_heating():
    app.heating_supervisor.user_start_heating()
    return redirect('/')


@app.route('/disable_heating')
def disable_heating():
    app.heating_supervisor.user_stop_heating()
    return redirect('/')


@app.route('/set_vacation_settings')
def set_vacation_settings():
    app.settings_worker.set_vacation_settings()
    return redirect('/')


@app.route('/set_standard_settings')
def set_standard_settings():
    app.settings_worker.set_standard_settings()
    return redirect('/')


@app.route('/get_status')
def get_status():
    return jsonify(
        {
            'vacation_mode_enabled': app.settings_worker.get_vacation_enabled(),
            'user_heating_enabled': app.heating_supervisor.get_user_heating_enabled(),
        }
    )


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
