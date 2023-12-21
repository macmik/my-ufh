from typing import Optional
from dataclasses import dataclass
from datetime import datetime as DT


@dataclass(frozen=True)
class Measurement:
    mac: str
    last_updated: DT
    battery: Optional[int] = None
    humidity: Optional[int] = None
    temperature: Optional[float] = None
    pressure: Optional[int] = None
    presence: Optional[bool] = None


def get_pre_initialized():
    return Measurement(
        mac='None',
        last_updated=DT.utcnow(),
        battery=None,
        humidity=None,
        temperature=None,
        presence=None,
        pressure=None,
    )
