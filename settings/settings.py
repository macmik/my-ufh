from dataclasses import dataclass


@dataclass(frozen=True)
class IntervalSetting:
    temperature: int
    hour: int
    minute: int


@dataclass(frozen=True)
class Setting:
    id: str
    day: IntervalSetting
    night: IntervalSetting


class Settings:
    def __init__(self, json_data):
        self._settings_by_id = {}
        self._init(json_data)

    def _init(self, json_data):
        for id_, data in json_data.items():
            self._settings_by_id[id_] = Setting(
                id=id_,
                day=IntervalSetting(**data['day']),
                night=IntervalSetting(**data['night'])
            )

    def get_setting_by_id(self, id_):
        return self._settings_by_id[id_]
