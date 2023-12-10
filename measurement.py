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
        battery=-1,
        humidity=-1,
        temperature=-1,
        presence=None,
        pressure=-1,
    )
