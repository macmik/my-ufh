import json
import logging
from pathlib import Path

from flask import Blueprint, render_template, jsonify, redirect, request, current_app

routes = Blueprint('routes', __name__)


@routes.route('/')
def index():
    state = []
    for zone_ctrl in current_app.zone_controllers:
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
        'heating_enabled': current_app.heating_supervisor.get_user_heating_enabled(),
        'vacation_enabled': current_app.settings_worker.get_vacation_enabled(),
    }
    outdoor_data_measurement = current_app.measurement_collector.get_measurements_by_mac(
        current_app.my_config['outdoor_measurement']
    )
    outdoor_data = {
        'temperature': outdoor_data_measurement.temperature,
        'humidity': outdoor_data_measurement.humidity,
        'pressure': outdoor_data_measurement.pressure,
        'battery': outdoor_data_measurement.battery,
        'last_updated': outdoor_data_measurement.last_updated.strftime('%Y%m%d-%H:%M:%S'),
    }
    cesspool_data_measurement = current_app.cesspool_data_collector.get_last_data()
    cesspool_data = {
        'distance_mm': cesspool_data_measurement.distance_mm,
        'level_percent': cesspool_data_measurement.level_percent,
        'last_updated': (
            cesspool_data_measurement.last_updated.strftime('%Y%m%d-%H:%M:%S')
            if cesspool_data_measurement.last_updated
            else None
        )
    }

    return render_template(
        'index.html',
        locations=state,
        settings=settings,
        outdoor_data=outdoor_data,
        cesspool_data=cesspool_data,
    )


@routes.route('/heating_data')
def heating_data():
    heating_time_collector = current_app.heating_supervisor.get_heating_time_collector()
    heating_time_data = heating_time_collector.get_heating_minutes_per_day()
    labels = [day.strftime('%Y-%m-%d') for day in heating_time_data]

    return render_template('heating.html', labels=labels, values=list(heating_time_data.values()))


@routes.route('/temp_settings')
def temp_settings():
    return render_template('temp_settings.html')


@routes.route('/tank_chart')
def tank_chart():
    tank_data_history = current_app.cesspool_data_collector.get_history()
    tank_data = [
        (cesspool_data.last_updated.strftime('%Y%m%d-%H:%M:%S'), cesspool_data.distance_mm)
        for cesspool_data in tank_data_history
    ]
    return render_template('tank_chart.html', tank_data=tank_data)


@routes.route('/temp_rooms')
def temp_rooms():
    zone_measurements = current_app.data_aggregator.get_zone_measurements()
    data = {}
    for zone_name, container in zone_measurements.items():
        data[zone_name] = [
            (measurement.last_updated.strftime('%Y%m%d %H:%M:%S'), measurement.temperature)
            for measurement in container.get_measurements()
        ]

    return render_template('temp_rooms.html', title='Temperatury pomieszczeń', data=data)


@routes.route('/settings.json', methods=['GET', 'POST'])
def settings():
    if request.method == 'GET':
        return Path('data/settings.json').read_text()
    if request.method == 'POST':
        Path('data/settings.json').write_text(json.dumps(request.get_json(), indent=4))
        return 'ok'
    return 404, 'not ok'


@routes.route('/enable_heating')
def enable_heating():
    current_app.heating_supervisor.user_start_heating()
    return redirect('/')


@routes.route('/disable_heating')
def disable_heating():
    current_app.heating_supervisor.user_stop_heating()
    return redirect('/')


@routes.route('/set_vacation_settings')
def set_vacation_settings():
    current_app.settings_worker.set_vacation_settings()
    return redirect('/')


@routes.route('/set_standard_settings')
def set_standard_settings():
    current_app.settings_worker.set_standard_settings()
    return redirect('/')


@routes.route('/get_status')
def get_status():
    return jsonify({
        'vacation_mode_enabled': current_app.settings_worker.get_vacation_enabled(),
        'user_heating_enabled': current_app.heating_supervisor.get_user_heating_enabled(),
    })
