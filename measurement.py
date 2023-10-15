from dataclasses import dataclass
from datetime import datetime as DT


@dataclass(frozen=True)
class Measurement:
    mac: str
    last_updated: DT
    battery: int
    humidity: int
    temperature: float


def get_pre_initialized():
    return Measurement(
        mac='None',
        last_updated=DT.utcnow(),
        battery=-1,
        humidity=-1,
        temperature=-1,
    )
