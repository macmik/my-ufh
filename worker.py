import logging
import time
from abc import ABC, abstractmethod
import threading
import traceback

logger = logging.getLogger(__name__)


class Worker(ABC, threading.Thread):
    def __init__(self, config, stop_event):
        super().__init__()
        self._config = config
        self._stop_event = stop_event

    def run(self):
        while not self._stop_event.is_set():
            try:
                self._do()
            except Exception as e:
                traceback.print_exc()
                logging.error(str(e))
                time.sleep(1)

    @abstractmethod
    def _do(self):
        pass
