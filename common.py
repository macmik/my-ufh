from functools import cached_property

class RelayType:
    LOW_ENABLED = 'low_enabled'
    HIGH_ENABLED = 'high_enabled'

    def __init__(self, relay_type):
        self._relay_type = relay_type

    @cached_property
    def enable(self):
        return 1 if self._relay_type == self.HIGH_ENABLED else 0

    @cached_property
    def disable(self):
        return int(not self.enable)
