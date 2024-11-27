import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from scipy import signal

from models.ecg import ECGContainer, ECGLead


class FilterMethods(Enum):
    BANDPASS = "bandpass"
    LOWPASS = "lowpass"

    @staticmethod
    def get_filtering_methods() -> list[str]:
        return [x.value for x in FilterMethods]


@dataclass
class FilterConfig:
    filter_method: FilterMethods
    lowcut_frequency: Optional[float] = None
    highcut_frequency: Optional[float] = None
    filter_order: int = 1.0

    def __post_init__(self):
        if (
            self.filter_method == FilterMethods.LOWPASS
            and self.highcut_frequency is None
        ):
            raise FilterInitError(
                "Lowpass filter requires high cut frequency to be set "
            )
        if self.filter_method == FilterMethods.BANDPASS and (
            self.lowcut_frequency is None or self.highcut_frequency is None
        ):
            raise FilterInitError(
                "Bandpass filter requires both - low and high cut frequencies to be set "
            )

    @classmethod
    def default_bandpass(cls):
        return cls(
            lowcut_frequency=2.0,
            highcut_frequency=15.0,
            filter_order=1,
            filter_method=FilterMethods.BANDPASS,
        )

    @classmethod
    def default_lowpass(cls):
        return cls(
            highcut_frequency=15.0, filter_order=1, filter_method=FilterMethods.LOWPASS
        )


class EcgSignalFilter:
    def __init__(self, config: FilterConfig):
        if config is None:
            raise RuntimeError("Cannot initialize filter with empty config")

        self.filter_config = config

    def filter(self, ecg: ECGContainer):
        logging.info(f"Applying filter {self.filter_config}")
        for lead in ecg.ecg_leads:
            lead.waveform = self._do_filter(lead)
            lead.is_filtered = True

    def _do_filter(self, lead: ECGLead):
        fs = lead.fs
        ecg_signal = lead.raw_waveform

        b, a = self._get_filter_params(fs)
        filtered = signal.lfilter(b, a, ecg_signal)
        filtered[:5] = filtered[5]
        return filtered

    def _get_filter_params(self, fs: float) -> tuple[float, float]:
        nyq = 0.5 * fs
        lowcut = (
            self.filter_config.lowcut_frequency / nyq
            if self.filter_config.lowcut_frequency
            else None
        )
        highcut = (
            self.filter_config.highcut_frequency / nyq
            if self.filter_config.highcut_frequency
            else None
        )
        filter_order = self.filter_config.filter_order

        if self.filter_config.filter_method == FilterMethods.BANDPASS:
            return signal.butter(filter_order, [lowcut, highcut], btype="bandpass")

        if self.filter_config.filter_method == FilterMethods.LOWPASS:
            return signal.butter(filter_order, [highcut], btype="lowpass")

        raise RuntimeError(
            f"Filter method  {self.filter_config.filter_method} not known"
        )


class FilterInitError(Exception):
    def __init__(self, message):
        super().__init__(message)
