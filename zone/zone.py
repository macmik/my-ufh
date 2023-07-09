from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    mac: str
    gpio: int
    slave: str

