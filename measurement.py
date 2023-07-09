from dataclasses import dataclass
from datetime import datetime as DT


@dataclass(frozen=True)
class Measurement:
    mac: str
    last_updated: DT
    battery: int
    humidity: int
    temperature: float
