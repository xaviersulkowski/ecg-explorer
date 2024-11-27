from enum import Enum
from typing import Optional

from frontend.observers.observer_abc import Subject
from models.ecg import ECGContainer


class ContainerEvents(Enum):
    CONTAINER_UPDATE = 1


class ContainerManager(Subject):
    """
    ECGPlotHandler & DescriptionFrame should subscribe
    """

    def __init__(self):
        super().__init__()
        self._ecg_container: Optional[ECGContainer] = None

    @property
    def container(self):
        return self._ecg_container

    @container.setter
    def container(self, ecg_container: ECGContainer):
        self._ecg_container = ecg_container
        self.notify_subscribers(
            event=ContainerEvents.CONTAINER_UPDATE, container=self._ecg_container
        )
