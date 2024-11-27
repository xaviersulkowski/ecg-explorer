from enum import Enum
from typing import Optional

from filters.ecg_signal_filter import FilterConfig
from frontend.observers.observer_abc import Subject


class FilterEvents(Enum):
    FILTER_CONFIG_UPDATE = 1
    DISPLAY_CONFIG_UPDATE = 2


class FilterManager(Subject):
    """
    ECGPlotHandler should subscribe
    """

    def __init__(self):
        super().__init__()
        self._filter_config: Optional[FilterConfig] = None
        self._show_filtered: bool = True

    @property
    def filter_config(self):
        return self._filter_config

    @filter_config.setter
    def filter_config(self, filter_config: FilterConfig):
        self._filter_config = filter_config
        self.notify_subscribers(
            event=FilterEvents.FILTER_CONFIG_UPDATE,
            container=self._filter_config,
        )

    @property
    def show_filtered(self):
        return self._show_filtered

    @show_filtered.setter
    def show_filtered(self, show_filtered: bool):
        self._show_filtered = show_filtered
        self.notify_subscribers(
            event=FilterEvents.DISPLAY_CONFIG_UPDATE,
            show_filtered=show_filtered,
        )
